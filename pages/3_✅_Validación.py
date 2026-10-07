"""Estación 3 · ¿Es un criterio? ¿Dice lo mismo que la cita?"""
import pandas as pd
import streamlit as st
from nucleo import ui, validacion
from nucleo.datos import gold, negativos, pares_fidelidad

ui.configurar("Validación", "✅")
st.title("✅ Estación 3 · Validación y fidelidad")
st.markdown("Una cita literal garantiza que el texto **existe**, no que sea un criterio. Aquí agregamos dos controles, "
            "y antes de confiar en ellos los **medimos** contra fragmentos cuya respuesta ya conocemos.")

t1, t2, t3 = st.tabs(["1 · El validador", "2 · El gate de fidelidad", "3 · Aplicar a mis extracciones"])

with t1:
    st.markdown("El validador clasifica un fragmento en siete categorías: criterio, hecho, transcripción, argumento de parte, "
                "valoración de prueba, aplicación al caso o trámite. Lo probamos con **30 fragmentos etiquetados**: "
                "22 criterios del gold y 8 que no lo son.")
    g, n = gold(), negativos()
    etiquetados = ([{"documento": d, "texto": t, "real": "criterio"} for d, t in zip(g.documento, g.cita_literal)]
                   + [{"documento": d, "texto": t, "real": r} for d, t, r in zip(n.documento, n.texto_literal, n.tipo)])
    if st.button("Clasificar los 30 fragmentos con Claude", type="primary"):
        barra, res = st.progress(0.0), []
        for i, e in enumerate(etiquetados, 1):
            ctx = ui.apartado_de(e["texto"], e["documento"])
            v = ui.con_claude(validacion.validar, e["texto"], ctx["texto"] if ctx else "", ui.key(), ui.sesion())
            if v is None and not ui.key():
                break
            res.append(v)
            barra.progress(i / len(etiquetados))
        if len(res) == len(etiquetados):
            st.session_state["veredictos"] = res

    if "veredictos" in st.session_state:
        umbral = st.slider("Confianza mínima para aceptar un criterio", 0.5, 0.95, 0.7, 0.05,
                           help="Mueve el umbral: no se vuelve a llamar al modelo, solo se recalcula.")
        df = pd.DataFrame(etiquetados)
        vs = st.session_state["veredictos"]
        df["predicho"] = [v.tipo if v else "inválido" for v in vs]
        df["confianza"] = [v.confianza if v else None for v in vs]
        df["razon"] = [v.razon if v else "" for v in vs]
        df["aceptado"] = [validacion.aceptar(v, umbral) for v in vs]
        df["es_criterio"] = df.real == "criterio"
        vp = int((df.aceptado & df.es_criterio).sum()); fp = int((df.aceptado & ~df.es_criterio).sum())
        fn = int((~df.aceptado & df.es_criterio).sum())
        c1, c2, c3 = st.columns(3)
        c1.metric("Precisión", f"{vp / max(vp + fp, 1):.2f}", help="De lo que aceptó, ¿cuánto era criterio?")
        c2.metric("Exhaustividad", f"{vp / max(vp + fn, 1):.2f}", help="De los criterios, ¿cuántos aceptó?")
        c3.metric("Errores", fp + fn)
        st.dataframe(pd.crosstab(df.real, df.predicho), use_container_width=True)
        errores = df[df.aceptado != df.es_criterio]
        if len(errores):
            st.markdown("**Errores, con la razón que dio el validador:**")
            st.dataframe(errores[["real", "predicho", "confianza", "texto", "razon"]], hide_index=True, use_container_width=True)
        with st.expander("🎯 Reto"):
            st.markdown("Sube el umbral hasta 0.95 y bájalo hasta 0.5. ¿Qué pasa con la precisión y la exhaustividad? "
                        "En una base que consultan abogados, ¿qué error es más caro: un hecho que se cuela o un criterio que se pierde?")
    ui.ver_codigo(validacion.validar, validacion.aceptar)

with t2:
    st.markdown("Un criterio real puede **resumirse mal**. La falla típica es la generalización: la cita dice «puede» y la "
                "abstracción dice «siempre». Revisar todo con el modelo cuesta, así que primero un filtro barato marca las "
                "abstracciones **de riesgo** y solo esas pasan por el gate.")
    palabras = [p.strip() for p in st.text_input("Palabras de riesgo (separadas por comas)",
                "todo, toda, todos, todas, siempre, nunca, cualquier, ningún, ninguna").split(",") if p.strip()]
    sin_filtro = st.checkbox("Revisar todos los pares, sin filtro de riesgo")
    pares = pares_fidelidad()
    fuente = gold().set_index("id_criterio")
    pares["de_riesgo"] = [sin_filtro or validacion.es_de_riesgo(a, palabras) for a in pares.abstraccion]
    st.dataframe(pares[["id", "abstraccion", "de_riesgo"]], hide_index=True, use_container_width=True)
    if st.button("Evaluar con el gate", type="primary"):
        filas = []
        for _, p in pares.iterrows():
            g_ = fuente.loc[p.criterio_fuente]
            v = None
            if p.de_riesgo:
                ctx = ui.apartado_de(g_.cita_literal, g_.documento)
                v = ui.con_claude(validacion.gate, g_.cita_literal, p.abstraccion, ctx["texto"] if ctx else "", ui.key(), ui.sesion())
            final = "fiel" if not p.de_riesgo else (v.etiqueta if v else "sin respuesta")
            filas.append({"id": p.id, "cita": g_.cita_literal, "abstraccion": p.abstraccion, "real": p.etiqueta,
                          "veredicto": final, "revisado": bool(p.de_riesgo), "razon": v.razon if v else ""})
        st.session_state["fidelidad"] = pd.DataFrame(filas)
    if "fidelidad" in st.session_state:
        fid = st.session_state["fidelidad"]
        c1, c2 = st.columns(2)
        c1.metric("Aciertos", f"{int((fid.real == fid.veredicto).sum())} de {len(fid)}")
        c2.metric("Pares revisados por el gate", f"{int(fid.revisado.sum())} de {len(fid)}")
        st.dataframe(fid, hide_index=True, use_container_width=True)
    with st.expander("🎯 Reto"):
        st.markdown("Hay una generalización que el filtro deja pasar: no usa ninguna palabra universal y aun así convierte "
                    "un indicador en una regla. Encuéntrala. ¿Qué palabra agregarías a la lista para atraparla? "
                    "¿Y cuánto costaría revisar todo, sin filtro?")
    ui.ver_codigo(validacion.es_de_riesgo, validacion.gate)

with t3:
    todas = [f for e in st.session_state["extracciones"].values() for f in e["filas"] if f["estado"] == "verificado"]
    if not todas:
        st.info("Primero extrae criterios en la estación 2.")
    else:
        st.markdown(f"Tienes **{len(todas)} criterios con cita verificada**. Pásalos por el validador y, si son de riesgo, por el gate.")
        umbral = st.slider("Confianza mínima", 0.5, 0.95, 0.7, 0.05, key="umbral_mias")
        if st.button("Validar mis extracciones", type="primary"):
            barra, salida = st.progress(0.0), []
            for i, f in enumerate(todas, 1):
                ctx = ui.apartado_de(f["cita_literal"], f["documento"])
                v = ui.con_claude(validacion.validar, f["cita_literal"], ctx["texto"] if ctx else "", ui.key(), ui.sesion())
                ok = validacion.aceptar(v, umbral)
                fid = "no_aplica"
                if ok:
                    if validacion.es_de_riesgo(f["criterio"], palabras):
                        g_ = ui.con_claude(validacion.gate, f["cita_literal"], f["criterio"], ctx["texto"] if ctx else "", ui.key(), ui.sesion())
                        fid = g_.etiqueta if g_ else "sin respuesta"
                    else:
                        fid = "sin_riesgo"
                salida.append({**f, "tipo_validador": v.tipo if v else "sin respuesta", "fidelidad": fid,
                               "aceptado": ok and fid in ("fiel", "sin_riesgo")})
                barra.progress(i / len(todas))
            st.session_state["validadas"] = salida
        if "validadas" in st.session_state:
            df = pd.DataFrame(st.session_state["validadas"])
            st.metric("Criterios aceptados", f"{int(df.aceptado.sum())} de {len(df)}")
            st.markdown("**Descartados:**")
            st.dataframe(df[~df.aceptado][["id_chunk", "tipo_validador", "fidelidad", "cita_literal"]], hide_index=True, use_container_width=True)
