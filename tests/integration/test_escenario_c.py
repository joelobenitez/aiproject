"""Escenario C - falla de rodamiento incipiente (definicion/caso_de_uso_fase1.md).

Solo la vibracion cruza umbral en este escenario (temperatura/corriente se mantienen
dentro de rango normal por diseno del emulador) — verifica que el detector aisla
correctamente la variable disparadora.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _apoyo import correr_escenario
from herramientas.emulador_motor import _escenario_c
from src.almacenamiento import influx_repo, sqlite_repo
from src.diagnostico import parser

_DIAGNOSTICO_OK = {
    "resumen_ejecutivo": "prueba",
    "hechos_destacados": ["prueba"],
    "fallo": False,
}


def test_escenario_c_genera_solo_alertas_de_vibracion(entorno_aislado, monkeypatch):
    monkeypatch.setattr(influx_repo, "escribir_lectura", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "escribir_evento_alerta", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "escribir_diagnostico", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "tendencia_24h", lambda *a, **k: "incremento progresivo")
    monkeypatch.setattr(parser, "diagnosticar", lambda entrada: _DIAGNOSTICO_OK)

    correr_escenario(_escenario_c)

    alertas = sqlite_repo.obtener_alertas_previas("motor_001", limite=10)

    assert len(alertas) >= 1
    assert all(a["variable_disparadora"] == "vibracion" for a in alertas)
