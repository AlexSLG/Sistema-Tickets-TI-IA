"""Extrae una muestra aleatoria de 100 traducciones (semilla 42) para revisión manual.

Salida: data/interim/muestra_calidad.csv.  Ejecutar: python -m src.data.muestra_calidad
"""
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
INTERIM = RAIZ / "data" / "interim"


def main():
    m = pd.read_csv(INTERIM / "multilang_traducido.csv", keep_default_na=False)
    x = pd.read_csv(INTERIM / "dataset_ticket_traducido.csv", keep_default_na=False)
    t = pd.read_csv(INTERIM / "tech_support_traducido.csv", keep_default_na=False)
    filas = []
    # 60 de la principal (30 en, 30 de), 30 del xlsx (15 en, 15 it), 10 de tech-support
    for idioma, n in (("en", 30), ("de", 30)):
        for _, f in m[m["idioma"] == idioma].sample(n, random_state=42).iterrows():
            filas.append(("multilang", idioma, f["body"], f["cuerpo_es"]))
    for idioma, n in (("en", 15), ("it", 15)):
        for _, f in x[x["idioma"] == idioma].sample(n, random_state=42).iterrows():
            filas.append(("dataset_ticket", idioma, f["texto"], f["texto_es"]))
    for _, f in t.sample(10, random_state=42).iterrows():
        filas.append(("tech_support", "en", f["issue_description"], f["descripcion_es"]))
    out = pd.DataFrame(filas, columns=["fuente", "idioma", "original", "traduccion"])
    out.insert(0, "n", range(1, len(out) + 1))
    out.to_csv(INTERIM / "muestra_calidad.csv", index=False, encoding="utf-8")
    print(len(out), "filas en data/interim/muestra_calidad.csv")


if __name__ == "__main__":
    main()
