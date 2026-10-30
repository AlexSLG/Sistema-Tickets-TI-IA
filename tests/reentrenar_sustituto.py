"""Sustituto de src.training.reentrenar para probar el proceso aparte sin entrenar ni tocar el registro de modelos."""
import argparse
import json

ap = argparse.ArgumentParser()
ap.add_argument("--epocas")
ap.add_argument("--correcciones")
ap.add_argument("--salida-json")
a = ap.parse_args()
print("Época 1/1: pérdida 0,1234", flush=True)
json.dump({"publicada": False, "motivo": "No mejora (sustituto de prueba).", "n_correcciones": 5, "archivo": a.correcciones},
          open(a.salida_json, "w", encoding="utf-8"))
