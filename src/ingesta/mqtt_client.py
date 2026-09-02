"""Conexion y suscripcion MQTT (contracts/mqtt-topico.md)."""
import logging
from typing import Callable

import paho.mqtt.client as mqtt

from src import config

logger = logging.getLogger(__name__)


def crear_cliente(al_recibir_mensaje: Callable[[str, bytes], None]) -> mqtt.Client:
    """Crea y conecta el cliente MQTT, suscripto a `{MQTT_TOPIC_BASE}/+`."""
    cliente = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)

    def _on_connect(client, userdata, connect_flags, reason_code, properties=None):
        topico = f"{config.MQTT_TOPIC_BASE}/+"
        client.subscribe(topico)
        logger.info(
            "Conectado a MQTT %s:%s, suscripto a %s", config.MQTT_HOST, config.MQTT_PORT, topico
        )

    def _on_message(client, userdata, msg):
        al_recibir_mensaje(msg.topic, msg.payload)

    def _on_disconnect(client, userdata, disconnect_flags, reason_code, properties=None):
        logger.warning("Desconectado de MQTT (reason_code=%s)", reason_code)

    cliente.on_connect = _on_connect
    cliente.on_message = _on_message
    cliente.on_disconnect = _on_disconnect

    if config.MQTT_USERNAME:
        cliente.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)

    cliente.connect(config.MQTT_HOST, config.MQTT_PORT)
    return cliente
