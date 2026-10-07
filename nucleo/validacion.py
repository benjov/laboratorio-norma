"""Estación 3: validador (¿es un criterio?) y gate de fidelidad (¿dice lo mismo que la cita?)."""
import re
from typing import Literal
from pydantic import BaseModel, Field, ValidationError
from .claude import llamar, esquema_plano

TIPOS = ("criterio", "hecho", "transcripcion", "argumento_parte", "valoracion_prueba", "aplicacion_al_caso", "tramite")

class Veredicto(BaseModel):
    tipo: Literal[TIPOS] = Field(description="Categoría del fragmento.")
    confianza: float = Field(description="Entre 0 y 1: qué tan seguro estás de la categoría.")
    razon: str = Field(description="Una oración que justifique la categoría.")

SISTEMA_VAL = """Eres un validador jurídico. Clasifica el FRAGMENTO, leído dentro de su APARTADO, en una categoría:
- criterio: proposición general sobre cómo se interpreta o aplica una norma, invocable en otro caso;
- hecho: dato del caso (fechas, montos, porcentajes, conductas concretas);
- transcripcion: texto copiado de un contrato, ley u otro documento;
- argumento_parte: lo que sostiene una de las partes;
- valoracion_prueba: lo que la autoridad concluye de pruebas concretas;
- aplicacion_al_caso: un criterio aplicado a los hechos de este caso;
- tramite: actuaciones del procedimiento.
Si dudas entre criterio y otra categoría, elige la otra."""
HERR_VAL = {"name": "clasificar_fragmento", "description": "Registra la categoría del fragmento.",
            "input_schema": esquema_plano(Veredicto)}

def validar(fragmento, apartado, key, sesion):
    usuario = f"APARTADO:\n{apartado}\n\nFRAGMENTO:\n{fragmento}"
    try:
        return Veredicto.model_validate(llamar(SISTEMA_VAL, usuario, HERR_VAL, key, sesion, max_tokens=300, etapa="Validador"))
    except ValidationError:
        return None

def aceptar(veredicto, umbral):
    """Fallar cerrado: solo pasa lo que es criterio con confianza suficiente."""
    return veredicto is not None and veredicto.tipo == "criterio" and veredicto.confianza >= umbral

class Fidelidad(BaseModel):
    etiqueta: Literal[("fiel", "generalizacion_no_sostenida")] = Field(description="Veredicto de fidelidad.")
    razon: str = Field(description="Una oración: qué afirma la abstracción que la cita no sostiene, o por qué es fiel.")

SISTEMA_FID = """Compara una ABSTRACCIÓN con la CITA y el APARTADO de donde proviene.
Es fiel si no afirma nada que el texto no sostenga: puede reformular y omitir detalles.
Es generalización no sostenida si amplía el alcance (de "puede" a "siempre", de un caso a todos),
convierte un indicador en una regla, o agrega consecuencias que el texto no establece."""
HERR_FID = {"name": "evaluar_fidelidad", "description": "Registra el veredicto de fidelidad.",
            "input_schema": esquema_plano(Fidelidad)}

def gate(cita, abstraccion, apartado, key, sesion):
    usuario = f"APARTADO:\n{apartado}\n\nCITA:\n{cita}\n\nABSTRACCIÓN:\n{abstraccion}"
    try:
        return Fidelidad.model_validate(llamar(SISTEMA_FID, usuario, HERR_FID, key, sesion, max_tokens=300, etapa="Gate de fidelidad"))
    except ValidationError:
        return None

def es_de_riesgo(abstraccion, palabras):
    """Filtro barato: solo las abstracciones con lenguaje de riesgo pasan por el gate."""
    if not palabras:
        return False
    patron = r"\b(" + "|".join(re.escape(p) for p in palabras) + r")\b"
    return bool(re.search(patron, abstraccion, re.IGNORECASE))
