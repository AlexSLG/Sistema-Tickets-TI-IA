"""Paso 5 · Análisis exploratorio: figuras en reports/figuras/ y reports/eda.md.

Funciones reutilizadas por notebooks/01_eda.ipynb.   Ejecutar:  python -m src.data.eda
"""
import re
from collections import Counter
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

RAIZ = Path(__file__).resolve().parents[2]
PROCESSED = RAIZ / "data" / "processed"
FIGURAS = RAIZ / "reports" / "figuras"
CATEGORIAS = ["Hardware", "Software", "Red", "Accesos", "Correo", "Seguridad"]
PRIORIDADES = ["Baja", "Media", "Alta", "Crítica"]
# Paleta apta para daltonismo (Okabe-Ito) y consistente entre figuras
COLOR_CAT = dict(zip(CATEGORIAS, ["#0072B2", "#E69F00", "#009E73", "#CC79A7", "#56B4E9", "#D55E00"]))
COLOR_PRI = dict(zip(PRIORIDADES, ["#9AC4A6", "#F2D16B", "#EE9D5C", "#C0392B"]))
plt.rcParams.update({"font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "figure.dpi": 110})


def cargar():
    df = pd.read_csv(PROCESSED / "tickets.csv", keep_default_na=False)
    df["real"] = df["origen_etiqueta"] != "aumento"
    df["palabras"] = df["descripcion"].str.split().str.len()
    for s in ("train", "val", "test"):
        ids = set(pd.read_csv(PROCESSED / f"{s}.csv", usecols=["id"])["id"])
        df.loc[df["id"].isin(ids), "subconjunto"] = s
    return df


def _guardar(fig, nombre):
    FIGURAS.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(FIGURAS / nombre, bbox_inches="tight")
    plt.close(fig)
    return f"figuras/{nombre}"


def fig_categorias(df):
    fig, ax = plt.subplots(figsize=(7, 3.6))
    reales = df[df.real]["categoria"].value_counts().reindex(CATEGORIAS)
    aum = df[~df.real]["categoria"].value_counts().reindex(CATEGORIAS).fillna(0)
    ax.bar(CATEGORIAS, reales, color=[COLOR_CAT[c] for c in CATEGORIAS])
    ax.bar(CATEGORIAS, aum, bottom=reales, color="#BBBBBB")
    for i, c in enumerate(CATEGORIAS):
        ax.text(i, reales[c] + aum[c] + 40, f"{int(reales[c] + aum[c])}", ha="center", fontsize=9)
    ax.set_ylabel("tickets"); ax.set_title("Tickets por categoría")
    from matplotlib.patches import Patch
    ax.legend(handles=[Patch(color="#555555", label="reales (color de la categoría)"), Patch(color="#BBBBBB", label="aumentados")], frameon=False)
    return _guardar(fig, "eda_categorias.png")


def fig_prioridades(df):
    fig, ax = plt.subplots(figsize=(5.5, 3.4))
    v = df["prioridad"].value_counts().reindex(PRIORIDADES)
    ax.bar(PRIORIDADES, v, color=[COLOR_PRI[p] for p in PRIORIDADES])
    for i, p in enumerate(PRIORIDADES):
        ax.text(i, v[p] + 30, f"{v[p]} ({v[p] / len(df):.1%})", ha="center", fontsize=9)
    ax.set_ylabel("tickets"); ax.set_title("Tickets por prioridad")
    return _guardar(fig, "eda_prioridades.png")


def fig_cruce(df):
    ct = pd.crosstab(df["categoria"], df["prioridad"], normalize="index").reindex(index=CATEGORIAS, columns=PRIORIDADES) * 100
    fig, ax = plt.subplots(figsize=(5.8, 3.8))
    im = ax.imshow(ct.values, cmap="Blues", vmin=0, vmax=50)
    ax.set_xticks(range(4), PRIORIDADES); ax.set_yticks(range(6), CATEGORIAS)
    for i in range(6):
        for j in range(4):
            ax.text(j, i, f"{ct.values[i, j]:.0f}%", ha="center", va="center", color="white" if ct.values[i, j] > 30 else "black")
    ax.set_title("Prioridad dentro de cada categoría (% por fila)")
    ax.spines[:].set_visible(False)
    return _guardar(fig, "eda_categoria_x_prioridad.png")


def fig_longitud(df):
    fig, ax = plt.subplots(figsize=(7, 3.4))
    r = df[df.real]
    bins = np.arange(0, 181, 6)
    for fuente, color in [("multilang", "#0072B2"), ("v1", "#E69F00"), ("dataset_ticket", "#009E73"), ("tech_support", "#CC79A7")]:
        ax.hist(r[r.fuente == fuente]["palabras"].clip(upper=180), bins=bins, alpha=0.65, label=fuente, color=color)
    ax.set_xlabel("palabras de la descripción"); ax.set_ylabel("tickets"); ax.set_yscale("log")
    ax.set_title("Longitud de la descripción por fuente (escala log)"); ax.legend(frameon=False)
    return _guardar(fig, "eda_longitud.png")


def fig_fuente_categoria(df):
    ct = pd.crosstab(df[df.real]["fuente"], df[df.real]["categoria"]).reindex(columns=CATEGORIAS)
    fig, ax = plt.subplots(figsize=(7, 3.4))
    izq = np.zeros(len(ct))
    for c in CATEGORIAS:
        ax.barh(ct.index, ct[c], left=izq, color=COLOR_CAT[c], label=c)
        izq += ct[c].values
    ax.set_xlabel("tickets reales"); ax.set_title("Categorías por fuente"); ax.legend(frameon=False, ncol=3, fontsize=8, loc="lower right")
    return _guardar(fig, "eda_fuente_x_categoria.png")


def fig_impacto_urgencia(df):
    ct = pd.crosstab(df["impacto"], df["urgencia"]).reindex(index=["Bajo", "Medio", "Alto"], columns=["Baja", "Media", "Alta"])
    fig, ax = plt.subplots(figsize=(4.6, 3.5))
    ax.imshow(ct.values, cmap="Blues")
    ax.set_xticks(range(3), ct.columns); ax.set_yticks(range(3), ct.index); ax.set_xlabel("urgencia"); ax.set_ylabel("impacto")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, int(ct.values[i, j]), ha="center", va="center", color="white" if ct.values[i, j] > ct.values.max() / 2 else "black")
    ax.set_title("Impacto × urgencia"); ax.spines[:].set_visible(False)
    return _guardar(fig, "eda_impacto_urgencia.png")


def terminos_distintivos(df, n=10):
    """Palabras con mayor TF-IDF medio en cada categoría respecto al resto (solo train, tickets reales)."""
    tr = df[(df.subconjunto == "train") & df.real]
    vec = TfidfVectorizer(min_df=5, sublinear_tf=True, stop_words=None, token_pattern=r"(?u)\b[a-záéíóúñü]{4,}\b")
    X = vec.fit_transform(tr["titulo"] + " " + tr["descripcion"])
    vocab = np.array(vec.get_feature_names_out())
    out = {}
    for c in CATEGORIAS:
        m = (tr["categoria"] == c).values
        dif = np.asarray(X[m].mean(axis=0)).ravel() - np.asarray(X[~m].mean(axis=0)).ravel()
        out[c] = list(vocab[np.argsort(-dif)[:n]])
    return out


def vocabulario(df):
    tok = lambda s: re.findall(r"\w+", s.lower())
    tr = df[df.subconjunto == "train"]
    cuenta = Counter(w for t in tr["titulo"] + " " + tr["descripcion"] for w in tok(t))
    con_min = {w for w, n in cuenta.items() if n >= 2}
    te = df[df.subconjunto == "test"]
    toks_test = [w for t in te["titulo"] + " " + te["descripcion"] for w in tok(t)]
    oov = np.mean([w not in con_min for w in toks_test])
    return len(cuenta), len(con_min), oov


def main():
    df = cargar()
    figs = {"cat": fig_categorias(df), "pri": fig_prioridades(df), "cruce": fig_cruce(df), "long": fig_longitud(df),
            "fuente": fig_fuente_categoria(df), "iu": fig_impacto_urgencia(df)}
    r = df[df.real]
    pal = r.groupby("categoria")["palabras"].describe(percentiles=[0.5, 0.9]).reindex(CATEGORIAS)[["count", "mean", "50%", "90%", "max"]].round(1)
    largos = (df["palabras"] > 120).mean()
    n_vocab, n_vocab_min, oov = vocabulario(df)
    term = terminos_distintivos(df)
    cruce_ct = pd.crosstab(r["fuente"], r["categoria"]).reindex(columns=CATEGORIAS)
    ejemplos = []
    for c in CATEGORIAS:
        s = r[(r.categoria == c) & (r.fuente == "multilang")].sample(2, random_state=42) if c != "Accesos" else r[(r.categoria == c)].sample(2, random_state=42)
        for x in s.itertuples():
            ejemplos.append(f"- **{c}** · {x.prioridad} · {x.fuente}: *{x.titulo[:90]}* — {x.descripcion[:170].replace(chr(10), ' ')}…")
    md = [
        "# Análisis exploratorio (paso 5)", "",
        f"Base: `data/processed/tickets.csv` — {len(df)} tickets ({len(r)} reales y {len(df) - len(r)} aumentados). Notebook: `notebooks/01_eda.ipynb`.", "",
        "## 1. Distribución de categorías", "", f"![categorías]({figs['cat']})", "",
        pd.crosstab(df["categoria"], df["real"].map({True: "reales", False: "aumentados"}), margins=True).reindex(CATEGORIAS + ["All"]).to_markdown(), "",
        "- Software es casi la mitad (45 %): en la fuente principal casi todo fallo de aplicación o plataforma es Software.",
        "- **Desbalance:** Software : Correo ≈ 10 : 1. Correo y Accesos están reforzados con variantes aumentadas (Correo solo 32 % real). "
        "Para entrenar se usarán pesos por clase y se reportará F1 macro y por clase.", "",
        "## 2. Distribución de prioridades", "", f"![prioridades]({figs['pri']})", "",
        "- Baja 32,6 %, Media 32,5 %, Alta 27,3 %, Crítica 7,6 %: Crítica es la clase minoritaria; el criterio del MLP exige recall ≥ 0,85 en ella.", "",
        "## 3. Categoría × prioridad", "", f"![cruce]({figs['cruce']})", "",
        "- Seguridad concentra las prioridades altas (los incidentes pasan a Alta como mínimo tras la auditoría); Hardware y Correo son sobre todo Baja "
        "(la mayoría viene de `Dataset_ticket.xlsx`, cuya prioridad se deriva del texto).",
        "- Cuidado: la prioridad depende de la categoría y de la fuente; el modelo podría usar la categoría como atajo. Se mide también por fuente.", "",
        "## 4. Fuentes", "", f"![fuentes]({figs['fuente']})", "", cruce_ct.to_markdown(), "",
        "- La fuente principal domina Seguridad, Software y Red; `Dataset_ticket.xlsx` aporta casi todo Hardware y Correo reales.",
        "- Riesgo de que el modelo aprenda el **estilo de la fuente** (plantilla larga frente a frase corta) en vez de la categoría. "
        "Hay que revisar la matriz de confusión por fuente (paso 7) y el conjunto de prueba del equipo (SCRUM-100).", "",
        "## 5. Longitud de los textos", "", f"![longitud]({figs['long']})", "",
        "Palabras de la descripción (tickets reales):", "", pal.to_markdown(), "",
        f"- El {largos:.1%} de los tickets supera 120 palabras; con `max_len = 128` tokens de la GRU se trunca muy poco (máximo ≈ 175 palabras).",
        "- `Dataset_ticket.xlsx` y `tech-support` son frases de 5–25 palabras; la fuente principal y la v1, párrafos de 40–120.", "",
        "## 6. Impacto y urgencia", "", f"![impacto]({figs['iu']})", "",
        f"- Excepciones a la matriz impacto × urgencia → prioridad: {df['excepcion_matriz'].astype(str).eq('True').mean():.1%}.",
        "- Urgencia Media y impacto Medio dominan; Bajo/Baja y Alto/Alta son menos frecuentes.", "",
        "## 7. Vocabulario (solo train)", "",
        f"- {n_vocab} palabras distintas; {n_vocab_min} aparecen al menos 2 veces (vocabulario candidato de la GRU).",
        f"- Fracción de palabras de test fuera de ese vocabulario (OOV): {oov:.1%}.", "",
        "Términos más distintivos por categoría (TF-IDF medio frente al resto):", "",
        "| Categoría | Términos |", "|---|---|"] + [f"| {c} | {', '.join(t)} |" for c, t in term.items()] + [
        "", "- Hardware, Correo, Red y Accesos se separan por vocabulario de problema (teclado, monitor; correos, outlook; router, dhcp; sesión, permiso).",
        "- **Riesgo de atajo:** Seguridad se distingue sobre todo por el relato de plantilla (*médicos, hospital, datos, protocolos*) y Software por "
        "*análisis, inversión, plataforma, saas, proyectos*. Un modelo puede aprender el escenario en vez del problema. "
        "Hay que comprobarlo con el conjunto de prueba del equipo (SCRUM-100) y con tickets de `Dataset_ticket.xlsx`, donde no existe ese relato.", "",
        "## 8. Ejemplos por clase (tickets reales)", ""] + ejemplos + [
        "", "## 9. Hallazgos para el entrenamiento", "",
        "1. Usar **pesos por clase** (o muestreo) para Accesos, Correo y para la prioridad Crítica.",
        "2. Evaluar sobre **tickets reales** (excluir `origen_etiqueta == aumento`) y reportar por fuente.",
        "3. El ruido de etiqueta estimado en la fuente principal (≈ 15 % en categoría, `reports/auditoria_etiquetas.md`) limita el F1 alcanzable.",
        "4. Dos regímenes de texto (frases cortas y párrafos): considerar `max_len` 128 y relleno al final con máscara.",
        "5. Vigilar el atajo por escenario (médicos/hospital → Seguridad) con un conjunto de prueba sin esos relatos.",
        "6. Crítica solo se deriva de la fuente `tech-support` (urgent), de la fuente principal con reglas y de la v1: comprobar que el MLP no se limite a memorizar esas reglas.", ""]
    (RAIZ / "reports" / "eda.md").write_text("\n".join(md), encoding="utf-8")
    print("eda.md escrito;", len(figs), "figuras")


if __name__ == "__main__":
    main()
