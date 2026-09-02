import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest

from src import config
from src import main as servicio
from src.almacenamiento import sqlite_repo
from src.deteccion import umbrales
from src.deteccion.detector import Detector


@pytest.fixture
def entorno_aislado(tmp_path, monkeypatch):
    """DB SQLite temporal por test + umbrales sin cache cruzado entre tests.

    Tambien vacia las credenciales de Telegram: si corre `.env` con credenciales reales
    (desarrollo local), estos tests no deben mandar mensajes reales al bot.

    H4: el `Detector` ahora persiste su estado en SQLite (`detector_estado`), asi que
    `servicio._detector` se reconstruye aca, despues de inicializar el schema en la DB
    temporal de este test — si no, heredaria cooldowns de la DB real de desarrollo o de
    otro test (el singleton de `src/main.py` solo se crea una vez por proceso).
    """
    monkeypatch.setattr(config, "SQLITE_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setattr(config, "TELEGRAM_BOT_TOKEN", "")
    monkeypatch.setattr(config, "TELEGRAM_CHAT_ID", "")
    umbrales.limpiar_cache()
    sqlite_repo.inicializar_schema()
    monkeypatch.setattr(servicio, "_detector", Detector())
    yield
    umbrales.limpiar_cache()
