"""Escenario B - sobrecarga mecanica (definicion/caso_de_uso_fase1.md)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _apoyo import correr_escenario
from herramientas.emulador_motor import _escenario_b
from src.almacenamiento import influx_repo, sqlite_repo
from src.diagnostico import parser

_DIAGNOSTICO_OK = {
    "causa_probable": "carga mecanica excesiva",
    "razonamiento": "prueba",
    "urgencia": "ALTA",
    "accion_recomendada": "prueba",
    "confianza": "MEDIA",
    "fallo": False,
}


def test_escenario_b_genera_alertas_de_sobrecarga(entorno_aislado, monkeypatch):
    monkeypatch.setattr(influx_repo, "escribir_lectura", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "escribir_evento_alerta", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "escribir_diagnostico", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "tendencia_24h", lambda *a, **k: "incremento sostenido")
    monkeypatch.setattr(parser, "diagnosticar", lambda entrada: _DIAGNOSTICO_OK)

    correr_escenario(_escenario_b)

    alertas = sqlite_repo.obtener_alertas_previas("motor_001", limite=10)
    variables_disparadoras = {a["variable_disparadora"] for a in alertas}

    assert variables_disparadoras
    assert variables_disparadoras.issubset({"temperatura", "corriente", "vibracion"})
