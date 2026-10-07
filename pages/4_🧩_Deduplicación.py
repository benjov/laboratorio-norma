"""Estación 4 · Deduplicación: proponer, decidir, vetar."""
import pandas as pd
import streamlit as st
from nucleo import ui, dedup
from nucleo.datos import gold, taxonomia

ui.configurar("Deduplicación", "🧩")
st.title("🧩 Estación 4 · Deduplicación")
st.markdown("Distintas resoluciones repiten el mismo criterio con otras palabras. Si no los juntamos, la base cuenta de más "
            "y el abogado no ve que un criterio se sostiene en varias resoluciones. Lo hacemos en tres capas:")
c1, c2, c3 = st.columns(3)
c1.info("**1 · Proponer** con similitud de textos. Gratis.")
c2.info("**2 · Decidir** con Claude como juez. Una llamada por par.")
c3.info("**3 · Vetar** con reglas en Python: mismo tema y artículos compatibles. Gratis y auditable.")

opciones = ["Gold del curso: 22 criterios, 2 duplicados conocidos"]
if st.session_state.get("validadas"):
    opciones.append("Mis criterios aceptados en la estación 3")
base_sel = st.radio("¿Sobre qué base?", opciones, horizontal=True)
es_gold = base_sel.startswith("Gold")

if es_gold:
    g = gold()
    filas = [{"id": r.id_criterio, "criterio": r.criterio, "cita_literal": r.cita_literal, "documento": r.documento,
              "pagina": int(r.pagina), "id_tema": r.id_tema, "articulos": r.articulos if isinstance(r.articulos, str) else ""}
             for r in g.itertuples()]
    dups = {tuple(sorted((r.id_criterio, r.duplicado_de))) for r in g.itertuples() if pd.notna(r.duplicado_de)}
else:
    acep = [f for f in st.session_state["validadas"] if f["aceptado"]]
    filas = [{**f, "id": f"E{i + 1:02d}"} for i, f in enumerate(acep)]
    dups = None
por_id = {f["id"]: f for f in filas}
if len(filas) < 2:
    st.info("Hacen falta al menos dos criterios para buscar duplicados.")
    st.stop()

@st.cache_data
def matriz(textos):
    return dedup.similitudes(textos)

S, metodo = matriz(tuple(f["criterio"] for f in filas))
df = pd.DataFrame(dedup.pares([f["id"] for f in filas], S)).sort_values("sim", ascending=False)
if dups is not None:
    df["duplicado_real"] = [tuple(sorted((a, b))) in dups for a, b in zip(df.a, df.b)]

st.markdown(f"#### 1 · Proponer · similitud por {metodo}")
defecto = round(float(df[df.duplicado_real].sim.min()) - 0.05, 2) if dups is not None and len(df) else 0.6
umbral = st.slider("Umbral de similitud: los pares por encima son candidatos", 0.0, 1.0, max(0.0, defecto), 0.01)
cand = df[df.sim >= umbral].copy()
c1, c2 = st.columns(2)
c1.metric("Candidatos", f"{len(cand)} de {len(df)} pares posibles")
if dups is not None:
    c2.metric("Duplicados reales entre los candidatos", f"{int(cand.duplicado_real.sum())} de {len(dups)}")
st.dataframe(df.head(15), hide_index=True, use_container_width=True)
st.caption("Los 15 pares más parecidos. Un candidato de más cuesta una llamada al juez; un duplicado que no entra se pierde para siempre.")

st.markdown("#### 2 · Decidir · Claude como juez")
st.session_state.setdefault("juicios", {})
if st.button(f"Juzgar los {len(cand)} candidatos con Claude", type="primary", disabled=len(cand) == 0):
    for a, b in zip(cand.a, cand.b):
        j = ui.con_claude(dedup.juzgar, por_id[a]["criterio"], por_id[b]["criterio"], ui.key(), ui.sesion())
        if j is None and not ui.key():
            break
        st.session_state["juicios"][(a, b)] = j
reglas_on = st.checkbox("3 · Vetar: aplicar las reglas duras", value=True)

def decision(a, b):
    j = st.session_state["juicios"].get((a, b))
    juez = bool(j and j.mismo_criterio and j.confianza >= 0.85)
    reglas = dedup.puede_fusionar(por_id[a], por_id[b])
    return juez, reglas, (juez and (reglas or not reglas_on)), (j.razon if j else "")

juzgados = [(a, b) for a, b in zip(cand.a, cand.b) if (a, b) in st.session_state["juicios"]]
if juzgados:
    tabla = []
    for a, b in juzgados:
        juez, reglas, fusion, razon = decision(a, b)
        tabla.append({"a": a, "b": b, "juez": juez, "reglas": reglas, "fusionar": fusion, "razón del juez": razon})
    t = pd.DataFrame(tabla)
    st.dataframe(t, hide_index=True, use_container_width=True)
    fusiones = [(r["a"], r["b"]) for r in tabla if r["fusionar"]]
    if dups is not None:
        pred = {tuple(sorted(p)) for p in fusiones}
        vp = len(pred & dups)
        c1, c2 = st.columns(2)
        c1.metric("Precisión de las fusiones", f"{vp / max(len(pred), 1):.2f}")
        c2.metric("Exhaustividad de las fusiones", f"{vp / len(dups):.2f}")
    grupos = dedup.consolidar(filas, fusiones)
    st.markdown(f"#### Resultado: {len(filas)} criterios → {len(grupos)} tras deduplicar")
    tax = taxonomia()
    for gr in grupos:
        if len(gr) > 1:
            with st.container(border=True):
                st.markdown(f"**{gr[0]['criterio']}**")
                st.caption(tax.get(gr[0]["id_tema"], ""))
                for f in gr:
                    st.markdown(f"↳ `{f['documento']}` p. {f['pagina']}: «{f['cita_literal'][:110]}…»")

if es_gold:
    with st.expander("🎯 Reto · prueba de estrés: dos criterios vecinos"):
        st.markdown("C09 («qué elementos considera la multa») y C21 («cómo debe motivarse la multa») suenan parecido, pero son "
                    "criterios distintos. Juzga el par aunque no sea candidato: ¿acierta el juez? Si se equivoca, ¿lo corrigen las reglas?")
        for x in ("C09", "C21"):
            st.markdown(f"- **{x}** [{por_id[x]['id_tema']}] {por_id[x]['criterio']}")
        if st.button("Juzgar C09 contra C21"):
            j = ui.con_claude(dedup.juzgar, por_id["C09"]["criterio"], por_id["C21"]["criterio"], ui.key(), ui.sesion())
            if j is not None:
                st.write(f"**Juez:** {'mismo criterio' if j.mismo_criterio else 'criterios distintos'} (confianza {j.confianza:.2f}). {j.razon}")
                st.write(f"**Reglas:** {'permiten' if dedup.puede_fusionar(por_id['C09'], por_id['C21']) else 'vetan'} la fusión: "
                         "están en nodos distintos de la taxonomía.")
ui.ver_codigo(dedup.puede_fusionar, dedup.consolidar)
