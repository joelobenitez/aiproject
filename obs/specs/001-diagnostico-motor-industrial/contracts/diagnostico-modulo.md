# Contrato: Modulo de Diagnostico (nucleo cognitivo)

Interfaz interna entre `deteccion/` (quien detecta el cruce de umbral) y `diagnostico/`
(quien arma el contexto, llama a Claude y devuelve el resultado estructurado). En el MVP es
una llamada de funcion dentro del mismo proceso (D9); el contrato se mantiene identico al
`/diagnose` que D3 preveia como endpoint HTTP, para poder exponerlo como servicio en red sin
reescribirlo cuando el roadmap de escala (D11) lo requiera.

## Entrada

```json
{
  "equipo": {
    "id": "motor_001",
    "nombre": "Motor M-01 | Linea A | Planta 1",
    "horas_operacion_acumuladas": 4820.5
  },
  "alerta": {
    "variable_disparadora": "temperatura",
    "valor": 87.3,
    "unidad": "C",
    "severidad": "ALERTA",
    "timestamp": "2026-08-29T15:04:00Z"
  },
  "tendencia_24h": {
    "temperatura": "incremento de 12C en las ultimas 3 horas",
    "corriente": "estable",
    "vibracion": "estable"
  },
  "alertas_previas": []
}
```

`tendencia_24h` y `alertas_previas` los arma `context.py` consultando InfluxDB y SQLite
respectivamente (FR-003) antes de invocar al modulo.

## Salida

```json
{
  "causa_probable": "degradacion del sistema de refrigeracion (filtro obstruido o ventilador con caudal reducido)",
  "razonamiento": "El incremento de temperatura sin aumento de corriente descarta sobrecarga mecanica...",
  "urgencia": "MEDIA",
  "accion_recomendada": "Inspeccionar circuito de enfriamiento antes de las proximas 8 horas de operacion.",
  "confianza": "ALTA"
}
```

Formato identico al de `definicion/caso_de_uso_fase1.md` (seccion "Formato de Diagnostico
Claude"), sin los campos que ya provee la capa de alerta (`equipo`, `timestamp_alerta`,
`variable_trigger`, etc.) para no duplicar datos entre el contrato de entrada y el de
salida.

## Comportamiento ante fallo (FR-013)

Si la llamada al modelo falla o no responde dentro del timeout, el modulo devuelve un
resultado marcado como fallido (`fallo: true` en el modelo de `Diagnostico`) en vez de
lanzar una excepcion que tumbe el proceso — la `Alerta` que origino el pedido ya quedo
persistida antes de invocar este modulo, asi que no se pierde independientemente del
resultado de esta llamada.

## Modelo y costo (D8)

Modelo por defecto: Haiku 4.5, con prompt caching sobre el system prompt y los ejemplos
few-shot (fijos entre llamadas). Configurable via `MODEL` (env var, ya prevista en D3) para
escalar a Sonnet 5 si la calidad no alcanza contra los 4 escenarios de validacion.
