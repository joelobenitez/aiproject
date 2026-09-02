"""Test de contrato: contracts/notificacion-telegram.md (formato de mensaje)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.notificacion import telegram

_RESULTADO_OK = {
    "resumen_ejecutivo": "La temperatura del motor alcanzo 87.3C, cruzando el umbral de "
    "severidad ALERTA.",
    "hechos_destacados": [
        "Temperatura actual: 87.3C (severidad ALERTA)",
        "Tendencia 24h temperatura: incremento sostenido",
    ],
}


def test_formatear_mensaje_exitoso_incluye_los_campos_del_contrato():
    mensaje = telegram.formatear_mensaje_exitoso(
        "Motor M-01 | Linea A | Planta 1", "temperatura", 87.3, "C", 75, "ALERTA", _RESULTADO_OK
    )

    assert "[ALERTA] Motor M-01 | Linea A | Planta 1" in mensaje
    assert "temperatura = 87.3 C (umbral: 75 C)" in mensaje
    assert "La temperatura del motor alcanzo 87.3C" in mensaje
    assert "Hechos:" in mensaje
    assert "- Temperatura actual: 87.3C (severidad ALERTA)" in mensaje
    assert "- Tendencia 24h temperatura: incremento sostenido" in mensaje


def test_formatear_mensaje_fallback_indica_diagnostico_no_disponible():
    mensaje = telegram.formatear_mensaje_fallback(
        "Motor M-01 | Linea A | Planta 1", "temperatura", 87.3, "C", 75, "ALERTA"
    )

    assert "[ALERTA] Motor M-01 | Linea A | Planta 1" in mensaje
    assert "temperatura = 87.3 C (umbral: 75 C)" in mensaje
    assert "Resumen no disponible" in mensaje
    assert "Revisar manualmente" in mensaje


def test_formatear_mensaje_crudo_referencia_el_diagnostico_bajo_demanda():
    mensaje = telegram.formatear_mensaje_crudo(
        "Motor M-01 | Linea A | Planta 1", "temperatura", 80.0, "C", 75, "ALERTA", 42
    )

    assert "[ALERTA] Motor M-01 | Linea A | Planta 1" in mensaje
    assert "temperatura = 80.0 C (umbral: 75 C)" in mensaje
    assert "alerta #42" in mensaje
    assert "/diagnosticar/42" in mensaje
