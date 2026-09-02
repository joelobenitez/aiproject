"""Simulador de motor industrial como esclavo Modbus RTU real por RS485/USB-RS485.

Reemplaza temporalmente al sensor real (todavia no disponible) para probar el enlace
fisico RS485 y el rol de maestro Modbus RTU del RUT956 (D11), a diferencia de
`emulador_motor.py` que publica directo por MQTT sin pasar por el gateway.

Mapa de registros (holding registers, todos uint16, escala x10):
  0: temperatura (C x10)
  1: corriente (A x10)
  2: vibracion (mm/s x10)
  3: horas_operacion (h x10)

Reutiliza las curvas de los escenarios A-D de `emulador_motor.py` para no duplicar la
logica de simulacion.
"""
import argparse
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pymodbus import FramerType
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusServerContext, ModbusSlaveContext
from pymodbus.server import StartSerialServer

from herramientas.emulador_motor import HORAS_OPERACION_INICIALES, _ESCENARIOS

_REGISTRO = {"temperatura": 0, "corriente": 1, "vibracion": 2, "horas_operacion": 3}


def _escalar(valor: float) -> int:
    return min(max(round(valor * 10), 0), 65535)


def _actualizar_registros(bloque: ModbusSequentialDataBlock, escenario: str, ticks: int, intervalo: float) -> None:
    generar = _ESCENARIOS[escenario]
    horas = HORAS_OPERACION_INICIALES
    for i in range(ticks):
        t = i / max(ticks - 1, 1)
        valores = generar(t)
        horas += intervalo / 3600
        valores["horas_operacion"] = horas
        for variable, valor in valores.items():
            bloque.setValues(_REGISTRO[variable] + 1, [_escalar(valor)])
        print(f"[{i + 1}/{ticks}] {valores}")
        time.sleep(intervalo)
    print("Escenario terminado — el esclavo sigue respondiendo con los ultimos valores")


def correr(puerto: str, baudrate: int, id_esclavo: int, escenario: str, ticks: int, intervalo: float) -> None:
    bloque = ModbusSequentialDataBlock(0, [0] * len(_REGISTRO))
    contexto_esclavo = ModbusSlaveContext(hr=bloque, zero_mode=True)
    contexto = ModbusServerContext(slaves={id_esclavo: contexto_esclavo}, single=False)

    hilo = threading.Thread(
        target=_actualizar_registros, args=(bloque, escenario, ticks, intervalo), daemon=True
    )
    hilo.start()

    print(
        f"Esclavo Modbus RTU en {puerto} @ {baudrate}bps, id={id_esclavo}, "
        f"escenario {escenario} — Ctrl+C para detener"
    )
    print(f"Mapa de registros (holding, x10): {_REGISTRO}")
    try:
        StartSerialServer(
            context=contexto,
            framer=FramerType.RTU,
            port=puerto,
            baudrate=baudrate,
            bytesize=8,
            parity="N",
            stopbits=1,
            timeout=1,
        )
    except KeyboardInterrupt:
        print("Simulador detenido por el usuario")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--puerto", required=True, help="puerto COM del adaptador USB-RS485, ej. COM5")
    parser.add_argument("--baudrate", type=int, default=9600)
    parser.add_argument("--id-esclavo", type=int, default=1, dest="id_esclavo")
    parser.add_argument("--escenario", choices=list(_ESCENARIOS), default="A")
    parser.add_argument("--ticks", type=int, default=120, help="cantidad de actualizaciones de registros")
    parser.add_argument("--intervalo", type=float, default=5.0, help="segundos entre actualizaciones")
    args = parser.parse_args()
    correr(args.puerto, args.baudrate, args.id_esclavo, args.escenario, args.ticks, args.intervalo)
