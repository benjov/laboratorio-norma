"""Rutas y carga del dataset ficticio del curso."""
import json
from pathlib import Path
import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
DATOS = RAIZ / "datos"
PDFS = sorted((DATOS / "pdf").glob("*.pdf"))
NOMBRES = {
    "R1_COFECE_PMR_lacteos.pdf": "R1 · COFECE sanciona exclusividad en refrigeradores",
    "R2_COFECE_CNT_farmacias.pdf": "R2 · COFECE autoriza fusión de farmacias con condiciones",
    "R3_PJF_JD_amparo_lacteos.pdf": "R3 · Juez de amparo revisa la sanción de R1",
}

def taxonomia():
    return {n["id"]: n["ruta_tema"] for n in json.load(open(DATOS / "taxonomia.json", encoding="utf-8"))}

def gold():
    return pd.read_csv(DATOS / "gold_criterios.csv")

def negativos():
    return pd.read_csv(DATOS / "negativos_validacion.csv")

def pares_fidelidad():
    return pd.read_csv(DATOS / "pares_fidelidad.csv")
