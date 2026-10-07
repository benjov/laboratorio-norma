"""Estación 5 · Evaluación contra el gold y costos."""
import pandas as pd
import streamlit as st
from nucleo import ui, evaluacion, extraccion
from nucleo.claude import PRECIOS, MODELO
from nucleo.datos import gold

ui.configurar("Evaluación y costos", "📊")
st.title("📊 Estación 5 · Evaluación y costos")
st.markdown("Un pipeline que no se mide es una demostración, no un sistema. Dos preguntas: **¿qué tan bien funciona?** y **¿cuánto cuesta?**")

t1, t2 = st.tabs(["1 · ¿Qué tan bien extrae?", "2 · ¿Cuánto cuesta?"])

with t1:
    ext = st.session_state["extracciones"]
    if not ext:
        st.info("Primero extrae criterios en la estación 2. Para una evaluación completa, extrae los tres documentos.")
    else:
        textos = [extraccion.normalizar(c["texto"]) for c in ui.todos_los_chunks() if c["id_chunk"] in ext]
        g = [r for r in gold().to_dict("records") if any(extraccion.normalizar(r["cita_literal"]) in t for t in textos)]
        todas = [f for e in ext.values() for f in e["filas"]]
        etapas = [("1 · Todo lo extraído", todas), ("2 · Cita verificada", [f for f in todas if f["estado"] == "verificado"])]
        if st.session_state.get("validadas"):
            etapas.append(("3 · Validador + gate", [f for f in st.session_state["validadas"] if f["aceptado"]]))
        tabla = pd.DataFrame([{"etapa": n, **evaluacion.evaluar(fs, g)} for n, fs in etapas])
        st.markdown(f"Comparamos contra los **{len(g)} criterios del gold** que están en los apartados que procesaste.")
        st.dataframe(tabla.style.format({"precision": "{:.2f}", "exhaustividad": "{:.2f}", "F1": "{:.2f}", "tema_correcto": "{:.2f}"}),
                     hide_index=True, use_container_width=True)
        st.markdown("- **Precisión:** de lo que extrajo, ¿cuánto es un criterio del gold?\n"
                    "- **Exhaustividad:** de los criterios del gold, ¿cuántos encontró?\n"
                    "- **Tema correcto:** de los que encontró, ¿cuántos quedaron en el nodo correcto de la taxonomía?")
        with st.expander("🎯 Para discutir"):
            st.markdown("Cada control debería subir la precisión. ¿Cuánto bajó la exhaustividad a cambio? Una base para litigio "
                        "prioriza precisión; una exploración académica quizá prefiera exhaustividad. Recuerda además que el gold "
                        "también tiene autor: medimos acuerdo con quien lo escribió, no la verdad.")
        ui.ver_codigo(evaluacion.emparejar, evaluacion.prf)

with t2:
    reg = pd.DataFrame(ui.sesion()["registro"])
    st.markdown("#### Lo que gastaste en esta sesión, por etapa")
    if len(reg):
        pagadas = reg[~reg.desde_cache]
        resumen = reg.groupby("etapa").agg(llamadas=("costo", "size"), desde_cache=("desde_cache", "sum"),
                                           tokens_entrada=("entrada", "sum"), tokens_salida=("salida", "sum"), costo_usd=("costo", "sum"))
        st.dataframe(resumen.style.format({"costo_usd": "{:.4f}"}), use_container_width=True)
        if len(pagadas):
            st.caption(f"En promedio, cada llamada pagada leyó {pagadas.entrada.mean():,.0f} tokens y escribió {pagadas.salida.mean():,.0f}.")
    else:
        st.info("Todavía no hay llamadas en esta sesión.")

    st.markdown("#### ¿Cuánto costaría procesar el acervo de la SCJN?")
    st.markdown("El deck de Norma+ estima unas **315 mil resoluciones** desde 1995, con unos **63 millones de páginas**. "
                "Ajusta los supuestos y mira cómo cambia el costo.")
    c1, c2 = st.columns(2)
    with c1:
        tokens_pagina = st.number_input("Tokens de entrada por página (supuesto)", 200, 15000, 700, 50,
                                        help="Una página de texto jurídico en español ronda varios cientos de tokens; incluye las instrucciones que se repiten.")
        salida_doc = st.number_input("Tokens de salida por resolución (supuesto)", 100, 500000, 1500, 100)
        pasadas = st.slider("Llamadas al modelo por página (extracción, validación, gate…)", 1, 6, 1)
    with c2:
        p_in = st.number_input("Precio de entrada (USD por millón de tokens)", 0.1, 100.0, float(PRECIOS[MODELO][0]), 0.1)
        p_out = st.number_input("Precio de salida (USD por millón de tokens)", 0.1, 400.0, float(PRECIOS[MODELO][1]), 0.5)
        cache_frac = st.slider("Fracción de la entrada que se lee de la caché de prompts", 0.0, 0.9, 0.0, 0.05,
                               help="Las lecturas de caché de prompts se cobran a una fracción del precio normal (alrededor de 10%).")
    usd = pasadas * evaluacion.costo_corpus(63_000_000, tokens_pagina, 315_000, salida_doc, p_in, p_out, cache_frac)
    c1, c2 = st.columns(2)
    c1.metric("Costo estimado del acervo", f"USD {usd:,.0f}")
    c2.metric("Por resolución", f"USD {usd / 315_000:.3f}")
    st.caption(f"Precios por defecto: {MODELO}. Cámbialos para comparar con un modelo más grande.")
    with st.expander("🎯 Para discutir"):
        st.markdown("¿Qué etapas merecen un modelo grande y cuáles se resuelven con uno pequeño, o sin modelo, como la estación 1? "
                    "Así se piensa la ingeniería de costos: medir tokens por etapa, cachear lo que se repite y reservar el modelo caro "
                    "para lo que lo necesita.")
    ui.ver_codigo(evaluacion.costo_corpus)
