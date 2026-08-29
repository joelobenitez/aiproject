"""Validacion/normalizacion del payload MQTT (contracts/mqtt-topico.md).

Un payload invalido se descarta y se loguea; nunca debe tumbar la suscripcion MQTT
ni generarse como una lectura valida.
"""
import json
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

_UNIDADES_VALIDAS = {"C", "A", "mm/s", "h"}


@dataclass
class Lectura:
    equipo_id: str
    variable: str
    valor: float
    unidad: str
    timestamp: str


def normalizar(topico: str, payload_bytes: bytes) -> Optional[Lectura]:
    partes = topico.split("/")
    if len(partes) != 5:
        logger.warning("Topico con formato inesperado: %s", topico)
        return None
    equipo_id, variable = partes[3], partes[4]

    try:
        datos = json.loads(payload_bytes)
    except (json.JSONDecodeError, UnicodeDecodeError):
        logger.warning("Payload invalido (no es JSON) en topico %s", topico)
        return None

    if not isinstance(datos, dict):
        logger.warning("Payload no es un objeto JSON en topico %s", topico)
        return None

    valor = datos.get("valor")
    unidad = datos.get("unidad")
    timestamp = datos.get("timestamp")

    if isinstance(valor, bool) or not isinstance(valor, (int, float)):
        logger.warning("Payload sin 'valor' numerico en topico %s: %s", topico, datos)
        return None
    if not isinstance(unidad, str) or unidad not in _UNIDADES_VALIDAS:
        logger.warning("Payload con 'unidad' invalida en topico %s: %s", topico, datos)
        return None
    if not isinstance(timestamp, str):
        logger.warning("Payload sin 'timestamp' valido en topico %s: %s", topico, datos)
        return None
    try:
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        logger.warning("Payload con 'timestamp' no parseable en topico %s: %s", topico, datos)
        return None

    return Lectura(
        equipo_id=equipo_id,
        variable=variable,
        valor=float(valor),
        unidad=unidad,
        timestamp=timestamp,
    )
