# Plan de Implementacion: Plugin LLM de Grafana + panel de diagnostico de IA

**Branch**: `002-grafana-llm-diagnostico` | **Fecha**: 2026-09-01 | **Spec**: [spec.md](./spec.md)

**Input**: Especificacion de feature en `specs/002-grafana-llm-diagnostico/spec.md`

**Nota**: a diferencia del feature 001, esta spec ya se escribio conociendo el alcance
decidido (D15) — no hay reconciliacion spec-vs-decision pendiente aca.

## Resumen

Requisito principal (spec, Historia 1+2): que Claude este disponible nativamente dentro de
Grafana OSS (plugin oficial `grafana-llm-app`, proveedor Anthropic) y que el dashboard
`motor-001-mvp` muestre el ultimo diagnostico de IA que `src/` ya genera (D13), sin agregar
un segundo camino a la API de Claude. Enfoque tecnico: (a) configuracion pura de
infraestructura para el plugin (env vars + un YAML de provisioning nuevo, sin codigo); (b)
una funcion nueva y chica en `src/almacenamiento/influx_repo.py` que espeja el diagnostico
ya persistido en SQLite hacia InfluxDB, mas un panel nuevo en `motor.json` que lo lee.

## Contexto Tecnico

**Lenguaje/Version**: Python 3.11+ (igual que el resto de `src/`, sin dependencias nuevas —
`influxdb-client` ya esta en uso). El plugin de Grafana es configuracion, no codigo propio.

**Dependencias principales**: ninguna libreria Python nueva. Grafana: plugin
`grafana-llm-app` (instalado via `GF_INSTALL_PLUGINS`, catalogo oficial de Grafana Labs).

**Storage**: InfluxDB 2.x — se agrega un espejo del diagnostico (ver `data-model.md`) al
mismo bucket que ya usan `lecturas_motor` y `alertas`. No se toca SQLite (sigue siendo la
fuente de verdad del `Diagnostico`, D9).

**Testing**: `pytest` para la funcion nueva de `influx_repo.py`, siguiendo el mismo patron
que ya existe para `escribir_evento_alerta` (best-effort, sin test unitario dedicado hoy —
ver Complexity Tracking). Para el plugin/panel de Grafana no hay tests automatizados en este
proyecto (ninguna parte de `grafana/provisioning/` los tiene hoy) — validacion manual contra
el stack Docker real, mismo criterio que se uso para el bug de anotaciones (Session
2026-08-30).

**Plataforma objetivo**: mismo `docker-compose.yml`, mismo contenedor `grafana` existente —
no se agrega ningun contenedor nuevo.

**Tipo de proyecto**: extension de lo existente (single project), no un componente nuevo.

**Objetivos de performance**: sin objetivo estricto nuevo — el panel de diagnostico se
refresca con el mismo ciclo que ya tienen los demas paneles del dashboard (definido por el
usuario en la UI de Grafana, no por `updateIntervalSeconds` de `dashboard.yml`, que solo
controla cada cuanto Grafana relee el JSON provisionado del disco).

**Restricciones**: FR-006 (sin llamadas nuevas a Claude desde Grafana) es una restriccion de
diseno dura, no solo de alcance — cualquier tarea que la viole en `/speckit-tasks` debe
rechazarse. Nombres exactos de campos del provisioning YAML de Anthropic quedan abiertos
hasta verificarlos empiricamente (ver `research.md`).

**Escala/Alcance**: mismo volumen bajo del MVP (un motor) — el espejo de diagnostico agrega
como mucho un punto de InfluxDB por diagnostico generado (frecuencia ya acotada por el
cooldown de 15 min, D9 research.md).

## Constitution Check

*GATE: debe pasar antes de la Fase 0. Re-chequeado despues del diseno de la Fase 1.*

| Principio | Evaluacion | Estado |
|---|---|---|
| I. Separacion de Capas | No aplica cambio de capas — esta feature no toca la logica de ingesta/deteccion/diagnostico, solo agrega un espejo de lectura (InfluxDB) y config de Grafana. | PASS |
| II. Deteccion Barata, Diagnostico con Contexto | No se toca `deteccion/` ni `diagnostico/` — el diagnostico se sigue generando exactamente igual que hoy (D13), esta feature solo lo persiste una vez mas para lectura. | PASS |
| III. Un Cerebro, Muchos Consumidores | Es el principio que mas directamente gobierna este feature: FR-006 prohibe explicitamente un segundo consumidor de la API de Claude. Grafana pasa a ser un consumidor de **lectura** del diagnostico (via InfluxDB), no un segundo cerebro. El boton nativo "Auto generate" (Historia 1) es una excepcion consciente: genera texto de metadata (titulo/descripcion de panel), no diagnostico de dominio — no compite con `src/`. | PASS |
| IV. Seguridad por Niveles en Canales de Entrada | No se agrega ningun canal de entrada nuevo (Grafana sigue siendo solo lectura/visualizacion). Manejo de secretos: `ANTHROPIC_API_KEY` se reutiliza via sustitucion de variable de entorno (mismo patron que `influxdb.yml` ya usa para `INFLUX_TOKEN`), consistente con la decision de `.env` + `.gitignore` para desarrollo (D8) — no es una decision de produccion nueva. Efecto secundario a documentar en `memory/risks.md`: la key queda materializada tambien en el secret store cifrado de Grafana, una segunda superficie para el mismo valor. | PASS (con nota de riesgo) |
| V. Documentacion y Decisiones Trazables | Spec, plan y D15 en espanol sin tildes, D15 ya registrada en `memory/decisions.md` antes de este plan. | PASS |

Sin violaciones que requieran justificacion — ver "Complexity Tracking" abajo, que queda
vacio a proposito.

## Estructura del Proyecto

### Documentacion (este feature)

```text
specs/002-grafana-llm-diagnostico/
├── plan.md              # este archivo
├── research.md          # Fase 0
├── data-model.md         # Fase 1
├── quickstart.md         # Fase 1
├── contracts/
│   └── diagnostico-influxdb.md
└── tasks.md              # Fase 2 (/speckit-tasks, no generado por este comando)
```

### Codigo fuente (raiz del repositorio) — archivos existentes que se tocan

```text
docker-compose.yml                          # servicio `grafana`: + GF_INSTALL_PLUGINS,
                                             # + GF_FEATURE_TOGGLES_ENABLE=dashgpt

grafana/provisioning/
├── plugins/
│   └── apps.yaml                           # NUEVO — provisioning del plugin (proveedor
│                                            # Anthropic, secureJsonData via ${ANTHROPIC_API_KEY})
└── dashboards/
    └── motor.json                          # + panel nuevo "Diagnostico IA" (Text/Table,
                                             # query Flux del ultimo evento de diagnostico)

src/almacenamiento/
└── influx_repo.py                          # + escribir_diagnostico() (mismo patron
                                             # best-effort que escribir_evento_alerta)

src/main.py                                 # _diagnosticar_y_notificar(): + 1 linea, llama
                                             # a influx_repo.escribir_diagnostico() junto a
                                             # sqlite_repo.crear_diagnostico()

tests/unit/
└── test_influx_repo.py                     # NUEVO — test de escribir_diagnostico() (mock
                                             # de write_api, mismo nivel que test_detector.py)
```

No se crean carpetas nuevas de codigo (`src/` mantiene su estructura de D9/D10) ni
contenedores nuevos en `docker-compose.yml`.

**Decision de estructura**: extension minima de lo existente — no aplica ninguna de las
opciones del template (no es un proyecto nuevo, ni web app, ni mobile). Se lista arriba el
set concreto de archivos tocados en vez del arbol generico del template.

## Complexity Tracking

*Vacio a proposito — el Constitution Check no encontro violaciones que justificar.*
