"""Test de integracion de notificacion Telegram (quickstart.md Escenarios 3 y 5)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import httpx

from src import config
from src.notificacion import telegram


def test_enviar_exitoso_en_el_primer_intento(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "token-de-prueba")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "12345")

    llamadas = []

    def _post_falso(url, json, timeout):
        llamadas.append((url, json))
        return httpx.Response(200, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", _post_falso)

    assert telegram.enviar("mensaje de prueba") is True
    assert len(llamadas) == 1


def test_enviar_reintenta_y_falla_sin_lanzar_excepcion(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "token-de-prueba")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "12345")
    monkeypatch.setattr(telegram, "_ESPERA_BASE_SEGUNDOS", 0)

    intentos = []

    def _post_falso(url, json, timeout):
        intentos.append(1)
        return httpx.Response(500, request=httpx.Request("POST", url))

    monkeypatch.setattr(httpx, "post", _post_falso)

    assert telegram.enviar("mensaje de prueba") is False
    assert len(intentos) == telegram._MAX_INTENTOS


def test_enviar_sin_credenciales_no_intenta_y_no_lanza_excepcion(monkeypatch):
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "")

    assert telegram.enviar("mensaje de prueba") is False
