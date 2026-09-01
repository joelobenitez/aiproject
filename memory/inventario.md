# Inventario — aiproject

Mapa de artefactos: ubicacion, contenido en una linea, estado.

---

## Memoria y contrato

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Contrato del proyecto | `CLAUDE.md` | Reglas estables: contexto, hardware, arquitectura, entorno de desarrollo, indice de donde leer cada cosa | Validado (reescrito 2026-08-29 al adoptar el metodo) |
| Estado vivo | `memory/progress.md` | Foto del presente + proximos pasos, se lee siempre al abrir sesion | Validado |
| Decisiones | `memory/decisions.md` | D1-D6, numeradas, con el porque y alternativas descartadas | Validado |
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
| Comandos | `.claude/skills/speckit-*/SKILL.md` | 9 comandos `/speckit-constitution`, `/speckit-specify`, `/speckit-clarify`, `/speckit-plan`, `/speckit-checklist`, `/speckit-tasks`, `/speckit-analyze`, `/speckit-implement`, `/speckit-converge`, `/speckit-taskstoissues` | Instalados Session 05. Usados para el loop completo del feature 001 (`/speckit-implement` corrido de punta a punta) |

La herramienta (`.specify/` + comandos) queda activa e instalada — no se jubila. Los
artefactos generados para el feature 001 (spec/plan/tasks/etc.) sí se jubilaron, ver
tabla "Jubilados (obs/)" (D14).

## Spec Kit — feature 002 (en progreso)

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Spec del feature 002 | `specs/002-grafana-llm-diagnostico/spec.md` | Plugin `grafana-llm-app` (dashgpt) + panel de diagnostico IA en el dashboard, reusando D13, sin panel custom (D15) | Draft — escrito a mano siguiendo `spec-template.md` (el comando `/speckit-specify` no corrio, ver nota operativa en D15 y `memory/risks.md`). |
| Plan del feature 002 | `specs/002-grafana-llm-diagnostico/plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `contracts/diagnostico-influxdb.md` | Contexto tecnico, Constitution Check (todo PASS), archivos concretos a tocar, verificacion pendiente de campos exactos del provisioning Anthropic, schema del measurement `diagnosticos` nuevo en InfluxDB | Hecho a mano (mismo motivo que el spec) — Fase 0+1 completas. |
| Tasks del feature 002 | `specs/002-grafana-llm-diagnostico/tasks.md` | 13 tareas en 2 historias independientes (US1 plugin, US2 panel) + Polish | 13/13 completas (2026-09-01), validadas contra el stack real. Ver `memory/progress.md` para el resumen. |

## Jubilados (obs/)

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Checkpoint viejo | `obs/CHECKPOINT.md` | Mecanismo de cierre/reanudacion ad-hoc, ultimo estado registrado: cierre Session 05 (2026-08-10) | Obsoleto — reemplazado por `memory/progress.md` + `memory/decisions.md`. Se conserva como registro historico. |
| Overview de Gemini | `obs/GEMINI.md` | Overview de la fase de investigacion temprana, generado por Gemini | Obsoleto — ya estaba marcado como "referencia historica" en el CLAUDE.md anterior. Se conserva. |
| CLAUDE.md pre-metodo | `obs/CLAUDE_pre-metodo.md` | Version de `CLAUDE.md` previa a adoptar el metodo de memoria multisesion (incluia estado y proximos pasos mezclados con las reglas estables) | Obsoleto — contenido decantado al nuevo `CLAUDE.md` + `memory/decisions.md` + `memory/historico.md`. Se conserva. |
| Spec Kit — artefactos del feature 001 | `obs/specs/001-diagnostico-motor-industrial/` (spec.md, plan.md, tasks.md, research.md, quickstart.md, data-model.md, contracts/, checklists/) | Ciclo SDD completo y cerrado del MVP (38/38 tareas). Incluye los contratos de datos originales (MQTT payload, schema InfluxDB, contrato interno del servicio) | Jubilado 2026-09-01 (D14) — registro historico constructivo. `src/` es la fuente de verdad viva del codigo/contratos implementados; este archivo se consulta solo si hace falta el detalle de diseno original o el razonamiento del spec/plan de esa etapa. No se migro contenido a otro lado para no duplicar. |

## Infraestructura

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Repositorio git (Windows) | esta carpeta | — | **No existe todavia** — no se corrio `git init` aca (ver risks.md) |
| Repositorio git (WSL2) | `/home/joelo/aiproject` | Repo con remote a `github.com/joelobenitez/aiproject` | Existe pero desactualizado y desincronizado de esta carpeta (ver risks.md) |
| Docker Compose | — | Servicios EMQX, InfluxDB, MySQL, Node-RED, n8n, Grafana | No implementado todavia — solo tabla de referencia (imagen/puerto) en `definicion/arquitectura_sistema.md` |
