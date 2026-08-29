"""Escenario D - operacion normal, cero falsos positivos (quickstart.md Escenario 2, SC-005)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from _apoyo import correr_escenario
from herramientas.emulador_motor import _escenario_d
from src.almacenamiento import influx_repo, sqlite_repo
from src.diagnostico import parser


def test_escenario_d_no_genera_alertas_ni_llama_al_diagnostico(entorno_aislado, monkeypatch):
    monkeypatch.setattr(influx_repo, "escribir_lectura", lambda *a, **k: None)
    monkeypatch.setattr(influx_repo, "tendencia_24h", lambda *a, **k: "estable")

    llamadas = []
    monkeypatch.setattr(parser, "diagnosticar", lambda entrada: llamadas.append(entrada) or {"fallo": True})

    correr_escenario(_escenario_d)

    assert sqlite_repo.obtener_alertas_previas("motor_001", limite=50) == []
    assert llamadas == []
