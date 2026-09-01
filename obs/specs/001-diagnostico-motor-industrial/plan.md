# Plan de Implementacion: Monitoreo de Motor Industrial con Diagnostico Inteligente via Claude

**Branch**: `001-diagnostico-motor-industrial` | **Fecha**: 2026-08-29 | **Spec**: [spec.md](./spec.md)

**Input**: Especificacion de feature en `specs/001-diagnostico-motor-industrial/spec.md`

**Nota**: este plan implementa el alcance de **MVP** definido en `memory/decisions.md` D9-D10
(no el stack completo de D1-D4, que queda como objetivo de escala segun el roadmap de D11).

## Resumen

Requisito principal (spec, Historia 1): ante una anomalia en el motor simulado, generar un
diagnostico en lenguaje natural (causa probable, urgencia, accion, confianza) en vez de una
alerta generica. Enfoque tecnico (D9-D10): un unico servicio Python de vida larga que
colapsa los roles de ingesta (ex Node-RED) y orquestacion (ex n8n) — se suscribe a MQTT,
escribe en InfluxDB, detecta cruces de umbral con histeresis en memoria, arma el contexto,
invoca al nucleo de diagnostico (modulos `prompt.py`/`context.py`/`parser.py` ya previstos en
D3/D8, aca como llamada de funcion en el mismo proceso, no HTTP) y notifica por Telegram. El
alcance de este plan es el subconjunto de la spec que D9 deja dentro del MVP (ver
"Alcance de este plan" abajo) — el resto queda marcado como post-MVP.

## Alcance de este plan (reconciliacion spec vs. D9)

**Conflicto detectado:** `spec.md` fue escrita antes de D9 y especifica Email como canal
obligatorio (FR-007, FR-008, e Historia de Usuario 3 completa). D9 (posterior) postergo
Email a una fase posterior junto con Web Report, para no sumar configuracion de SMTP a un
MVP que no la necesita para demostrar el caso de uso central.

**Resolucion para este plan (no silenciosa — reportada al usuario):**
- **En alcance de este plan:** Historia 1 (P1, diagnostico), Historia 2 (P1, solo el canal
  Telegram — FR-006), Historia 4 (P3, Grafana — FR-009). Requisitos FR-001 a FR-006,
  FR-009 a FR-013.
- **Fuera de alcance de este plan (post-MVP, pendiente de reflejar en `spec.md`):**
  Historia 3 completa (reporte diario) y la mitad de Historia 2 que depende de correo
  (FR-007 email critico de respaldo, FR-008 reporte diario por correo). Se retoman cuando
  se implemente el roadmap de D11 o cuando Joelo decida agregar el canal de correo antes.

**Confirmado por Joelo (2026-08-29):** este desfasaje entre `spec.md` y el plan es
intencional, no un descuido — la prioridad es tener el producto viable minimo primero, y
tanto esto como la actualizacion pendiente de `spec.md` quedan anotados para abordarse mas
adelante. No bloquea avanzar a `/speckit-tasks`.

## Contexto Tecnico

**Lenguaje/Version**: Python 3.11+

**Dependencias principales**: `paho-mqtt` (cliente MQTT), `anthropic` (SDK oficial de
Claude, D3/D8), `influxdb-client` (InfluxDB 2.x), `sqlite3` (stdlib), `httpx` (llamadas a la
API HTTP de Telegram Bot), `pytest` (tests)

**Storage**: InfluxDB 2.x (series de tiempo — lecturas del motor) + SQLite (equipos,
umbrales, alertas, diagnosticos — reemplaza a MySQL para el MVP, D9)

**Testing**: `pytest`, con foco en tests de integracion que reproducen los 4 escenarios A-D
del caso de uso (Independent Test de Historia 1) sin depender de Telegram/Grafana reales

**Plataforma objetivo**: contenedor Linux via Docker Compose — Fase 1 en Windows + WSL2 +
Docker Desktop (`CLAUDE.md`), mismo contenedor sin cambios en produccion (D3, D10)

**Tipo de proyecto**: servicio unico de vida larga (single project / daemon), no
serverless (D10)

**Objetivos de performance**: lectura disponible para consulta en <5s (SC-001);
notificacion con diagnostico en <90s desde el evento (SC-002); diagnostico completo
generado en <10s desde la deteccion (SC-003)

**Restricciones**: sin UI de configuracion de umbrales en Fase 1 (hardcoded por tipo de
equipo); salida en espanol (convencion de documentacion del proyecto); sin acciones de
escritura desde Telegram (Nivel 0, D2); secretos via `.env` local + `.gitignore` para esta
etapa de desarrollo (D8), no la decision de produccion

**Escala/Alcance**: un unico motor (una planta, una linea), lecturas cada 30s por variable
(temperatura, corriente, vibracion, horas de operacion) — volumen bajo, sin necesidad de
particionamiento ni colas para el MVP

## Constitution Check

*GATE: debe pasar antes de la Fase 0. Re-chequeado despues del diseno de la Fase 1.*

| Principio | Evaluacion | Estado |
|---|---|---|
| I. Separacion de Capas | **VIOLACION JUSTIFICADA.** El principio nombra Node-RED/n8n/Claude Agent como componentes separados; D9 los colapsa en un unico servicio Python para el MVP. Ver Complexity Tracking abajo — la justificacion ya esta documentada en D9 y referenciada aca, no se repite el razonamiento de negocio. | FLAG (justificado) |
| II. Deteccion Barata, Diagnostico con Contexto | Se respeta a nivel de modulos internos: `deteccion/` (umbral + histeresis en memoria, sin consultar historial largo) permanece separado de `diagnostico/` (contexto 24h + Claude), aunque ambos corran en el mismo proceso. | PASS |
| III. Un Cerebro, Muchos Consumidores | El nucleo de diagnostico (`prompt.py`/`context.py`/`parser.py`) se aisla en su propio modulo con una interfaz de funcion clara, preservando el contrato de datos de D3 (`contracts/diagnostico-modulo.md`) para poder exponerlo por HTTP mas adelante sin reescribirlo. Un solo consumidor en el MVP (el propio servicio) — no hay duplicacion de logica que evitar todavia. | PASS |
| IV. Seguridad por Niveles en Canales de Entrada | Telegram queda en Nivel 0 (solo push, D2) — sin comandos ni acciones de escritura. Secretos manejados con `.env` + `.gitignore` para esta etapa (D8), decision de produccion sigue pendiente y documentada en `memory/risks.md` (no bloquea el MVP). | PASS |
| V. Documentacion y Decisiones Trazables | Este plan, la spec y las decisiones D9-D11 que lo motivan estan en espanol sin tildes y registradas en `memory/decisions.md` de forma append-only. | PASS |

## Estructura del Proyecto

### Documentacion (este feature)

```text
specs/001-diagnostico-motor-industrial/
├── plan.md              # este archivo
├── research.md          # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/            # Fase 1
│   ├── mqtt-topico.md
│   ├── diagnostico-modulo.md
│   └── notificacion-telegram.md
└── tasks.md              # Fase 2 (/speckit-tasks, no generado por este comando)
```

### Codigo fuente (raiz del repositorio)

```text
src/
├── ingesta/            # suscripcion MQTT + normalizacion + escritura a InfluxDB (ex Node-RED, D9)
│   ├── mqtt_client.py
│   └── normalizador.py
├── deteccion/          # evaluacion de umbral + histeresis en memoria (Principio II)
│   ├── umbrales.py
│   └── detector.py
├── diagnostico/        # nucleo cognitivo (D3/D8) — contexto, prompt, llamada a Claude, parseo
│   ├── context.py
│   ├── prompt.py
│   └── parser.py
├── notificacion/       # Telegram Nivel 0 (D2) — email queda fuera de alcance de este plan
│   └── telegram.py
├── almacenamiento/      # acceso a InfluxDB (lecturas) y SQLite (equipos/umbrales/alertas/diagnosticos)
│   ├── influx_repo.py
│   └── sqlite_repo.py
└── main.py              # arranque del proceso de vida larga (D10), conecta los modulos de arriba

herramientas/
└── emulador_motor.py    # script standalone que simula el motor y publica MQTT — no es parte
                          # del sistema en si (juega el rol del RUT956 real, ver Supuestos de spec.md)

tests/
├── contract/            # valida los contratos de contracts/ (payload MQTT, IO del modulo diagnostico)
├── integration/         # los 4 escenarios A-D end-to-end (Independent Test de Historia 1)
└── unit/                # deteccion, parser, normalizador

docker-compose.yml        # broker MQTT (Mosquitto) + InfluxDB + Grafana + servicio (src/main.py)
```

**Decision de estructura**: proyecto unico (Option 1 del template), reflejando D9-D10 — un
solo servicio Python de vida larga, sin separacion backend/frontend ni mobile. El emulador
vive fuera de `src/` porque no es parte del sistema que se esta especificando: cumple el
mismo rol que ocupara el RUT956 en produccion (fuente externa de datos MQTT).

## Complexity Tracking

| Violacion | Por que hace falta | Alternativa mas simple descartada porque |
|---|---|---|
| Principio I (Separacion de Capas): Node-RED y n8n colapsados en un unico servicio Python en vez de tres componentes separados | D9: el stack completo (~9 piezas) es pesado para un MVP cuyo objetivo es demostrar interconexion y el potencial de programar con Claude Code; Node-RED/n8n son herramientas de bajo-codigo sin nada que un agente de codigo pueda escribir/testear/versionar con git diffs claros | Mantener Node-RED + n8n como en D1/D3 fue descartado porque agrega superficie de fallo (mas contenedores, mas configuracion via UI) sin aportar valor a una demo de un solo equipo, y el riesgo de version de flows/workflows en JSON ya esta senalado en `memory/risks.md` |

**Nota:** esta violacion es especifica del MVP. El roadmap D11 restaura la separacion
(detector stateful vs. workers de diagnostico) cuando el sistema escale — en ese momento el
Principio I vuelve a cumplirse sin necesidad de enmendar la constitucion. Quedo sugerida una
enmienda de aclaracion via `/speckit-constitution` para que el Principio I reconozca esta
excepcion de fase MVP explicitamente; **Joelo confirmo (2026-08-29) que se posterga
deliberadamente** junto con el resto de los items que no son bloqueantes para llegar al
producto viable minimo — no se hace ahora.
