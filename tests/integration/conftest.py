import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from src import config
from src.almacenamiento import sqlite_repo
from src.deteccion import umbrales


@pytest.fixture
def entorno_aislado(tmp_path, monkeypatch):
    """DB SQLite temporal por test + umbrales sin cache cruzado entre tests.

    Tambien vacia las credenciales de Telegram: si corre `.env` con credenciales reales
    (desarrollo local), estos tests no deben mandar mensajes reales al bot.
    """
    monkeypatch.setattr(config, "SQLITE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "")
    umbrales.limpiar_cache()
    sqlite_repo.inicializar_schema()
    yield
    umbrales.limpiar_cache()
