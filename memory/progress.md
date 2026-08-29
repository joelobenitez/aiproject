# Progress — aiproject

> **Ultima actualizacion:** 2026-08-29
> **Donde estamos:** MVP del feature `001-diagnostico-motor-industrial` IMPLEMENTADO,
> VALIDADO EN DOCKER REAL, COMMITEADO Y PUSHEADO. `/speckit-implement` corrido de punta a
> punta: 38/38 tareas de `tasks.md` completas. Codigo en `src/` +
> `herramientas/emulador_motor.py` + `docker-compose.yml` + provisioning de Grafana. 31
> tests de pytest en verde. Stack levantado con `docker compose up` (broker+influxdb+
> servicio+grafana) y probado end-to-end con el emulador real: deteccion, persistencia
> SQLite/InfluxDB, degradacion controlada de diagnostico/notificacion (sin credenciales
> reales todavia) y Grafana provisionado, todo confirmado funcionando. Commit `2badaab`
> pusheado a `main` en GitHub — repo local y remoto identicos (verificado 2026-08-29,
> `git rev-list --left-right --count origin/main...HEAD` → `0 0`). Solo falta probar el
> diagnostico real de Claude y la notificacion real de Telegram (requiere cargar
> `ANTHROPIC_API_KEY`/`TELEGRAM_BOT_TOKEN`/`CHAT_ID` reales en `.env`, que hoy esta vacio
> a proposito y NO esta trackeado en git) y mirar el dashboard en el navegador. Metodo de
> memoria multisesion instalado (D6).

---

## Estado por frente

| Frente | Estado |
|---|---|
| Definicion (arquitectura + caso de uso) | CERRADO — D1, D2, D3, D4 resueltas. Ver `memory/decisions.md` |
| Ubicacion de la carpeta de trabajo (Windows vs WSL2) | RESUELTO (D7) — Windows/OneDrive es la fuente de verdad |
| Repo git local (esta carpeta) | CREADO — `git init -b main` + primer commit (35 archivos). Remote `origin` configurado |
| Push a GitHub | HECHO — `2badaab` en `main` en `github.com/joelobenitez/aiproject` (incluye `fe521e6` anterior), local y remoto identicos |
| Spec Kit — constitucion | HECHO — `.specify/memory/constitution.md` v1.0.0, 5 principios basados en D1-D7 |
| Spec Kit — spec del feature | HECHO — `specs/001-diagnostico-motor-industrial/spec.md`, checklist en verde, sin clarificaciones pendientes |
| Spec Kit — plan/tasks | HECHO — `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md` (38 tareas) |
| Spec Kit — implement | COMPLETO — 38/38 tareas de `tasks.md`, incluyendo T037 (validacion en Docker real) |
| Stack objetivo del MVP | REDEFINIDO (D9) — broker MQTT + InfluxDB + Grafana + 1 servicio Python (colapsa Node-RED+n8n+Agent), SQLite en vez de MySQL, Email/Web Report postergados |
| Stack objetivo a escala industrial | Roadmap anotado (D11) — vuelve a separar detector/diagnostico, RUT956 real, EMQX cluster, Postgres/MySQL, dimensionamiento de hardware |
| Contratos de datos (MQTT payload, schema InfluxDB, schema DB, contrato interno del servicio Python) | HECHO — `specs/001-diagnostico-motor-industrial/contracts/` + `data-model.md`, implementados en `src/` |
| Codigo del MVP (`src/`, `herramientas/emulador_motor.py`) | IMPLEMENTADO Y COMMITEADO — pipeline completo ingesta→deteccion→diagnostico→notificacion→Grafana, 31 tests pytest en verde |
| Docker Compose real (version MVP simplificada) | VALIDADO — `docker compose up -d --build` corrido con exito (broker+influxdb+servicio+grafana), pipeline probado end-to-end con el emulador real (ver "Pendientes sueltos") |
| Memoria multi-sesion (este metodo) | INSTALADO — 2026-08-29 |

---

## Problemas abiertos

Ninguno bloqueante. Ver "Pendientes sueltos" abajo para lo que falta cerrar.

---

## Proximos pasos

**Foco de la proxima sesion (default):** el MVP esta implementado, validado en Docker real
y commiteado/pusheado (`2badaab`, `main`, local y remoto identicos). No hay nada bloqueante
pendiente — lo que queda es opcional/de mejora continua.

Pendiente, en orden sugerido:
1. Cargar credenciales reales (`ANTHROPIC_API_KEY` en la consola de developer de Anthropic,
   NO el credito de suscripcion de Claude.ai que es una billetera distinta — ver conversacion
   2026-08-29; `TELEGRAM_BOT_TOKEN`/`CHAT_ID`) en `.env` y reiniciar el servicio para ver el
   diagnostico real de Claude y la notificacion real de Telegram funcionando.
2. Mirar el dashboard de Grafana en el navegador (`http://localhost:3000`) para confirmar
   visualmente lo que ya se valido por API (datasource sano, dashboard provisionado).
3. Reconciliar `spec.md` con el alcance real implementado (Historia 3/email fuera de
   alcance — ver nota abajo, arrastrada desde `/speckit-plan`).
4. Enmienda de `/speckit-constitution` para que el Principio I reconozca la excepcion de
   fase MVP (D9) — sigue pendiente, no bloquea nada.

---

## Pendientes sueltos

- **Implementacion del MVP (2026-08-29):** `/speckit-implement` corrido completo. 37/38
  tareas de `tasks.md` en `[X]`. Codigo en `src/` (ingesta, deteccion, diagnostico,
  notificacion, almacenamiento, main.py), `herramientas/emulador_motor.py` (4 escenarios
  A-D), `docker-compose.yml` (broker+influxdb+servicio+grafana), provisioning de Grafana
  (`grafana/provisioning/`), 31 tests en `tests/` (contract+integration+unit), todos en
  verde. Detalles tecnicos que no estan en `data-model.md`/`contracts/` porque surgieron
  durante la implementacion: (a) las anotaciones de Grafana sobre `Alerta` se arman desde un
  espejo liviano en InfluxDB (measurement `alertas`, escritura best-effort en
  `influx_repo.escribir_evento_alerta`) porque Grafana no trae plugin de SQLite por defecto;
  (b) dentro de `docker-compose.yml`, `servicio` y `grafana` fuerzan `MQTT_HOST`/`INFLUX_URL`
  a los hostnames de la red interna (`broker`/`influxdb`) via `environment:`, que pisa los
  valores de `.env` pensados para desarrollo local fuera de Docker.
- **T037 — infraestructura validada (2026-08-29):** con Docker Desktop levantado, se corrio
  `docker compose up -d --build` (broker+influxdb+servicio+grafana, todos healthy) y el
  emulador (Escenario A) contra el stack real. Confirmado end-to-end: MQTT → deteccion
  (Alerta #1 al cruzar 75C) → SQLite (`Alerta`+`Diagnostico` persistidos, `fallo=1` esperado
  sin `ANTHROPIC_API_KEY` real) → InfluxDB (20 lecturas + evento en measurement `alertas`) →
  Telegram omitido correctamente (sin credenciales) → Grafana (datasource `InfluxDB` health
  OK "3 buckets found", dashboard `motor-001-mvp` provisionado). Bloqueador encontrado y
  resuelto en el camino: un mosquitto nativo de Windows (servicio, ver `memory/risks.md`)
  competia por el puerto 1883 — Joelo lo detuvo (`net stop mosquitto`, admin). **Todavia
  falta probar el diagnostico real de Claude + notificacion Telegram real** (necesita
  `ANTHROPIC_API_KEY`/`TELEGRAM_BOT_TOKEN`/`CHAT_ID` validos en `.env`, que hoy estan vacios
  a proposito) y confirmar visualmente el dashboard en el navegador
  (`http://localhost:3000`).
- **Commit y push (2026-08-29):** Joelo pidio el commit — hecho como `2badaab` en `main` y
  pusheado a `github.com/joelobenitez/aiproject`. Verificado: working tree limpio, local y
  remoto identicos (`git rev-list --left-right --count origin/main...HEAD` → `0 0`).
- **Facturacion de la API de Claude (2026-08-29):** Joelo tiene $90.23 de credito
  promocional (vence 19/9/2026) pero es de su cuenta de Claude.ai, NO de
  `console.anthropic.com` (la consola de developer que factura el `ANTHROPIC_API_KEY` que
  usa `src/config.py`) — son billeteras separadas, confirmado via busqueda web. Desde el
  15/6/2026 Anthropic tiene un "Agent SDK credit" mensual atado a los planes pagos de
  Claude.ai/Code para uso programatico via sus propias herramientas (Agent SDK, `claude -p`,
  GitHub Actions), pero se consume autenticando como suscriptor, no via una API key suelta
  como la que usa este proyecto. Conclusion: para probar el diagnostico real hay que revisar
  el saldo en `console.anthropic.com` y cargar el minimo (~$5) si esta en cero — a esta
  escala de uso (estimado centavos de dolar por diagnostico con Haiku 4.5 + prompt caching)
  alcanza para meses.
- `/speckit-plan` (corrido 2026-08-29) dejo dos items deliberadamente diferidos (confirmado
  por Joelo, no bloqueantes): (1) `spec.md` sigue exigiendo Email/Historia 3 pero la
  implementacion los deja fuera de alcance — falta actualizar `spec.md` para que no diverja
  del codigo; (2) el gate de constitucion marco al Principio I (Separacion de Capas) como
  violado-pero-justificado por D9 — falta una enmienda de aclaracion via
  `/speckit-constitution`.
- Confirmar con Joelo el "por que" completo de D5 (adoptar Spec Kit) — no quedo registrado
  mas alla de "arrancar SDD". Ver nota en `memory/decisions.md` D5.
- Definir manejo de secretos del Claude Agent en PRODUCCION (`ANTHROPIC_API_KEY` y
  credenciales de InfluxDB/MySQL). Joelo confirmo (2026-08-29) que todavia no sabe como
  quiere gestionarlo — D8 ya resuelve la etapa de desarrollo con `.env` local (verificado:
  no esta trackeado en git). Ver `memory/risks.md`.
- Copia WSL2 (`/home/joelo/aiproject`), obsoleta: evaluacion (2026-08-29) confirmo que NO
  interfiere con la estructura de memoria multisesion ni con el codigo actual — accion de
  borrado/resincronizacion pendiente de Joelo, sin apuro.
