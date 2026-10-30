"""Historial de tickets de demostración (~60), para que el panel de métricas tenga datos desde el primer arranque.

- Los textos salen de data/processed/test.csv (tickets reales) y se registran con la IA real: cada uno tiene su `analisis_ia`.
  Seis tickets más usan frases típicas de soluciones_rapidas.json y se cierran con la solución rápida.
- Fechas repartidas en los últimos 30 días. Estados por antigüedad: 60 % Cerrado, 15 % Resuelto, 15 % En progreso, 10 % Abierto.
- Los tiempos de resolución siguen las medias por categoría y prioridad de historial_asignaciones.csv.
- La asignación usa las cargas que habría en cada momento (los tickets abiertos que siguen sin resolver en esa fecha).
- Algunos tickets cuya categoría sugerida difiere de la etiqueta de la fuente se "corrigen" (como haría Soporte); estas correcciones
  se guardan solo en la BD, no en data/correcciones.csv.
- Algunos tickets se reabren (el solicitante indica que el problema sigue): dos Cerrados que se resolvieron en un segundo intento y
  uno que volvió a En progreso.
- Un técnico guarda un ticket Cerrado como solución rápida (HU26). Se agrega al catálogo solo si no existe ya (la semilla se puede
  repetir sin duplicarla).
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
COMENTARIOS_REAPERTURA = ["Sigue pasando lo mismo, el problema volvió a aparecer.", "Lo probé otra vez y sigue sin funcionar."]
N_REABIERTOS_CERRADOS, N_REABIERTOS_EN_PROGRESO = 2, 1
# Lo que el técnico escribe en el formulario «Guardar como solución rápida» para el ticket de la unidad compartida
SOLUCION_SOPORTE = {"clave": "unidad compartida", "problema": "No puedo conectarme a la unidad compartida de red",
                    "frases_ejemplo": ["no puedo entrar a la unidad compartida", "la carpeta compartida no abre",
                                       "me sale acceso denegado en la unidad de red", "desapareció la unidad compartida del explorador"],
                    "pasos": ["Comprueba que estás conectado a la red de la oficina o a la VPN.",
                              "Abre el Explorador de archivos, clic derecho sobre la unidad y elige «Desconectar»; luego vuelve a iniciar sesión en el equipo.",
                              "Si aparece «acceso denegado», cierra sesión y vuelve a entrar para renovar tus permisos.",
                              "Si sigue sin abrir, registra un ticket indicando el nombre de la carpeta y el mensaje de error que aparece."]}
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
    from src.models import catalogo_soluciones
    soluciones = [x for x in catalogo_soluciones.leer() if x.get("origen") != "ticket"]  # solo las del catálogo original: muestra estable
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
    meta = {}       # ticket → (técnico, inicio del trabajo)
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
        meta[t.id] = (tec, inicio_trabajo)
        creados.append(t)
    reabiertos = _reabrir_algunos(db, rng, creados, meta, ahora_)
    db.commit()
    solucion = _guardar_solucion_rapida(db, creados, meta)
    if verbose:
        por_estado = pd.Series([t.estado for t in creados]).value_counts().to_dict()
        abiertas = {t.id: sum(1 for x in creados if x.tecnico_id == t.id and x.estado in ("Abierto", "En progreso")) for t in tecnicos}
        print(f"Historial: {len(creados)} tickets {por_estado}; {correcciones} correcciones; {reabiertos} reabiertos; "
              f"solución rápida de Soporte: {solucion or '—'}; cargas abiertas {abiertas}")


def _reabrir_algunos(db: Session, rng, creados, meta, ahora_):
    """Reaperturas: el solicitante indica que el problema sigue. Cerrados: se resolvieron en un segundo intento. En progreso: el
    técnico lo había resuelto y está trabajando de nuevo en él."""
    n = 0
    cerrados = [t for t in creados if t.estado == "Cerrado" and not t.resuelto_con_solucion_rapida]
    en_progreso = [t for t in creados if t.estado == "En progreso" and meta[t.id][1] < ahora_ - timedelta(hours=3)]
    for t in rng.sample(cerrados, min(N_REABIERTOS_CERRADOS, len(cerrados))):
        tec, _ = meta[t.id]
        primer = t.resuelto_en
        reapertura = primer + (t.cerrado_en - primer) / 3
        segundo = primer + 2 * (t.cerrado_en - primer) / 3
        _anotar_reapertura(db, rng, t, tec, reapertura)
        db.add(Historial(ticket_id=t.id, usuario_id=tec.usuario_id, accion="estado", creado_en=segundo,
                         detalle="Resuelto: se repitió el procedimiento y se verificó con el usuario que el problema no vuelve a aparecer"))
        db.add(Comentario(ticket_id=t.id, autor_id=tec.usuario_id, texto="Lo revisé de nuevo y apliqué la corrección completa; por favor confirma.",
                          creado_en=segundo + timedelta(minutes=1)))
        t.resuelto_en = segundo
        n += 1
    for t in rng.sample(en_progreso, min(N_REABIERTOS_EN_PROGRESO, len(en_progreso))):
        tec, inicio = meta[t.id]
        resuelto = inicio + (ahora_ - inicio) / 3
        db.add(Historial(ticket_id=t.id, usuario_id=tec.usuario_id, accion="estado", creado_en=resuelto,
                         detalle=f"Resuelto: {_solucion_texto({}, t.categoria)[:120]}"))
        _anotar_reapertura(db, rng, t, tec, inicio + 2 * (ahora_ - inicio) / 3)
        n += 1
    return n


def _anotar_reapertura(db, rng, t, tec, cuando):
    db.add(Comentario(ticket_id=t.id, autor_id=t.solicitante_id, texto=rng.choice(COMENTARIOS_REAPERTURA), creado_en=cuando - timedelta(minutes=1)))
    db.add(Historial(ticket_id=t.id, usuario_id=t.solicitante_id, accion="estado", detalle="Reabierto por el solicitante: el problema persiste",
                     creado_en=cuando))
    t.actualizado_en = max(t.actualizado_en, cuando)


def _guardar_solucion_rapida(db: Session, creados, meta):
    """Un técnico guarda un ticket Cerrado como solución rápida (como lo haría desde el detalle del ticket)."""
    from src.models import catalogo_soluciones as catalogo
    cerrados = [t for t in creados if t.estado == "Cerrado" and not t.resuelto_con_solucion_rapida and t.solucion]
    candidatos = [t for t in cerrados if SOLUCION_SOPORTE["clave"] in t.titulo.lower()] or cerrados
    if not candidatos:
        return None
    t = min(candidatos, key=lambda x: x.codigo)
    tec, _ = meta[t.id]
    soluciones = catalogo.leer()
    redactada = SOLUCION_SOPORTE["clave"] in t.titulo.lower()
    problema = SOLUCION_SOPORTE["problema"] if redactada else t.titulo
    existente = next((s for s in soluciones if s.get("origen") == "ticket" and s.get("problema") == problema), None)
    if existente is None:
        if redactada:
            frases, pasos = [t.titulo] + SOLUCION_SOPORTE["frases_ejemplo"], SOLUCION_SOPORTE["pasos"]
        else:
            frases, pasos = [t.titulo], [t.solucion[:500]]
        existente = {"id": catalogo.siguiente_id(soluciones), "categoria": t.categoria, "problema": problema, "frases_ejemplo": frases,
                     "pasos": pasos, "activa": True,
                     "origen": "ticket", "ticket_origen": t.codigo, "creada_por": tec.nombre,
                     "fecha": (t.cerrado_en + timedelta(minutes=5)).strftime("%Y-%m-%d %H:%M")}
        catalogo.guardar(soluciones + [existente])
        try:
            ia.servicio().recargar_soluciones()
        except Exception:
            pass  # el servicio lo indexará al iniciar
    db.add(Historial(ticket_id=t.id, usuario_id=tec.usuario_id, accion="solución rápida", creado_en=t.cerrado_en + timedelta(minutes=5),
                     detalle=f"Guardado como {existente['id']}: {existente['problema']}"))
    db.commit()
    return existente["id"]
