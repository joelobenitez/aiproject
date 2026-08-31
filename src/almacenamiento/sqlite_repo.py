"""Acceso a SQLite: Equipo, Umbral, Alerta, Diagnostico (data-model.md, D9 reemplaza MySQL)."""
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from src import config

_ESQUEMA = """
CREATE TABLE IF NOT EXISTS equipo (
    id TEXT PRIMARY KEY,
    nombre TEXT NOT NULL,
    planta TEXT NOT NULL,
    linea TEXT NOT NULL,
    tipo_equipo TEXT NOT NULL,
    horas_operacion_acumuladas REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS umbral (
    tipo_equipo TEXT NOT NULL,
    variable TEXT NOT NULL,
    valor_alerta REAL NOT NULL,
    valor_critico REAL NOT NULL,
    unidad TEXT NOT NULL,
    PRIMARY KEY (tipo_equipo, variable)
);

CREATE TABLE IF NOT EXISTS alerta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    equipo_id TEXT NOT NULL REFERENCES equipo(id),
    variable_disparadora TEXT NOT NULL,
    valor REAL NOT NULL,
    severidad TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    estado_cooldown TEXT NOT NULL DEFAULT 'en_cooldown'
);

CREATE TABLE IF NOT EXISTS diagnostico (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    alerta_id INTEGER NOT NULL UNIQUE REFERENCES alerta(id),
    causa_probable TEXT,
    razonamiento TEXT,
    urgencia TEXT,
    accion_recomendada TEXT,
    confianza TEXT,
    generado_en TEXT NOT NULL,
    fallo INTEGER NOT NULL DEFAULT 0
);
"""

# Valores iniciales por tipo de equipo (definicion/caso_de_uso_fase1.md).
_UMBRALES_INICIALES = [
    ("motor_induccion", "temperatura", 75.0, 90.0, "C"),
    ("motor_induccion", "corriente", 22.0, 26.0, "A"),
    ("motor_induccion", "vibracion", 4.5, 7.1, "mm/s"),
]

EQUIPO_DEFAULT = {
    "id": "motor_001",
    "nombre": "Motor M-01 | Linea A | Planta 1",
    "planta": "planta1",
    "linea": "linea_a",
    "tipo_equipo": "motor_induccion",
}


@contextmanager
def conexion():
    conn = sqlite3.connect(config.SQLITE_DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def inicializar_schema() -> None:
    Path(config.SQLITE_DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    with conexion() as conn:
        conn.executescript(_ESQUEMA)
        for tipo_equipo, variable, valor_alerta, valor_critico, unidad in _UMBRALES_INICIALES:
            conn.execute(
                """INSERT OR IGNORE INTO umbral
                   (tipo_equipo, variable, valor_alerta, valor_critico, unidad)
                   VALUES (?, ?, ?, ?, ?)""",
                (tipo_equipo, variable, valor_alerta, valor_critico, unidad),
            )
        conn.execute(
            """INSERT OR IGNORE INTO equipo
               (id, nombre, planta, linea, tipo_equipo, horas_operacion_acumuladas)
               VALUES (?, ?, ?, ?, ?, 0)""",
            (
                EQUIPO_DEFAULT["id"],
                EQUIPO_DEFAULT["nombre"],
                EQUIPO_DEFAULT["planta"],
                EQUIPO_DEFAULT["linea"],
                EQUIPO_DEFAULT["tipo_equipo"],
            ),
        )


def obtener_umbral(tipo_equipo: str, variable: str) -> dict | None:
    with conexion() as conn:
        fila = conn.execute(
            "SELECT * FROM umbral WHERE tipo_equipo = ? AND variable = ?",
            (tipo_equipo, variable),
        ).fetchone()
        return dict(fila) if fila else None


def obtener_equipo(equipo_id: str) -> dict | None:
    with conexion() as conn:
        fila = conn.execute("SELECT * FROM equipo WHERE id = ?", (equipo_id,)).fetchone()
        return dict(fila) if fila else None


def actualizar_horas_operacion(equipo_id: str, horas: float) -> None:
    with conexion() as conn:
        conn.execute(
            "UPDATE equipo SET horas_operacion_acumuladas = ? WHERE id = ?",
            (horas, equipo_id),
        )


def crear_alerta(equipo_id: str, variable: str, valor: float, severidad: str, timestamp: str) -> int:
    with conexion() as conn:
        cursor = conn.execute(
            """INSERT INTO alerta
               (equipo_id, variable_disparadora, valor, severidad, timestamp, estado_cooldown)
               VALUES (?, ?, ?, ?, ?, 'en_cooldown')""",
            (equipo_id, variable, valor, severidad, timestamp),
        )
        return cursor.lastrowid


def obtener_alerta(alerta_id: int) -> dict | None:
    with conexion() as conn:
        fila = conn.execute("SELECT * FROM alerta WHERE id = ?", (alerta_id,)).fetchone()
        return dict(fila) if fila else None


def obtener_diagnostico(alerta_id: int) -> dict | None:
    with conexion() as conn:
        fila = conn.execute("SELECT * FROM diagnostico WHERE alerta_id = ?", (alerta_id,)).fetchone()
        return dict(fila) if fila else None


def obtener_alertas_previas(equipo_id: str, limite: int = 5) -> list[dict]:
    with conexion() as conn:
        filas = conn.execute(
            "SELECT * FROM alerta WHERE equipo_id = ? ORDER BY id DESC LIMIT ?",
            (equipo_id, limite),
        ).fetchall()
        return [dict(f) for f in filas]


def crear_diagnostico(alerta_id: int, resultado: dict, fallo: bool = False) -> int:
    with conexion() as conn:
        cursor = conn.execute(
            """INSERT INTO diagnostico
               (alerta_id, causa_probable, razonamiento, urgencia, accion_recomendada,
                confianza, generado_en, fallo)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                alerta_id,
                resultado.get("causa_probable"),
                resultado.get("razonamiento"),
                resultado.get("urgencia"),
                resultado.get("accion_recomendada"),
                resultado.get("confianza"),
                datetime.now(timezone.utc).isoformat(),
                1 if fallo else 0,
            ),
        )
        return cursor.lastrowid
