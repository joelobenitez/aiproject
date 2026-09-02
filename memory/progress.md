# Progress — aiproject

> **Ultima actualizacion:** 2026-09-02
> **Donde estamos:** MVP (feature 001) y feature 002 (plugin LLM de Grafana) completos,
> commiteados y validados end-to-end contra el stack Docker real (Claude real, Telegram real,
> Grafana real). 39/39 tests en verde. **D17** (2026-09-01) cambio el nucleo de IA de
> diagnostico a resumen factual (`resumen_ejecutivo`/`hechos_destacados`, sin
> causa/urgencia/accion) — es el comportamiento vigente en todo el pipeline. **D18**
> (2026-09-02) conecto el RUT956 real por primera vez, publicando al Mosquitto local del
> proyecto. **D19** (2026-09-02) abrio la spec `003-robustez-seguridad` a partir de una
> auditoria real del codigo (7 hallazgos, ver `investigacion/handoff_spec_003_robustez.md`);
> **D20** resolvio las 9 `NEEDS CLARIFICATION` de esa spec. Ciclo SDD completo hasta
> `tasks.md` (37 tareas, 6 historias) — falta la implementacion.
>
> Historial completo de sesiones anteriores (implementacion del MVP, bugs encontrados y
> arreglados, feature 002, D13-D18) decantado en `memory/historico.md` en el barrido de stores
> del 2026-09-02.

---

## Foco actual: spec 003 (robustez + seguridad del servicio) — lista para implementar

`specs/003-robustez-seguridad/` completa: `spec.md` (D19/D20, sin `NEEDS CLARIFICATION`),
`plan.md` (diseno tecnico por hallazgo), `data-model.md`, `quickstart.md` (6 escenarios) y
`tasks.md` (37 tareas en 6 historias — Fase 1 combina H1+H2 por acoplamiento real de
`src/main.py`; Fase 5/US6 depende de esa misma base).

**Proximo paso:** implementacion, empezando por Fase 1 (T001-T007, el MVP minimo de esta
spec: ingesta resiliente + no bloqueante). Ojo — Fase 4 (US5, seguridad) tiene 2 tareas
manuales que no son codigo: **T024** rotar `ANTHROPIC_API_KEY` en `console.anthropic.com`
(pendiente desde el 2026-09-01) y **T025** actualizar la config "Data to Server" del RUT956
con las credenciales MQTT nuevas (D18) — sin esto el router deja de poder publicar en cuanto
el broker deje de aceptar conexiones anonimas. Comandos `/speckit-*` no instalados en esta
terminal — seguir usando `.specify/scripts/powershell/*.ps1` + templates a mano (D19).

---

## Foco secundario: integracion del RUT956 (D11/D18), bloqueada en hardware

Joelo todavia no tiene el adaptador **USB-RS485**. Hasta que llegue, este frente queda en
pausa. El simulador ya esta escrito y probado en seco:
`herramientas/simulador_modbus_rtu.py` (esclavo Modbus RTU, reutiliza los escenarios A-D de
`emulador_motor.py`).

**Proximos pasos cuando llegue el adaptador:**
1. Cablear A/B del adaptador a los terminales RS485 del router (verificar etiquetado fisico,
   no confirmado todavia).
2. Anotar el puerto COM que Windows le asigna.
3. En el RUT956: habilitar el puerto fisico en modo RS485 (probablemente en "Serial
   Utilities", no confirmado en vivo) y agregar una instancia de **Modbus Serial Client**
   (id de esclavo 1, mismo baudrate que el script).
4. Correr `python herramientas/simulador_modbus_rtu.py --puerto COM<X>` y confirmar que sube
   el contador de "successful requests".
5. Mapear el payload de "Data to Server" (formato propio de Teltonika, ver D18) al contrato
   que espera `src/ingesta` — hoy solo llega auto-sondeo/GPS, no datos de un "motor".

Bibliografia oficial de las APIs del RUT956 (RutOS Web API, JSON-RPC, Modbus, MQTT, SSH):
guardada en la memoria del asistente (no en este repo), para usar cuando se configure el
equipo.

---

## Git

Local y remoto sincronizados en `548de51` (terminal `jbenitez`). La terminal `joelo` necesita
`git pull` para traer toda la sesion del 2026-09-02: `2db7cf7` (D18, simulador Modbus RTU),
`7c76e47` (fix de terminologia, riesgo de migracion InfluxDB), `c3e43e2` (auditoria de stores
+ spec 003 / D19), `b264077` (D20 + plan.md), `548de51` (tasks.md).

---

## Pendientes sueltos (genuinamente abiertos, sin apuro)

- **Secretos en produccion** (`ANTHROPIC_API_KEY`, credenciales DB) — sin decision todavia.
  Ver D3/D8 en `memory/decisions.md` y el riesgo abierto en `memory/risks.md`.
- **Migracion InfluxDB en la terminal `joelo`** — probable que tenga el mismo problema de
  esquemas `diagnosticos` mezclados que se arreglo hoy en `jbenitez`. Ver riesgo nuevo en
  `memory/risks.md`.
- **Telegram Nivel 1** (webhook/long-polling para que el bot dispare el diagnostico bajo
  demanda) — valor futuro, no urgente. Ver D2/D13 en `memory/decisions.md`.
- **Por que completo de D5** (adoptar Spec Kit) — nunca se confirmo con Joelo mas alla de
  "arrancar SDD". Ver D5 en `memory/decisions.md`.
- **Copia WSL2 obsoleta** (`/home/joelo/aiproject`) — borrado/resincronizacion pendiente de
  Joelo, sin apuro (D7).
