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
> `tasks.md` (37 tareas, 6 historias). **Fase 1 implementada y validada** (T001-T007, H1+H2:
> cola/worker no bloqueante, ingesta resiliente a excepciones) — 41/41 tests en verde.
> **D21** (2026-09-02, durante esta implementacion) encontro y arreglo un bug real preexistente:
> el servicio ahora arranca con `python -m src` (nunca `python src/main.py` directo), porque
> ese modo duplicaba la instancia del modulo `main.py` y dejaba `ultima_lectura_en` de
> `/health` en `null` para siempre. Faltan Fases 2-5 + Polish de la spec 003.
>
> Historial completo de sesiones anteriores (implementacion del MVP, bugs encontrados y
> arreglados, feature 002, D13-D18) decantado en `memory/historico.md` en el barrido de stores
> del 2026-09-02.

---

## Foco actual: spec 003 (robustez + seguridad del servicio) — Fase 1 completa, siguen 2-5

`specs/003-robustez-seguridad/` completa: `spec.md` (D19/D20, sin `NEEDS CLARIFICATION`),
`plan.md` (diseno tecnico por hallazgo), `data-model.md`, `quickstart.md` (6 escenarios) y
`tasks.md` (37 tareas en 6 historias — Fase 1 combina H1+H2 por acoplamiento real de
`src/main.py`; Fase 5/US6 depende de esa misma base).

**Fase 1 (T001-T007, H1+H2) implementada y validada 2026-09-02:**
- `src/main.py`: el callback MQTT (`_al_recibir_mensaje`) solo normaliza y encola
  (`queue.Queue(maxsize=1000)`); un hilo worker (`_worker_loop`, daemon) consume la cola y
  corre todo el pipeline (`_procesar_lectura`), envuelto en `try/except Exception` de ultimo
  recurso — una excepcion puntual (ej. InfluxDB caido) ya no mata el proceso ni bloquea las
  lecturas siguientes.
- `GET /health` (`src/api.py`) suma `ultima_lectura_en` (FR-002).
- Backpressure: cola llena descarta el item mas viejo + warning.
- Tests nuevos: `tests/integration/test_robustez_ingesta.py` (worker real + Queue real).
  41/41 en verde (`tests/integration/_apoyo.py` ahora drena la cola en el mismo hilo para
  mantener el determinismo de los tests de escenario A-D).
- Validado en vivo contra el stack Docker real: `docker compose stop/start influxdb` +
  emulador — el servicio sigue respondiendo `/health` durante la caida, retoma solo al
  volver InfluxDB, `ultima_lectura_en` se actualiza correctamente.
- **D21** (hallazgo real durante esta validacion, no anticipado en `plan.md`): el servicio
  ahora arranca con `python -m src` (`Dockerfile`, `README.md`), nunca `python src/main.py`
  directo — ese modo duplicaba la instancia del modulo y `ultima_lectura_en` quedaba en
  `null` para siempre. Ver D21 en `memory/decisions.md` para el detalle tecnico completo.

**Fase 2 (T008-T011, H3) implementada y validada 2026-09-02:**
- `src/deteccion/detector.py`: `CONFIRMACION_LECTURAS = 3` y `BANDA_MUERTA = 0.05` (D20).
  `Detector._estado` suma `lecturas_consecutivas` (se resetea a 0 cuando una lectura no
  supera el umbral). Un evento nuevo (primera alerta O escalada) solo se genera al llegar a
  3 lecturas consecutivas. La vuelta a NORMAL exige bajar de `valor_alerta * 0.95`, no solo
  cruzar el umbral en sentido inverso.
- Detalle de diseno no anticipado en `plan.md`: una escalada ALERTA->CRITICO dispara de
  inmediato (sin esperar 3 lecturas CRITICO nuevas) porque el contador de confirmacion sigue
  vivo mientras el equipo no vuelve a NORMAL — evita retrasar una escalada real y preserva el
  comportamiento que ya validaba el test existente de escalada.
- `tests/unit/test_detector.py` reescrito: los tests viejos asumian alerta inmediata de una
  sola lectura (ya no es el comportamiento vigente) + tests nuevos de aislada/confirmada/
  banda muerta. 45/45 en verde.
- Validado con el emulador real: escenario D con 3 semillas distintas -> 0 alertas cada vez;
  escenario A -> exactamente 1 alerta (severidad ALERTA).

**Proximo paso:** Fase 3 (Historia 4, T012-T017 — cooldown persistido en SQLite +
validacion de skew del reloj del sensor, `src/almacenamiento/sqlite_repo.py` +
`src/deteccion/detector.py`). Fase 4 (US5, seguridad) tiene 2 tareas manuales que no son
codigo: **T024**
rotar `ANTHROPIC_API_KEY` en `console.anthropic.com` (pendiente desde el 2026-09-01) y
**T025** actualizar la config "Data to Server" del RUT956 con las credenciales MQTT nuevas
(D18) — sin esto el router deja de poder publicar en cuanto el broker deje de aceptar
conexiones anonimas. Comandos `/speckit-*` no instalados en esta terminal — seguir usando
`.specify/scripts/powershell/*.ps1` + templates a mano (D19).

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

Local en `49c2eee` (terminal `jbenitez`), pendiente de push. La terminal `joelo` necesita
`git pull` para traer toda la sesion del 2026-09-02, incluida la de hoy: `2db7cf7` (D18,
simulador Modbus RTU), `7c76e47` (fix de terminologia, riesgo de migracion InfluxDB),
`c3e43e2` (auditoria de stores + spec 003 / D19), `b264077` (D20 + plan.md), `548de51`
(tasks.md), `fa950e7` (cierre de sesion), `49c2eee` (Fase 1 de la spec 003 + D21 — **ojo**:
esta trae el cambio de entrypoint a `python -m src`, la terminal `joelo` tiene que actualizar
cualquier script/alias local que todavia invoque `python src/main.py` directo).

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
