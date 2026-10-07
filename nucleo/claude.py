"""Llamadas a Claude con esquema forzado, caché compartida y control de gasto por sesión."""
import json, hashlib, threading
from pathlib import Path
import anthropic

MODELO = "claude-haiku-4-5"
PRECIOS = {"claude-haiku-4-5": (1.0, 5.0)}  # USD por millón de tokens (entrada, salida)
RESPALDO = Path(__file__).resolve().parent.parent / "datos" / "respaldo" / "cache.json"

_cache = json.load(open(RESPALDO, encoding="utf-8")) if RESPALDO.exists() else {}
_candado = threading.Lock()

class SinKey(Exception):
    """No hay key y la respuesta no está en caché."""

class SinSaldo(Exception):
    """La sesión alcanzó su límite de gasto."""

def clave(sistema, usuario, herramienta):
    base = json.dumps([MODELO, sistema, usuario, herramienta["input_schema"]], ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(base.encode()).hexdigest()

def llamar(sistema, usuario, herramienta, key, sesion, max_tokens=1500, limite_usd=1.5, etapa=""):
    """Devuelve el input de la herramienta. `sesion` es un dict con 'gasto' y 'registro'.
    La caché es compartida: si alguien ya hizo exactamente esta llamada, no se vuelve a pagar."""
    k = clave(sistema, usuario, herramienta)
    with _candado:
        if k in _cache:
            sesion.setdefault("registro", []).append({"etapa": etapa, "desde_cache": True, "entrada": 0, "salida": 0, "costo": 0.0})
            return _cache[k]
    if not key:
        raise SinKey()
    if sesion.get("gasto", 0.0) >= limite_usd:
        raise SinSaldo()
    r = anthropic.Anthropic(api_key=key).messages.create(
        model=MODELO, max_tokens=max_tokens, system=sistema, tools=[herramienta],
        tool_choice={"type": "tool", "name": herramienta["name"]},
        messages=[{"role": "user", "content": usuario}])
    salida = next(b.input for b in r.content if b.type == "tool_use")
    p_in, p_out = PRECIOS[MODELO]
    costo = (r.usage.input_tokens * p_in + r.usage.output_tokens * p_out) / 1e6
    sesion["gasto"] = sesion.get("gasto", 0.0) + costo
    sesion.setdefault("registro", []).append({"etapa": etapa, "desde_cache": False, "entrada": r.usage.input_tokens,
                                              "salida": r.usage.output_tokens, "costo": costo})
    with _candado:
        _cache[k] = salida
    return salida

def exportar_cache(ruta):
    """Para el instructor: guarda la caché acumulada como respaldo para la siguiente sesión."""
    with _candado:
        json.dump(_cache, open(ruta, "w", encoding="utf-8"), ensure_ascii=False)
    return len(_cache)

def esquema_plano(modelo):
    """JSON Schema de Pydantic con las referencias $ref resueltas en línea."""
    s = modelo.model_json_schema()
    defs = s.pop("$defs", {})
    def resolver(x):
        if isinstance(x, dict):
            if "$ref" in x:
                return resolver(defs[x["$ref"].split("/")[-1]])
            return {k: resolver(v) for k, v in x.items()}
        return [resolver(v) for v in x] if isinstance(x, list) else x
    return resolver(s)
