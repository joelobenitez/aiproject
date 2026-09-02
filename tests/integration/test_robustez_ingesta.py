"""Robustez del pipeline de ingesta (H1/H2, quickstart.md Escenarios 1 y 2).

A diferencia de los tests de escenario A-D (que drenan la cola en el mismo hilo para
mantener determinismo), estos tests corren el worker real en un hilo aparte: lo que se
valida aca es justamente el comportamiento asincronico (una excepcion puntual no mata el
worker, una llamada lenta no bloquea el encolado de lecturas nuevas).
"""
import json
import queue
import sys
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src import main as servicio
from src.almacenamiento import influx_repo
from src.diagnostico import parser

_DIAGNOSTICO_OK = {
    "resumen_ejecutivo": "prueba",
    "hechos_destacados": ["prueba"],
    "fallo": False,
}


def _payload(valor: float, timestamp: str, unidad: str = "C") -> bytes:
    return json.dumps({"valor": valor, "unidad": unidad, "timestamp": timestamp}).encode()


def _iniciar_worker(monkeypatch) -> threading.Thread:
    # Cola fresca por test: evita que un worker de un test anterior (ya inactivo, esperando
    # en su propia cola vacia) interfiera con las lecturas de este test.
    monkeypatch.setattr(servicio, "_cola", queue.Queue(maxsize=1000))
    hilo = threading.Thread(target=servicio._worker_loop, daemon=True)
    hilo.start()
    return hilo


def _esperar(condicion, timeout: float = 2.0, paso: float = 0.02) -> bool:
    limite = time.monotonic() + timeout
    while time.monotonic() < limite:
        if condicion():
            return True
        time.sleep(paso)
    return condicion()


def test_excepcion_en_una_lectura_no_mata_el_worker(entorno_aislado, monkeypatch):
    llamadas = []

    def _falla_en_la_primera(*_args, **_kwargs):
        llamadas.append(1)
        if len(llamadas) == 1:
            raise RuntimeError("influx caido")

    monkeypatch.setattr(influx_repo, "escribir_lectura", _falla_en_la_primera)
    _iniciar_worker(monkeypatch)

    base = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    topico = "demo/planta1/linea_a/motor_001/temperatura"
    servicio._al_recibir_mensaje(topico, _payload(60.0, base.isoformat().replace("+00:00", "Z")))
    servicio._al_recibir_mensaje(
        topico, _payload(61.0, (base + timedelta(seconds=1)).isoformat().replace("+00:00", "Z"))
    )

    assert _esperar(lambda: len(llamadas) >= 2)
    assert len(llamadas) == 2


def test_lectura_no_espera_a_una_llamada_de_ia_lenta(entorno_aislado, monkeypatch):
    monkeypatch.setattr(influx_repo, "escribir_evento_alerta", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "escribir_diagnostico", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "tendencia_24h", lambda *a, **k: "estable")

    def _diagnostico_lento(_entrada):
        time.sleep(0.3)
        return _DIAGNOSTICO_OK

    monkeypatch.setattr(parser, "diagnosticar", _diagnostico_lento)

    lecturas_influx = []
    monkeypatch.setattr(
        influx_repo,
        "escribir_lectura",
        lambda equipo_id, variable, *resto: lecturas_influx.append(variable),
    )

    _iniciar_worker(monkeypatch)

    base = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    ts_a = base.isoformat().replace("+00:00", "Z")
    ts_b = (base + timedelta(seconds=1)).isoformat().replace("+00:00", "Z")

    # Dispara CRITICO en temperatura -> el worker queda ocupado ~0.3s en el diagnostico.
    servicio._al_recibir_mensaje("demo/planta1/linea_a/motor_001/temperatura", _payload(95.0, ts_a))

    inicio = time.monotonic()
    # Publicar una lectura de otra variable NO debe esperar a que termine el diagnostico:
    # el callback MQTT solo normaliza y encola (H2).
    servicio._al_recibir_mensaje("demo/planta1/linea_a/motor_001/corriente", _payload(10.0, ts_b, unidad="A"))
    duracion_encolado = time.monotonic() - inicio

    assert duracion_encolado < 0.1

    # Eventualmente (una vez que el worker termina el diagnostico lento) la lectura de
    # corriente se procesa igual — no se pierde por haber llegado durante la llamada lenta.
    assert _esperar(lambda: "corriente" in lecturas_influx, timeout=2.0)
