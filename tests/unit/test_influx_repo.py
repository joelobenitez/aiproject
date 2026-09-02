"""Test unitario de escribir_diagnostico (feature 002, contracts/diagnostico-influxdb.md)."""
import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.almacenamiento import influx_repo


def _con_cliente_falso(monkeypatch):
    cliente_falso = MagicMock()
    write_api_falso = MagicMock()
    cliente_falso.write_api.return_value = write_api_falso
    monkeypatch.setattr(influx_repo, "_obtener_cliente", lambda: cliente_falso)
    return write_api_falso


def test_escribir_diagnostico_exitoso_escribe_un_punto(monkeypatch):
    write_api_falso = _con_cliente_falso(monkeypatch)
    resultado = {
        "resumen_ejecutivo": "La temperatura del motor alcanzo el umbral de ALERTA.",
        "hechos_destacados": ["Temperatura actual: 87.3C", "Tendencia 24h: incremento sostenido"],
    }

    influx_repo.escribir_diagnostico("motor_001", 42, resultado, fallo=False)

    assert write_api_falso.write.call_count == 1
    punto = write_api_falso.write.call_args.kwargs["record"]
    texto = punto.to_line_protocol()
    assert "diagnosticos" in texto
    assert 'equipo_id=motor_001' in texto
    assert "alerta_id=42i" in texto
    assert "fallo=false" in texto


def test_escribir_diagnostico_con_fallo_escribe_campos_en_blanco(monkeypatch):
    write_api_falso = _con_cliente_falso(monkeypatch)

    influx_repo.escribir_diagnostico("motor_001", 43, {}, fallo=True)

    assert write_api_falso.write.call_count == 1
    punto = write_api_falso.write.call_args.kwargs["record"]
    texto = punto.to_line_protocol()
    assert "fallo=true" in texto
    assert 'resumen_ejecutivo=""' in texto


def test_escribir_diagnostico_no_relanza_si_falla_la_escritura(monkeypatch):
    cliente_falso = MagicMock()
    cliente_falso.write_api.side_effect = Exception("influxdb caido")
    monkeypatch.setattr(influx_repo, "_obtener_cliente", lambda: cliente_falso)

    # No debe lanzar excepcion (best-effort, mismo patron que escribir_evento_alerta)
    influx_repo.escribir_diagnostico("motor_001", 44, {"resumen_ejecutivo": "x"}, fallo=False)
