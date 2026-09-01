# Contrato: Topico y Payload MQTT

Interfaz externa entre la fuente de datos del motor (emulador en Fase 1, RUT956 en
produccion — D11) y el servicio de ingesta (`src/ingesta/`). Este contrato NO cambia entre
el emulador y el hardware real (Supuestos de spec.md, roadmap D11).

## Topico

```
demo/planta1/linea_a/motor_001/{variable}
```

Sigue el patron UNS ya fijado en `CLAUDE.md`: `empresa/planta/equipo/sensor`.
`{variable}` es una de: `temperatura`, `corriente`, `vibracion`, `horas_operacion`.

## Payload (JSON)

```json
{
  "valor": 87.3,
  "unidad": "C",
  "timestamp": "2026-08-29T15:04:00Z"
}
```

| Campo | Tipo | Obligatorio | Notas |
|---|---|---|---|
| valor | number | si | valor de la lectura |
| unidad | string | si | `C`, `A`, `mm/s`, `h` segun la variable |
| timestamp | string (RFC3339) | si | hora de la lectura en origen, no de recepcion |

## Frecuencia esperada

Una publicacion por variable cada 30 segundos (caso de uso de referencia). El servicio de
ingesta usa la ausencia de mensajes nuevos (no la falta de valor) para distinguir "sin
datos" de "dato en rango normal" (caso limite de `spec.md`, FR-012).

## Manejo de errores

Un payload que no matchea el esquema (JSON invalido, campos faltantes, tipo incorrecto) se
descarta y se loguea; no debe tumbar la suscripcion ni generarse como una lectura valida.
