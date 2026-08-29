"""Armado de contexto para el nucleo de diagnostico (FR-003).

Contrato de salida: ver contracts/diagnostico-modulo.md ("Entrada"). Combina tendencia 24h
(InfluxDB) con metadata del equipo y alertas previas (SQLite).
"""
from src.almacenamiento import influx_repo, sqlite_repo

_VARIABLES_MOTOR = ["temperatura", "corriente", "vibracion"]


def armar_contexto(
    equipo_id: str, variable_disparadora: str, valor: float, unidad: str, severidad: str, timestamp: str
) -> dict:
    equipo = sqlite_repo.obtener_equipo(equipo_id)
    tendencia_24h = {
        variable: influx_repo.tendencia_24h(equipo_id, variable) for variable in _VARIABLES_MOTOR
    }
    alertas_previas = [
        {
            "variable_disparadora": alerta["variable_disparadora"],
            "valor": alerta["valor"],
            "severidad": alerta["severidad"],
            "timestamp": alerta["timestamp"],
        }
        for alerta in sqlite_repo.obtener_alertas_previas(equipo_id, limite=5)
    ]

    return {
        "equipo": {
            "id": equipo["id"],
            "nombre": equipo["nombre"],
            "horas_operacion_acumuladas": equipo["horas_operacion_acumuladas"],
        },
        "alerta": {
            "variable_disparadora": variable_disparadora,
            "valor": valor,
            "unidad": unidad,
            "severidad": severidad,
            "timestamp": timestamp,
        },
        "tendencia_24h": tendencia_24h,
        "alertas_previas": alertas_previas,
    }
