"""Servidor HTTP minimo para diagnostico bajo demanda (D13).

Un solo endpoint de accion (POST, porque dispara una llamada a Claude que cuesta) mas un
health check. Usa `http.server` de la libreria estandar: a este volumen no justifica sumar
un framework (FastAPI) todavia — ver D9 (MVP simplificado).
"""
import json
import logging
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src import main as servicio

logger = logging.getLogger(__name__)

_RUTA_DIAGNOSTICAR = re.compile(r"^/diagnosticar/(\d+)$")


class _Handler(BaseHTTPRequestHandler):
    def log_message(self, formato: str, *args) -> None:
        logger.info("HTTP %s - %s", self.address_string(), formato % args)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._responder(200, {"status": "ok", "ultima_lectura_en": servicio.obtener_ultima_lectura_en()})
        else:
            self._responder(404, {"error": "no_encontrado"})

    def do_POST(self) -> None:
        match = _RUTA_DIAGNOSTICAR.match(self.path)
        if not match:
            self._responder(404, {"error": "no_encontrado"})
            return

        alerta_id = int(match.group(1))
        resultado = servicio.diagnosticar_bajo_demanda(alerta_id)
        codigo = 404 if resultado.get("error") == "alerta_no_encontrada" else 200
        self._responder(codigo, resultado)

    def _responder(self, codigo: int, cuerpo: dict) -> None:
        payload = json.dumps(cuerpo).encode("utf-8")
        self.send_response(codigo)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)


def crear_servidor(host: str, puerto: int) -> ThreadingHTTPServer:
    return ThreadingHTTPServer((host, puerto), _Handler)
