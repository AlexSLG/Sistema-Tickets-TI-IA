"""Inventario de las fuentes en data/raw/ -> reports/inventario_fuentes.md

Usa solo la biblioteca estándar (csv, zipfile) para poder ejecutarse en cualquier
entorno. Ejecutar:  python -m src.data.inventario
"""
import csv
import re
import sys
import zipfile
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "data" / "raw"
SALIDA = RAIZ / "reports" / "inventario_fuentes.md"

csv.field_size_limit(sys.maxsize)
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}

# Columnas de texto libre (no se resumen por valores) y columnas categóricas por archivo
TEXTO = {"subject", "body", "answer", "text", "Text", "issue_description", "resolution_notes",
         "customer_name", "customer_email", "ticket_id", "customer_id"}
LICENCIAS = {
    "aa_dataset-tickets-multi-lang-5-2-50-version.csv": "Pública (Kaggle/Hugging Face, tickets multilingües de soporte). Licencia por confirmar.",
    "dataset_clean_es_812.csv": "Propia del equipo (versión 1, derivada de la fuente anterior).",
    "Dataset_ticket.xlsx": "Pública (Kaggle). Licencia por confirmar.",
    "tech-support-ticket-analytics.csv": "Pública (Kaggle). Licencia por confirmar.",
    "issues.csv": "Pública (Kaggle, issues de Jira). Licencia por confirmar.",
}


def leer_csv(ruta):
    with open(ruta, encoding="utf-8-sig", newline="") as f:
        lector = csv.DictReader(f)
        return lector.fieldnames, list(lector)


def leer_xlsx(ruta):
    with zipfile.ZipFile(ruta) as z:
        compartidas = []
        if "xl/sharedStrings.xml" in z.namelist():
            raiz = ET.fromstring(z.read("xl/sharedStrings.xml"))
            for si in raiz.findall("m:si", NS):
                compartidas.append("".join(t.text or "" for t in si.iter(f"{{{NS['m']}}}t")))
        hoja = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    filas = []
    for fila in hoja.iter(f"{{{NS['m']}}}row"):
        valores = {}
        for c in fila.findall("m:c", NS):
            col = re.match(r"[A-Z]+", c.get("r")).group()
            v = c.find("m:v", NS)
            if v is None:
                is_ = c.find("m:is", NS)
                texto = "".join(t.text or "" for t in is_.iter(f"{{{NS['m']}}}t")) if is_ is not None else ""
            else:
                texto = compartidas[int(v.text)] if c.get("t") == "s" else v.text
            valores[col] = texto
        filas.append(valores)
    cols = sorted(filas[0], key=lambda c: (len(c), c))
    encabezado = [filas[0][c] for c in cols]
    datos = [{encabezado[i]: f.get(c, "") for i, c in enumerate(cols)} for f in filas[1:]]
    return encabezado, datos


def idioma_aprox(texto):
    """Heurística por palabras vacías frecuentes; solo para el inventario."""
    palabras = set(re.findall(r"[a-zäöüßàèéìòùñáíóú]+", texto.lower()))
    puntaje = {
        "inglés": len(palabras & {"the", "and", "is", "to", "my", "with", "for", "this", "not", "please", "have"}),
        "alemán": len(palabras & {"und", "der", "die", "das", "nicht", "ich", "ist", "mit", "für", "bitte", "wir"}),
        "italiano": len(palabras & {"il", "di", "che", "non", "per", "una", "sono", "con", "della", "mi", "ho"}),
        "español": len(palabras & {"el", "la", "de", "que", "no", "en", "los", "con", "para", "mi", "una"}),
    }
    mejor = max(puntaje, key=puntaje.get)
    return mejor if puntaje[mejor] > 0 else "indeterminado"


def resumir(nombre, columnas, filas):
    out = [f"## `{nombre}`", "", f"- **Filas:** {len(filas):,}".replace(",", " "),
           f"- **Columnas ({len(columnas)}):** " + ", ".join(f"`{c}`" for c in columnas),
           f"- **Licencia / origen:** {LICENCIAS.get(nombre, 'desconocida')}"]

    # idioma sobre una muestra del campo de texto principal
    campo_texto = next((c for c in ("body", "text", "Text", "issue_description") if c in columnas), None)
    if campo_texto:
        cuenta = Counter(idioma_aprox(f[campo_texto]) for f in filas[::max(1, len(filas) // 2000)])
        total = sum(cuenta.values())
        out.append("- **Idioma (muestra, heurística):** " + ", ".join(f"{k} {v / total:.0%}" for k, v in cuenta.most_common()))
        longitudes = sorted(len(f[campo_texto].split()) for f in filas)
        out.append(f"- **Palabras por texto (`{campo_texto}`):** mediana {longitudes[len(longitudes) // 2]}, "
                   f"mín {longitudes[0]}, máx {longitudes[-1]}; con menos de 5 palabras: {sum(l < 5 for l in longitudes)}")
    if "language" in columnas:
        out.append("- **Columna `language`:** " + ", ".join(f"{k} {v}" for k, v in Counter(f['language'] for f in filas).most_common()))

    out += ["", "| Columna | Nulos/vacíos | Distintos | Valores más frecuentes |", "|---|---:|---:|---|"]
    for c in columnas:
        vals = [f.get(c, "") for f in filas]
        nulos = sum(1 for v in vals if v is None or v.strip() == "")
        cnt = Counter(v for v in vals if v and v.strip())
        if c in TEXTO or len(cnt) > 40:
            resumen = "(texto libre / alta cardinalidad)" if c in TEXTO else f"(alta cardinalidad; ej.: {', '.join(list(cnt)[:3])})"
        else:
            resumen = "; ".join(f"{k} ({v})" for k, v in cnt.most_common(12))
        out.append(f"| `{c}` | {nulos} | {len(cnt)} | {resumen.replace('|', '/')} |")
    out.append("")
    return out


def main():
    lineas = ["# Inventario de fuentes", "",
              "Generado por `python -m src.data.inventario` sobre las copias en `data/raw/`.", ""]
    resumen = ["| Archivo | Filas | Columnas |", "|---|---:|---:|"]
    bloques = []
    for ruta in sorted(RAW.iterdir()):
        if ruta.suffix == ".csv":
            columnas, filas = leer_csv(ruta)
        elif ruta.suffix == ".xlsx":
            columnas, filas = leer_xlsx(ruta)
        else:
            continue
        resumen.append(f"| `{ruta.name}` | {len(filas):,} | {len(columnas)} |".replace(",", " "))
        bloques += resumir(ruta.name, columnas, filas)

        # detalles específicos útiles para el filtrado
        if "queue" in columnas and "tag_1" in columnas:
            etiquetas = Counter(f[c] for f in filas for c in columnas if c.startswith("tag_") and f[c])
            bloques += ["**Colas × idioma:**", "", "| Cola | " + " | ".join(sorted({f['language'] for f in filas})) + " |",
                        "|---|" + "---:|" * len({f['language'] for f in filas})]
            idiomas = sorted({f['language'] for f in filas})
            for q, _ in Counter(f["queue"] for f in filas).most_common():
                bloques.append(f"| {q} | " + " | ".join(str(sum(1 for f in filas if f['queue'] == q and f['language'] == i)) for i in idiomas) + " |")
            bloques += ["", "**Etiquetas (`tag_1..tag_8`) más frecuentes:** " + ", ".join(f"{k} ({v})" for k, v in etiquetas.most_common(40)), ""]
        if "Subcategory" in columnas:
            bloques += ["**Categoría × subcategoría:**", ""]
            pares = Counter((f["Category"], f["Subcategory"]) for f in filas)
            bloques += [f"- {c} / {s}: {n}" for (c, s), n in sorted(pares.items())] + [""]
    lineas += resumen + [""] + bloques
    SALIDA.parent.mkdir(exist_ok=True)
    SALIDA.write_text("\n".join(lineas), encoding="utf-8")
    print(f"Escrito {SALIDA.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
