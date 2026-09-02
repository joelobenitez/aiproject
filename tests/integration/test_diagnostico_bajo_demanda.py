"""Diagnostico bajo demanda (D13): CRITICO diagnostica automatico, ALERTA queda pendiente
hasta que se pide explicitamente via `main.diagnosticar_bajo_demanda`.
"""
import sys
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
