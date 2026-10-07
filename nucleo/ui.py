"""Piezas de interfaz compartidas por todas las estaciones."""
import html, inspect
import streamlit as st
import anthropic
from .claude import SinKey, SinSaldo
from .datos import PDFS, NOMBRES
from . import estructura

def limite_sesion():
    try:
        return float(st.secrets.get("LIMITE_SESION_USD", 1.5))
    except Exception:
        return 1.5

def configurar(titulo, icono="⚖️"):
    st.set_page_config(page_title=f"{titulo} · Laboratorio Norma+", page_icon=icono, layout="wide")
    st.session_state.setdefault("sesion", {"gasto": 0.0, "registro": []})
    st.session_state.setdefault("extracciones", {})
    with st.sidebar:
        st.markdown("### Tu API key")
        st.session_state["api_key"] = st.text_input(
            "Pega la key que te dieron", type="password", value=st.session_state.get("api_key", ""),
            help="Se guarda solo mientras tengas abierta esta pestaña; nunca se escribe en disco.")
        if not st.session_state["api_key"]:
            st.info("Sin key solo verás resultados que ya se calcularon antes.")
        s = st.session_state["sesion"]
        pagadas = sum(1 for r in s["registro"] if not r["desde_cache"])
        cache = len(s["registro"]) - pagadas
        st.metric("Gasto de esta sesión", f"USD {s['gasto']:.4f}", help=f"Límite por sesión: USD {limite_sesion():.2f}")
        st.caption(f"{pagadas} llamadas pagadas · {cache} desde caché")
        st.divider()
        st.caption("Documentos ficticios, escritos con el formato de la COFECE y del PJF para fines didácticos.")

def key():
    return st.session_state.get("api_key", "").strip()

def sesion():
    return st.session_state["sesion"]

def con_claude(funcion, *args, **kwargs):
    """Ejecuta una función que llama a Claude y traduce los errores a mensajes para el alumno."""
    try:
        return funcion(*args, **kwargs)
    except SinKey:
        st.warning("Esta respuesta todavía no está calculada. Pega tu API key en la barra lateral para generarla.")
    except SinSaldo:
        st.error("Llegaste al límite de gasto de esta sesión. Sigue con los resultados en pantalla o avisa a Imanol.")
    except anthropic.AuthenticationError:
        st.error("La key no es válida. Revisa que la copiaste completa.")
    except anthropic.RateLimitError:
        st.warning("Demasiadas llamadas por minuto. Espera unos segundos y vuelve a intentar.")
    except anthropic.APIStatusError as e:
        st.error(f"La API respondió con un error ({e.status_code}). Intenta de nuevo en un momento.")
    except anthropic.APIConnectionError:
        st.error("No hay conexión con la API. Intenta de nuevo en un momento.")
    return None

def ver_codigo(*funciones, titulo="Ver el código"):
    """El código real que corre en esta estación."""
    with st.expander(titulo):
        for f in funciones:
            st.code(inspect.getsource(f), language="python")

def resaltar(texto, verdes=(), naranjas=()):
    """Texto con fragmentos marcados: azul = criterio, naranja = no criterio o cita no literal."""
    t = html.escape(texto)
    for frag, color in [(f, "#cfe3ee") for f in verdes] + [(f, "#f6d6c2") for f in naranjas]:
        f = html.escape(estructura.norm(frag))
        if f and f in t:
            t = t.replace(f, f'<mark style="background:{color};padding:0 2px">{f}</mark>')
    return f'<div style="line-height:1.7;font-size:1rem;background:#fffdf8;padding:1rem 1.25rem;border:1px solid #d9d4c8;border-radius:8px">{t}</div>'

@st.cache_resource
def procesado(nombre):
    ruta = next(p for p in PDFS if p.name == nombre)
    return estructura.procesar(ruta)

def todos_los_chunks():
    return [c for p in PDFS for c in procesado(p.name)["chunks"]]

def selector_documento(clave="doc"):
    return st.selectbox("Documento", [p.name for p in PDFS], format_func=lambda n: NOMBRES.get(n, n), key=clave)

@st.cache_data
def imagen_pagina(nombre, pagina):
    """Render de la página del PDF; si pypdfium2 no está disponible, devuelve None."""
    try:
        import pypdfium2 as pdfium
        ruta = next(p for p in PDFS if p.name == nombre)
        return pdfium.PdfDocument(str(ruta))[pagina - 1].render(scale=1.4).to_pil()
    except Exception:
        return None

def apartado_de(fragmento, documento=None):
    """Texto del apartado (chunk) que contiene un fragmento, para dar contexto al modelo."""
    f = estructura.norm(fragmento)
    for c in todos_los_chunks():
        if (documento is None or c["documento"] == documento) and f in c["texto"]:
            return c
    return None
