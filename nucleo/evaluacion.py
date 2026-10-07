"""Estación 5: evaluación contra el gold y proyección de costos."""
import difflib
from .extraccion import normalizar

def prf(vp, fp, fn):
    p = vp / (vp + fp) if vp + fp else 0.0
    r = vp / (vp + fn) if vp + fn else 0.0
    return p, r, (2 * p * r / (p + r) if p + r else 0.0)

def similitud(a, b):
    a, b = normalizar(a).lower(), normalizar(b).lower()
    if a in b or b in a:
        return 1.0
    return difflib.SequenceMatcher(None, a.split(), b.split()).ratio()

def emparejar(extraidos, gold, umbral=0.6):
    """Uno a uno, de la pareja más parecida a la menos, dentro de cada documento."""
    parejas = sorted(((similitud(e["cita_literal"], g["cita_literal"]), i, j)
                      for i, e in enumerate(extraidos) for j, g in enumerate(gold)
                      if e["documento"] == g["documento"]), reverse=True)
    ue, ug, m = set(), set(), {}
    for s, i, j in parejas:
        if s >= umbral and i not in ue and j not in ug:
            ue.add(i); ug.add(j); m[i] = j
    return m

def evaluar(extraidos, gold):
    m = emparejar(extraidos, gold)
    vp, fp, fn = len(m), len(extraidos) - len(m), len(gold) - len(m)
    p, r, f1 = prf(vp, fp, fn)
    tema = sum(extraidos[i]["id_tema"] == gold[j]["id_tema"] for i, j in m.items()) / max(len(m), 1)
    return {"n": len(extraidos), "VP": vp, "FP": fp, "FN": fn, "precision": p, "exhaustividad": r, "F1": f1, "tema_correcto": tema}

def costo_corpus(paginas, tokens_pagina, documentos, salida_doc, precio_in, precio_out, fraccion_cacheada=0.0):
    """Las lecturas de caché de prompts se cobran a ~10% del precio de entrada."""
    entrada = paginas * tokens_pagina
    costo_in = entrada * (1 - fraccion_cacheada) * precio_in + entrada * fraccion_cacheada * precio_in * 0.10
    return (costo_in + documentos * salida_doc * precio_out) / 1e6
