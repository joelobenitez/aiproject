"""Llamada a Claude (D8: Haiku 4.5, prompt caching) y parseo de la respuesta estructurada.

FR-013: ante cualquier fallo (timeout, error de API, respuesta no parseable) se devuelve un
resultado marcado `fallo: True` en vez de lanzar una excepcion — la Alerta que origino el
pedido ya quedo persistida independientemente de este resultado.
"""
import json
import logging

import anthropic

from src import config
from src.diagnostico import prompt as prompt_mod

logger = logging.getLogger(__name__)

_MAX_TOKENS = 1024
_TIMEOUT_SEGUNDOS = 10.0
_CLAVES_ESPERADAS = {"causa_probable", "razonamiento", "urgencia", "accion_recomendada", "confianza"}

_client: anthropic.Anthropic | None = None


def _obtener_cliente() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY)
    return _client


def diagnosticar(entrada: dict) -> dict:
    """Contrato: contracts/diagnostico-modulo.md. Nunca lanza excepcion."""
    try:
        mensajes = prompt_mod.construir_mensajes(entrada)
        if len(mensajes) >= 2:
            # Marca el ultimo mensaje del few-shot fijo para cachear ese prefijo (D8).
            mensajes[-2] = {
                "role": mensajes[-2]["role"],
                "content": [
                    {
                        "type": "text",
                        "text": mensajes[-2]["content"],
                        "cache_control": {"type": "ephemeral"},
                    }
                ],
            }

        respuesta = _obtener_cliente().messages.create(
            model=config.MODEL,
            max_tokens=_MAX_TOKENS,
            system=[
                {
                    "type": "text",
                    "text": prompt_mod.SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},
                }
            ],
            messages=mensajes,
            timeout=_TIMEOUT_SEGUNDOS,
        )
        texto = "".join(bloque.text for bloque in respuesta.content if bloque.type == "text")
        resultado = json.loads(texto)

        if not isinstance(resultado, dict) or not _CLAVES_ESPERADAS.issubset(resultado.keys()):
            logger.error("Respuesta de Claude sin las claves esperadas: %s", resultado)
            return {"fallo": True}

        resultado["fallo"] = False
        return resultado
    except Exception:
        logger.exception("Fallo la llamada o el parseo del nucleo de diagnostico")
        return {"fallo": True}
