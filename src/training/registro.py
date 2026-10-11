"""Registro de versiones de modelos (models/registry.json): alta, publicación, descarte y restauración."""
import json
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
MODELOS = RAIZ / "models"
REGISTRO = MODELOS / "registry.json"


def cargar():
    if REGISTRO.exists():
        return json.loads(REGISTRO.read_text(encoding="utf-8"))
    return {"activa": None, "versiones": []}


def guardar(reg):
    MODELOS.mkdir(parents=True, exist_ok=True)
    REGISTRO.write_text(json.dumps(reg, ensure_ascii=False, indent=2), encoding="utf-8")


def version_activa(reg=None):
    reg = reg or cargar()
    return next((v for v in reg["versiones"] if v["version"] == reg["activa"]), None)


def siguiente_version(reg=None):
    reg = reg or cargar()
    nums = [int(v["version"][1:]) for v in reg["versiones"] if v["version"][1:].isdigit()]
    return f"v{max(nums, default=0) + 1}"


def registrar(version, metricas, n_correcciones=0, estado="publicada", nota="", activar=False):
    """Añade (o reemplaza) una versión. `estado`: publicada | descartada. Si `activar`, pasa a ser la versión activa."""
    reg = cargar()
    reg["versiones"] = [v for v in reg["versiones"] if v["version"] != version]
    reg["versiones"].append({
        "version": version, "fecha": datetime.now().isoformat(timespec="seconds"), "directorio": f"models/{version}",
        "metricas": metricas, "n_correcciones": n_correcciones, "estado": estado, "nota": nota,
    })
    if activar and estado == "publicada":
        reg["activa"] = version
    guardar(reg)
    return reg


def restaurar(version):
    """Vuelve a una versión publicada anterior. Lanza ValueError si no existe o fue descartada."""
    reg = cargar()
    v = next((v for v in reg["versiones"] if v["version"] == version), None)
    if v is None:
        raise ValueError(f"La versión {version} no existe en el registro.")
    if v["estado"] != "publicada":
        raise ValueError(f"La versión {version} fue descartada y no se puede activar.")
    if not (RAIZ / v["directorio"]).exists():
        raise ValueError(f"Faltan los archivos de la versión {version} ({v['directorio']}).")
    reg["activa"] = version
    guardar(reg)
    return reg


def resumen_metricas(directorio):
    """Métricas clave de una carpeta de modelos para el registro."""
    d = Path(directorio)
    cat = json.loads((d / "metricas_categoria.json").read_text(encoding="utf-8"))
    pri = json.loads((d / "metricas_prioridad.json").read_text(encoding="utf-8"))
    asi = json.loads((d / "metricas_asignacion.json").read_text(encoding="utf-8"))
    sim = json.loads((d / "metricas_similitud.json").read_text(encoding="utf-8"))
    return {
        "f1_macro_categoria_gru": cat["gru"]["reales"]["f1_macro"],
        "f1_macro_categoria_base": cat["base"]["reales"]["f1_macro"],
        "f1_macro_prioridad": pri["mlp completo"]["reales"]["f1_macro"],
        "recall_critica": pri["mlp completo"]["reales"]["por_clase"]["Crítica"]["recall"],
        "top1_asignacion": asi["top1"],
        "similares_3_de_5": sim["casos_similares"]["criterio_3_de_5_misma_categoria"],
    }
