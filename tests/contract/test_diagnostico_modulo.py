"""Test de contrato: contracts/diagnostico-modulo.md (entrada/salida del nucleo cognitivo)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.diagnostico import parser

ENTRADA_VALIDA = {
    "equipo": {
        "id": "motor_001",
        "nombre": "Motor M-01 | Linea A | Planta 1",
        "horas_operacion_acumuladas": 4820.5,
    },
    "alerta": {
        "variable_disparadora": "temperatura",
        "valor": 87.3,
        "unidad": "C",
        "severidad": "ALERTA",
        "timestamp": "2026-08-29T15:04:00Z",
    },
    "tendencia_24h": {
        "temperatura": "incremento de 12C en las ultimas 3 horas",
        "corriente": "estable",
        "vibracion": "estable",
    },
    "alertas_previas": [],
}

_CLAVES_SALIDA = {"resumen_ejecutivo", "hechos_destacados"}


class _BloqueTexto:
    def __init__(self, texto):
        self.type = "text"
        self.text = texto


class _RespuestaFalsa:
    def __init__(self, texto):
        self.content = [_BloqueTexto(texto)]


def _cliente_falso(texto_respuesta=None, excepcion=None):
    cliente = MagicMock()
    if excepcion is not None:
        cliente.messages.create.side_effect = excepcion
    else:
        cliente.messages.create.return_value = _RespuestaFalsa(texto_respuesta)
    return cliente


def test_diagnosticar_devuelve_las_claves_del_contrato(monkeypatch):
    salida_json = '{"resumen_ejecutivo": "prueba", "hechos_destacados": ["prueba"]}'
    monkeypatch.setattr(parser, "_obtener_cliente", lambda: _cliente_falso(salida_json))

    resultado = parser.diagnosticar(ENTRADA_VALIDA)

    assert resultado["fallo"] is False
    assert _CLAVES_SALIDA.issubset(resultado.keys())


def test_diagnosticar_marca_fallo_si_la_respuesta_no_es_json_valido(monkeypatch):
    monkeypatch.setattr(parser, "_obtener_cliente", lambda: _cliente_falso("esto no es JSON"))

    resultado = parser.diagnosticar(ENTRADA_VALIDA)

    assert resultado == {"fallo": True}


def test_diagnosticar_marca_fallo_si_faltan_claves_en_la_respuesta(monkeypatch):
    monkeypatch.setattr(parser, "_obtener_cliente", lambda: _cliente_falso('{"resumen_ejecutivo": "prueba"}'))

    resultado = parser.diagnosticar(ENTRADA_VALIDA)

    assert resultado == {"fallo": True}


def test_diagnosticar_marca_fallo_si_la_api_lanza_excepcion(monkeypatch):
    monkeypatch.setattr(
        parser, "_obtener_cliente", lambda: _cliente_falso(excepcion=RuntimeError("timeout simulado"))
    )

    resultado = parser.diagnosticar(ENTRADA_VALIDA)

    assert resultado == {"fallo": True}
