"""Carga de configuracion desde variables de entorno / `.env` (D8)."""
import os
from pathlib import Path

_RAIZ = Path(__file__).resolve().parent.parent


def _cargar_dotenv(ruta: Path = None) -> None:
    ruta = ruta or _RAIZ / ".env"
    if not ruta.exists():
        return
    for linea in ruta.read_text(encoding="utf-8").splitlines():
        linea = linea.strip()
        if not linea or linea.startswith("#") or "=" not in linea:
            continue
        clave, valor = linea.split("=", 1)
        os.environ.setdefault(clave.strip(), valor.strip())


_cargar_dotenv()

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
MODEL = os.environ.get("MODEL", "claude-haiku-4-5-20251001")

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

INFLUX_URL = os.environ.get("INFLUX_URL", "http://localhost:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "aiproject")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "lecturas_motor")

COOLDOWN_MINUTOS = int(os.environ.get("COOLDOWN_MINUTOS", "15"))

MQTT_HOST = os.environ.get("MQTT_HOST", "localhost")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_TOPIC_BASE = os.environ.get("MQTT_TOPIC_BASE", "demo/planta1/linea_a/motor_001")
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

SQLITE_DB_PATH = os.environ.get("SQLITE_DB_PATH", str(_RAIZ / "data" / "aiproject.db"))

HTTP_PORT = int(os.environ.get("HTTP_PORT", "8000"))
API_TOKEN = os.environ.get("API_TOKEN", "")
