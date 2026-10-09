"""Paso 6 · Datos auxiliares: plantel de técnicos e historial de asignaciones.

Ninguna fuente trae técnicos con aptitudes ni historial de asignación; se derivan con las reglas de
reports/datos_auxiliares.md, calibradas con las distribuciones reales de data/raw/issues.csv:
  · tickets por responsable  -> límite de carga relativo de cada técnico
  · tiempo total por prioridad -> razón de tiempos de resolución entre prioridades y su dispersión
  · reaperturas (wfe_reopened > 0) -> tasa base de reasignación
  · pasos del proceso (processing_steps) -> pasos por ticket
Salida: data/processed/tecnicos.csv, data/processed/historial_asignaciones.csv, reports/datos_auxiliares_resumen.md

Ejecutar:  python -m src.data.auxiliares
"""
import heapq
from pathlib import Path

import numpy as np
import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
PROCESSED = RAIZ / "data" / "processed"
SEMILLA = 42
CATEGORIAS = ["Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"]
UTILIZACION_OBJETIVO = 0.78  # carga media del equipo respecto a la suma de sus límites
RUIDO_ASIGNACION = 0.15      # desviación del ruido en la decisión de asignación (dos técnicos casi iguales)
HORAS_MEDIA_BASE = 8.0       # mediana de resolución (horas laborables) de un ticket de prioridad Media

# (id, nombre, área, aptitudes H,S,R,A,C,Se). Al menos 2 técnicos con aptitud >= 4 por categoría.
PLANTEL = [
    ("T01", "Carolina Méndez", "Infraestructura y hardware", (5, 3, 3, 2, 2, 2)),
    ("T02", "Diego Rojas", "Infraestructura y hardware", (4, 3, 4, 2, 2, 2)),
    ("T03", "Valeria Ortiz", "Aplicaciones", (2, 5, 2, 3, 3, 2)),
    ("T04", "Andrés Salazar", "Aplicaciones", (3, 4, 2, 4, 3, 3)),
    ("T05", "Marcela Vega", "Redes y comunicaciones", (3, 2, 5, 2, 2, 4)),
    ("T06", "Julián Paredes", "Redes y seguridad", (2, 3, 4, 3, 2, 5)),
    ("T07", "Lucía Herrera", "Accesos y correo", (2, 3, 2, 5, 5, 3)),
    ("T08", "Mateo Quispe", "Mesa de ayuda (generalista)", (4, 4, 3, 4, 4, 2)),
]
ORDEN_CAPACIDAD = ["T08", "T07", "T04", "T02", "T03", "T01", "T05", "T06"]  # de mayor a menor capacidad relativa
PRIORIDAD_A_JIRA = {"Baja": ["Low"], "Media": ["Medium"], "Alta": ["High"], "Crítica": ["Highest", "Blocker"]}


def calibracion_issues():
    d = pd.read_csv(RAIZ / "data" / "raw" / "issues.csv", low_memory=False,
                    usecols=["issue_type", "issue_priority", "issue_assignee", "wf_total_time", "wfe_reopened", "processing_steps"])
    d = d[d["issue_type"].isin(["Ticket", "Service", "HD Service", "Task", "Story"])]
    horas = d["wf_total_time"] / 3600
    med_medium = horas[d["issue_priority"] == "Medium"].median()
    razon, sigma = {}, {}
    for p, nombres in PRIORIDAD_A_JIRA.items():
        h = horas[d["issue_priority"].isin(nombres)]
        razon[p] = h.median() / med_medium
        s = np.log(h.quantile(0.75) / max(h.quantile(0.25), 1e-6)) / 1.349
        sigma[p] = float(min(s, 0.9))  # la dispersión real (≈ 1,9) se acota para que el tiempo sea aprendible
    por_resp = d.dropna(subset=["issue_assignee"])["issue_assignee"].value_counts()
    activos = por_resp[por_resp >= 50]
    cuantiles = np.quantile(activos.values, (np.arange(8) + 0.5) / 8)
    capacidad = cuantiles / cuantiles.mean()
    return {
        "razon_tiempo": razon, "sigma": sigma, "capacidad": capacidad,
        "tasa_reapertura": float((d["wfe_reopened"] > 0).mean()),
        "pasos_mediana": float(d["processing_steps"].median()), "pasos_p90": float(d["processing_steps"].quantile(0.9)),
        "n_responsables": int(len(por_resp)), "n_activos": int(len(activos)), "med_medium_h": float(med_medium),
        "tickets_issues": int(len(d)),
    }


def generar_tecnicos(cal):
    cap = dict(zip(ORDEN_CAPACIDAD, cal["capacidad"][::-1]))  # el generalista recibe la capacidad más alta
    filas = []
    for tid, nombre, area, apt in PLANTEL:
        limite = int(np.clip(round(10 * cap[tid]), 6, 14))
        filas.append({"id_tecnico": tid, "nombre": nombre, "area": area, "limite_carga": limite,
                      **{f"aptitud_{c.lower()}": a for c, a in zip(CATEGORIAS, apt)}})
    t = pd.DataFrame(filas)
    for c in CATEGORIAS:  # comprobación del requisito
        assert (t[f"aptitud_{c.lower()}"] >= 4).sum() >= 2, c
    return t


def generar_historial(tickets, tecnicos, cal):
    rng = np.random.default_rng(SEMILLA)
    n = len(tickets)
    ids = tecnicos["id_tecnico"].tolist()
    limite = tecnicos["limite_carga"].to_numpy()
    apt = np.stack([tecnicos[f"aptitud_{c.lower()}"].to_numpy() for c in CATEGORIAS], axis=1)  # (técnicos, categorías)
    cat_idx = {c: i for i, c in enumerate(CATEGORIAS)}

    mediana = {p: HORAS_MEDIA_BASE * cal["razon_tiempo"][p] for p in cal["razon_tiempo"]}
    sigma = cal["sigma"]
    # tasa de llegadas (por hora laborable) que da la utilización objetivo
    media_t = np.mean([mediana[p] * np.exp(sigma[p] ** 2 / 2) for p in tickets["prioridad"]])
    lam = UTILIZACION_OBJETIVO * limite.sum() / media_t

    orden = rng.permutation(n)  # llegada aleatoria: los tickets de train, val y test se intercalan en el tiempo
    t_llegada = np.cumsum(rng.exponential(1 / lam, n))
    inicio = pd.Timestamp("2026-03-02 09:00")

    def a_fecha(h):  # horas laborables (8 por día, lunes a viernes) -> fecha y hora
        dias, resto = divmod(h, 8.0)
        semanas, dia_sem = divmod(int(dias), 5)
        return inicio + pd.Timedelta(days=7 * semanas + dia_sem, hours=float(resto))

    abiertos = [[] for _ in ids]  # montones de instantes de cierre
    filas = []
    for k, i in enumerate(orden):
        r = tickets.iloc[i]
        t = t_llegada[k]
        for h in abiertos:
            while h and h[0] <= t:
                heapq.heappop(h)
        carga = np.array([len(h) for h in abiertos])
        c = cat_idx[r["categoria"]]
        ocupacion = carga / limite
        puntaje = apt[:, c] - 1.6 * ocupacion + rng.normal(0, RUIDO_ASIGNACION, len(ids))
        libres = np.where(carga < limite)[0]
        if len(libres):
            elegido = libres[np.argmax(puntaje[libres])]
        else:  # todos al límite: el de menor ocupación
            elegido = int(np.argmin(ocupacion))
        inicial = elegido
        # reasignación: tasa base de reaperturas de issues.csv, mayor si el técnico no es apto o el ticket es crítico
        p_re = cal["tasa_reapertura"] * (1.8 if apt[elegido, c] <= 2 else 1.0) * (1.5 if r["prioridad"] == "Crítica" else 1.0)
        reasignado = rng.random() < p_re
        if reasignado:
            alternativos = [j for j in np.argsort(-puntaje) if j != elegido and carga[j] < limite[j]]
            if alternativos:
                elegido = alternativos[0]
            else:
                reasignado = False
        # tiempo de resolución: lognormal por prioridad, más lento con aptitud baja y con la carga; más largo si se reasignó
        f_apt = 1.0 + 0.25 * (3 - apt[elegido, c]) / 2
        f_carga = 1.0 + 0.3 * ocupacion[elegido]
        horas = rng.lognormal(np.log(mediana[r["prioridad"]]), sigma[r["prioridad"]]) * f_apt * f_carga * (1.5 if reasignado else 1.0)
        horas = float(np.clip(horas, 0.25, 160))
        heapq.heappush(abiertos[elegido], t + horas)
        pasos = int(1 + rng.poisson(max(cal["pasos_mediana"] - 1, 0.5) + (0.5 if r["prioridad"] in ("Alta", "Crítica") else 0)) + (1 if reasignado else 0))
        fila = {"id_ticket": r["id"], "subconjunto": r["subconjunto"], "categoria": r["categoria"], "prioridad": r["prioridad"],
                "fecha_creacion": a_fecha(t).strftime("%Y-%m-%d %H:%M"), "tecnico_inicial": ids[inicial], "tecnico": ids[elegido],
                "reasignado": int(reasignado), "aptitud_tecnico": int(apt[elegido, c]), "carga_tecnico": int(carga[elegido]),
                "limite_tecnico": int(limite[elegido]), "saturado": int(carga[elegido] >= limite[elegido]),
                "tiempo_resolucion_h": round(horas, 2), "pasos_proceso": pasos,
                "fecha_cierre": a_fecha(t + horas).strftime("%Y-%m-%d %H:%M")}
        fila.update({f"carga_{ids[j]}": int(carga[j]) for j in range(len(ids))})
        filas.append(fila)
    h = pd.DataFrame(filas)
    # exactitud de la regla sin ruido (techo para el modelo de asignación)
    return h, lam


def main():
    cal = calibracion_issues()
    tecnicos = generar_tecnicos(cal)
    partes = []
    for s in ("train", "val", "test"):
        p = pd.read_csv(PROCESSED / f"{s}.csv", keep_default_na=False, usecols=["id", "categoria", "prioridad"])
        p["subconjunto"] = s
        partes.append(p)
    tickets = pd.concat(partes, ignore_index=True)
    historial, lam = generar_historial(tickets, tecnicos, cal)
    tecnicos.to_csv(PROCESSED / "tecnicos.csv", index=False, encoding="utf-8")
    historial.to_csv(PROCESSED / "historial_asignaciones.csv", index=False, encoding="utf-8")

    # techo de la regla: ¿coincide el técnico real con el mejor puntaje determinista (aptitud y ocupación) entre los libres?
    ids = tecnicos["id_tecnico"].tolist()
    lim = tecnicos["limite_carga"].to_numpy()
    apt = {c: tecnicos[f"aptitud_{c.lower()}"].to_numpy() for c in CATEGORIAS}
    aciertos = 0
    for r in historial.itertuples():
        carga = np.array([getattr(r, f"carga_{i}") for i in ids])
        libres = np.where(carga < lim)[0]
        sc = apt[r.categoria] - 1.6 * carga / lim
        esperado = libres[np.argmax(sc[libres])] if len(libres) else int(np.argmin(carga / lim))
        aciertos += ids[esperado] == r.tecnico_inicial
    techo = aciertos / len(historial)

    md = ["# Datos auxiliares: resumen (paso 6)", "",
          "Plantel, historial y soluciones rápidas se derivan con las reglas de `reports/datos_auxiliares.md`.", "",
          "## Calibración con `issues.csv`", "",
          f"- {cal['tickets_issues']} tickets de tipos Ticket/Service/HD Service/Task/Story; {cal['n_responsables']} responsables, {cal['n_activos']} con ≥ 50 tickets.",
          f"- Mediana de tiempo total de los de prioridad Medium: {cal['med_medium_h']:.0f} h.",
          "- Razón del tiempo mediano frente a Medium: " + ", ".join(f"{p} {v:.2f}" for p, v in cal["razon_tiempo"].items())
          + "; dispersión (σ del log, acotada a 0,9): " + ", ".join(f"{p} {v:.2f}" for p, v in cal["sigma"].items()) + ".",
          f"- Tasa de reaperturas: {cal['tasa_reapertura']:.1%}. Pasos del proceso: mediana {cal['pasos_mediana']:.0f}, p90 {cal['pasos_p90']:.0f}.", "",
          "## Técnicos", "", tecnicos.to_markdown(index=False), "",
          "## Historial", "",
          f"- {len(historial)} asignaciones (todos los tickets: train, val y test), de {historial['fecha_creacion'].min()} a {historial['fecha_cierre'].max()}; "
          f"{lam:.2f} tickets por hora laborable.",
          f"- Carga media al asignar: {(historial['carga_tecnico'] / historial['limite_tecnico']).mean():.2f} del límite; "
          f"asignaciones con el técnico saturado: {historial['saturado'].mean():.1%}; reasignaciones: {historial['reasignado'].mean():.1%}.",
          f"- Aptitud del técnico asignado: " + ", ".join(f"{k}: {v:.1%}" for k, v in historial['aptitud_tecnico'].value_counts(normalize=True).sort_index().items()) + ".",
          f"- Tiempo de resolución (h laborables): mediana {historial['tiempo_resolucion_h'].median():.1f}, p90 {historial['tiempo_resolucion_h'].quantile(.9):.1f}.", "",
          "Tickets por técnico y categoría:", "", pd.crosstab(historial["tecnico"], historial["categoria"], margins=True).to_markdown(), "",
          "Tiempo medio de resolución por prioridad (h):", "", historial.groupby("prioridad")["tiempo_resolucion_h"].agg(["mean", "median"]).reindex(["Baja", "Media", "Alta", "Crítica"]).round(1).to_markdown(), "",
          f"**Techo de la regla:** la asignación inicial coincide con el mejor puntaje determinista (aptitud y ocupación entre los técnicos libres) en el {techo:.1%} de los casos; "
          "el resto es el ruido de la decisión, que ningún modelo puede recuperar. El criterio del paso 7 (≥ 80 % de técnico esperado en primer lugar) debe medirse contra la **asignación inicial** (`tecnico_inicial`).", ""]
    (RAIZ / "reports" / "datos_auxiliares_resumen.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md[:60]))


if __name__ == "__main__":
    main()
