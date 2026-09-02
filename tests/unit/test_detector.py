"""Tests unitarios del detector/histeresis (FR-010, research.md: cooldown de 15 min).

FR-004 (H3, D20): un evento nuevo (primera alerta o escalada) requiere `CONFIRMACION_LECTURAS`
lecturas consecutivas por encima del umbral; la vuelta a NORMAL exige bajar `BANDA_MUERTA` por
debajo de `valor_alerta`, no solo cruzar el umbral en sentido inverso.
"""
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.deteccion import umbrales
from src.deteccion.detector import CONFIRMACION_LECTURAS, Detector

_UMBRAL_TEMPERATURA = {
    "tipo_equipo": "motor_induccion",
    "variable": "temperatura",
    "valor_alerta": 75.0,
    "valor_critico": 90.0,
    "unidad": "C",
}


def _con_umbral_falso(monkeypatch):
    monkeypatch.setattr(umbrales, "obtener", lambda *a, **k: _UMBRAL_TEMPERATURA)


def _confirmar(detector, valor, base, variable="temperatura", n=CONFIRMACION_LECTURAS):
    """Alimenta `n` lecturas consecutivas del mismo valor y devuelve el resultado de la ultima."""
    resultado = None
    for i in range(n):
        resultado = detector.evaluar("motor_001", "motor_induccion", variable, valor, base + timedelta(seconds=i))
    return resultado


def test_no_genera_evento_en_rango_normal(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)

    assert detector.evaluar("motor_001", "motor_induccion", "temperatura", 60.0, datetime.now(timezone.utc)) is None


def test_lectura_aislada_no_genera_evento(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)

    evento = detector.evaluar("motor_001", "motor_induccion", "temperatura", 80.0, datetime.now(timezone.utc))

    assert evento is None


def test_tres_lecturas_consecutivas_generan_evento(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    evento = _confirmar(detector, 80.0, ahora)

    assert evento is not None
    assert evento.severidad == "ALERTA"
    assert evento.es_escalada is False


def test_una_lectura_normal_en_el_medio_reinicia_el_contador(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    detector.evaluar("motor_001", "motor_induccion", "temperatura", 80.0, ahora)
    detector.evaluar("motor_001", "motor_induccion", "temperatura", 80.0, ahora + timedelta(seconds=1))
    # vuelve a NORMAL de verdad (60 esta debajo de la banda muerta) -> resetea el contador
    detector.evaluar("motor_001", "motor_induccion", "temperatura", 60.0, ahora + timedelta(seconds=2))
    tercera = detector.evaluar("motor_001", "motor_induccion", "temperatura", 80.0, ahora + timedelta(seconds=3))

    assert tercera is None


def test_no_duplica_alertas_dentro_del_cooldown(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    primero = _confirmar(detector, 80.0, ahora)
    segundo = detector.evaluar("motor_001", "motor_induccion", "temperatura", 81.0, ahora + timedelta(minutes=5))

    assert primero is not None
    assert segundo is None


def test_reinicia_cooldown_si_escala_de_alerta_a_critico(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    _confirmar(detector, 80.0, ahora)
    # la alerta ya esta confirmada (severidad=ALERTA, contador >= 3): una escalada a CRITICO
    # dispara de inmediato, sin esperar 3 lecturas nuevas — el contador acumulado sigue vivo
    # mientras el equipo no vuelva a NORMAL.
    escalada = detector.evaluar("motor_001", "motor_induccion", "temperatura", 95.0, ahora + timedelta(minutes=5))

    assert escalada is not None
    assert escalada.severidad == "CRITICO"
    assert escalada.es_escalada is True


def test_vuelve_a_alertar_despues_de_volver_a_normal(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    _confirmar(detector, 80.0, ahora)
    detector.evaluar("motor_001", "motor_induccion", "temperatura", 60.0, ahora + timedelta(minutes=1))
    nueva = _confirmar(detector, 80.0, ahora + timedelta(minutes=2))

    assert nueva is not None


def test_banda_muerta_no_vuelve_a_normal_dentro_del_5_por_ciento(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    _confirmar(detector, 80.0, ahora)
    # 74.0 esta debajo de valor_alerta (75.0) pero dentro de la banda muerta del 5% (>= 71.25):
    # el estado NO debe volver a NORMAL todavia (Acceptance Scenario 3, Historia 3).
    resultado = detector.evaluar("motor_001", "motor_induccion", "temperatura", 74.0, ahora + timedelta(seconds=3))

    assert resultado is None
    assert detector._estado[("motor_001", "temperatura")]["severidad"] == "ALERTA"


def test_banda_muerta_si_vuelve_a_normal_por_debajo_del_umbral_menos_la_banda(monkeypatch):
    _con_umbral_falso(monkeypatch)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    _confirmar(detector, 80.0, ahora)
    # 70.0 esta por debajo de la banda muerta (71.25) -> esta vez si vuelve a NORMAL.
    detector.evaluar("motor_001", "motor_induccion", "temperatura", 70.0, ahora + timedelta(seconds=3))

    assert detector._estado[("motor_001", "temperatura")]["severidad"] == "NORMAL"


def test_variables_distintas_del_mismo_equipo_son_independientes(monkeypatch):
    def _umbral(tipo_equipo, variable):
        return {"tipo_equipo": tipo_equipo, "variable": variable, "valor_alerta": 20.0, "valor_critico": 26.0, "unidad": "A"}

    monkeypatch.setattr(umbrales, "obtener", _umbral)
    detector = Detector(cooldown_minutos=15)
    ahora = datetime.now(timezone.utc)

    evento_corriente = _confirmar(detector, 22.0, ahora, variable="corriente")
    evento_vibracion = _confirmar(detector, 22.0, ahora, variable="vibracion")

    assert evento_corriente is not None
    assert evento_vibracion is not None
