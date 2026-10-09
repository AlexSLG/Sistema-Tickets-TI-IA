"""Paso 3a · Filtrado de colas y muestreo previo a la traducción.

Salida en data/interim/: multilang_filtrado.csv, dataset_ticket_filtrado.csv,
tech_support_filtrado.csv y reports/filtrado_resumen.md.
La categoría de este script (`cat_aprox`) solo sirve para repartir la muestra por cuotas;
el etiquetado definitivo se hace en el paso 4 sobre el texto en español.

Ejecutar:  python -m src.data.filtrar
"""
import re
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "data" / "raw"
INTERIM = RAIZ / "data" / "interim"
SEMILLA = 42
CUOTA_POR_CATEGORIA = 1600
MIN_PALABRAS = 5

COLAS_TI = {"Technical Support", "IT Support", "Product Support", "Service Outages and Maintenance"}
ETIQUETAS_TI_CS = {"login", "account", "network", "security", "hardware"}  # sin "it": está en casi todas las filas
ETIQUETAS_NO_TI = {"billing", "payment", "refund", "sales", "marketing", "campaign", "lead", "strategy",
                   "healthcare", "feedback loop", "finance", "invoice"}

# Reglas de categoría aproximada (etiquetas en inglés + palabras clave en inglés y alemán)
REGLAS = [
    ("Seguridad", {"security", "virus", "data breach", "malware", "data protection", "ransomware", "phishing"},
     r"phishing|malware|virus|ransomware|breach|hack|sicherheitsvorfall|datenpanne|cyber"),
    ("Accesos", {"login", "account", "password", "authentication", "access"},
     r"password|passwort|login|log in|anmeld|locked|gesperrt|permission|berechtigung|zugriff|access denied|credentials"),
    ("Correo", {"email", "mail", "outlook"}, r"e-?mail|outlook|mailbox|postfach|exchange|smtp"),
    ("Red", {"network", "vpn", "wifi", "dns"}, r"network|netzwerk|vpn|wi-?fi|wlan|internet|router|dns|firewall|bandwidth"),
    ("Hardware", {"hardware", "printer"}, r"printer|drucker|laptop|disk|festplatte|monitor|bildschirm|keyboard|tastatur|"
                                         r"server room|serverraum|projector|projektor|hardware|battery|akku|fan|l[uü]fter|scanner"),
]


def categoria_aprox(etiquetas, texto):
    t = texto.lower()
    for cat, tags, patron in REGLAS:
        if etiquetas & tags or re.search(patron, t):
            return cat
    return "Software"


def limpiar_texto(s):
    """Normaliza saltos de línea escapados y etiquetas HTML sencillas."""
    if not isinstance(s, str):
        return ""
    s = s.replace("\\n", "\n").replace("\\r", "")
    s = re.sub(r"<br\s*/?>", "\n", s, flags=re.I)
    return re.sub(r"[ \t]+", " ", s).strip()


def filtrar_multilang():
    d = pd.read_csv(RAW / "aa_dataset-tickets-multi-lang-5-2-50-version.csv")
    n0 = len(d)
    tag_cols = [f"tag_{i}" for i in range(1, 9)]
    d["etiquetas"] = d[tag_cols].apply(lambda f: {str(v).lower() for v in f if isinstance(v, str)}, axis=1)
    d["id_fuente"] = d.index
    pasos = [("Filas originales", n0)]

    cs = d["queue"] == "Customer Service"
    ok = d["queue"].isin(COLAS_TI) | (cs & d["etiquetas"].map(lambda e: bool(e & ETIQUETAS_TI_CS)))
    d = d[ok]
    pasos.append(("Colas de TI (+ Customer Service con etiqueta específica)", len(d)))
    d = d[~d["etiquetas"].map(lambda e: bool(e & ETIQUETAS_NO_TI))]
    pasos.append(("Sin etiquetas comerciales (billing, payment, sales, marketing…)", len(d)))

    for c in ("subject", "body", "answer"):
        d[c] = d[c].map(limpiar_texto)
    d = d[d["body"].str.split().str.len() >= MIN_PALABRAS]
    pasos.append((f"Cuerpo con ≥ {MIN_PALABRAS} palabras", len(d)))
    d = d.drop_duplicates(subset="body")
    pasos.append(("Sin cuerpos duplicados", len(d)))

    d["cat_aprox"] = [categoria_aprox(e, f"{s} {b}") for e, s, b in zip(d["etiquetas"], d["subject"], d["body"])]
    antes = d["cat_aprox"].value_counts().to_dict()
    # muestreo por cuotas, equilibrado entre idiomas dentro de cada categoría
    partes = []
    for cat, g in d.groupby("cat_aprox"):
        if len(g) <= CUOTA_POR_CATEGORIA:
            partes.append(g)
        else:
            mitad = CUOTA_POR_CATEGORIA // 2
            sub = [x.sample(min(len(x), mitad), random_state=SEMILLA) for _, x in g.groupby("language")]
            partes.append(pd.concat(sub))
    d = pd.concat(partes).sample(frac=1, random_state=SEMILLA)
    pasos.append((f"Muestra por cuotas (≤ {CUOTA_POR_CATEGORIA} por categoría)", len(d)))

    d["etiquetas"] = d["etiquetas"].map(lambda e: "|".join(sorted(e)))
    d = d.rename(columns={"language": "idioma"})
    d["fuente"] = "multilang"
    cols = ["fuente", "id_fuente", "idioma", "queue", "type", "priority", "etiquetas", "cat_aprox", "subject", "body", "answer"]
    d[cols].to_csv(INTERIM / "multilang_filtrado.csv", index=False, encoding="utf-8")
    return pasos, antes, d["cat_aprox"].value_counts().to_dict(), d["idioma"].value_counts().to_dict()


def idioma_xlsx(texto):
    p = set(re.findall(r"[a-zàèéìòù']+", texto.lower().replace("'", " ")))
    it = len(p & {"il", "lo", "la", "le", "di", "che", "non", "per", "una", "sono", "con", "della", "mi", "ho", "mio",
                  "sto", "del", "nel", "ma", "più", "è", "dei", "delle", "uno", "gli", "dal", "alla", "l", "un", "al"})
    en = len(p & {"the", "my", "is", "to", "and", "of", "for", "with", "not", "me", "can", "have", "it", "on", "this",
                  "i", "a", "in", "are", "how", "could", "need"})
    return "it" if it > en else "en"


def filtrar_dataset_ticket():
    x = pd.read_excel(RAW / "Dataset_ticket.xlsx").rename(columns={"Text": "texto"})
    x["texto"] = x["texto"].map(limpiar_texto)
    x = x[x["texto"].str.split().str.len() >= MIN_PALABRAS].drop_duplicates("texto")
    x["idioma"] = x["texto"].map(idioma_xlsx)
    x["fuente"] = "dataset_ticket"
    x["id_fuente"] = x.index
    x.to_csv(INTERIM / "dataset_ticket_filtrado.csv", index=False, encoding="utf-8")
    return len(x), x["idioma"].value_counts().to_dict()


def filtrar_tech_support():
    t = pd.read_csv(RAW / "tech-support-ticket-analytics.csv")
    n0 = len(t)
    t = t[t["issue_category"] != "billing"].copy()  # descripciones muy cortas por naturaleza: sin mínimo de palabras
    t["issue_description"] = t["issue_description"].map(limpiar_texto)
    t["resolution_notes"] = t["resolution_notes"].map(limpiar_texto)
    t = t[t["issue_description"] != ""]
    t = t[["ticket_id", "issue_category", "issue_description", "priority", "resolution_notes", "assigned_agent_id",
           "assigned_agent_name", "escalated", "status"]]
    t["idioma"] = "en"
    t["fuente"] = "tech_support"
    t.to_csv(INTERIM / "tech_support_filtrado.csv", index=False, encoding="utf-8")
    return n0, len(t)


def main():
    INTERIM.mkdir(parents=True, exist_ok=True)
    pasos, antes, despues, idiomas = filtrar_multilang()
    n_x, idi_x = filtrar_dataset_ticket()
    n_t0, n_t = filtrar_tech_support()

    md = ["# Resumen del filtrado (paso 3a)", "", "## Fuente principal (multi-lang)", "", "| Paso | Filas |", "|---|---:|"]
    md += [f"| {p} | {n:,} |".replace(",", " ") for p, n in pasos]
    md += ["", f"Categoría aproximada antes del muestreo: {antes}", "",
           f"Categoría aproximada de la muestra: {despues}", "", f"Idiomas de la muestra: {idiomas}", "",
           "## Dataset_ticket.xlsx", "", f"{n_x} filas conservadas. Idiomas detectados: {idi_x}", "",
           "## tech-support", "", f"{n_t0} → {n_t} filas (se descartó `billing`; sin mínimo de palabras).", ""]
    (RAIZ / "reports" / "filtrado_resumen.md").write_text("\n".join(md), encoding="utf-8")
    print("\n".join(md))


if __name__ == "__main__":
    main()
