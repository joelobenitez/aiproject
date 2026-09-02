"""Diagnostico bajo demanda (D13): CRITICO diagnostica automatico, ALERTA queda pendiente
hasta que se pide explicitamente via `main.diagnosticar_bajo_demanda`.

H5/H6 (D20): un diagnostico fallido (`fallo: true`) se puede reintentar sin tocar la base a
mano, y dos pedidos concurrentes de la misma alerta generan una sola llamada a Claude.
"""
import sys
import threading
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src import main as servicio
from src.almacenamiento import influx_repo, sqlite_repo
from src.diagnostico import parser

_DIAGNOSTICO_OK = {
    "resumen_ejecutivo": "prueba",
    "hechos_destacados": ["prueba"],
    "fallo": False,
}


def _ultima_alerta_id() -> int:
    return sqlite_repo.obtener_alertas_previas("motor_001", limite=1)[0]["id"]


def test_alerta_no_diagnostica_automaticamente(entorno_aislado, monkeypatch):
    monkeypatch.setattr(influx_repo, "escribir_evento_alerta", lambda *a, **k: None)
    llamadas = []
    monkeypatch.setattr(parser, "diagnosticar", lambda entrada: llamadas.append(entrada) or _DIAGNOSTICO_OK)

    servicio._procesar_evento("motor_001", "temperatura", 80.0, "C", "ALERTA", "2026-08-31T12:00:00Z")

    assert llamadas == []
    assert sqlite_repo.obtener_diagnostico(_ultima_alerta_id()) is None


def test_critico_diagnostica_automaticamente(entorno_aislado, monkeypatch):
    monkeypatch.setattr(influx_repo, "escribir_evento_alerta", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "escribir_diagnostico", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "tendencia_24h", lambda *a, **k: "estable")
    llamadas = []
    monkeypatch.setattr(parser, "diagnosticar", lambda entrada: llamadas.append(entrada) or _DIAGNOSTICO_OK)

    servicio._procesar_evento("motor_001", "temperatura", 95.0, "C", "CRITICO", "2026-08-31T12:00:00Z")

    assert len(llamadas) == 1
    assert sqlite_repo.obtener_diagnostico(_ultima_alerta_id())["fallo"] == 0


def test_diagnostico_bajo_demanda_diagnostica_una_sola_vez(entorno_aislado, monkeypatch):
    monkeypatch.setattr(influx_repo, "escribir_evento_alerta", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "escribir_diagnostico", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "tendencia_24h", lambda *a, **k: "estable")
    llamadas = []
    monkeypatch.setattr(parser, "diagnosticar", lambda entrada: llamadas.append(entrada) or _DIAGNOSTICO_OK)

    servicio._procesar_evento("motor_001", "temperatura", 80.0, "C", "ALERTA", "2026-08-31T12:00:00Z")
    alerta_id = _ultima_alerta_id()

    resultado_1 = servicio.diagnosticar_bajo_demanda(alerta_id)
    resultado_2 = servicio.diagnosticar_bajo_demanda(alerta_id)

    assert len(llamadas) == 1
    assert resultado_1["cacheado"] is False
    assert resultado_2["cacheado"] is True
    assert resultado_2["resumen_ejecutivo"] == "prueba"
    assert resultado_2["hechos_destacados"] == ["prueba"]


def test_diagnostico_bajo_demanda_alerta_inexistente(entorno_aislado):
    assert servicio.diagnosticar_bajo_demanda(9999) == {"error": "alerta_no_encontrada"}


def test_reintento_exitoso_sobrescribe_diagnostico_fallido(entorno_aislado, monkeypatch):
    """T027 (H5): un diagnostico con `fallo: true` no queda cacheado — el proximo pedido
    reintenta contra Claude y sobrescribe el registro anterior (UPSERT, no INSERT)."""
    monkeypatch.setattr(influx_repo, "escribir_evento_alerta", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "escribir_diagnostico", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "tendencia_24h", lambda *a, **k: "estable")

    servicio._procesar_evento("motor_001", "temperatura", 80.0, "C", "ALERTA", "2026-08-31T12:00:00Z")
    alerta_id = _ultima_alerta_id()

    monkeypatch.setattr(parser, "diagnosticar", lambda entrada: {"fallo": True})
    fallido = servicio.diagnosticar_bajo_demanda(alerta_id)

    assert fallido["cacheado"] is False
    assert fallido["fallo"] is True

    monkeypatch.setattr(parser, "diagnosticar", lambda entrada: dict(_DIAGNOSTICO_OK))
    reintentado = servicio.diagnosticar_bajo_demanda(alerta_id)

    assert reintentado["cacheado"] is False
    assert reintentado["fallo"] is False
    assert reintentado["resumen_ejecutivo"] == "prueba"

    # el reintento exitoso ahora si queda cacheado
    tercero = servicio.diagnosticar_bajo_demanda(alerta_id)
    assert tercero["cacheado"] is True
    assert tercero["fallo"] is False


def test_dos_pedidos_concurrentes_generan_una_sola_llamada(entorno_aislado, monkeypatch):
    """T028 (H6): dos hilos pidiendo el diagnostico de la misma alerta al mismo tiempo no
    disparan dos llamadas a Claude — el segundo espera al primero (lock) y encuentra el
    resultado ya cacheado."""
    monkeypatch.setattr(influx_repo, "escribir_evento_alerta", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "escribir_diagnostico", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "tendencia_24h", lambda *a, **k: "estable")

    llamadas = []

    def _diagnostico_lento(entrada):
        llamadas.append(entrada)
        time.sleep(0.1)
        return dict(_DIAGNOSTICO_OK)

    monkeypatch.setattr(parser, "diagnosticar", _diagnostico_lento)

    servicio._procesar_evento("motor_001", "temperatura", 80.0, "C", "ALERTA", "2026-08-31T12:00:00Z")
    alerta_id = _ultima_alerta_id()

    resultados = []

    def _pedir():
        resultados.append(servicio.diagnosticar_bajo_demanda(alerta_id))

    hilo_1 = threading.Thread(target=_pedir)
    hilo_2 = threading.Thread(target=_pedir)
    hilo_1.start()
    hilo_2.start()
    hilo_1.join()
    hilo_2.join()

    assert len(llamadas) == 1
    assert sorted(r["cacheado"] for r in resultados) == [False, True]
