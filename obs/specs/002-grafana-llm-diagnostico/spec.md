# Feature Specification: Plugin LLM de Grafana + panel de diagnostico de IA

**Feature Branch**: `002-grafana-llm-diagnostico`

**Created**: 2026-09-01

**Status**: Draft

**Input**: User description: "Instalar y provisionar el plugin grafana-llm-app en Grafana OSS
con el proveedor Anthropic/Claude (feature toggle dashgpt) y agregar al dashboard
motor-001-mvp un panel que muestre el ultimo diagnostico de IA ya generado por src/ (D13),
sin llamar a Claude desde Grafana."

**Contexto previo:** investigacion de otra sesion (LLM plugin de Grafana, ver
`memory/decisions.md` D15) mas verificacion propia contra documentacion oficial y codigo
fuente del proyecto durante la sesion que abre este feature. El alcance de abajo ya
descarto explicitamente la alternativa de un panel custom que le pregunte a Claude en vivo
desde Grafana (ver seccion "Fuera de alcance").

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Confirmar que Claude esta vivo dentro de Grafana OSS (Priority: P1)

Como responsable del proyecto, quiero que Grafana tenga el plugin oficial de LLM instalado
y conectado a la misma cuenta de Anthropic que ya usa `src/`, para demostrar que Claude
puede integrarse nativamente en el stack de monitoreo sin pagar licencia de Grafana
Cloud/Enterprise.

**Why this priority**: es la base tecnica (instalacion + credenciales) de la que depende
cualquier uso posterior del plugin. Sin esto no hay nada que mostrar.

**Independent Test**: con el stack levantado (`docker compose up -d influxdb grafana`) y
`ANTHROPIC_API_KEY` real en `.env`, entrar a editar el titulo o la descripcion de un panel
del dashboard `motor-001-mvp` y usar el boton nativo "Auto generate" de Grafana (habilitado
por el feature toggle `dashgpt`). Genera texto coherente sin error de conexion.

**Acceptance Scenarios**:

1. **Given** el contenedor `grafana` levantado con el plugin instalado y provisionado,
   **When** se abre la configuracion de plugins de Grafana (Administration > Plugins >
   LLM), **Then** el plugin aparece habilitado y su chequeo de conexion con el proveedor
   Anthropic es exitoso.
2. **Given** el feature toggle `dashgpt` habilitado, **When** se edita el titulo de un panel
   del dashboard `motor-001-mvp` y se presiona "Auto generate", **Then** Grafana devuelve un
   titulo generado por Claude sin error, confirmando que la llamada real a la API de
   Anthropic funciona desde adentro de Grafana.

---

### User Story 2 - Ver el ultimo diagnostico de IA dentro del dashboard (Priority: P2)

Como usuario que mira el dashboard operacional (`motor-001-mvp`), quiero ver el texto del
ultimo diagnostico de IA generado para el motor (causa probable, urgencia, accion
recomendada) sin tener que ir a buscar el mensaje de Telegram o pedirlo por el endpoint
`/diagnosticar/<id>`, para tener el contexto de IA a la vista junto con las curvas de
temperatura/corriente/vibracion.

**Why this priority**: es el valor real que pedia el caso de uso original ("resumen del
estado del motor"), pero resuelto reusando el diagnostico que `src/` ya genera (D13) en vez
de duplicar la logica de llamar a Claude dentro de Grafana (ver Principio III de la
constitucion, "Un Cerebro, Muchos Consumidores").

**Independent Test**: con una alerta CRITICO real (diagnostico automatico) o una alerta
ALERTA con diagnostico pedido via `POST /diagnosticar/<id>` (D13), verificar que el texto
del diagnostico aparece en el panel nuevo del dashboard `motor-001-mvp` sin recargar
manualmente mas alla del refresco normal del dashboard.

**Acceptance Scenarios**:

1. **Given** una Alerta CRITICO recien generada con diagnostico automatico exitoso,
   **When** el dashboard `motor-001-mvp` se refresca, **Then** el panel de diagnostico
   muestra causa probable, urgencia y accion recomendada de esa alerta, con su timestamp.
2. **Given** una Alerta ALERTA sin diagnostico pedido todavia, **When** se consulta el
   panel de diagnostico, **Then** el panel muestra el ultimo diagnostico disponible (de una
   alerta anterior) o un estado vacio explicito si nunca hubo ninguno — nunca un error ni un
   dato en blanco ambiguo.
3. **Given** que se pide el diagnostico de esa Alerta ALERTA via `POST /diagnosticar/<id>`,
   **When** el pedido termina con exito, **Then** el panel se actualiza con el nuevo
   diagnostico en el siguiente refresco, sin intervencion manual mas alla de mirar el
   dashboard.

---

### Edge Cases

- Que pasa si `ANTHROPIC_API_KEY` no esta seteada en `.env` cuando arranca `grafana`: el
  plugin MUST quedar instalado pero con el chequeo de conexion en error, visible en
  Administration > Plugins — MUST NOT impedir que el resto de Grafana (dashboards,
  datasource de InfluxDB) siga funcionando.
- Que pasa si el schema de provisioning (`jsonData`/`secureJsonData`) no coincide con el que
  espera la version instalada del plugin: MUST fallar de forma visible en los logs de
  Grafana al arrancar (mismo patron ya usado para diagnosticar provisioning en este proyecto,
  ver Session 2026-09-01), no silenciosamente.
- Que pasa con un diagnostico viejo cuando llega una alerta nueva sin diagnostico propio
  todavia: el panel MUST mostrar el timestamp del diagnostico que esta mostrando, para que
  no se lea como si fuera del momento actual.
- Que pasa si `escribir_diagnostico` (la nueva escritura a InfluxDB) falla: MUST ser
  best-effort igual que `escribir_evento_alerta` ya existente — un fallo aca no MUST
  bloquear el pipeline de deteccion/diagnostico/notificacion, que ya persistio el
  diagnostico en SQLite.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST instalar el plugin `grafana-llm-app` en el contenedor
  `grafana` (`GF_INSTALL_PLUGINS`), sin tocar la imagen base del `docker-compose.yml`.
- **FR-002**: El sistema MUST provisionar el plugin con el proveedor Anthropic via un
  archivo YAML nuevo (`grafana/provisioning/plugins/`), reutilizando `ANTHROPIC_API_KEY` de
  `.env` por sustitucion de variable de entorno — MUST NOT hardcodear el valor de la key en
  ningun archivo versionado en git.
- **FR-003**: El sistema MUST habilitar el feature toggle `dashgpt`
  (`GF_FEATURE_TOGGLES_ENABLE`) para exponer el boton nativo "Auto generate" de titulo y
  descripcion en paneles/dashboards.
- **FR-004**: El sistema MUST persistir en InfluxDB el texto del ultimo diagnostico de IA
  (causa probable, urgencia, accion recomendada) generado por `src/`, en el momento en que
  `src/` lo genera — tanto en el camino automatico (severidad CRITICO) como en el camino
  on-demand (severidad ALERTA, D13).
- **FR-005**: El dashboard `motor-001-mvp` MUST mostrar un panel nuevo con el ultimo
  diagnostico disponible del equipo, leido desde InfluxDB (no desde SQLite — Grafana no
  tiene plugin de SQLite, mismo motivo ya documentado para las anotaciones de alerta).
- **FR-006**: El sistema MUST NOT agregar ningun llamado nuevo a la API de Claude desde
  Grafana ni desde ningun plugin/panel custom de Grafana — el unico consumidor de la API de
  Anthropic para diagnostico sigue siendo `src/` (Principio III de la constitucion).
- **FR-007**: El panel de diagnostico MUST mostrar el timestamp del diagnostico junto al
  texto.
- **FR-008**: Si no existe ningun diagnostico todavia para el equipo, el panel MUST mostrar
  un estado vacio explicito.

*Item que queda para `/speckit-plan` (research.md), no se fija en este spec:*

- **FR-009**: El sistema MUST provisionar el proveedor Anthropic usando los nombres de
  campo exactos (`jsonData`/`secureJsonData`) que espera la version del plugin efectivamente
  instalada [NEEDS CLARIFICATION: la documentacion oficial y los ejemplos publicos de
  Grafana Labs son inconsistentes entre si sobre el nombre/casing de estos campos —
  verificar empiricamente contra la version instalada antes de escribir el YAML final].

### Key Entities *(include if feature involves data)*

- **Evento de diagnostico (InfluxDB)**: espejo liviano del ultimo `Diagnostico` de SQLite
  para un equipo — equipo_id, alerta_id, causa_probable, urgencia, accion_recomendada,
  timestamp. Escritura best-effort, igual patron que el `escribir_evento_alerta` que ya
  existe para las anotaciones (`src/almacenamiento/influx_repo.py`).
- **Configuracion del plugin LLM (provisioning de Grafana)**: proveedor Anthropic, URL del
  API, referencia (no valor) a `ANTHROPIC_API_KEY`. No es un dato del dominio del motor —
  es configuracion de infraestructura de Grafana.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con el stack levantado y `ANTHROPIC_API_KEY` real, el boton "Auto generate" de
  Grafana genera texto sin error de conexion, confirmando que el plugin habla con Claude
  real usando la misma cuenta que `src/`.
- **SC-002**: Al generarse un diagnostico real (automatico CRITICO u on-demand ALERTA via
  D13), el texto aparece en el panel del dashboard `motor-001-mvp` sin intervencion manual
  mas alla del refresco normal del dashboard.
- **SC-003**: Ningun cambio de este feature agrega una llamada nueva a la API de Claude
  fuera de `src/` — verificable revisando el diff final: no se agrega codigo TypeScript ni
  ningun plugin/panel custom de Grafana.
- **SC-004**: El endpoint `/diagnosticar/<alerta_id>` (D13) sigue funcionando exactamente
  igual que antes de este feature — este feature solo agrega un consumidor de lectura
  (Grafana) al dato que `src/` ya genera, no cambia el contrato del endpoint.

## Assumptions

- `ANTHROPIC_API_KEY` ya esta cargada en `.env` (confirmado en sesiones anteriores) y sigue
  siendo la misma cuenta/billetera que ya paga los diagnosticos de `src/` — este feature no
  agrega gasto nuevo de tokens salvo el uso puntual del boton "Auto generate" (Historia 1).
- No se construye ningun panel/plugin custom de Grafana con `@grafana/llm` que le pregunte a
  Claude en vivo por el estado del motor — se descarta explicitamente (ver "Fuera de
  alcance") por falta de referencia mantenida (el ejemplo oficial `grafana-llmexamples-app`
  esta archivado desde 2026-06-05) y por tension directa con el Principio III de la
  constitucion (un solo consumidor de la API de Claude).
- El measurement/campo exacto donde se escribe el diagnostico en InfluxDB (extender el
  measurement `alertas` existente o crear uno nuevo `diagnosticos`) se decide en `plan.md`
  segun lo que sea mas simple de consultar con Flux — no es una decision de producto, es de
  diseno de datos.
- El nombre de la carpeta `grafana/provisioning/plugins/` no existe hoy en el repo — este
  feature la crea.

## Fuera de alcance

- **Panel custom con resumen de datos en vivo** (TypeScript + React + `@grafana/llm`
  llamando a Claude con las ultimas lecturas): es el caso de uso original que motivo la
  investigacion, pero se descarta para este feature. Motivo: (a) el unico ejemplo publico
  mantenido por Grafana Labs para este patron esta archivado y ya no recibe soporte; (b)
  abre un segundo camino cognitivo en paralelo a `src/`, en tension directa con el
  Principio III de la constitucion ("Un Cerebro, Muchos Consumidores", D3). Si en el futuro
  se decide construirlo de todos modos, requiere una decision nueva y explicita en
  `memory/decisions.md` que reconozca y acepte esa tension, no es continuacion natural de
  este feature.
- Funcionalidades de Grafana Cloud/Enterprise (Grafana ML, Grafana Assistant, Grafana Sift):
  no aplican, Grafana OSS no las tiene disponibles (ver investigacion previa referenciada en
  D15).
