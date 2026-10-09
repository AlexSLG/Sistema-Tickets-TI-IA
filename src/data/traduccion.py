"""Traducción en/de/it -> es con MarianMT (preprocesamiento, no parte del sistema).

Medir velocidad:  python -m src.data.traduccion --benchmark 100 [--dispositivo cpu|cuda]
"""
import argparse
import csv
import random
import sys
import time
from pathlib import Path

import torch
from transformers import MarianMTModel, MarianTokenizer

RAIZ = Path(__file__).resolve().parents[2]
MODELOS = {"en": "Helsinki-NLP/opus-mt-en-es", "de": "Helsinki-NLP/opus-mt-de-es",
           "it": "Helsinki-NLP/opus-mt-it-es"}
SEMILLA = 42
csv.field_size_limit(2**30)


class Traductor:
    def __init__(self, idioma, dispositivo="cpu"):
        self.dispositivo = dispositivo
        self.tok = MarianTokenizer.from_pretrained(MODELOS[idioma])
        self.modelo = MarianMTModel.from_pretrained(MODELOS[idioma]).to(dispositivo).eval()
        if dispositivo == "cuda":
            self.modelo = self.modelo.half()

    @torch.inference_mode()
    def traducir(self, textos, lote=16):
        # ordenar por longitud reduce el relleno dentro de cada lote
        orden = sorted(range(len(textos)), key=lambda i: len(textos[i]))
        salida = [None] * len(textos)
        for k in range(0, len(orden), lote):
            idx = orden[k:k + lote]
            enc = self.tok([textos[i] for i in idx], return_tensors="pt", padding=True,
                           truncation=True, max_length=400).to(self.dispositivo)
            gen = self.modelo.generate(**enc, num_beams=2, max_new_tokens=450)
            for i, t in zip(idx, self.tok.batch_decode(gen, skip_special_tokens=True)):
                salida[i] = t
        return salida


def benchmark(n, dispositivo, lote):
    ruta = RAIZ / "data" / "raw" / "aa_dataset-tickets-multi-lang-5-2-50-version.csv"
    filas = list(csv.DictReader(open(ruta, encoding="utf-8-sig", newline="")))
    filas = [f for f in filas if f["queue"] in ("Technical Support", "IT Support") and len(f["body"].split()) >= 5]
    random.Random(SEMILLA).shuffle(filas)
    torch.set_num_threads(torch.get_num_threads())
    total_t, total_n = 0.0, 0
    for idioma in ("en", "de"):
        textos = [f["body"] for f in filas if f["language"] == idioma][: n // 2]
        t = Traductor(idioma, dispositivo)
        t.traducir(textos[:4], lote=4)  # calentamiento
        if dispositivo == "cuda":
            torch.cuda.synchronize()
        t0 = time.perf_counter()
        sal = t.traducir(textos, lote=lote)
        if dispositivo == "cuda":
            torch.cuda.synchronize()
        dt = time.perf_counter() - t0
        total_t += dt
        total_n += len(textos)
        print(f"{idioma}: {len(textos)} textos en {dt:.1f} s -> {len(textos) / dt:.2f} textos/s")
        print("  ej:", textos[0][:120].replace("\n", " "), "=>", sal[0][:120].replace("\n", " "))
    print(f"TOTAL {dispositivo}: {total_n / total_t:.2f} textos/s (lote={lote}, hilos={torch.get_num_threads()})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--benchmark", type=int, default=0)
    ap.add_argument("--dispositivo", default="cpu")
    ap.add_argument("--lote", type=int, default=16)
    a = ap.parse_args()
    if a.benchmark:
        benchmark(a.benchmark, a.dispositivo, a.lote)
