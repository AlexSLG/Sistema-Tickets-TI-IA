"""Lógica de inferencia: carga la versión activa del registro y analiza tickets."""
import json
import threading
import time
from pathlib import Path

import numpy as np
import pandas as pd
import torch

from src.models.comun import CATEGORIAS, PRIORIDADES, PROCESSED, RAIZ, Vocabulario
from src.models.gru_clasificador import predecir
from src.models.mlp_asignacion import MLPAsignacion, aptitudes_matriz, balancear, features_batch, puntuar
from src.models.mlp_prioridad import MLPPrioridad, construir_features, predecir_proba
from src.models.similitud import IndiceTickets, SolucionesRapidas
from src.training import registro
from src.training.entrenar_prioridad import cargar_gru

CARGA_INICIAL = 0.4  # fracción del límite con la que arranca el estado de los técnicos (se puede editar con PUT /api/tecnicos)


class Servicio:
    """Modelos de una versión cargados en memoria + estado de carga de los técnicos."""

    def __init__(self, version=None):
        reg = registro.cargar()
        version = version or reg["activa"]
        if version is None:
            raise RuntimeError("No hay versión activa en models/registry.json. Ejecuta: python -m src.training.entrenar_todo")
        self.version = version
        d = RAIZ / "models" / version
        torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
        self.vocab, self.gru = cargar_gru(d)
        ck = torch.load(d / "mlp_prioridad.pt", map_location="cpu")
        self.mlp_prio = MLPPrioridad(ck["n_entrada"])
        self.mlp_prio.load_state_dict(ck["estado"])
        self.mlp_prio.eval()
        ck = torch.load(d / "mlp_asignacion.pt", map_location="cpu")
        self.mlp_asig = MLPAsignacion(ck["n_entrada"])
        self.mlp_asig.load_state_dict(ck["estado"])
        self.mlp_asig.eval()
        self.tiempos = np.load(d / "tiempos_medios.npy")
        self.tecnicos = pd.read_csv(PROCESSED / "tecnicos.csv")
        self.ids = self.tecnicos["id_tecnico"].tolist()
        self.limites = self.tecnicos["limite_carga"].to_numpy().astype(np.float32)
        self.aptitudes = aptitudes_matriz(self.tecnicos)
        self.indice = IndiceTickets.cargar(d)
        cfg = json.loads((d / "config.json").read_text(encoding="utf-8"))
        soluciones = json.loads((PROCESSED / "soluciones_rapidas.json").read_text(encoding="utf-8"))
        self.rapidas = SolucionesRapidas.cargar(d, soluciones, cfg.get("umbral_solucion_rapida", 0.7))
        self.cargas = {t: int(round(CARGA_INICIAL * lim)) for t, lim in zip(self.ids, self.limites)}
        self.lock = threading.Lock()

    # ------------------------------------------------------------------ estado de técnicos
    def estado_tecnicos(self):
        return [{"id_tecnico": t, "nombre": r.nombre, "area": r.area, "limite_carga": int(r.limite_carga), "carga": self.cargas[t],
                 "aptitudes": {c: int(getattr(r, f"aptitud_{c.lower()}")) for c in CATEGORIAS}}
                for t, r in zip(self.ids, self.tecnicos.itertuples())]

    def fijar_cargas(self, cargas):
        desconocidos = [t for t in cargas if t not in self.cargas]
        if desconocidos:
            raise ValueError(f"Técnicos desconocidos: {desconocidos}")
        if any(v < 0 for v in cargas.values()):
            raise ValueError("Las cargas no pueden ser negativas.")
        with self.lock:
            self.cargas.update({t: int(v) for t, v in cargas.items()})
        return self.estado_tecnicos()

    # ------------------------------------------------------------------ inferencia
    def _embedding(self, texto):
        X, L = self.vocab.matriz([texto])
        logits, emb = predecir(self.gru, X, L)
        return emb.numpy(), torch.softmax(logits, 1).numpy()[0]

    def asignar(self, cat_idx, prio_idx, cargas=None):
        """Puntajes del MLP + reglas de balanceo. Devuelve la lista de técnicos en orden de asignación."""
        cargas = self.cargas if cargas is None else cargas
        car = np.array([[cargas[t] for t in self.ids]], dtype=np.float32)
        X = features_batch(np.array([cat_idx]), np.array([prio_idx]), car, self.limites, self.aptitudes, self.tiempos)
        p = puntuar(self.mlp_asig, X)[0]
        orden, elegido = balancear(p, car[0], self.limites)
        # el técnico más adecuado "en frío" (sin carga): sirve para explicar cuándo el balanceo lo salta
        p0 = puntuar(self.mlp_asig, features_batch(np.array([cat_idx]), np.array([prio_idx]), np.zeros_like(car), self.limites,
                                                   self.aptitudes, self.tiempos))[0]
        ideal = int(np.argmax(p0))
        todos_llenos = bool((car[0] >= self.limites).all())
        e = np.exp(p - p.max())
        adecuacion = e / e.sum()  # softmax entre los técnicos: lectura en % del puntaje
        salida = []
        for pos, i in enumerate(orden):
            sat = bool(car[0, i] >= self.limites[i])
            nota = None
            if i == ideal and sat:
                nota = "Es el más adecuado por aptitud, pero está al límite de carga: la asignación pasa al siguiente."
            elif pos == 0 and todos_llenos:
                nota = "Todos los técnicos están al límite de carga: se elige el de menor ocupación."
            elif pos == 0 and i != ideal:
                nota = "Mejor opción con capacidad disponible."
            salida.append({"id_tecnico": self.ids[i], "nombre": self.tecnicos.iloc[i]["nombre"], "area": self.tecnicos.iloc[i]["area"],
                           "aptitud": int(self.aptitudes[i, cat_idx]), "carga": int(car[0, i]), "limite_carga": int(self.limites[i]),
                           "saturado": sat, "puntaje": float(p[i]), "adecuacion": float(adecuacion[i]), "recomendado": pos == 0, "nota": nota})
        return salida

    def analizar(self, titulo, descripcion, impacto, urgencia, usuarios_afectados):
        t0 = time.perf_counter()
        texto = f"{titulo} . {descripcion}"
        with torch.no_grad():
            emb, p_cat = self._embedding(texto)
            fila = pd.DataFrame([{"impacto": impacto, "urgencia": urgencia, "usuarios_afectados": usuarios_afectados}])
            x = construir_features(fila, emb, cat_probs=p_cat[None, :])
            p_pri = predecir_proba(self.mlp_prio, x)[0]
        cat_idx, pri_idx = int(p_cat.argmax()), int(p_pri.argmax())
        tecnicos = self.asignar(cat_idx, pri_idx)
        rapida = self.rapidas.consultar(emb[0], texto)
        similares = self._similares(emb[0], 5)
        return {
            "clasificacion": {"categoria": CATEGORIAS[cat_idx], "probabilidades": {c: float(p) for c, p in zip(CATEGORIAS, p_cat)}},
            "prioridad": {"prioridad": PRIORIDADES[pri_idx], "probabilidades": {c: float(p) for c, p in zip(PRIORIDADES, p_pri)}},
            "tecnicos": tecnicos, "solucion_rapida": rapida, "similares": similares, "version_modelos": self.version,
            "tiempo_ms": (time.perf_counter() - t0) * 1000,
        }

    def _similares(self, emb, k):
        out = []
        for r in self.indice.buscar(emb, k):
            sol = r.get("solucion")
            out.append({"id": str(r["id"]), "titulo": str(r["titulo"]), "descripcion": str(r["descripcion"])[:400], "categoria": r["categoria"],
                        "prioridad": r["prioridad"], "fuente": r["fuente"], "similitud": r["similitud"],
                        "solucion": sol if isinstance(sol, str) and sol.strip() else None})
        return out

    def similares(self, texto, k=5):
        t0 = time.perf_counter()
        with torch.no_grad():
            emb, _ = self._embedding(texto)
        return {"similares": self._similares(emb[0], k), "tiempo_ms": (time.perf_counter() - t0) * 1000}
