"""Tests unitarios del normalizador de payload MQTT (complementa tests/contract)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingesta.normalizador import Lectura, normalizar

TOPICO = "demo/planta1/linea_a/motor_001/corriente"


def test_valor_booleano_se_rechaza():
    payload = json.dumps({"valor": True, "unidad": "A", "timestamp": "2026-08-29T10:00:00Z"}).encode()
    assert normalizar(TOPICO, payload) is None


def test_campos_extra_se_ignoran():
    payload = json.dumps(
        {"valor": 15.2, "unidad": "A", "timestamp": "2026-08-29T10:00:00Z", "campo_extra": "ignorar"}
    ).encode()

    lectura = normalizar(TOPICO, payload)

    assert lectura == Lectura(
        equipo_id="motor_001", variable="corriente", valor=15.2, unidad="A", timestamp="2026-08-29T10:00:00Z"
    )


def test_payload_vacio_se_rechaza():
    assert normalizar(TOPICO, b"{}") is None


def test_lista_json_en_vez_de_objeto_se_rechaza():
    payload = json.dumps([1, 2, 3]).encode()
    assert normalizar(TOPICO, payload) is None


def test_valor_entero_se_acepta_y_se_convierte_a_float():
    payload = json.dumps({"valor": 15, "unidad": "A", "timestamp": "2026-08-29T10:00:00Z"}).encode()

    lectura = normalizar(TOPICO, payload)

    assert lectura is not None
    assert lectura.valor == 15.0
    assert isinstance(lectura.valor, float)
