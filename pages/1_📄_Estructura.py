"""Estación 1 · Del PDF a la estructura, sin LLM."""
import pandas as pd
import streamlit as st
from nucleo import ui, estructura
from nucleo.datos import PDFS, gold, negativos

ui.configurar("Estructura", "📄")
st.title("📄 Estación 1 · Del PDF a la estructura")
st.markdown("Antes de pedirle nada a un modelo de lenguaje, hay que saber **dónde** está lo que buscamos. "
            "Todo lo de esta estación se hace con reglas y expresiones regulares: es gratis, rápido y reproducible.")

nombre = ui.selector_documento()
r = ui.procesado(nombre)

t1, t2, t3, t4, t5 = st.tabs(["1 · El PDF", "2 · Ruido repetido", "3 · ¿Qué procedimiento es?", "4 · Mapa de secciones", "5 · Zona argumentativa"])

with t1:
    pag = st.radio("Página", [p["pagina"] for p in r["paginas"]], horizontal=True)
    c1, c2 = st.columns(2)
    img = ui.imagen_pagina(nombre, pag)
    with c1:
        if img is not None:
            st.image(img, caption=f"Página {pag}", use_container_width=True)
        else:
            st.info("La vista previa de la página no está disponible en este servidor.")
    with c2:
        st.markdown("**Lo que lee la computadora:** cada línea con su posición vertical en la página.")
        lineas = r["paginas"][pag - 1]["lineas"]
        st.dataframe(pd.DataFrame([{"posición": round(l["top"]), "texto": l["text"]} for l in lineas]),
                     hide_index=True, use_container_width=True, height=480)

with t2:
    st.markdown("El pie de página se repite en cada hoja y contamina el texto: parte oraciones y rompe la búsqueda de citas. "
                "Buscamos líneas de las franjas superior e inferior que se repiten en la mayoría de las páginas, "
                "después de cambiar los dígitos por `#` para que «Página 2» y «Página 3» cuenten como la misma línea.")
    st.markdown("**Líneas detectadas como ruido:**")
    for f in r["ruido"]:
        st.code(f, language=None)
    ui.ver_codigo(estructura.firma, estructura.detectar_ruido)

with t3:
    st.markdown("Una resolución de la COFECE y una sentencia de amparo no se leen igual. Un *router* mira el encabezado "
                "y cuenta cuántas señales de cada perfil aparecen.")
    c1, c2 = st.columns([1, 2])
    c1.metric("Perfil elegido", r["procedimiento"])
    c2.bar_chart(pd.Series(r["puntajes"], name="señales encontradas"))
    with st.expander("🎯 Reto: compara R1 y R3"):
        st.markdown("Selecciona R3 (el amparo). Suma un punto para `COFECE_INV`, el perfil de R1. ¿Por qué? "
                    "¿Qué pasaría si el router mirara todo el texto y no solo el encabezado?")
        st.caption("Pista: lee el primer párrafo de R3. Cita el expediente de la resolución que impugna.")
    ui.ver_codigo(estructura.clasificar)

with t4:
    st.markdown("Con el perfil sabemos qué secciones esperar. Ubicamos cada sección y cada apartado ordinal "
                "(«PRIMERO.», «SEGUNDO.»…) con su posición exacta en el texto y su página.")
    st.dataframe(pd.DataFrame(r["mapa"])[["seccion", "apartado", "titulo", "pag_ini", "pag_fin"]],
                 hide_index=True, use_container_width=True)
    ui.ver_codigo(estructura.mapa_secciones)

with t5:
    st.markdown("Los criterios jurídicos viven en los **considerandos**: la zona donde la autoridad razona. "
                "Si la aislamos bien, el modelo lee menos texto y con menos distractores. ¿La aislamos bien? **Lo medimos.**")
    g, n = gold(), negativos()
    zonas = {p.name: ui.procesado(p.name)["zona"] for p in PDFS}
    g_en = sum(estructura.norm(c) in zonas[d] for d, c in zip(g.documento, g.cita_literal))
    n_en = sum(estructura.norm(t) in zonas[d] for d, t in zip(n.documento, n.texto_literal))
    c1, c2 = st.columns(2)
    c1.metric("Criterios del gold dentro de la zona", f"{g_en} de {len(g)}")
    c2.metric("Fragmentos que NO son criterios, dentro de la zona", f"{n_en} de {len(n)}")
    st.markdown("La zona conserva todos los criterios, pero también casi todo el ruido: hechos, transcripciones y "
                "argumentos de las partes viven en el mismo lugar. **La posición no basta**; hace falta entender el texto.")
    st.markdown("**Zona argumentativa de este documento.** Azul: criterios del gold. Naranja: fragmentos que no son criterios.")
    st.markdown(ui.resaltar(r["zona"], g[g.documento == nombre].cita_literal, n[n.documento == nombre].texto_literal),
                unsafe_allow_html=True)
