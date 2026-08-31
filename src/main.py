"""Arranque del servicio de vida larga (D10): ingesta -> deteccion -> diagnostico -> notificacion.

Colapsa los roles de ingesta (ex Node-RED) y orquestacion (ex n8n) en un unico proceso (D9).

D13: el diagnostico de IA es automatico solo para severidad CRITICO. Para ALERTA se manda un
mensaje crudo (datos + umbral, sin IA) y el diagnostico queda disponible bajo demanda via
POST /diagnosticar/<alerta_id> (servidor HTTP embebido, ver src/api.py).
"""
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src import config  # noqa: E402
from src.almacenamiento import influx_repo, sqlite_repo  # noqa: E402
from src.deteccion import umbrales  # noqa: E402
from src.deteccion.detector import Detector  # noqa: E402
from src.diagnostico import context, parser  # noqa: E402
from src.ingesta import mqtt_client, normalizador  # noqa: E402
from src.notificacion import telegram  # noqa: E402

logger = logging.getLogger(__name__)

_detector = Detector()


def configurar_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )


def _parsear_timestamp(timestamp: str) -> datetime:
    return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))


def _procesar_evento(equipo_id: str, variable: str, valor: float, unidad: str, severidad: str, timestamp: str) -> None:
    alerta_id = sqlite_repo.crear_alerta(equipo_id, variable, valor, severidad, timestamp)
    influx_repo.escribir_evento_alerta(equipo_id, variable, severidad, valor, timestamp)
    logger.info(
        "Alerta #%s: equipo=%s variable=%s valor=%s severidad=%s", alerta_id, equipo_id, variable, valor, severidad
    )

    if severidad == "CRITICO":
        _diagnosticar_y_notificar(alerta_id, equipo_id, variable, valor, unidad, severidad, timestamp)
    else:
        _notificar_crudo(alerta_id, equipo_id, variable, valor, unidad, severidad)


def _diagnosticar_y_notificar(
    alerta_id: int, equipo_id: str, variable: str, valor: float, unidad: str, severidad: str, timestamp: str
) -> dict:
    entrada = context.armar_contexto(equipo_id, variable, valor, unidad, severidad, timestamp)
    resultado = parser.diagnosticar(entrada)
    fallo = resultado.get("fallo", False)
    sqlite_repo.crear_diagnostico(alerta_id, resultado, fallo=fallo)

    if fallo:
        logger.warning("Diagnostico no disponible para alerta #%s (fallo del nucleo cognitivo)", alerta_id)
    else:
        logger.info("Diagnostico para alerta #%s: %s", alerta_id, resultado.get("causa_probable"))

    _notificar(equipo_id, variable, valor, unidad, severidad, resultado, fallo)
    return resultado


def diagnosticar_bajo_demanda(alerta_id: int) -> dict:
    """D13: dispara (o recupera) el diagnostico de IA de una alerta puntual, a pedido.

    Idempotente: si ya existe un diagnostico para esta alerta, lo devuelve sin volver a
    llamar a Claude (evita pagar dos veces el mismo diagnostico).
    """
    alerta = sqlite_repo.obtener_alerta(alerta_id)
    if alerta is None:
        return {"error": "alerta_no_encontrada"}

    existente = sqlite_repo.obtener_diagnostico(alerta_id)
    if existente is not None:
        existente["fallo"] = bool(existente["fallo"])
        existente["cacheado"] = True
        return existente

    equipo = sqlite_repo.obtener_equipo(alerta["equipo_id"])
    umbral = umbrales.obtener(equipo["tipo_equipo"], alerta["variable_disparadora"])
    resultado = _diagnosticar_y_notificar(
        alerta_id,
        alerta["equipo_id"],
        alerta["variable_disparadora"],
        alerta["valor"],
        umbral["unidad"],
        alerta["severidad"],
        alerta["timestamp"],
    )
    resultado["cacheado"] = False
    return resultado


def _notificar(
    equipo_id: str, variable: str, valor: float, unidad: str, severidad: str, resultado: dict, fallo: bool
) -> None:
    equipo = sqlite_repo.obtener_equipo(equipo_id)
    umbral = umbrales.obtener(equipo["tipo_equipo"], variable)
    valor_umbral = umbral["valor_critico"] if severidad == "CRITICO" else umbral["valor_alerta"]

    if fallo:
        mensaje = telegram.formatear_mensaje_fallback(
            equipo["nombre"], variable, valor, unidad, valor_umbral, severidad
        )
    else:
        mensaje = telegram.formatear_mensaje_exitoso(
            equipo["nombre"], variable, valor, unidad, valor_umbral, severidad, resultado
        )

    telegram.enviar(mensaje)


def _notificar_crudo(alerta_id: int, equipo_id: str, variable: str, valor: float, unidad: str, severidad: str) -> None:
    equipo = sqlite_repo.obtener_equipo(equipo_id)
    umbral = umbrales.obtener(equipo["tipo_equipo"], variable)
    mensaje = telegram.formatear_mensaje_crudo(
        equipo["nombre"], variable, valor, unidad, umbral["valor_alerta"], severidad, alerta_id
    )
    telegram.enviar(mensaje)


def _al_recibir_mensaje(topico: str, payload: bytes) -> None:
    lectura = normalizador.normalizar(topico, payload)
    if lectura is None:
        return

    influx_repo.escribir_lectura(lectura.equipo_id, lectura.variable, lectura.valor, lectura.unidad, lectura.timestamp)

    if lectura.variable == "horas_operacion":
        sqlite_repo.actualizar_horas_operacion(lectura.equipo_id, lectura.valor)
        return

    equipo = sqlite_repo.obtener_equipo(lectura.equipo_id)
    if equipo is None:
        logger.warning("Lectura de equipo desconocido, se descarta: %s", lectura.equipo_id)
        return

    evento = _detector.evaluar(
        lectura.equipo_id,
        equipo["tipo_equipo"],
        lectura.variable,
        lectura.valor,
        _parsear_timestamp(lectura.timestamp),
    )
    if evento is None:
        return

    _procesar_evento(evento.equipo_id, evento.variable, evento.valor, lectura.unidad, evento.severidad, lectura.timestamp)


def main() -> None:
    configurar_logging()
    logger.info("Inicializando esquema SQLite en %s", config.SQLITE_DB_PATH)
    sqlite_repo.inicializar_schema()

    cliente = mqtt_client.crear_cliente(_al_recibir_mensaje)
    cliente.loop_start()

    from src import api  # import diferido: api importa este modulo, evita ciclo al arrancar

    servidor = api.crear_servidor("0.0.0.0", config.HTTP_PORT)
    logger.info("Servicio listo: MQTT conectado, HTTP en :%s (diagnostico bajo demanda)", config.HTTP_PORT)
    try:
        servidor.serve_forever()
    finally:
        cliente.loop_stop()


if __name__ == "__main__":
    main()
