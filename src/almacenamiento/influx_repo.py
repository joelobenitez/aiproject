"""Acceso a InfluxDB: measurement `lecturas_motor` (data-model.md)."""
import logging
from datetime import datetime, timezone

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS

from src import config

logger = logging.getLogger(__name__)

MEASUREMENT = "lecturas_motor"

_client: InfluxDBClient | None = None


def _obtener_cliente() -> InfluxDBClient:
    global _client
    if _client is None:
        _client = InfluxDBClient(url=config.INFLUX_URL, token=config.INFLUX_TOKEN, org=config.INFLUX_ORG)
    return _client


def escribir_lectura(equipo_id: str, variable: str, valor: float, unidad: str, timestamp: str) -> None:
    punto = (
        Point(MEASUREMENT)
        .tag("equipo_id", equipo_id)
        .tag("variable", variable)
        .field("valor", valor)
        .field("unidad", unidad)
        .time(timestamp)
    )
    write_api = _obtener_cliente().write_api(write_options=SYNCHRONOUS)
    write_api.write(bucket=config.INFLUX_BUCKET, record=punto)


def escribir_evento_alerta(equipo_id: str, variable: str, severidad: str, valor: float, timestamp: str) -> None:
    """Espejo liviano de una Alerta en InfluxDB, solo para anotarla en el dashboard de
    Grafana (Historia 4, research.md). Best-effort: un fallo aca no debe afectar el
    pipeline de deteccion/diagnostico, que ya persistio la Alerta en SQLite."""
    try:
        punto = (
            Point("alertas")
            .tag("equipo_id", equipo_id)
            .tag("variable", variable)
            .tag("severidad", severidad)
            .field("valor", valor)
            .time(timestamp)
        )
        write_api = _obtener_cliente().write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=config.INFLUX_BUCKET, record=punto)
    except Exception:
        logger.exception("Fallo al escribir el evento de alerta en InfluxDB (no bloquea el pipeline)")


def escribir_diagnostico(
    equipo_id: str, alerta_id: int, resultado: dict, fallo: bool, timestamp: str | None = None
) -> None:
    """Espejo liviano de un Diagnostico en InfluxDB, solo para mostrarlo en el dashboard de
    Grafana (Historia 2, feature 002, contracts/diagnostico-influxdb.md). Best-effort: un
    fallo aca no debe afectar el pipeline de diagnostico/notificacion, que ya persistio el
    Diagnostico en SQLite."""
    if timestamp is None:
        timestamp = datetime.now(timezone.utc).isoformat()
    try:
        punto = (
            Point("diagnosticos")
            .tag("equipo_id", equipo_id)
            .field("alerta_id", alerta_id)
            .field("resumen_ejecutivo", resultado.get("resumen_ejecutivo") or "")
            .field("hechos_destacados", "; ".join(resultado.get("hechos_destacados") or []))
            .field("fallo", bool(fallo))
            .time(timestamp)
        )
        write_api = _obtener_cliente().write_api(write_options=SYNCHRONOUS)
        write_api.write(bucket=config.INFLUX_BUCKET, record=punto)
    except Exception:
        logger.exception("Fallo al escribir el evento de diagnostico en InfluxDB (no bloquea el pipeline)")


def tendencia_24h(equipo_id: str, variable: str) -> str:
    """Resumen simple de tendencia 24h para el contrato de diagnostico-modulo.md (FR-003)."""
    query = f'''
    from(bucket: "{config.INFLUX_BUCKET}")
      |> range(start: -24h)
      |> filter(fn: (r) => r._measurement == "{MEASUREMENT}")
      |> filter(fn: (r) => r.equipo_id == "{equipo_id}")
      |> filter(fn: (r) => r.variable == "{variable}")
      |> filter(fn: (r) => r._field == "valor")
    '''
    try:
        tablas = _obtener_cliente().query_api().query(query, org=config.INFLUX_ORG)
    except Exception:
        logger.exception("Fallo la consulta de tendencia 24h para %s/%s", equipo_id, variable)
        return "sin datos disponibles"

    valores = [registro.get_value() for tabla in tablas for registro in tabla.records]
    if len(valores) < 2:
        return "sin datos suficientes para tendencia"

    delta = valores[-1] - valores[0]
    if abs(delta) < 0.5:
        return "estable"
    direccion = "incremento" if delta > 0 else "descenso"
    return f"{direccion} de {abs(delta):.1f} en las ultimas 24 horas"
