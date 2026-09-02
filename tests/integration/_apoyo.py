"""Utilidades compartidas por los tests de integracion de los escenarios A-D.

No es un modulo de test (no empieza con `test_`); publica una lectura por variable por
tick, exactamente como lo haria el emulador real, pero invocando el handler del servicio
directamente en vez de pasar por un broker MQTT real.
"""
import json
import random
from datetime import datetime, timedelta, timezone

from src import main as servicio

_UNIDADES = {"temperatura": "C", "corriente": "A", "vibracion": "mm/s"}


def correr_escenario(generar, ticks: int = 40, segundos_por_tick: int = 1, semilla: int = 42) -> None:
    random.seed(semilla)
    base = datetime(2026, 8, 29, 12, 0, 0, tzinfo=timezone.utc)
    for i in range(ticks):
        t = i / max(ticks - 1, 1)
        timestamp = (base + timedelta(seconds=i * segundos_por_tick)).isoformat().replace("+00:00", "Z")
        for variable, valor in generar(t).items():
            topico = f"demo/planta1/linea_a/motor_001/{variable}"
            payload = json.dumps(
                {"valor": round(valor, 2), "unidad": _UNIDADES[variable], "timestamp": timestamp}
            ).encode()
            servicio._al_recibir_mensaje(topico, payload)
            _procesar_cola_sincrono()


def _procesar_cola_sincrono() -> None:
    """Estos tests no corren el worker en un hilo aparte (D19/tasks.md T003): procesan la cola
    en el mismo hilo de test, en orden, para mantener el determinismo de las aserciones."""
    while not servicio._cola.empty():
        lectura = servicio._cola.get_nowait()
        servicio._procesar_lectura(lectura)
