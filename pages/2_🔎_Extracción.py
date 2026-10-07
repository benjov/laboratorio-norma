"""Estación 2 · Extracción con esquema y citas verificadas."""
import hashlib, json
import pandas as pd
import streamlit as st
from nucleo import ui, extraccion, estructura

ui.configurar("Extracción", "🔎")
st.title("🔎 Estación 2 · Extracción con esquema y citas verificadas")
st.markdown("Le pedimos a Claude que extraiga **criterios jurídicos** de un apartado. Tres ideas guían esta estación:")
c1, c2, c3 = st.columns(3)
c1.info("**Esquema antes que prompt.** Claude no puede responder con texto libre: llena un formulario con campos fijos.")
c2.info("**Una cita que no está en el texto no existe.** Revisamos que cada cita aparezca literalmente.")
c3.info("**Fallar cerrado.** Lo que no pasa una verificación se marca y se aparta; nunca se arregla en silencio.")

chunks = ui.todos_los_chunks()
por_id = {c["id_chunk"]: c for c in chunks}
st.session_state.setdefault("prompt", extraccion.PROMPT_BASE)

def huella(prompt):
    return hashlib.sha256(prompt.encode()).hexdigest()[:8]

def guardar(chunk, filas, prompt):
    pags = ui.procesado(chunk["documento"])["paginas_limpias"]
    for f in filas:
        f.update(documento=chunk["documento"], id_chunk=chunk["id_chunk"], apartado=chunk["titulo"],
                 pagina=estructura.anclar(pags, f["cita_literal"]) if f["estado"] == "verificado" else None)
    st.session_state["extracciones"][chunk["id_chunk"]] = {"prompt": huella(prompt), "filas": filas}

col_izq, col_der = st.columns([3, 2])
with col_der:
    st.markdown("#### El prompt")
    st.session_state["prompt"] = st.text_area("Instrucciones para Claude (puedes editarlas)", st.session_state["prompt"], height=360)
    if st.button("Restablecer el prompt original"):
        st.session_state["prompt"] = extraccion.PROMPT_BASE
        st.rerun()
    with st.expander("El esquema que Claude debe llenar"):
        st.json(extraccion.HERRAMIENTA["input_schema"]["properties"]["criterios"]["items"]["properties"], expanded=False)

with col_izq:
    st.markdown("#### Un apartado")
    cid = st.selectbox("Elige un apartado de la zona argumentativa", list(por_id),
                       format_func=lambda i: f"{i} · {por_id[i]['titulo']}", index=list(por_id).index("R1-QUINTO") if "R1-QUINTO" in por_id else 0)
    chunk = por_id[cid]
    if st.button("✨ Extraer criterios con Claude", type="primary"):
        with st.spinner("Claude está leyendo el apartado…"):
            res = ui.con_claude(extraccion.extraer, chunk, st.session_state["prompt"], ui.key(), ui.sesion())
        if res is not None:
            filas, error = res
            if error:
                st.error(f"La respuesta no respetó el esquema y se descarta completa. {error}")
            guardar(chunk, filas, st.session_state["prompt"])
    actual = st.session_state["extracciones"].get(cid)
    filas = actual["filas"] if actual else []
    st.markdown(ui.resaltar(chunk["texto"], [f["cita_literal"] for f in filas if f["estado"] == "verificado"],
                            [f["cita_literal"] for f in filas if f["estado"] != "verificado"]), unsafe_allow_html=True)
    st.caption(f"Páginas {chunk['pag_ini']}–{chunk['pag_fin']} · Azul: cita verificada · Naranja: cita que no aparece literalmente")

if filas:
    st.markdown("#### Lo que extrajo Claude")
    if actual and actual["prompt"] != huella(st.session_state["prompt"]):
        st.caption("Estos resultados se obtuvieron con una versión anterior del prompt.")
    for f in filas:
        icono = "✅" if f["estado"] == "verificado" else "⚠️"
        with st.container(border=True):
            st.markdown(f"{icono} **{f['criterio']}**")
            st.markdown(f"> {f['cita_literal']}")
            st.caption(f"Tema: {f['id_tema']} · {extraccion.TAX.get(f['id_tema'], '')} · Artículos: {', '.join(f['articulos']) or '—'} · "
                       + (f"Página {f['pagina']}" if f["pagina"] else "**Cita no literal: se aparta para revisión**"))
elif actual is not None:
    st.info("Claude no encontró criterios en este apartado.")

with st.expander("🎯 Retos"):
    st.markdown(
        "1. Extrae **R1-SEGUNDO** (Hechos acreditados). ¿Encontró criterios? Debería devolver una lista vacía.\n"
        "2. Borra del prompt la lista de lo que **NO** son criterios y vuelve a extraer R1-SEGUNDO. ¿Qué cambia? "
        "Después restablece el prompt.\n"
        "3. Extrae varios apartados y busca una cita marcada en naranja. ¿Qué cambió el modelo respecto del texto?")

st.divider()
st.markdown("#### Extraer todo el corpus")
st.markdown(f"Los {len(chunks)} apartados de las tres resoluciones, con el prompt actual. Cuesta alrededor de USD 0.07 con Haiku; "
            "lo que ya esté en caché no se vuelve a pagar. El resultado alimenta las estaciones 3, 4 y 5.")
if st.button("Extraer los tres documentos"):
    barra = st.progress(0.0)
    for i, ch in enumerate(chunks, 1):
        res = ui.con_claude(extraccion.extraer, ch, st.session_state["prompt"], ui.key(), ui.sesion())
        if res is None:
            break
        guardar(ch, res[0], st.session_state["prompt"])
        barra.progress(i / len(chunks), text=f"{ch['id_chunk']} ({i} de {len(chunks)})")

todas = [f for e in st.session_state["extracciones"].values() for f in e["filas"]]
if todas:
    df = pd.DataFrame(todas)
    c1, c2, c3 = st.columns(3)
    c1.metric("Apartados procesados", len(st.session_state["extracciones"]))
    c2.metric("Criterios con cita verificada", int((df.estado == "verificado").sum()))
    c3.metric("Citas no literales", int((df.estado == "cita_no_literal").sum()))

ui.ver_codigo(extraccion.es_literal, extraccion.extraer)
