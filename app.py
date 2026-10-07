"""Laboratorio Norma+ · Del documento al dato."""
import json
import streamlit as st
from nucleo import ui
from nucleo.claude import exportar_cache, RESPALDO

ui.configurar("Inicio")

st.title("Laboratorio Norma+")
st.markdown("#### Del documento al dato: cómo convertir resoluciones jurídicas en datos trazables con IA")
st.markdown(
    "En este laboratorio recorres, paso a paso, el método con el que **Norma+** convierte decisiones legales "
    "en una base de conocimiento. Trabajamos con tres resoluciones **ficticias**, escritas con el formato "
    "de la COFECE y del Poder Judicial, que incluyen a propósito los casos difíciles.")

st.markdown("### Cinco estaciones")
estaciones = [
    ("📄 1 · Estructura", "Del PDF a secciones, sin inteligencia artificial.", "Lo que se puede resolver sin LLM, se resuelve sin LLM."),
    ("🔎 2 · Extracción", "Claude extrae criterios con un esquema; verificamos cada cita.", "Una cita que no está en el texto no existe."),
    ("✅ 3 · Validación", "¿Es un criterio? ¿La abstracción dice lo mismo que la cita?", "Antes de confiar en un control, mídelo."),
    ("🧩 4 · Deduplicación", "El mismo criterio en varias resoluciones: proponer, decidir, vetar.", "Proponer barato, decidir caro, vetar con reglas."),
    ("📊 5 · Evaluación y costos", "Precisión, exhaustividad y cuánto costaría el acervo de la SCJN.", "Sin gold no hay sistema; sin medir tokens no hay negocio."),
]
for col, (titulo, que, leccion) in zip(st.columns(5), estaciones):
    with col:
        st.markdown(f"**{titulo}**")
        st.write(que)
        st.caption(f"_{leccion}_")

st.markdown("### Cómo usarlo")
st.markdown(
    "1. Pega en la barra lateral la API key que te dieron. Se guarda solo mientras esta pestaña esté abierta.\n"
    "2. Avanza por las estaciones en orden con el menú de la izquierda. Cada una tiene **retos**: cambia algo y observa qué pasa.\n"
    "3. Abre **Ver el código** cuando quieras saber exactamente qué hace cada paso. Es el código real que corre la app.\n"
    "4. Vigila el gasto en la barra lateral. Repetir algo que ya se calculó no cuesta: sale de la caché.")

with st.expander("Para el instructor"):
    clave = st.text_input("Clave de instructor", type="password")
    try:
        esperada = st.secrets.get("CLAVE_INSTRUCTOR", "")
    except Exception:  # el servidor no tiene archivo de secretos
        esperada = ""
    if clave and esperada and clave == esperada:
        n = exportar_cache("/tmp/cache_laboratorio.json")
        st.write(f"Hay {n} respuestas en la caché de esta instancia.")
        st.download_button("Descargar caché como respaldo", open("/tmp/cache_laboratorio.json", "rb"), file_name="cache.json")
        st.caption(f"Para usarla como respaldo, reemplaza `{RESPALDO.relative_to(RESPALDO.parents[2])}` en el repositorio y vuelve a desplegar.")
    elif clave and not esperada:
        st.error("El servidor no tiene `CLAVE_INSTRUCTOR` en Secrets. Agrégala en share.streamlit.io › ⋮ › Settings › Secrets.")
    elif clave:
        st.error("Clave incorrecta.")
