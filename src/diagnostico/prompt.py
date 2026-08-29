"""Prompt versionado del nucleo de diagnostico (D8): system prompt + ejemplos few-shot.

Los ejemplos anclan formato y estilo de razonamiento con los escenarios A-C de
definicion/caso_de_uso_fase1.md. Contenido fijo entre llamadas para aprovechar el prompt
caching de Claude (D8: modelo por defecto Haiku 4.5).
"""
import json

SYSTEM_PROMPT = """Sos el nucleo de diagnostico de un sistema de monitoreo industrial. Recibis el \
contexto de una alerta de un motor industrial de induccion (lectura que cruzo un umbral, \
tendencia de las ultimas 24 horas y alertas previas del mismo equipo) y devolves un \
diagnostico en lenguaje natural, en espanol sin tildes.

Reglas:
- Respondes UNICAMENTE con un objeto JSON, sin texto adicional antes o despues.
- El JSON tiene exactamente estas claves: causa_probable, razonamiento, urgencia, \
accion_recomendada, confianza.
- "urgencia" y "confianza" son uno de: ALTA, MEDIA, BAJA.
- "razonamiento" explica por que se descartan otras causas posibles, no solo repite el \
valor de la alerta.
- "accion_recomendada" es una accion concreta y ejecutable, con un plazo cuando aplique.
- Si el contexto no alcanza para un diagnostico confiable, decilo en "causa_probable" y \
usa confianza BAJA en vez de inventar una causa especifica.
"""

_EJEMPLOS = [
    {
        "entrada": {
            "equipo": {
                "id": "motor_001",
                "nombre": "Motor M-01 | Linea A | Planta 1",
                "horas_operacion_acumuladas": 4820.5,
            },
            "alerta": {
                "variable_disparadora": "temperatura",
                "valor": 87.3,
                "unidad": "C",
                "severidad": "ALERTA",
                "timestamp": "2026-08-29T15:04:00Z",
            },
            "tendencia_24h": {
                "temperatura": "incremento de 12C en las ultimas 3 horas",
                "corriente": "estable",
                "vibracion": "estable",
            },
            "alertas_previas": [],
        },
        "salida": {
            "causa_probable": "degradacion del sistema de refrigeracion (filtro obstruido "
            "o ventilador con caudal reducido)",
            "razonamiento": "El incremento de temperatura sin aumento de corriente descarta "
            "sobrecarga mecanica. La curva gradual y sostenida es tipica de restriccion de "
            "flujo de aire, no de falla electrica.",
            "urgencia": "MEDIA",
            "accion_recomendada": "Inspeccionar circuito de enfriamiento antes de las "
            "proximas 8 horas de operacion. Revisar filtros y verificar caudal del "
            "ventilador.",
            "confianza": "ALTA",
        },
    },
    {
        "entrada": {
            "equipo": {
                "id": "motor_001",
                "nombre": "Motor M-01 | Linea A | Planta 1",
                "horas_operacion_acumuladas": 5100.0,
            },
            "alerta": {
                "variable_disparadora": "corriente",
                "valor": 23.5,
                "unidad": "A",
                "severidad": "ALERTA",
                "timestamp": "2026-08-29T10:00:00Z",
            },
            "tendencia_24h": {
                "temperatura": "incremento moderado y sostenido",
                "corriente": "incremento de 8A en las ultimas 4 horas",
                "vibracion": "leve incremento",
            },
            "alertas_previas": [],
        },
        "salida": {
            "causa_probable": "carga mecanica excesiva, posible obstruccion o "
            "desalineamiento del eje",
            "razonamiento": "El aumento conjunto de corriente, temperatura y vibracion "
            "descarta una causa puramente termica (como refrigeracion) y apunta a mayor "
            "esfuerzo mecanico sostenido en el eje.",
            "urgencia": "ALTA",
            "accion_recomendada": "Detener el equipo en la proxima ventana disponible e "
            "inspeccionar acople, rodamientos y alineamiento antes de reanudar operacion "
            "continua.",
            "confianza": "MEDIA",
        },
    },
    {
        "entrada": {
            "equipo": {
                "id": "motor_001",
                "nombre": "Motor M-01 | Linea A | Planta 1",
                "horas_operacion_acumuladas": 8300.0,
            },
            "alerta": {
                "variable_disparadora": "vibracion",
                "valor": 5.2,
                "unidad": "mm/s",
                "severidad": "ALERTA",
                "timestamp": "2026-08-29T06:30:00Z",
            },
            "tendencia_24h": {
                "temperatura": "leve incremento",
                "corriente": "leve incremento",
                "vibracion": "incremento progresivo de zona aceptable a alerta",
            },
            "alertas_previas": [],
        },
        "salida": {
            "causa_probable": "desgaste incipiente de rodamiento",
            "razonamiento": "La vibracion avanzando progresivamente de forma aislada, con "
            "temperatura y corriente casi estables, es el patron tipico de deterioro "
            "mecanico localizado en rodamientos antes que de sobrecarga o falla termica.",
            "urgencia": "MEDIA",
            "accion_recomendada": "Planificar reemplazo preventivo del rodamiento en la "
            "proxima parada programada; monitorear vibracion diariamente hasta entonces.",
            "confianza": "ALTA",
        },
    },
]


def construir_mensajes(entrada: dict) -> list[dict]:
    """Arma los mensajes (few-shot fijo + entrada real) para la llamada a Claude."""
    mensajes = []
    for ejemplo in _EJEMPLOS:
        mensajes.append({"role": "user", "content": json.dumps(ejemplo["entrada"], ensure_ascii=False)})
        mensajes.append({"role": "assistant", "content": json.dumps(ejemplo["salida"], ensure_ascii=False)})
    mensajes.append({"role": "user", "content": json.dumps(entrada, ensure_ascii=False)})
    return mensajes
