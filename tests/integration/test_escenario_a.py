"""Escenario A - degradacion de refrigeracion (quickstart.md Escenario 1).

El diagnostico real (llamada a Claude) se mockea: este test valida el pipeline
deteccion -> persistencia, no la calidad del diagnostico generado por el LLM.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _apoyo import correr_escenario
from herramientas.emulador_motor import _escenario_a
from src.almacenamiento import influx_repo, sqlite_repo
from src.diagnostico import parser

_DIAGNOSTICO_OK = {
    "causa_probable": "degradacion del sistema de refrigeracion",
    "razonamiento": "prueba",
    "urgencia": "MEDIA",
    "accion_recomendada": "prueba",
    "confianza": "ALTA",
    "fallo": False,
}


def test_escenario_a_genera_una_alerta_de_temperatura(entorno_aislado, monkeypatch):
    monkeypatch.setattr(influx_repo, "escribir_lectura", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "escribir_evento_alerta", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "tendencia_24h", lambda *a, **k: "incremento sostenido")
    monkeypatch.setattr(parser, "diagnosticar", lambda entrada: _DIAGNOSTICO_OK)

    correr_escenario(_escenario_a)

    alertas = sqlite_repo.obtener_alertas_previas("motor_001", limite=10)
    assert len(alertas) == 1
    assert alertas[0]["variable_disparadora"] == "temperatura"
    assert alertas[0]["severidad"] == "ALERTA"
