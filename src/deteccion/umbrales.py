"""Carga de Umbral por tipo de equipo, con cache en memoria (Principio II: deteccion barata)."""
from src.almacenamiento import sqlite_repo

_cache: dict[tuple[str, str], dict] = {}


def obtener(tipo_equipo: str, variable: str) -> dict | None:
    clave = (tipo_equipo, variable)
    if clave not in _cache:
        _cache[clave] = sqlite_repo.obtener_umbral(tipo_equipo, variable)
    return _cache[clave]


def limpiar_cache() -> None:
    _cache.clear()
