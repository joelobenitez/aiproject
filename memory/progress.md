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
> **D20** resolvio las 9 `NEEDS CLARIFICATION` de esa spec. **Las 6 historias de usuario de la
> spec 003 estan implementadas y validadas end-to-end contra el stack Docker real** (T001-T037,
> salvo T024/T025 — manuales, pendientes). 49/49 tests en verde. **D21** (entrypoint,
> `python -m src`) y **D22** (mosquitto/passwd al build) son dos bugs reales preexistentes
> encontrados y arreglados durante la implementacion — detalle en `memory/decisions.md`.
>
> Historial completo de sesiones anteriores (implementacion del MVP, bugs encontrados y
> arreglados, feature 002, D13-D18) decantado en `memory/historico.md` en el barrido de stores
> del 2026-09-02.

---

## Foco actual: spec 003 (robustez + seguridad del servicio) — completa, quedan 2 tareas manuales

`specs/003-robustez-seguridad/` (H1-H7 del handoff, D19/D20) esta **completa**: 37/37 tareas
de codigo/validacion (`tasks.md`), las 6 historias de usuario implementadas y validadas tanto
por tests (39->49 en verde) como en vivo contra el stack Docker real, fase por fase. Detalle
completo (que toco cada fase, los 2 bugs reales encontrados en el camino D21/D22, y como se
valido cada escenario de `quickstart.md`) decantado en `memory/historico.md`
("Implementacion completa de la spec 003").

**Pendiente (manuales, no codigo, sin apuro pero bloquean al RUT956 real):**
- **T024** — rotar `ANTHROPIC_API_KEY` en `console.anthropic.com` (pendiente desde el
  2026-09-01) y actualizar `.env`.
- **T025** — cargar las credenciales MQTT nuevas (usuario `aiproject`, ver `.env`) en la
  config "Data to Server" del RUT956 (D18) — **el router real esta efectivamente
  desconectado del broker** desde que se activo `allow_anonymous false` (D22/Fase 4).

**Proximo paso:** ninguno de codigo pendiente en esta spec. El proximo trabajo depende de que
Joelo indique un nuevo foco (ver "Pendientes sueltos" y el foco secundario del RUT956 abajo).
Comandos `/speckit-*` no instalados en esta terminal — seguir usando
`.specify/scripts/powershell/*.ps1` + templates a mano si se abre una spec nueva (D19).

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

Local y remoto sincronizados en `2ce05bc` (terminal `jbenitez`). La terminal `joelo` necesita
`git pull` para traer toda la sesion del 2026-09-02 (RUT956/D18 + spec 003 completa, D19-D22)
— detalle commit por commit en `memory/historico.md`. **Tres cambios que le van a pedir accion
manual al traer el pull:**
1. El servicio ahora arranca con `python -m src` (D21) — actualizar cualquier script/alias
   local que invoque `python src/main.py` directo.
2. El broker ahora es `build: ./mosquitto` (D22) — generar `mosquitto/passwd` local antes del
   primer build (ver `README.md`).
3. `.env` necesita `MQTT_USERNAME`/`MQTT_PASSWORD`/`API_TOKEN`/`GRAFANA_ADMIN_PASSWORD`
   nuevos — sin ellos el stack no arranca sano.

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
