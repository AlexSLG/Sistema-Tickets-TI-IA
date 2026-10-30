"""Ciclo de aprendizaje continuo verificable con el conjunto de prueba del equipo (HU37 · CRISP-ML(Q) fase 6).

1. Divide los tickets válidos del equipo en dos mitades estratificadas por categoría (semilla 42): A (aprendizaje) y B (evaluación).
2. Escribe las etiquetas de A como correcciones en un archivo de trabajo (mismo formato que data/correcciones.csv; el real no se toca).
3. Reentrena con src/training/reentrenar.py. La regla de publicación es la de siempre: solo si no empeora en test.csv.
   Se mide también en A (¿reproduce las correcciones?) y en B (¿generaliza a tickets nuevos del equipo?).
4. Prueba negativa: reentrena con las etiquetas de A cambiadas a propósito a otra categoría; la versión no debe publicarse.
   Si por azar se publicara, se restaura la versión anterior y se informa (no se maquilla).

Ejecutar:  python -m src.training.ciclo_aprendizaje [--epocas 6] [--sin-prueba-negativa]
Requiere:  data/prueba_equipo/tickets_equipo_validos.csv  (python -m src.data.validar_prueba_equipo)
Salida:    reports/aprendizaje_continuo_final.md y reports/aprendizaje_continuo_final.json
"""
import argparse
import json
import sys
import tempfile
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split

from src.models.comun import CATEGORIAS, RAIZ
from src.training import registro
from src.training.reentrenar import COLUMNAS, PERFIL_PRIORIDAD, reentrenar

VALIDOS = RAIZ / "data" / "prueba_equipo" / "tickets_equipo_validos.csv"
INFORME = RAIZ / "reports" / "aprendizaje_continuo_final.md"
JSON = RAIZ / "reports" / "aprendizaje_continuo_final.json"
SEMILLA = 42


def dividir(df, semilla=SEMILLA):
    """Mitades A y B estratificadas por categoría (si alguna categoría tiene un solo ticket, sin estratificar)."""
    estrato = df["categoria"] if df["categoria"].value_counts().min() >= 2 else None
    a, b = train_test_split(df, test_size=0.5, random_state=semilla, stratify=estrato)
    return a.reset_index(drop=True), b.reset_index(drop=True)


def a_correcciones(df, ruta, cambiar_categoria=False):
    """Escribe los tickets como correcciones. Con `cambiar_categoria`, cada categoría se cambia por la siguiente (etiquetas erróneas)."""
    filas = []
    for _, r in df.iterrows():
        cat = CATEGORIAS[(CATEGORIAS.index(r["categoria"]) + 1) % len(CATEGORIAS)] if cambiar_categoria else r["categoria"]
        imp, urg, afect = (r.get("impacto"), r.get("urgencia"), r.get("usuarios_afectados"))
        if not imp:
            imp, urg, afect = PERFIL_PRIORIDAD[r["prioridad"]]
        filas.append([r["titulo"], r["descripcion"], cat, r["prioridad"], "", imp, urg, afect, "ciclo de aprendizaje"])
    pd.DataFrame(filas, columns=COLUMNAS).to_csv(ruta, index=False, encoding="utf-8")
    return ruta


def reproduccion(df, predicciones):
    """Porcentaje de tickets cuya categoría predicha coincide con la etiqueta del equipo."""
    return float(np.mean(np.array(predicciones) == df["categoria"].to_numpy())) if len(df) else 0.0


def ejecutar(epocas=6, prueba_negativa=True, progreso=print):
    if not VALIDOS.exists():
        raise FileNotFoundError(f"No existe {VALIDOS.relative_to(RAIZ)}: ejecuta primero python -m src.data.validar_prueba_equipo")
    df = pd.read_csv(VALIDOS, dtype=str, keep_default_na=False)
    df["usuarios_afectados"] = df["usuarios_afectados"].astype(int)
    A, B = dividir(df)
    version_inicial = registro.version_activa()["version"]
    resultado = {"semilla": SEMILLA, "n_A": len(A), "n_B": len(B), "version_inicial": version_inicial}
    progreso(f"Conjunto del equipo: {len(df)} tickets → A = {len(A)} (aprendizaje), B = {len(B)} (evaluación). Versión vigente: {version_inicial}.")

    with tempfile.TemporaryDirectory(prefix="ciclo_aprendizaje_") as tmp:
        # --- ciclo positivo
        ruta = a_correcciones(A, Path(tmp) / "correcciones_A.csv")
        r = reentrenar(epocas=epocas, progreso=progreso, ruta_correcciones=ruta, evaluaciones_extra={"A": A, "B": B})
        ex = r.get("evaluaciones_extra", {})
        resultado["positivo"] = {k: v for k, v in r.items() if k != "evaluaciones_extra"}
        resultado["positivo"]["A"] = {"vigente": {k: v for k, v in ex["A"]["vigente"].items() if k != "predicciones"},
                                      "nueva": {k: v for k, v in ex["A"]["nueva"].items() if k != "predicciones"},
                                      "reproduccion_vigente": reproduccion(A, ex["A"]["vigente"]["predicciones"]),
                                      "reproduccion_nueva": reproduccion(A, ex["A"]["nueva"]["predicciones"])}
        resultado["positivo"]["B"] = {"vigente": {k: v for k, v in ex["B"]["vigente"].items() if k != "predicciones"},
                                      "nueva": {k: v for k, v in ex["B"]["nueva"].items() if k != "predicciones"}}

        # --- prueba negativa: etiquetas cambiadas a propósito
        if prueba_negativa:
            antes = registro.version_activa()["version"]
            ruta_mala = a_correcciones(A, Path(tmp) / "correcciones_erroneas.csv", cambiar_categoria=True)
            n = reentrenar(epocas=epocas, progreso=progreso, ruta_correcciones=ruta_mala, evaluaciones_extra={"B": B})
            neg = {k: v for k, v in n.items() if k != "evaluaciones_extra"}
            neg["B"] = {e: {k: v for k, v in n["evaluaciones_extra"]["B"][e].items() if k != "predicciones"} for e in ("vigente", "nueva")}
            if n["publicada"]:  # no debería ocurrir; si ocurre, se deja constancia y se vuelve a la versión anterior
                registro.restaurar(antes)
                neg["restaurada"] = antes
            resultado["negativo"] = neg
    resultado["version_final"] = registro.version_activa()["version"]
    return resultado


def f(x):
    return f"{x:.4f}".replace(".", ",")


def informe(res):
    p = res["positivo"]
    md = ["# Aprendizaje continuo verificado con el conjunto del equipo", "",
          f"Conjunto de prueba del equipo dividido en dos mitades estratificadas por categoría (semilla {res['semilla']}): "
          f"**A = {res['n_A']}** tickets usados como correcciones y **B = {res['n_B']}** tickets que el modelo no ve.",
          f"Versión vigente al inicio: **{res['version_inicial']}**. Versión activa al terminar: **{res['version_final']}**.", "",
          "## 1. Reentrenamiento con las correcciones de A", "",
          "| Conjunto | Vigente | Nueva | Diferencia |", "|---|---:|---:|---:|",
          f"| test.csv (referencia, decide la publicación) · F1 macro | {f(p['vigente']['f1_macro'])} | {f(p['nueva']['f1_macro'])} | {p['diferencia']:+.4f} |",
          f"| B (tickets del equipo no vistos) · F1 macro | {f(p['B']['vigente']['f1_macro'])} | {f(p['B']['nueva']['f1_macro'])} | {p['B']['nueva']['f1_macro'] - p['B']['vigente']['f1_macro']:+.4f} |",
          f"| A (corregidos) · categoría reproducida | {f(p['A']['reproduccion_vigente'])} | {f(p['A']['reproduccion_nueva'])} | {p['A']['reproduccion_nueva'] - p['A']['reproduccion_vigente']:+.4f} |", "",
          f"**Decisión:** {'publicada' if p['publicada'] else 'no publicada'} ({p['motivo']}) Versión candidata: {p['nueva']['version']}.", ""]
    if "negativo" in res:
        n = res["negativo"]
        md += ["## 2. Prueba negativa: correcciones con la categoría cambiada a propósito", "",
               "Cada ticket de A se registró con la categoría siguiente de la lista (Hardware → Software, …, Seguridad → Hardware).", "",
               "| Conjunto | Vigente | Nueva |", "|---|---:|---:|",
               f"| test.csv · F1 macro | {f(n['vigente']['f1_macro'])} | {f(n['nueva']['f1_macro'])} |",
               f"| B · F1 macro | {f(n['B']['vigente']['f1_macro'])} | {f(n['B']['nueva']['f1_macro'])} |", "",
               f"**Resultado:** {'no se publicó (correcto)' if not n['publicada'] else 'se publicó; se restauró ' + n.get('restaurada', '') + ' y se registra como hallazgo'}. {n['motivo']}", ""]
    md += ["## 3. Lectura", "",
           "- La publicación depende solo de `test.csv` (tickets reales que ninguna versión usa para entrenar): así una corrección mal hecha no puede degradar el sistema.",
           "- La mitad A mide si el modelo aprende lo que se le corrige; la mitad B, si ese aprendizaje se traslada a tickets nuevos escritos por el equipo.",
           "- Las versiones descartadas quedan en `models/registry.json` con su F1 y el motivo; las publicadas se pueden restaurar desde la pantalla Modelos.", ""]
    return "\n".join(md)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--epocas", type=int, default=6)
    ap.add_argument("--sin-prueba-negativa", action="store_true")
    a = ap.parse_args()
    try:
        res = ejecutar(a.epocas, not a.sin_prueba_negativa, progreso=lambda m: print(m, flush=True))
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)
    JSON.write_text(json.dumps(res, ensure_ascii=False, indent=2), encoding="utf-8")
    INFORME.write_text(informe(res), encoding="utf-8")
    print(f"Informe: {INFORME.relative_to(RAIZ)}")


if __name__ == "__main__":
    main()
