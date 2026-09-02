# Progress — aiproject

> **Ultima actualizacion:** 2026-09-02
> **Donde estamos:** MVP (feature 001) y feature 002 (plugin LLM de Grafana) completos,
> commiteados y validados end-to-end contra el stack Docker real (Claude real, Telegram real,
> Grafana real). 39/39 tests en verde. **D17** (2026-09-01) cambio el nucleo de IA de
> diagnostico a resumen factual (`resumen_ejecutivo`/`hechos_destacados`, sin
> causa/urgencia/accion) — es el comportamiento vigente en todo el pipeline. **D18**
> (2026-09-02) conecto el RUT956 real por primera vez, publicando al Mosquitto local del
> proyecto. **D19** (2026-09-02) abrio la spec `003-robustez-seguridad` a partir de una
> auditoria real del codigo (7 hallazgos, ver `investigacion/handoff_spec_003_robustez.md`).
>
> Historial completo de sesiones anteriores (implementacion del MVP, bugs encontrados y
> arreglados, feature 002, D13-D18) decantado en `memory/historico.md` en el barrido de stores
> del 2026-09-02.

---

## Foco actual: spec 003 (robustez + seguridad del servicio) — no bloqueada, avanzar aca

`specs/003-robustez-seguridad/spec.md` escrita (D19), a partir de un handoff de auditoria
(`investigacion/handoff_spec_003_robustez.md`) que encontro 7 hallazgos reales en `src/`
(hilo de ingesta que muere en silencio, pipeline bloqueante en el callback MQTT, deteccion
sin banda muerta, cooldown solo en RAM, resumen fallido cacheado para siempre, race en el
endpoint bajo demanda, superficie de seguridad mas ancha de lo documentado). Queda **Draft**
con 9 `NEEDS CLARIFICATION` — antes de `plan.md` hay que resolver sobre todo: mecanismo de
auth del endpoint, credenciales/TLS del broker, y que puertos cerrar (preguntas 3, 4, 5 del
handoff) son decisiones de producto, no de diseno tecnico. El resto puede resolverse con
valores por defecto razonables en `plan.md`/`research.md`.

**Proximo paso:** resolver los `NEEDS CLARIFICATION` (con Joelo, sobre todo las 3 de
seguridad) y seguir con el equivalente de `/speckit-plan`. Comandos `/speckit-*` no
instalados en esta terminal — usar `.specify/scripts/powershell/*.ps1` + templates a mano,
mismo rodeo que el feature 002 (ver D19, nota operativa).

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

Local y remoto sincronizados en `7c76e47` (terminal `jbenitez`). La terminal `joelo` necesita
`git pull` para traer `2db7cf7` y `7c76e47` (sesion del 2026-09-02: D18, simulador Modbus RTU,
fix de terminologia, riesgo de migracion InfluxDB).

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
