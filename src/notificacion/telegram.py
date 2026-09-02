"""Cliente Telegram Nivel 0 (D2): notificacion push via Bot API
(contracts/notificacion-telegram.md).

D13: para severidad ALERTA el diagnostico de IA es bajo demanda, no automatico — el mensaje
crudo (`formatear_mensaje_crudo`) reemplaza al diagnostico en ese caso.
"""
import logging
import time

import httpx

from src import config

logger = logging.getLogger(__name__)

_URL_BASE = "https://api.telegram.org/bot{token}/sendMessage"
_MAX_INTENTOS = 3
_ESPERA_BASE_SEGUNDOS = 1.0


def formatear_mensaje_exitoso(
    equipo_nombre: str,
    variable: str,
    valor: float,
    unidad: str,
    umbral: float,
    severidad: str,
    resultado: dict,
) -> str:
    hechos = "\n".join(f"- {hecho}" for hecho in resultado.get("hechos_destacados") or [])
    return (
        f"[{severidad}] {equipo_nombre}\n"
        f"Variable: {variable} = {valor} {unidad} (umbral: {umbral} {unidad})\n\n"
        f"{resultado['resumen_ejecutivo']}\n\n"
        f"Hechos:\n{hechos}"
    )


def formatear_mensaje_fallback(
    equipo_nombre: str, variable: str, valor: float, unidad: str, umbral: float, severidad: str
) -> str:
    return (
        f"[{severidad}] {equipo_nombre}\n"
        f"Variable: {variable} = {valor} {unidad} (umbral: {umbral} {unidad})\n\n"
        f"Resumen no disponible (fallo temporal del servicio de IA). Revisar manualmente."
    )


def formatear_mensaje_crudo(
    equipo_nombre: str, variable: str, valor: float, unidad: str, umbral: float, severidad: str, alerta_id: int
) -> str:
    return (
        f"[{severidad}] {equipo_nombre}\n"
        f"Variable: {variable} = {valor} {unidad} (umbral: {umbral} {unidad})\n\n"
        f"Resumen de IA disponible bajo demanda para la alerta #{alerta_id} "
        f"(POST /diagnosticar/{alerta_id})."
    )


def enviar(mensaje: str) -> bool:
    """Envia el mensaje via Bot API con reintentos simples.

    Nunca lanza excepcion: un fallo de notificacion no debe tumbar el pipeline (misma
    filosofia que FR-013 aplicada al canal de salida) — la Alerta y el Diagnostico ya
    quedaron persistidos antes de llegar aca.
    """
    if not config.TELEGRAM_BOT_TOKEN or not config.TELEGRAM_CHAT_ID:
        logger.warning("Notificacion Telegram omitida: falta TELEGRAM_BOT_TOKEN o TELEGRAM_CHAT_ID")
        return False

    url = _URL_BASE.format(token=config.TELEGRAM_BOT_TOKEN)
    for intento in range(1, _MAX_INTENTOS + 1):
        try:
            respuesta = httpx.post(
                url, json={"chat_id": config.TELEGRAM_CHAT_ID, "text": mensaje}, timeout=10.0
            )
            respuesta.raise_for_status()
            return True
        except httpx.HTTPError:
            logger.warning("Fallo el intento %s/%s de enviar notificacion Telegram", intento, _MAX_INTENTOS)
            if intento < _MAX_INTENTOS:
                time.sleep(_ESPERA_BASE_SEGUNDOS * intento)

    logger.error("No se pudo enviar la notificacion Telegram luego de %s intentos", _MAX_INTENTOS)
    return False
