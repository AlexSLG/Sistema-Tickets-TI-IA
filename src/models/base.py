"""Modelo base: TF-IDF + regresión logística (scikit-learn). Referencia para la GRU y el MLP de prioridad."""
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score

from src.models.comun import CATEGORIAS, PRIORIDADES, SEMILLA, texto_ticket


def entrenar_base(train, val, columna="categoria", clases=CATEGORIAS):
    """Elige C en la validación (F1 macro sobre tickets reales) y reentrena con el mejor."""
    y_tr = train[columna].map({c: i for i, c in enumerate(clases)}).to_numpy()
    y_va = val[columna].map({c: i for i, c in enumerate(clases)}).to_numpy()
    vec = TfidfVectorizer(ngram_range=(1, 2), min_df=2, sublinear_tf=True)
    Xtr = vec.fit_transform(texto_ticket(train))
    Xva = vec.transform(texto_ticket(val))
    real = val["real"].to_numpy()
    mejor = (-1, None)
    for C in (1, 3, 10, 30, 100):
        clf = LogisticRegression(C=C, class_weight="balanced", max_iter=3000, random_state=SEMILLA)
        clf.fit(Xtr, y_tr)
        f1 = f1_score(y_va[real], clf.predict(Xva[real]), average="macro")
        if f1 > mejor[0]:
            mejor = (f1, (C, clf))
    return vec, mejor[1][1], {"C": mejor[1][0], "f1_macro_val": float(mejor[0])}


def predecir_base(vec, clf, df):
    return clf.predict(vec.transform(texto_ticket(df)))
