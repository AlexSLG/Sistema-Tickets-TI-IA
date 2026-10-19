"""Historial de tickets de demostración (~60), para que el panel de métricas tenga datos desde el primer arranque.

- Los textos salen de data/processed/test.csv (tickets reales) y se registran con la IA real: cada uno tiene su `analisis_ia`.
  Seis tickets más usan frases típicas de soluciones_rapidas.json y se cierran con la solución rápida.
- Fechas repartidas en los últimos 30 días. Estados por antigüedad: 60 % Cerrado, 15 % Resuelto, 15 % En progreso, 10 % Abierto.
- Los tiempos de resolución siguen las medias por categoría y prioridad de historial_asignaciones.csv.
- La asignación usa las cargas que habría en cada momento (los tickets abiertos que siguen sin resolver en esa fecha).
- Algunos tickets cuya categoría sugerida difiere de la etiqueta de la fuente se "corrigen" (como haría Soporte); estas correcciones
  se guardan solo en la BD, no en data/correcciones.csv.
"""
import json
import random
from datetime import timedelta

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.sistema import ia
from src.sistema.modelos import (AnalisisIA, Comentario, Correccion, Historial, Tecnico, Ticket, Usuario, ahora)

from src.sistema.config import RAIZ
PROCESSED = RAIZ / "data" / "processed"
N_RAPIDAS = 6
MAX_CORRECCIONES = 5
COMENTARIOS_TECNICO = ["Estoy revisando el caso; te aviso en cuanto tenga novedades.", "Ya identifiqué el origen del problema, estoy aplicando la solución.",
                       "Recibido. Empiezo a trabajar en esto ahora mismo."]
COMENTARIOS_RESOLUCION = ["Apliqué la solución indicada; por favor confirma si el problema quedó resuelto.",
                          "Listo, el servicio quedó funcionando. Avísame si vuelve a fallar."]
COMENTARIOS_USUARIO = ["Confirmado, ya funciona. Gracias.", "Todo en orden, gracias por la ayuda.", "Perfecto, quedó resuelto."]


def _solucion_texto(fila, categoria):
    s = str(fila.get("solucion", "") or "").strip()
    if s:
        return s[:700]
    return f"Se atendió el caso siguiendo el procedimiento estándar de {categoria} y se verificó el funcionamiento con el usuario."


def sembrar_historial(db: Session, n_total=60, verbose=False):
    rng = random.Random(42)
    servicio = ia.servicio()
    ahora_ = ahora()
    tecnicos = db.scalars(select(Tecnico).order_by(Tecnico.id)).all()
    ctx = ia.contexto_tecnicos(db)
    solicitantes = db.scalars(select(Usuario).where(Usuario.rol == "Usuario").order_by(Usuario.correo)).all()

    # --- textos: tickets reales de prueba + frases típicas de soluciones rápidas
    test = pd.read_csv(PROCESSED / "test.csv", keep_default_na=False)
    test = test[test["origen_etiqueta"] != "aumento"]
    n_rapidas = min(N_RAPIDAS, max(0, n_total // 10))
    n_csv = n_total - n_rapidas
    muestra = test.sample(n_csv, random_state=42).to_dict("records")
    soluciones = json.loads((PROCESSED / "soluciones_rapidas.json").read_text(encoding="utf-8"))
    rapidas = [{"titulo": s["frases_ejemplo"][0].capitalize(), "descripcion": s["frases_ejemplo"][0].capitalize(), "impacto": "Bajo", "urgencia": "Media",
                "usuarios_afectados": 1, "categoria": s["categoria"], "prioridad": "Baja", "solucion": "", "rapida": True}
               for s in rng.sample(soluciones, n_rapidas)]
    items = [dict(r, rapida=False) for r in muestra]

    # --- estados por antigüedad y fechas repartidas en 30 días
    n = len(items) + len(rapidas)
    cierre = [("Cerrado", round(0.60 * n)), ("Resuelto", round(0.15 * n)), ("En progreso", round(0.15 * n))]
    estados = [e for e, k in cierre for _ in range(k)]
    estados += ["Abierto"] * (n - len(estados))
    rng.shuffle(items)
    pos_rapidas = set(rng.sample(range(round(0.60 * n)), len(rapidas)))  # las rápidas caen entre los Cerrados
    it_normales, it_rapidas = iter(items), iter(rapidas)
    slots = [next(it_rapidas) if i in pos_rapidas else next(it_normales) for i in range(n)]
    inicio, fin_ventana = ahora_ - timedelta(days=30), ahora_ - timedelta(hours=3)
    segundos = sorted(rng.uniform(0, (fin_ventana - inicio).total_seconds()) for _ in range(n))
    horas = (pd.read_csv(PROCESSED / "historial_asignaciones.csv").groupby(["categoria", "prioridad"])["tiempo_resolucion_h"].mean().to_dict())

    registro = []   # (técnico, instante en que deja de contar como abierto o None)
    creados = []
    correcciones = 0
    for i, (fila, estado) in enumerate(zip(slots, estados)):
        creado = inicio + timedelta(seconds=segundos[i])
        cargas = {t.id: sum(1 for tid, fin in registro if tid == t.id and (fin is None or fin > creado)) for t in tecnicos}
        r = servicio.analizar(fila["titulo"], fila["descripcion"], fila["impacto"], fila["urgencia"], int(fila["usuarios_afectados"]),
                              cargas=cargas, limites=ctx["limites"], aptitudes=ctx["aptitudes"])
        cat, pri = r["clasificacion"]["categoria"], r["prioridad"]["prioridad"]
        rapida = r["solucion_rapida"] if fila["rapida"] else None
        if fila["rapida"] and rapida is None:
            fila["rapida"] = False  # la IA no la reconoció como solución rápida: se trata como un ticket normal
        t = Ticket(codigo=f"TK-{i + 1:04d}", titulo=fila["titulo"][:200], descripcion=fila["descripcion"], impacto=fila["impacto"], urgencia=fila["urgencia"],
                   usuarios_afectados=int(fila["usuarios_afectados"]), solicitante_id=solicitantes[i % len(solicitantes)].id, categoria=cat,
                   prioridad=pri, estado=estado, creado_en=creado, actualizado_en=creado)
        db.add(t)
        db.flush()
        db.add(AnalisisIA(ticket_id=t.id, version_modelos=r["version_modelos"], categoria_sugerida=cat, prob_categoria=r["clasificacion"]["probabilidades"],
                          prioridad_sugerida=pri, prob_prioridad=r["prioridad"]["probabilidades"], tecnicos_sugeridos=r["tecnicos"],
                          solucion_rapida=r["solucion_rapida"], similares=r["similares"], tiempo_ms=r["tiempo_ms"]))
        db.add(Historial(ticket_id=t.id, usuario_id=t.solicitante_id, accion="creado", detalle=f"Clasificado como {cat}, prioridad {pri}", creado_en=creado))

        if fila["rapida"]:  # autoservicio: el usuario resolvió con la solución rápida
            t.estado, t.resuelto_con_solucion_rapida = "Cerrado", True
            t.solucion = f"Solución rápida «{rapida['problema']}»: " + " ".join(f"{k}. {p}" for k, p in enumerate(rapida["pasos"], 1))
            t.resuelto_en = t.cerrado_en = t.actualizado_en = creado + timedelta(minutes=2)
            db.add(Historial(ticket_id=t.id, usuario_id=t.solicitante_id, accion="estado", creado_en=t.cerrado_en,
                             detalle="Cerrado: el usuario resolvió el problema con la solución rápida sugerida por la IA"))
            creados.append(t)
            continue

        elegido = ia.elegir_tecnico(r["tecnicos"])
        tec = next(x for x in tecnicos if x.id == elegido["id_tecnico"])
        t.tecnico_id = tec.id
        db.add(Historial(ticket_id=t.id, accion="asignado", creado_en=creado,
                         detalle=f"Asignado automáticamente a {tec.nombre} ({tec.id})" + (f". {elegido['nota']}" if elegido["nota"] else "")))
        h_res = max(0.5, horas.get((cat, pri), 6.0) * rng.lognormvariate(0, 0.35))
        inicio_trabajo = creado + timedelta(hours=rng.uniform(0.2, 2.0))
        resuelto = min(creado + timedelta(hours=h_res), ahora_ - timedelta(minutes=30))
        if estado in ("En progreso", "Resuelto", "Cerrado"):
            t.actualizado_en = inicio_trabajo
            db.add(Historial(ticket_id=t.id, usuario_id=tec.usuario_id, accion="estado", detalle="En progreso", creado_en=inicio_trabajo))
            db.add(Comentario(ticket_id=t.id, autor_id=tec.usuario_id, texto=rng.choice(COMENTARIOS_TECNICO), creado_en=inicio_trabajo + timedelta(minutes=3)))
        if estado in ("Resuelto", "Cerrado"):
            resuelto = max(resuelto, inicio_trabajo + timedelta(minutes=20))
            t.solucion, t.resuelto_en, t.actualizado_en = _solucion_texto(fila, cat), resuelto, resuelto
            db.add(Historial(ticket_id=t.id, usuario_id=tec.usuario_id, accion="estado", detalle=f"Resuelto: {t.solucion[:120]}", creado_en=resuelto))
            db.add(Comentario(ticket_id=t.id, autor_id=tec.usuario_id, texto=rng.choice(COMENTARIOS_RESOLUCION), creado_en=resuelto + timedelta(minutes=1)))
            # corrección de Soporte cuando la IA se equivocó respecto a la etiqueta de la fuente (algunos casos)
            if correcciones < MAX_CORRECCIONES and fila.get("categoria") and fila["categoria"] != cat and not fila["rapida"]:
                cat_ok = fila["categoria"]
                pri_ok = fila.get("prioridad") or pri
                db.add(Correccion(ticket_id=t.id, usuario_id=tec.usuario_id, categoria_ia=cat, categoria_correcta=cat_ok, prioridad_ia=pri,
                                  prioridad_correcta=pri_ok, version_modelos=r["version_modelos"], creado_en=inicio_trabajo + timedelta(minutes=10)))
                db.add(Historial(ticket_id=t.id, usuario_id=tec.usuario_id, accion="corregido", creado_en=inicio_trabajo + timedelta(minutes=10),
                                 detalle=f"Categoría {cat} → {cat_ok}; prioridad {pri} → {pri_ok}"))
                t.categoria, t.prioridad = cat_ok, pri_ok
                correcciones += 1
        if estado == "Cerrado":
            t.cerrado_en = min(resuelto + timedelta(hours=rng.uniform(0.5, 20)), ahora_ - timedelta(minutes=10))
            t.actualizado_en = t.cerrado_en
            db.add(Historial(ticket_id=t.id, usuario_id=t.solicitante_id, accion="estado", detalle="Cerrado: el solicitante confirmó la solución", creado_en=t.cerrado_en))
            db.add(Comentario(ticket_id=t.id, autor_id=t.solicitante_id, texto=rng.choice(COMENTARIOS_USUARIO), creado_en=t.cerrado_en - timedelta(minutes=1)))
        registro.append((tec.id, t.resuelto_en if estado in ("Resuelto", "Cerrado") else None))
        creados.append(t)
    db.commit()
    if verbose:
        por_estado = pd.Series([t.estado for t in creados]).value_counts().to_dict()
        abiertas = {t.id: sum(1 for x in creados if x.tecnico_id == t.id and x.estado in ("Abierto", "En progreso")) for t in tecnicos}
        print(f"Historial: {len(creados)} tickets {por_estado}; {correcciones} correcciones; cargas abiertas {abiertas}")
