"""Estación 2: extracción con esquema y verificación literal de citas."""
import re
from typing import Literal
from pydantic import BaseModel, Field, ValidationError
from .datos import taxonomia
from .claude import llamar, esquema_plano

TAX = taxonomia()
TemaId = Literal[tuple(TAX)]

class Criterio(BaseModel):
    criterio: str = Field(description="Abstracción fiel del criterio en una oración, sin datos del caso concreto.")
    cita_literal: str = Field(description="Copia EXACTA del fragmento que sustenta el criterio, de 10 a 60 palabras.")
    id_tema: TemaId = Field(description="Nodo más específico de la taxonomía.")
    articulos: list[str] = Field(default_factory=list, description="Artículos invocados, como 'LFCE 58'. Lista vacía si no hay.")

class Extraccion(BaseModel):
    criterios: list[Criterio] = Field(description="Criterios del fragmento. Lista vacía si no hay ninguno.")

HERRAMIENTA = {"name": "registrar_criterios", "description": "Registra los criterios jurídicos extraídos del fragmento.",
               "input_schema": esquema_plano(Extraccion)}

TAX_TEXTO = "\n".join(f"{k}: {v}" for k, v in TAX.items())
PROMPT_BASE = """Eres un analista jurídico especializado en competencia económica en México.
Recibirás un fragmento de una resolución. Extrae sus CRITERIOS JURÍDICOS: proposiciones generales sobre
cómo se interpreta o aplica una norma, que podrían invocarse en un caso distinto.

NO son criterios:
- hechos del caso (fechas, montos, porcentajes, conductas concretas);
- transcripciones de contratos, leyes u otros documentos;
- argumentos de las partes;
- la valoración de pruebas concretas;
- la aplicación de un criterio a los hechos del caso.

Reglas:
- La cita_literal debe copiarse EXACTAMENTE del fragmento.
- Si el fragmento no contiene criterios, devuelve una lista vacía."""

def sistema(prompt):
    return f"{prompt}\n\nTaxonomía (usa el id):\n{TAX_TEXTO}"

def normalizar(s):
    s = s.replace("“", '"').replace("”", '"').replace("«", '"').replace("»", '"')
    return re.sub(r"\s+", " ", s).strip()

def es_literal(cita, texto):
    """Una cita que no está en el texto no existe."""
    return normalizar(cita) in normalizar(texto)

def extraer(chunk, prompt, key, sesion):
    """Devuelve (lista de criterios como dict con estado, error)."""
    salida = llamar(sistema(prompt), f"Fragmento ({chunk['titulo']}):\n\n{chunk['texto']}", HERRAMIENTA, key, sesion, etapa="Extracción")
    try:
        res = Extraccion.model_validate(salida)
    except ValidationError as e:
        return [], f"Esquema inválido: {str(e)[:200]}"
    filas = []
    for c in res.criterios:
        d = c.model_dump()
        d["estado"] = "verificado" if es_literal(c.cita_literal, chunk["texto"]) else "cita_no_literal"
        filas.append(d)
    return filas, None
