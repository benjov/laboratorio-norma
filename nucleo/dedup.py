"""Estación 4: proponer pares con similitud, decidir con Claude, vetar con reglas."""
import itertools, functools
import numpy as np
from pydantic import BaseModel, Field, ValidationError
from .claude import llamar, esquema_plano

@functools.lru_cache(maxsize=1)
def _modelo_embeddings():
    """Se carga una sola vez. Si sentence-transformers no está instalado, se usa TF-IDF."""
    try:
        from sentence_transformers import SentenceTransformer
        return SentenceTransformer("sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
    except Exception:
        return None

def similitudes(textos):
    """Matriz de similitud coseno. Usa embeddings si están instalados; si no, TF-IDF de caracteres."""
    modelo = _modelo_embeddings()
    if modelo is not None:
        v = modelo.encode(list(textos), normalize_embeddings=True)
        metodo = "embeddings (MiniLM multilingüe)"
    else:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.preprocessing import normalize
        v = normalize(TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5)).fit_transform(list(textos)).toarray())
        metodo = "TF-IDF de n-gramas de caracteres"
    return np.asarray(v) @ np.asarray(v).T, metodo

def pares(ids, S):
    return [{"a": ids[i], "b": ids[j], "sim": float(S[i, j])} for i, j in itertools.combinations(range(len(ids)), 2)]

class Juicio(BaseModel):
    mismo_criterio: bool = Field(description="True si ambos expresan la misma regla jurídica, aunque la redacción difiera.")
    confianza: float = Field(description="Entre 0 y 1.")
    razon: str = Field(description="Una oración.")

SISTEMA_JUEZ = """Decide si dos criterios jurídicos expresan LA MISMA REGLA, aunque estén redactados distinto
o provengan de resoluciones diferentes. No son el mismo criterio si uno es más amplio, si tratan aspectos
distintos de un mismo tema, o si uno es condición o consecuencia del otro."""
HERR_JUEZ = {"name": "registrar_juicio", "description": "Registra si los criterios son el mismo.",
             "input_schema": esquema_plano(Juicio)}

def juzgar(a, b, key, sesion):
    try:
        return Juicio.model_validate(llamar(SISTEMA_JUEZ, f"CRITERIO A:\n{a}\n\nCRITERIO B:\n{b}", HERR_JUEZ, key, sesion, max_tokens=300, etapa="Juez de duplicados"))
    except ValidationError:
        return None

def a_conjunto(x):
    if isinstance(x, (list, set, tuple)):
        return set(x)
    if isinstance(x, str) and x.strip():
        return {a.strip() for a in x.split(";")}
    return set()

def puede_fusionar(fila_a, fila_b):
    """Reglas duras: mismo tema y artículos compatibles (comparten alguno, o ninguno tiene)."""
    aa, ab = a_conjunto(fila_a["articulos"]), a_conjunto(fila_b["articulos"])
    compatibles = (not aa and not ab) or bool(aa & ab)
    return fila_a["id_tema"] == fila_b["id_tema"] and compatibles

def consolidar(filas, fusiones):
    """Agrupa los pares fusionados y conserva todas las fuentes de cada grupo."""
    grupo = {f["id"]: f["id"] for f in filas}
    def raiz(i):
        while grupo[i] != i:
            i = grupo[i]
        return i
    for a, b in fusiones:
        grupo[raiz(b)] = raiz(a)
    grupos = {}
    for f in filas:
        grupos.setdefault(raiz(f["id"]), []).append(f)
    return list(grupos.values())
