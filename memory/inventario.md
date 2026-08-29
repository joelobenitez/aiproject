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
| Constitution | `.specify/memory/constitution.md` | Template vacio de Spec Kit, sin completar | Pendiente — ver risks.md |
| Templates | `.specify/templates/*.md` | spec-template, plan-template, tasks-template, checklist-template, constitution-template | Sin tocar (default de Spec Kit) |
| Scripts | `.specify/scripts/powershell/*.ps1` | Scripts de soporte del workflow Spec Kit (PowerShell, acorde al entorno Windows) | Sin tocar (default de Spec Kit) |
| Comandos | `.claude/skills/speckit-*/SKILL.md` | 9 comandos `/speckit-constitution`, `/speckit-specify`, `/speckit-clarify`, `/speckit-plan`, `/speckit-checklist`, `/speckit-tasks`, `/speckit-analyze`, `/speckit-implement`, `/speckit-converge`, `/speckit-taskstoissues` | Instalados Session 05, no usados todavia |

## Jubilados (obs/)

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Checkpoint viejo | `obs/CHECKPOINT.md` | Mecanismo de cierre/reanudacion ad-hoc, ultimo estado registrado: cierre Session 05 (2026-08-10) | Obsoleto — reemplazado por `memory/progress.md` + `memory/decisions.md`. Se conserva como registro historico. |
| Overview de Gemini | `obs/GEMINI.md` | Overview de la fase de investigacion temprana, generado por Gemini | Obsoleto — ya estaba marcado como "referencia historica" en el CLAUDE.md anterior. Se conserva. |
| CLAUDE.md pre-metodo | `obs/CLAUDE_pre-metodo.md` | Version de `CLAUDE.md` previa a adoptar el metodo de memoria multisesion (incluia estado y proximos pasos mezclados con las reglas estables) | Obsoleto — contenido decantado al nuevo `CLAUDE.md` + `memory/decisions.md` + `memory/historico.md`. Se conserva. |

## Infraestructura

| Artefacto | Ubicacion | Contenido | Estado |
|---|---|---|---|
| Repositorio git (Windows) | esta carpeta | — | **No existe todavia** — no se corrio `git init` aca (ver risks.md) |
| Repositorio git (WSL2) | `/home/joelo/aiproject` | Repo con remote a `github.com/joelobenitez/aiproject` | Existe pero desactualizado y desincronizado de esta carpeta (ver risks.md) |
| Docker Compose | — | Servicios EMQX, InfluxDB, MySQL, Node-RED, n8n, Grafana | No implementado todavia — solo tabla de referencia (imagen/puerto) en `definicion/arquitectura_sistema.md` |
