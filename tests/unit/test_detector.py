"""Tests unitarios del detector/histeresis (FR-010, research.md: cooldown de 15 min)."""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.deteccion import umbrales
from src.deteccion.detector import Detector

_UMBRAL_TEMPERATURA = {
    "tipo_equipo": "motor_induccion",
    "variable": "temperatura",
    "valor_alerta": 75.0,
    "valor_critico": 90.0,
    "unidad": "C",
}


def _con_umbral_falso(monkeypatch):
    monkeypatch.setattr(umbrales, "obtener", lambda *a, **k: _UMBRAL_TEMPERATURA)


def test_no_genera_evento_en_rango_normal(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)

    assert detector.evaluar("motor_001", "motor_induccion", "temperatura", 60.0, datetime.now(timezone.utc)) is None


def test_genera_evento_alerta_al_cruzar_umbral(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)

    evento = detector.evaluar("motor_001", "motor_induccion", "temperatura", 80.0, datetime.now(timezone.utc))

    assert evento is not None
    assert evento.severidad == "ALERTA"
    assert evento.es_escalada is False


def test_no_duplica_alertas_dentro_del_cooldown(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    primero = detector.evaluar("motor_001", "motor_induccion", "temperatura", 80.0, ahora)
    segundo = detector.evaluar("motor_001", "motor_induccion", "temperatura", 81.0, ahora + timedelta(minutes=5))

    assert primero is not None
    assert segundo is None


def test_reinicia_cooldown_si_escala_de_alerta_a_critico(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    detector.evaluar("motor_001", "motor_induccion", "temperatura", 80.0, ahora)
    escalada = detector.evaluar("motor_001", "motor_induccion", "temperatura", 95.0, ahora + timedelta(minutes=5))

    assert escalada is not None
    assert escalada.severidad == "CRITICO"
    assert escalada.es_escalada is True


def test_vuelve_a_alertar_despues_de_volver_a_normal(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    detector.evaluar("motor_001", "motor_induccion", "temperatura", 80.0, ahora)
    detector.evaluar("motor_001", "motor_induccion", "temperatura", 60.0, ahora + timedelta(minutes=1))
    nueva = detector.evaluar("motor_001", "motor_induccion", "temperatura", 80.0, ahora + timedelta(minutes=2))

    assert nueva is not None


def test_variables_distintas_del_mismo_equipo_son_independientes(monkeypatch):
    def _umbral(tipo_equipo, variable):
        return {"tipo_equipo": tipo_equipo, "variable": variable, "valor_alerta": 20.0, "valor_critico": 26.0, "unidad": "A"}

    monkeypatch.setattr(umbrales, "obtener", _umbral)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    evento_corriente = detector.evaluar("motor_001", "motor_induccion", "corriente", 22.0, ahora)
    evento_vibracion = detector.evaluar("motor_001", "motor_induccion", "vibracion", 22.0, ahora)

    assert evento_corriente is not None
    assert evento_vibracion is not None
