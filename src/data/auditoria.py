"""Auditoría manual de etiquetas (paso 4b).

La muestra (200 tickets reales, estratificada por categoría, semilla 42) se revisó a mano leyendo título y descripción:
`VEREDICTO_CAT` y `VEREDICTO_PRI` listan SOLO los tickets donde la etiqueta original era incorrecta y la que correspondía
(la de la primera auditoría, con las reglas anteriores). El resto de la muestra se consideró correcto.
FUERA_TI = el ticket no debía estar en el conjunto (tema comercial o administrativo).

Uso:
    python -m src.data.auditoria muestra   # genera data/interim/auditoria_muestra.csv
    python -m src.data.auditoria medir     # compara tickets.csv actual con los veredictos
"""
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
CATEGORIAS_N = {"Accesos": 34, "Correo": 33, "Hardware": 33, "Red": 34, "Seguridad": 33, "Software": 33}

# n (posición en la muestra, 1-200) -> categoría correcta
VEREDICTO_CAT = {
    3: "Software", 4: "Software", 6: "Seguridad", 7: "Software", 9: "FUERA_TI", 12: "Red", 17: "Software",
    18: "FUERA_TI", 28: "Software", 29: "Software", 33: "Software", 34: "Software", 44: "FUERA_TI", 48: "Seguridad",
    51: "FUERA_TI", 60: "Software", 61: "FUERA_TI", 63: "Software", 64: "Software", 65: "Software", 72: "Software",
    95: "Seguridad", 96: "Seguridad", 105: "Software", 115: "Software", 116: "Software", 117: "Software",
    118: "Software", 121: "FUERA_TI", 122: "FUERA_TI", 130: "FUERA_TI", 138: "Hardware", 149: "Software",
    150: "Software", 152: "Hardware", 156: "FUERA_TI", 170: "Software", 172: "FUERA_TI", 174: "Software",
    181: "Software", 185: "Accesos", 197: "Software",
}
# n -> prioridad correcta
VEREDICTO_PRI = {
    7: "Media", 9: "Baja", 13: "Alta", 17: "Media", 28: "Baja", 35: "Alta", 42: "Media", 43: "Media", 44: "Media",
    48: "Alta", 49: "Alta", 59: "Media", 61: "Baja", 62: "Media", 70: "Baja", 73: "Alta", 85: "Media", 87: "Alta",
    96: "Baja", 97: "Baja", 103: "Alta", 104: "Alta", 106: "Alta", 113: "Media", 119: "Alta", 122: "Baja",
    130: "Baja", 134: "Baja", 150: "Media", 153: "Alta", 156: "Baja", 157: "Media", 159: "Media", 170: "Media",
    172: "Baja", 174: "Media", 175: "Alta", 179: "Baja", 183: "Baja", 194: "Baja",
}
# Segunda muestra, independiente de la primera (60 tickets, 10 por categoría, semilla 7, sin repetir ids de la primera)
VEREDICTO2_CAT = {4: "FUERA_TI", 11: "Software", 14: "Software", 22: "Software", 25: "Software", 35: "Software", 37: "Seguridad",
                  39: "Software", 48: "FUERA_TI", 49: "FUERA_TI", 50: "FUERA_TI", 54: "Software"}
VEREDICTO2_PRI = {3: "Baja", 4: "Baja", 9: "Media", 19: "Media", 22: "Media", 27: "Baja", 41: "Alta", 44: "Alta", 48: "Baja",
                  49: "Baja", 50: "Baja", 54: "Media"}
# Tercera muestra (60 tickets, semilla 99), revisada DESPUÉS de fijar las reglas finales y sin retocarlas: estimación sin sesgo
VEREDICTO3_CAT = {17: "Software", 19: "Software", 23: "Hardware", 28: "Software", 30: "Software", 45: "Accesos",
                  49: "FUERA_TI", 56: "Software", 58: "Hardware"}
VEREDICTO3_PRI = {9: "Baja", 49: "Baja", 50: "Media", 56: "Media"}
ORDEN = ["Baja", "Media", "Alta", "Crítica"]


def muestra(t=None):
    t = t if t is not None else pd.read_csv(RAIZ / "data" / "processed" / "tickets.csv", keep_default_na=False)
    t = t[t["origen_etiqueta"] != "aumento"]
    m = pd.concat([t[t["categoria"] == c].sample(k, random_state=42) for c, k in CATEGORIAS_N.items()])
    m = m.sample(frac=1, random_state=42).reset_index(drop=True)
    m.insert(0, "n", range(1, len(m) + 1))
    return m


def medir(archivo="auditoria_muestra.csv", vcat=None, vpri=None):
    """Compara los tickets actuales con los veredictos. Un ticket cuya etiqueta cambió se evalúa contra la
    etiqueta correcta del veredicto; uno que no tenía error se considera acertado si no cambió de etiqueta."""
    vcat = VEREDICTO_CAT if vcat is None else vcat
    vpri = VEREDICTO_PRI if vpri is None else vpri
    base = pd.read_csv(RAIZ / "data" / "interim" / archivo, keep_default_na=False)
    act = pd.read_csv(RAIZ / "data" / "processed" / "tickets.csv", keep_default_na=False).set_index("id")
    ok_cat = ok_pri = 0
    detalle = []
    for r in base.itertuples():
        if r.id not in act.index:
            ok_cat += vcat.get(r.n) == "FUERA_TI"  # fue descartado
            ok_pri += vcat.get(r.n) == "FUERA_TI"
            detalle.append((r.n, "descartado", "descartado"))
            continue
        a = act.loc[r.id]
        correcta_cat = vcat.get(r.n, r.categoria)
        correcta_pri = vpri.get(r.n, r.prioridad)
        c_ok = a["categoria"] == correcta_cat
        p_ok = a["prioridad"] == correcta_pri
        ok_cat += c_ok
        ok_pri += p_ok
        detalle.append((r.n, c_ok, p_ok))
    n = len(base)
    return ok_cat / n, ok_pri / n, detalle


if __name__ == "__main__":
    if sys.argv[1:] == ["muestra"]:
        m = muestra()
        m.to_csv(RAIZ / "data" / "interim" / "auditoria_muestra.csv", index=False, encoding="utf-8")
        print(len(m))
    else:
        c, p, d = medir()
        c2, p2, d2 = medir("auditoria_muestra2.csv", VEREDICTO2_CAT, VEREDICTO2_PRI)
        print(f"muestra 1 (n=200): categoría {c:.1%} · prioridad {p:.1%}")
        print(f"muestra 2 (n=60):  categoría {c2:.1%} · prioridad {p2:.1%}")
        c3, p3, d3 = medir("auditoria_muestra3.csv", VEREDICTO3_CAT, VEREDICTO3_PRI)
        print(f"muestra 3 (n=60):  categoría {c3:.1%} · prioridad {p3:.1%}")
