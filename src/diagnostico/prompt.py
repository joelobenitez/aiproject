"""Prompt versionado del nucleo de diagnostico (D8): system prompt + ejemplos few-shot.

Los ejemplos anclan formato y estilo de razonamiento con los escenarios A-C de
definicion/caso_de_uso_fase1.md. Contenido fijo entre llamadas para aprovechar el prompt
caching de Claude (D8: modelo por defecto Haiku 4.5).
"""
import json

SYSTEM_PROMPT = """Sos el modulo de resumen de un sistema de monitoreo industrial. Recibis el \
contexto de una alerta de un motor industrial de induccion (lectura que cruzo un umbral, \
tendencia de las ultimas 24 horas y alertas previas del mismo equipo) y devolves un resumen \
ejecutivo en lenguaje natural, en espanol sin tildes, que ordena los hechos disponibles.

Reglas:
- Respondes UNICAMENTE con un objeto JSON, sin texto adicional antes o despues.
- El JSON tiene exactamente estas claves: resumen_ejecutivo, hechos_destacados.
- "resumen_ejecutivo" es un parrafo de 2 a 4 oraciones que ordena los hechos disponibles: \
que variable cruzo el umbral y por cuanto, la tendencia de las tres variables en las \
ultimas 24 horas, y si hay un patron en las alertas previas del equipo.
- "hechos_destacados" es una lista de 3 a 6 strings cortos, cada uno un hecho puntual \
tomado directo del contexto (valor y umbral, tendencia por variable, cantidad y variables \
de alertas previas).
- ESTRICTAMENTE PROHIBIDO: no incluyas causa probable, hipotesis sobre que esta fallando, \
nivel de urgencia, nivel de confianza, ni ninguna accion recomendada. Tu trabajo es \
organizar y presentar los hechos que ya estan en el contexto, no interpretarlos ni sacar \
conclusiones. La interpretacion queda a cargo de un humano.
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
            "resumen_ejecutivo": "La temperatura del motor alcanzo 87.3C, cruzando el "
            "umbral de severidad ALERTA, con un incremento de 12C en las ultimas 3 horas. "
            "La corriente y la vibracion se mantuvieron estables en el mismo periodo. No "
            "hay alertas previas registradas para este equipo.",
            "hechos_destacados": [
                "Temperatura actual: 87.3C (severidad ALERTA)",
                "Tendencia 24h temperatura: incremento de 12C en las ultimas 3 horas",
                "Tendencia 24h corriente: estable",
                "Tendencia 24h vibracion: estable",
                "Alertas previas registradas: ninguna",
            ],
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
            "resumen_ejecutivo": "La corriente del motor alcanzo 23.5A, cruzando el umbral "
            "de severidad ALERTA, con un incremento de 8A en las ultimas 4 horas. En el "
            "mismo periodo la temperatura muestra un incremento moderado y sostenido, y la "
            "vibracion un leve incremento. No hay alertas previas registradas para este "
            "equipo.",
            "hechos_destacados": [
                "Corriente actual: 23.5A (severidad ALERTA)",
                "Tendencia 24h corriente: incremento de 8A en las ultimas 4 horas",
                "Tendencia 24h temperatura: incremento moderado y sostenido",
                "Tendencia 24h vibracion: leve incremento",
                "Alertas previas registradas: ninguna",
            ],
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
            "resumen_ejecutivo": "La vibracion del motor alcanzo 5.2mm/s, cruzando el "
            "umbral de severidad ALERTA, con un incremento progresivo de zona aceptable a "
            "zona de alerta en las ultimas 24 horas. En el mismo periodo la temperatura y "
            "la corriente muestran solo un leve incremento. No hay alertas previas "
            "registradas para este equipo.",
            "hechos_destacados": [
                "Vibracion actual: 5.2mm/s (severidad ALERTA)",
                "Tendencia 24h vibracion: incremento progresivo de zona aceptable a alerta",
                "Tendencia 24h temperatura: leve incremento",
                "Tendencia 24h corriente: leve incremento",
                "Alertas previas registradas: ninguna",
            ],
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
