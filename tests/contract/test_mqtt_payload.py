"""Test de contrato: contracts/mqtt-topico.md (topico y payload)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.ingesta import normalizador

TOPICO = "demo/planta1/linea_a/motor_001/temperatura"


def test_payload_valido_se_normaliza_correctamente():
    payload = json.dumps({"valor": 87.3, "unidad": "C", "timestamp": "2026-08-29T15:04:00Z"}).encode()

    lectura = normalizador.normalizar(TOPICO, payload)

    assert lectura is not None
    assert lectura.equipo_id == "motor_001"
    assert lectura.variable == "temperatura"
    assert lectura.valor == 87.3
    assert lectura.unidad == "C"
    assert lectura.timestamp == "2026-08-29T15:04:00Z"


def test_payload_no_json_se_descarta():
    assert normalizador.normalizar(TOPICO, b"esto no es json") is None


def test_payload_sin_valor_se_descarta():
    payload = json.dumps({"unidad": "C", "timestamp": "2026-08-29T15:04:00Z"}).encode()
    assert normalizador.normalizar(TOPICO, payload) is None


def test_payload_con_valor_no_numerico_se_descarta():
    payload = json.dumps({"valor": "87.3", "unidad": "C", "timestamp": "2026-08-29T15:04:00Z"}).encode()
    assert normalizador.normalizar(TOPICO, payload) is None


def test_payload_con_unidad_invalida_se_descarta():
    payload = json.dumps({"valor": 87.3, "unidad": "XYZ", "timestamp": "2026-08-29T15:04:00Z"}).encode()
    assert normalizador.normalizar(TOPICO, payload) is None


def test_payload_con_timestamp_no_parseable_se_descarta():
    payload = json.dumps({"valor": 87.3, "unidad": "C", "timestamp": "no-es-una-fecha"}).encode()
    assert normalizador.normalizar(TOPICO, payload) is None


def test_topico_con_formato_inesperado_se_descarta():
    payload = json.dumps({"valor": 87.3, "unidad": "C", "timestamp": "2026-08-29T15:04:00Z"}).encode()
    assert normalizador.normalizar("topico/muy/corto", payload) is None
