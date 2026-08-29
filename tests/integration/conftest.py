import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest

from src import config
from src.almacenamiento import sqlite_repo
from src.deteccion import umbrales


@pytest.fixture
def entorno_aislado(tmp_path, monkeypatch):
    """DB SQLite temporal por test + umbrales sin cache cruzado entre tests."""
    monkeypatch.setattr(config, "SQLITE_DB_PATH", str(tmp_path / "test.db"))
    umbrales.limpiar_cache()
    sqlite_repo.inicializar_schema()
    yield
    umbrales.limpiar_cache()
