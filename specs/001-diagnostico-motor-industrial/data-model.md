# Modelo de Datos — Fase 1

Feature: Monitoreo de Motor Industrial con Diagnostico Inteligente via Claude
(`001-diagnostico-motor-industrial`)

Deriva de la seccion "Entidades Clave" de `spec.md`. Dos motores de almacenamiento (D9):
**InfluxDB** para series de tiempo (Lectura) y **SQLite** para todo lo relacional
(Equipo, Umbral, Alerta, Diagnostico).

---

## Lectura (InfluxDB)

Un valor de una variable del motor en un momento dado. Alimenta la deteccion de umbral y la
tendencia de 24h que consume el diagnostico (FR-001, FR-003).

| Campo | Tipo | Notas |
|---|---|---|
| measurement | string | `lecturas_motor` |
| tag: equipo_id | string | identifica el motor (una sola instancia en Fase 1, ver Supuestos de spec.md) |
| tag: variable | string | `temperatura` \| `corriente` \| `vibracion` \| `horas_operacion` |
| field: valor | float | valor de la lectura |
| field: unidad | string | `C`, `A`, `mm/s`, `h` |
| timestamp | RFC3339 | provisto por el publicador (emulador o RUT956 real) |

**Retencion**: sin politica de retencion especial en Fase 1 (bucket por defecto); se
revisita en la fase de escala (D11).

---

## Equipo (SQLite)

El activo monitoreado.

| Campo | Tipo | Notas |
|---|---|---|
| id | TEXT PK | ej. `motor_001` |
| nombre | TEXT | ej. "Motor M-01 \| Linea A \| Planta 1" |
| planta | TEXT | |
| linea | TEXT | |
| tipo_equipo | TEXT FK -> Umbral.tipo_equipo | determina que umbrales aplican |
| horas_operacion_acumuladas | REAL | se actualiza con cada lectura de la variable `horas_operacion` |

---

## Umbral (SQLite)

Valores de referencia por variable y tipo de equipo (FR-002). Estatico por tipo de equipo
en Fase 1 — sin UI de configuracion (Supuestos de spec.md).

| Campo | Tipo | Notas |
|---|---|---|
| tipo_equipo | TEXT PK (parte 1) | ej. `motor_induccion` |
| variable | TEXT PK (parte 2) | `temperatura` \| `corriente` \| `vibracion` |
| valor_alerta | REAL | cruce = estado ALERTA |
| valor_critico | REAL | cruce = estado CRITICO |
| unidad | TEXT | |

**Valores iniciales** (de `definicion/caso_de_uso_fase1.md`): temperatura alerta=75,
critico=90 (°C); corriente alerta=22, critico=26 (A); vibracion alerta=4.5, critico=7.1
(mm/s, ISO 10816 clase II).

---

## Alerta (SQLite)

El evento generado cuando una lectura cruza un umbral (FR-002, FR-010, FR-011).

| Campo | Tipo | Notas |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | |
| equipo_id | TEXT FK -> Equipo.id | |
| variable_disparadora | TEXT | variable que cruzo el umbral |
| valor | REAL | valor de la lectura que disparo la alerta |
| severidad | TEXT | `ALERTA` \| `CRITICO` |
| timestamp | DATETIME | momento del cruce |
| estado_cooldown | TEXT | `activa` \| `en_cooldown` \| `resuelta` — soporta FR-010 (no duplicar mientras la anomalia sigue en curso) |

**Regla de cooldown** (ver `research.md`): una alerta en curso para el mismo
`equipo_id`+`variable_disparadora` no genera una `Alerta` nueva mientras este en estado
`en_cooldown`, salvo que la severidad escale (de `ALERTA` a `CRITICO`), caso en el que el
cooldown se reinicia y se genera una nueva evaluacion de diagnostico.

---

## Diagnostico (SQLite)

El resultado generado por el nucleo cognitivo para una alerta (FR-004, FR-005). Asociacion
1 a 1 con `Alerta`.

| Campo | Tipo | Notas |
|---|---|---|
| id | INTEGER PK AUTOINCREMENT | |
| alerta_id | INTEGER FK -> Alerta.id UNIQUE | 1:1 |
| causa_probable | TEXT | |
| razonamiento | TEXT | explicito, ver formato de `definicion/caso_de_uso_fase1.md` |
| urgencia | TEXT | `ALTA` \| `MEDIA` \| `BAJA` |
| accion_recomendada | TEXT | |
| confianza | TEXT | `ALTA` \| `MEDIA` \| `BAJA` |
| generado_en | DATETIME | |
| fallo | BOOLEAN | `true` si la llamada a Claude fallo/no respondio a tiempo (FR-013) — la fila de `Alerta` igual persiste aunque esta quede vacia/marcada como fallo |

---

## Fuera de alcance de este modelo

**Reporte diario**: entidad descrita en `spec.md` pero fuera del alcance de este plan
(ver "Alcance de este plan" en `plan.md` — depende de Email, postergado por D9). No se
modela aca; se retoma junto con esa decision.
