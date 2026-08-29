"""Emulador del motor industrial — publica los 4 escenarios A-D via MQTT.

No es parte del sistema en si: cumple el rol que ocupara el RUT956 real en produccion
(D11). Ver definicion/caso_de_uso_fase1.md para la descripcion de cada escenario y
contracts/mqtt-topico.md para el formato de topico/payload.
"""
import argparse
import json
import random
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import paho.mqtt.client as mqtt

from src import config

HORAS_OPERACION_INICIALES = 4820.0
_UNIDADES = {"temperatura": "C", "corriente": "A", "vibracion": "mm/s", "horas_operacion": "h"}


def _lineal(inicio: float, fin: float, t: float) -> float:
    return inicio + (fin - inicio) * t


def _con_ruido(valor: float, amplitud: float) -> float:
    return valor + random.uniform(-amplitud, amplitud)


def _escenario_a(t: float) -> dict:
    """Degradacion de refrigeracion: temperatura sube, corriente y vibracion estables."""
    return {
        "temperatura": _con_ruido(_lineal(60, 88, t), 0.8),
        "corriente": _con_ruido(15, 0.8),
        "vibracion": _con_ruido(2.0, 0.3),
    }


def _escenario_b(t: float) -> dict:
    """Sobrecarga mecanica: temperatura, corriente y vibracion suben juntas."""
    return {
        "temperatura": _con_ruido(_lineal(60, 80, t), 0.8),
        "corriente": _con_ruido(_lineal(15, 24, t), 0.5),
        "vibracion": _con_ruido(_lineal(2.0, 5.0, t), 0.3),
    }


def _escenario_c(t: float) -> dict:
    """Falla de rodamiento incipiente: vibracion progresiva, temp/corriente casi estables."""
    return {
        "temperatura": _con_ruido(_lineal(60, 72, t), 0.8),
        "corriente": _con_ruido(_lineal(15, 18, t), 0.5),
        "vibracion": _con_ruido(_lineal(2.0, 6.0, t), 0.3),
    }


def _escenario_d(t: float) -> dict:
    """Operacion normal con variacion: sin tendencia, sin cruces de umbral."""
    return {
        "temperatura": _con_ruido(55, 6),
        "corriente": _con_ruido(15, 2),
        "vibracion": _con_ruido(2.5, 0.8),
    }


_ESCENARIOS = {"A": _escenario_a, "B": _escenario_b, "C": _escenario_c, "D": _escenario_d}


def _publicar(cliente: mqtt.Client, variable: str, valor: float) -> None:
    topico = f"{config.MQTT_TOPIC_BASE}/{variable}"
    payload = {
        "valor": round(valor, 2),
        "unidad": _UNIDADES[variable],
        "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    cliente.publish(topico, json.dumps(payload))


def correr(escenario: str, ticks: int, intervalo: float) -> None:
    generar = _ESCENARIOS[escenario]
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    cliente.connect(config.MQTT_HOST, config.MQTT_PORT)
    cliente.loop_start()

    horas = HORAS_OPERACION_INICIALES
    print(f"Emulador iniciado - escenario {escenario}, {ticks} lecturas cada {intervalo}s")

    try:
        for i in range(ticks):
            t = i / max(ticks - 1, 1)
            valores = generar(t)
            for variable, valor in valores.items():
                _publicar(cliente, variable, valor)
            horas += intervalo / 3600
            _publicar(cliente, "horas_operacion", horas)
            print(f"[{i + 1}/{ticks}] {valores}")
            time.sleep(intervalo)
    except KeyboardInterrupt:
        print("Emulador detenido por el usuario")
    finally:
        cliente.loop_stop()
        cliente.disconnect()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--escenario", choices=list(_ESCENARIOS), default="A")
    parser.add_argument("--ticks", type=int, default=60, help="cantidad de lecturas a publicar")
    parser.add_argument("--intervalo", type=float, default=5.0, help="segundos entre lecturas")
    args = parser.parse_args()
    correr(args.escenario, args.ticks, args.intervalo)
