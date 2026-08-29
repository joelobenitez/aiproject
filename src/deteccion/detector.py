"""Deteccion de cruce de umbral con histeresis y cooldown en memoria (Principio II).

FR-010: una alerta en curso para el mismo equipo+variable no genera una alerta nueva
mientras el cooldown este activo, salvo que la severidad escale (ALERTA -> CRITICO), caso
en el que el cooldown se reinicia (research.md).
"""
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from src import config
from src.deteccion import umbrales

NORMAL, ALERTA, CRITICO = "NORMAL", "ALERTA", "CRITICO"
_ORDEN_SEVERIDAD = {NORMAL: 0, ALERTA: 1, CRITICO: 2}


@dataclass
class EventoAlerta:
    equipo_id: str
    variable: str
    valor: float
    severidad: str
    timestamp: datetime
    es_escalada: bool


class Detector:
    def __init__(self, cooldown_minutos: Optional[int] = None):
        self._cooldown = timedelta(minutes=cooldown_minutos if cooldown_minutos is not None else config.COOLDOWN_MINUTOS)
        self._estado: dict[tuple[str, str], dict] = {}

    def evaluar(
        self, equipo_id: str, tipo_equipo: str, variable: str, valor: float, timestamp: datetime
    ) -> Optional[EventoAlerta]:
        umbral = umbrales.obtener(tipo_equipo, variable)
        if umbral is None:
            return None

        severidad = self._clasificar(valor, umbral)
        clave = (equipo_id, variable)
        estado = self._estado.get(clave, {"severidad": NORMAL, "cooldown_hasta": None})

        if severidad == NORMAL:
            self._estado[clave] = {"severidad": NORMAL, "cooldown_hasta": None}
            return None

        en_cooldown = estado["cooldown_hasta"] is not None and timestamp < estado["cooldown_hasta"]
        es_escalada = (
            estado["severidad"] != NORMAL
            and _ORDEN_SEVERIDAD[severidad] > _ORDEN_SEVERIDAD[estado["severidad"]]
        )

        if en_cooldown and not es_escalada:
            return None

        self._estado[clave] = {"severidad": severidad, "cooldown_hasta": timestamp + self._cooldown}

        return EventoAlerta(
            equipo_id=equipo_id,
            variable=variable,
            valor=valor,
            severidad=severidad,
            timestamp=timestamp,
            es_escalada=es_escalada,
        )

    @staticmethod
    def _clasificar(valor: float, umbral: dict) -> str:
        if valor >= umbral["valor_critico"]:
            return CRITICO
        if valor >= umbral["valor_alerta"]:
            return ALERTA
        return NORMAL
