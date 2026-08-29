# Historico — aiproject

Hitos cerrados, decantados desde `progress.md`. Se lee casi nunca.

---

## Fase de investigacion (previa a Session 02)

Se investigaron proyectos de referencia en GitHub sobre IoT, MQTT, Node-RED, OPC-UA e IA.
Se identificaron y documentaron 3 proyectos principales como referencia (ver
`investigacion/Resumen_investigacion.md`), con un analisis en profundidad del proyecto
"IoT Predictive Maintenance System (Mic-360)" (ver `investigacion/Proyecto_explicado.md`).
Cerrada — decanto en la base de `investigacion/`, que se mantiene como archivo de consulta.

## Session 02 (2026-06-04) — Definicion de arquitectura y caso de uso

Se definio la arquitectura completa del sistema (diagrama de flujo, roles de cada
componente, stack Docker Compose de referencia, estructura de topicos MQTT) y el caso de
uso de Fase 1 (motor industrial simulado, variables, escenarios de falla, formato de
diagnostico esperado). Cerrada — decanto en `definicion/arquitectura_sistema.md` y
`definicion/caso_de_uso_fase1.md`, ambos vigentes.

## Session 03 — Resueltas D1, D2, D3

Se resolvieron tres de las cuatro decisiones de diseno abiertas: deteccion de anomalia
(Node-RED + webhook a n8n), modelo de Telegram (bidireccional por niveles) y arquitectura
del Claude Agent (Python daemon en Docker). Fecha exacta no registrada en las fuentes
disponibles (posterior a 2026-06-04). Cerrada — decanto en `memory/decisions.md` (D1-D3).

## Session 04 — Resuelta D4

Se resolvio la ultima decision de diseno pendiente: el Web Report ejecutivo como HTML
estatico generado por el Claude Agent. Fecha exacta no registrada. Cerrada — decanto en
`memory/decisions.md` (D4). Con esta sesion se cerro toda la fase de definicion (D1-D4
resueltas).

## Session 05 (2026-08-10) — Instalacion de Spec Kit

Se instalo `uv` y `specify-cli` (via git+github.com/github/spec-kit), y se inicializo Spec
Kit en la carpeta de trabajo (Windows/OneDrive) con `specify init --here --integration
claude --force`, en modo merge sin tocar `definicion/` ni `CLAUDE.md`. Quedaron
scaffoldeados `.specify/` y los 9 comandos `/speckit-*`. Se detecto la duplicacion entre
esta carpeta (Windows, con todo el contenido pero sin git) y `/home/joelo/aiproject` (WSL2,
con git pero desactualizada); se le pregunto a Joelo como resolverlo y la decision de esa
sesion fue no tocar nada todavia. Cerrada — decanto en `memory/decisions.md` (D5) y el
riesgo de la carpeta duplicada paso a `memory/risks.md`.

## Mecanismo de memoria anterior (Sesiones 01-05) — jubilado 2026-08-29

Hasta esta migracion, el estado del proyecto se llevaba en un unico archivo `CHECKPOINT.md`
reescrito manualmente al cierre de cada sesion (estado actual + que se hizo + proximos
pasos + un "prompt de reanudacion" para pegar en la sesion siguiente), sin separacion entre
tipo de informacion. Al adoptar el metodo de memoria multisesion (D6, 2026-08-29), ese
archivo se jubilo a `obs/CHECKPOINT.md` junto con `obs/GEMINI.md` (overview temprano de la
fase de investigacion) y `obs/CLAUDE_pre-metodo.md` (version anterior del contrato). Su
contenido vigente quedo distribuido en `memory/progress.md`, `memory/decisions.md` (D5) y
esta seccion de historico.
