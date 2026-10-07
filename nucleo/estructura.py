"""Estación 1: del PDF a la estructura, sin LLM."""
import re, collections
import pdfplumber

def leer_pdf(ruta):
    """Cada página con sus líneas y la posición vertical de cada una."""
    paginas = []
    with pdfplumber.open(ruta) as pdf:
        for n, p in enumerate(pdf.pages, 1):
            paginas.append({"pagina": n, "alto": p.height,
                            "lineas": [{"text": l["text"], "top": l["top"], "bottom": l["bottom"]}
                                       for l in p.extract_text_lines()]})
    return paginas

def firma(texto):
    return re.sub(r"\d+", "#", texto.strip())

def detectar_ruido(paginas, umbral=0.6, franja=0.12):
    """Líneas de las franjas superior e inferior que se repiten en la mayoría de las páginas."""
    conteo = collections.Counter()
    for p in paginas:
        conteo.update({firma(l["text"]) for l in p["lineas"]
                       if l["top"] > (1 - franja) * p["alto"] or l["bottom"] < franja * p["alto"]})
    minimo = max(2, umbral * len(paginas))
    return {f for f, c in conteo.items() if c >= minimo}

def limpiar(paginas, ruido):
    """Texto sin ruido y un mapa (offset de inicio, página) para ubicar cualquier fragmento."""
    texto, mapa = "", []
    for p in paginas:
        mapa.append((len(texto), p["pagina"]))
        texto += "\n".join(l["text"] for l in p["lineas"] if firma(l["text"]) not in ruido) + "\n"
    return texto, mapa

def pagina_de(offset, mapa):
    return max(pag for ini, pag in mapa if ini <= offset)

PERFILES = {
    "COFECE_INV": {"señales": [r"Agente económico investigado", r"\bDE-[\w-]+"],
                   "secciones": ["RESULTANDO", "CONSIDERANDO", "RESUELVE"], "argumentativa": "CONSIDERANDO"},
    "COFECE_CNT": {"señales": [r"Notificantes", r"\bCNT-[\w-]+"],
                   "secciones": ["RESULTANDO", "CONSIDERANDO", "RESUELVE"], "argumentativa": "CONSIDERANDO"},
    "PJF_JD": {"señales": [r"Juzgado .{0,40}de Distrito", r"Amparo indirecto"],
               "secciones": ["RESULTANDOS", "CONSIDERANDOS", "PUNTOS RESOLUTIVOS"], "argumentativa": "CONSIDERANDOS"},
}

def clasificar(texto, ventana=800):
    """Router: cuenta las señales de cada perfil en el encabezado y elige el que más tenga."""
    cabeza = texto[:ventana]
    puntajes = {nombre: sum(bool(re.search(s, cabeza)) for s in perfil["señales"])
                for nombre, perfil in PERFILES.items()}
    mejor = max(puntajes, key=puntajes.get)
    return (mejor if puntajes[mejor] > 0 else "DESCONOCIDO"), puntajes

ORDINALES = "PRIMERO|SEGUNDO|TERCERO|CUARTO|QUINTO|SEXTO|SÉPTIMO|OCTAVO|NOVENO|DÉCIMO"
RE_APARTADO = re.compile(rf"^(?P<ord>{ORDINALES})\.\s+(?P<titulo>[^.\n]+)", re.MULTILINE)

def mapa_secciones(texto, mapa, procedimiento):
    """Secciones del perfil y apartados ordinales, con offsets exactos y páginas."""
    perfil = PERFILES[procedimiento]
    secciones = [(s, m.start()) for s in perfil["secciones"]
                 for m in [re.search(rf"^{s}$", texto, re.MULTILINE)] if m]
    limites = secciones + [("FIN", len(texto))]
    filas = []
    for (sec, ini), (_, fin) in zip(limites, limites[1:]):
        aps = list(RE_APARTADO.finditer(texto, ini, fin))
        for a, sig in zip(aps, aps[1:] + [None]):
            a_fin = sig.start() if sig else fin
            filas.append({"seccion": sec, "apartado": a["ord"], "titulo": a["titulo"].strip()[:60],
                          "inicio": a.start(), "fin": a_fin,
                          "pag_ini": pagina_de(a.start(), mapa), "pag_fin": pagina_de(a_fin - 1, mapa)})
    return filas

def norm(s):
    return re.sub(r"\s+", " ", s).strip()

def procesar(ruta):
    """Todo el flujo de la estación para un documento."""
    paginas = leer_pdf(ruta)
    ruido = detectar_ruido(paginas)
    texto, mapa = limpiar(paginas, ruido)
    proc, puntajes = clasificar(texto)
    filas = mapa_secciones(texto, mapa, proc) if proc in PERFILES else []
    arg = PERFILES.get(proc, {}).get("argumentativa")
    zona = [f for f in filas if f["seccion"] == arg]
    chunks = [{"id_chunk": f"{ruta.name[:2]}-{f['apartado']}", "documento": ruta.name, "procedimiento": proc,
               "apartado": f["apartado"], "titulo": f["titulo"], "pag_ini": f["pag_ini"], "pag_fin": f["pag_fin"],
               "texto": norm(texto[f["inicio"]:f["fin"]])} for f in zona]
    texto_zona = norm(texto[zona[0]["inicio"]:zona[-1]["fin"]]) if zona else ""
    return {"paginas": paginas, "ruido": ruido, "texto": texto, "procedimiento": proc, "puntajes": puntajes,
            "mapa": filas, "zona": texto_zona, "chunks": chunks,
            "paginas_limpias": [norm(" ".join(l["text"] for l in p["lineas"] if firma(l["text"]) not in ruido)) for p in paginas]}

def anclar(paginas_limpias, cita):
    """Página donde empieza la cita (también si cruza un salto de página)."""
    c = norm(cita)
    for i, t in enumerate(paginas_limpias, 1):
        if c in t:
            return i
    for i in range(1, len(paginas_limpias)):
        if c in paginas_limpias[i - 1] + " " + paginas_limpias[i]:
            return i
    return None
