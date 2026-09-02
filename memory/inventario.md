# Inventario — aiproject

Mapa de artefactos: ubicacion, contenido en una linea, estado.

---

## Memoria y contrato

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Contrato del proyecto | `CLAUDE.md` | Reglas estables: contexto, hardware, arquitectura, entorno de desarrollo, indice de donde leer cada cosa | Validado (reescrito 2026-08-29 al adoptar el metodo) |
| Estado vivo | `memory/progress.md` | Foto del presente + proximos pasos, se lee siempre al abrir sesion | Validado |
| Decisiones | `memory/decisions.md` | Numeradas (D1-D18 al 2026-09-02), con el porque y alternativas descartadas | Validado |
| Riesgos | `memory/risks.md` | Precondiciones y "no romper" (carpeta duplicada, secretos, etc.) | Validado |
| Inventario | `memory/inventario.md` | Este archivo | Validado |
| Historico | `memory/historico.md` | Sesiones y hitos cerrados | Validado |

## Definicion del producto

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Arquitectura del sistema | `definicion/arquitectura_sistema.md` | Diagrama de flujo completo, roles de cada componente, detalle de D1-D4, stack docker-compose de referencia, estructura de topicos MQTT (UNS) y payload JSON | Validado — definido Session 02, decisiones cerradas Session 03-04 |
| Caso de uso Fase 1 | `definicion/caso_de_uso_fase1.md` | Motor industrial simulado: variables, umbrales, escenarios de falla (A-D), flujo end-to-end, formato JSON del diagnostico esperado, criterios de exito, alcance excluido | Validado — definido Session 02 |

## Investigacion (previa a la definicion)

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Investigacion Claude + IoT | `investigacion/investigacion_claude_iot.md` | Stack completo evaluado, repos de GitHub relevados, roadmap propuesto | No releido en esta migracion (archivo de 20972 bytes) — mantiene su contenido original |
| Resumen de investigacion | `investigacion/Resumen_investigacion.md` | Top 3 proyectos de GitHub identificados como referencia (IoT/MQTT/Node-RED/OPC-UA/AI) | Validado, referencia |
| Proyecto explicado | `investigacion/Proyecto_explicado.md` | Analisis en detalle del proyecto "IoT Predictive Maintenance System (Mic-360)", uno de los 3 identificados | Validado, referencia |

## Spec Kit (herramienta de desarrollo)

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Constitution | `.specify/memory/constitution.md` | v1.1.0 — 5 principios, Principio I con excepcion de fase MVP (D12) | Usado para el feature 001 (cerrado). Queda activo, disponible para features futuras |
| Templates | `.specify/templates/*.md` | spec-template, plan-template, tasks-template, checklist-template, constitution-template | Sin tocar (default de Spec Kit) |
| Scripts | `.specify/scripts/powershell/*.ps1` | Scripts de soporte del workflow Spec Kit (PowerShell, acorde al entorno Windows) | Sin tocar (default de Spec Kit) |
| Comandos | `.claude/skills/speckit-*/SKILL.md` | 9 comandos `/speckit-constitution`, `/speckit-specify`, `/speckit-clarify`, `/speckit-plan`, `/speckit-checklist`, `/speckit-tasks`, `/speckit-analyze`, `/speckit-implement`, `/speckit-converge`, `/speckit-taskstoissues` | Instalados Session 05. **No instalados en la terminal `jbenitez`** (`.claude/` no viaja con git) — rodeo usado: `.specify/scripts/powershell/*.ps1` (100% local) + templates a mano |
| Feature 003 | `specs/003-robustez-seguridad/` (spec.md, plan.md, data-model.md, quickstart.md, tasks.md) | Robustez + seguridad del servicio (H1-H7 de `investigacion/handoff_spec_003_robustez.md`), estado del detector persistido. Ver D19 (alcance), D20 (`NEEDS CLARIFICATION` resueltas), D21 (fix de entrypoint), D22 (mosquitto/passwd al build) | Fases 1-5 (las 6 historias de usuario) implementadas y validadas 2026-09-02, salvo T024/T025 (manuales, pendientes). Falta solo Polish (T032-T037) |
| Broker Mosquitto | `mosquitto/` (Dockerfile, mosquitto.conf, acl.conf, passwd*) | Autenticado desde D22/T019: `Dockerfile` copia la config al build (no bind-mount, ver D22); `passwd` gitignoreado, se genera local con `mosquitto_passwd` | Activo — `docker-compose.yml` build `./mosquitto`. *`passwd` no esta en git, hay que generarlo (`README.md`) |

La herramienta (`.specify/` + comandos) queda activa e instalada — no se jubila. Los
artefactos generados para el feature 001 (spec/plan/tasks/etc.) sí se jubilaron, ver
tabla "Jubilados (obs/)" (D14).


## Jubilados (obs/)

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Checkpoint viejo | `obs/CHECKPOINT.md` | Mecanismo de cierre/reanudacion ad-hoc, ultimo estado registrado: cierre Session 05 (2026-08-10) | Obsoleto — reemplazado por `memory/progress.md` + `memory/decisions.md`. Se conserva como registro historico. |
| Overview de Gemini | `obs/GEMINI.md` | Overview de la fase de investigacion temprana, generado por Gemini | Obsoleto — ya estaba marcado como "referencia historica" en el CLAUDE.md anterior. Se conserva. |
| CLAUDE.md pre-metodo | `obs/CLAUDE_pre-metodo.md` | Version de `CLAUDE.md` previa a adoptar el metodo de memoria multisesion (incluia estado y proximos pasos mezclados con las reglas estables) | Obsoleto — contenido decantado al nuevo `CLAUDE.md` + `memory/decisions.md` + `memory/historico.md`. Se conserva. |
| Spec Kit — artefactos del feature 001 | `obs/specs/001-diagnostico-motor-industrial/` (spec.md, plan.md, tasks.md, research.md, quickstart.md, data-model.md, contracts/, checklists/) | Ciclo SDD completo y cerrado del MVP (38/38 tareas). Incluye los contratos de datos originales (MQTT payload, schema InfluxDB, contrato interno del servicio) | Jubilado 2026-09-01 (D14) — registro historico constructivo. `src/` es la fuente de verdad viva del codigo/contratos implementados; este archivo se consulta solo si hace falta el detalle de diseno original o el razonamiento del spec/plan de esa etapa. No se migro contenido a otro lado para no duplicar. |
| Spec Kit — artefactos del feature 002 | `obs/specs/002-grafana-llm-diagnostico/` (spec.md, plan.md, tasks.md, research.md, data-model.md, quickstart.md, contracts/) | Ciclo SDD completo y cerrado del plugin LLM de Grafana + panel de diagnostico (13/13 tareas, D15). Incluye la investigacion real del schema del plugin y el bug del modelo default encontrado/arreglado | Jubilado 2026-09-01 (D16) — mismo criterio que D14. `src/`, `grafana/provisioning/` y `docker-compose.yml` son la fuente de verdad viva. No se agrega mas superficie de IA en Grafana (confirmado con Joelo tras el cierre del feature). |

## Herramientas de prueba (no forman parte del sistema)

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Emulador de motor (MQTT directo) | `herramientas/emulador_motor.py` | Publica los 4 escenarios A-D directo por MQTT, sin pasar por el RUT956 | Validado, en uso desde el MVP |
| Simulador Modbus RTU (via RS485) | `herramientas/simulador_modbus_rtu.py` | Expone un esclavo Modbus RTU (holding registers x10, reutiliza los escenarios A-D del emulador) por un puerto serie/USB-RS485, para que el RUT956 lo lea como si fuera un sensor real (D11, D18) | Escrito y probado en seco (2026-09-02) — sin validar contra hardware real, falta el adaptador USB-RS485 |

## Infraestructura

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Repositorio git | esta carpeta | Remote `origin` a `github.com/joelobenitez/aiproject` | Activo desde D7 (2026-08-29), decenas de commits, sincronizado entre terminales `jbenitez`/`joelo` via `git pull`/`push` |
| Repositorio git (WSL2) | `/home/joelo/aiproject` | Copia vieja, previa a D7 | Obsoleta, sin resincronizar — pendiente de Joelo, sin apuro (ver D7 en `memory/decisions.md`) |
| Docker Compose | `docker-compose.yml` | 4 servicios: `broker` (Mosquitto), `influxdb`, `servicio` (build local, `src/`), `grafana` (D9) | Implementado y en uso desde el MVP. Ver `memory/decisions.md` D9 y `investigacion/sistema_src_funcionamiento_detallado.md` seccion 15 para el detalle |
