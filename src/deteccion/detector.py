"""Deteccion de cruce de umbral con histeresis y cooldown en memoria (Principio II).

FR-010: una alerta en curso para el mismo equipo+variable no genera una alerta nueva
mientras el cooldown este activo, salvo que la severidad escale (ALERTA -> CRITICO), caso
en el que el cooldown se reinicia (research.md).

FR-004 (H3, D20): para filtrar ruido, un evento nuevo (primera alerta o escalada) solo se
genera despues de `CONFIRMACION_LECTURAS` lecturas consecutivas por encima del umbral, y la
vuelta a NORMAL exige bajar `BANDA_MUERTA` por debajo de `valor_alerta` (no alcanza con
cruzar el umbral en sentido inverso). El contador de lecturas consecutivas es efimero (no se
persiste, a diferencia de `severidad`/`cooldown_hasta` de H4).

FR-005/FR-006 (H4, D20): `severidad`/`cooldown_hasta` por (equipo,variable) se persisten en
SQLite (`detector_estado`, `data-model.md`) — se cargan una sola vez al construir el
`Detector` y se graban solo cuando `evaluar()` cambia alguno de los dos (no en cada lectura,
Principio II). Un timestamp de lectura desfasado mas de 5 minutos respecto del reloj del
servidor no se descarta: se evalua igual, pero usando el reloj del servidor (no el del
payload) para el calculo/comparacion de cooldown, y se loguea un warning.
"""
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

from src import config
from src.almacenamiento import sqlite_repo
from src.deteccion import umbrales

logger = logging.getLogger(__name__)

NORMAL, ALERTA, CRITICO = "NORMAL", "ALERTA", "CRITICO"
_ORDEN_SEVERIDAD = {NORMAL: 0, ALERTA: 1, CRITICO: 2}

CONFIRMACION_LECTURAS = 3
BANDA_MUERTA = 0.05
SKEW_MAXIMO = timedelta(minutes=5)


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
        self._estado: dict[tuple[str, str], dict] = {
            clave: {**estado, "lecturas_consecutivas": 0}
            for clave, estado in sqlite_repo.cargar_estado_detector().items()
        }

    def evaluar(
        self, equipo_id: str, tipo_equipo: str, variable: str, valor: float, timestamp: datetime
    ) -> Optional[EventoAlerta]:
        umbral = umbrales.obtener(tipo_equipo, variable)
        if umbral is None:
            return None

        timestamp = self._resolver_skew(timestamp)

        clasificacion = self._clasificar(valor, umbral)
        clave = (equipo_id, variable)
        estado = self._estado.get(clave, {"severidad": NORMAL, "cooldown_hasta": None, "lecturas_consecutivas": 0})

        if clasificacion == NORMAL:
            # Banda muerta (FR-004): una alerta en curso solo vuelve a NORMAL si el valor cae
            # por debajo de `valor_alerta * (1 - BANDA_MUERTA)`, no apenas cruza el umbral en
            # sentido inverso — evita reactivar/desactivar en cada lectura ruidosa.
            en_banda_muerta = estado["severidad"] != NORMAL and valor >= umbral["valor_alerta"] * (1 - BANDA_MUERTA)
            if en_banda_muerta:
                nuevo_estado = {**estado, "lecturas_consecutivas": 0}
            else:
                nuevo_estado = {"severidad": NORMAL, "cooldown_hasta": None, "lecturas_consecutivas": 0}
            self._actualizar_estado(equipo_id, variable, estado, nuevo_estado)
            return None

        lecturas_consecutivas = estado["lecturas_consecutivas"] + 1
        en_cooldown = estado["cooldown_hasta"] is not None and timestamp < estado["cooldown_hasta"]
        es_escalada = (
            estado["severidad"] != NORMAL
            and _ORDEN_SEVERIDAD[clasificacion] > _ORDEN_SEVERIDAD[estado["severidad"]]
        )

        # Confirmacion por lecturas consecutivas (FR-004): recien alcanzado el umbral, hace
        # falta sostenerlo `CONFIRMACION_LECTURAS` veces seguidas antes de generar un evento.
        if lecturas_consecutivas < CONFIRMACION_LECTURAS:
            self._actualizar_estado(equipo_id, variable, estado, {**estado, "lecturas_consecutivas": lecturas_consecutivas})
            return None

        if en_cooldown and not es_escalada:
            self._actualizar_estado(equipo_id, variable, estado, {**estado, "lecturas_consecutivas": lecturas_consecutivas})
            return None

        nuevo_estado = {
            "severidad": clasificacion,
            "cooldown_hasta": timestamp + self._cooldown,
            "lecturas_consecutivas": lecturas_consecutivas,
        }
        self._actualizar_estado(equipo_id, variable, estado, nuevo_estado)

        return EventoAlerta(
            equipo_id=equipo_id,
            variable=variable,
            valor=valor,
            severidad=clasificacion,
            timestamp=timestamp,
            es_escalada=es_escalada,
        )

    def _actualizar_estado(self, equipo_id: str, variable: str, estado_anterior: dict, estado_nuevo: dict) -> None:
        clave = (equipo_id, variable)
        self._estado[clave] = estado_nuevo
        if (estado_anterior["severidad"], estado_anterior["cooldown_hasta"]) == (
            estado_nuevo["severidad"],
            estado_nuevo["cooldown_hasta"],
        ):
            return
        sqlite_repo.guardar_estado_detector(equipo_id, variable, estado_nuevo["severidad"], estado_nuevo["cooldown_hasta"])

    @staticmethod
    def _resolver_skew(timestamp: datetime) -> datetime:
        ahora = datetime.now(timezone.utc)
        if abs((timestamp - ahora).total_seconds()) <= SKEW_MAXIMO.total_seconds():
            return timestamp
        logger.warning(
            "Timestamp de lectura desfasado mas de %s respecto del reloj del servidor "
            "(payload=%s, servidor=%s) — se usa el reloj del servidor para el cooldown",
            SKEW_MAXIMO,
            timestamp.isoformat(),
            ahora.isoformat(),
        )
        return ahora

    @staticmethod
    def _clasificar(valor: float, umbral: dict) -> str:
        if valor >= umbral["valor_critico"]:
            return CRITICO
        if valor >= umbral["valor_alerta"]:
            return ALERTA
        return NORMAL
