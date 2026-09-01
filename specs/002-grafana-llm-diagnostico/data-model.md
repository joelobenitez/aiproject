# Modelo de Datos — Fase 1

Feature: Plugin LLM de Grafana + panel de diagnostico de IA (`002-grafana-llm-diagnostico`)

Este feature no agrega entidades nuevas al dominio (motor, alerta, diagnostico ya existen,
ver `obs/specs/001-diagnostico-motor-industrial/data-model.md` para el modelo original). Lo
unico nuevo es un **espejo de lectura** del `Diagnostico` (SQLite, fuente de verdad, D9)
hacia InfluxDB, para que Grafana pueda consultarlo — mismo patron ya usado para `Alerta` con
`escribir_evento_alerta`.

---

## Evento de diagnostico (InfluxDB)

**Measurement**: `diagnosticos` (nuevo, separado de `alertas` — ver justificacion en
`research.md`).

**Bucket**: mismo bucket del proyecto (`lecturas_motor`, o el que defina `INFLUX_BUCKET`) —
no se crea un bucket nuevo.

| Campo | Tipo InfluxDB | Origen (SQLite `diagnostico`) | Notas |
|---|---|---|---|
| `equipo_id` | tag | `alerta.equipo_id` (via join) | Igual que en `alertas` — permite filtrar por equipo en el query del panel. |
| `alerta_id` | field (int) | `diagnostico.alerta_id` | Referencia a la alerta que origino el diagnostico — no es tag (alta cardinalidad, un valor por diagnostico). |
| `causa_probable` | field (string) | `diagnostico.causa_probable` | Puede venir `None` si `fallo=1`. |
| `razonamiento` | field (string) | `diagnostico.razonamiento` | Idem. |
| `urgencia` | field (string) | `diagnostico.urgencia` | Idem. |
| `accion_recomendada` | field (string) | `diagnostico.accion_recomendada` | Idem. |
| `confianza` | field (string o float, ver nota) | `diagnostico.confianza` | Se escribe tal cual lo devuelve `parser.py` — no se fuerza tipo si el valor no es numerico. |
| `fallo` | field (bool) | parametro `fallo` de `crear_diagnostico` | Permite al panel distinguir "diagnostico exitoso" de "fallo del nucleo cognitivo" (mismo caso que ya maneja `telegram.formatear_mensaje_fallback`). |
| timestamp del punto | InfluxDB `_time` | `datetime.now(timezone.utc)` al momento de escribir | Igual criterio que `escribir_evento_alerta` — el timestamp es el de generacion del diagnostico, no el de la alerta original (pueden diferir por el modelo on-demand de D13). |

**Escritura**: nueva funcion `escribir_diagnostico(equipo_id, alerta_id, resultado, fallo)`
en `src/almacenamiento/influx_repo.py`, llamada una sola vez desde
`src/main.py::_diagnosticar_y_notificar()` (cubre automaticamente los dos caminos que llegan
ahi: CRITICO automatico y ALERTA on-demand via D13 — ver `src/main.py` lineas 53-67).

**Best-effort**: mismo patron que `escribir_evento_alerta` — un `try/except` que loguea y no
relanza. Un fallo aca no debe afectar el pipeline de diagnostico/notificacion, que ya
persistio el `Diagnostico` en SQLite (fuente de verdad) antes de este punto.

**Que pasa si `fallo=1`**: se escribe igual el punto (con `causa_probable`, etc. en `None` y
`fallo=true`), para que el panel de Grafana pueda mostrar explicitamente "diagnostico no
disponible" en vez de mostrar el ultimo diagnostico exitoso anterior como si fuera el
actual — evita la ambiguedad temporal senalada en el Edge Case de `spec.md`.

---

## Query Flux del panel (referencia para `/speckit-tasks`)

Ultimo diagnostico de un equipo — pivot para tener todos los fields como columnas de una
sola fila (necesario para un panel de tipo Table/Text, igual razonamiento que el fix de
`|> group()` en las anotaciones):

```flux
from(bucket: "lecturas_motor")
  |> range(start: -30d)
  |> filter(fn: (r) => r._measurement == "diagnosticos")
  |> filter(fn: (r) => r.equipo_id == "motor_001")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"], desc: true)
  |> limit(n: 1)
```

`range(start: -30d)` en vez de una ventana corta: un diagnostico puede ser el "ultimo
disponible" aunque haya pasado bastante tiempo desde que se genero (ver Acceptance Scenario
2 de Historia 2 en `spec.md` — mostrar el ultimo disponible, no solo el reciente). El valor
exacto de la ventana se ajusta en `/speckit-tasks` si 30 dias resulta insuficiente o
excesivo en la practica.
