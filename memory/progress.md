# Progress — aiproject

> **Ultima actualizacion:** 2026-08-31
> **Donde estamos:** MVP del feature `001-diagnostico-motor-industrial` IMPLEMENTADO,
> VALIDADO EN DOCKER REAL CON PIPELINE COMPLETO END-TO-END: MQTT → deteccion → **Claude
> real** → **Telegram real** → **Grafana con anotaciones reales**, sin fallos. Los 5 items
> pendientes de la sesion 2026-08-29 quedaron todos cerrados el 2026-08-30.
> **2026-08-31 (sesion nueva, terminal distinta — `C:\Users\jbenitez\proyectos\aiproject`,
> mismo repo/commit que la terminal de desarrollo original):** se valido que el repo corre
> igual de bien en una maquina/terminal distinta (Docker Desktop instalado pero apagado, sin
> `.env`, sin deps — todo se resolvio y quedo documentado). Se cargaron credenciales reales
> de Telegram nuevas para esta terminal. Se implemento y valido **D13: diagnostico de IA bajo
> demanda** — la IA ya no diagnostica automatico en severidad `ALERTA` (solo en `CRITICO`);
> para `ALERTA` se manda un mensaje Telegram crudo y el diagnostico se pide via
> `POST /diagnosticar/<alerta_id>` contra un servidor HTTP nuevo embebido en el servicio
> (`src/api.py`, puerto 8000). Validado en vivo contra el stack Docker de esta terminal
> (Alerta #3: mensaje crudo → pedido on-demand → diagnostico + notificacion → pedido
> repetido devuelve cache sin re-llamar a Claude). Se repitio la validacion completa con
> `ANTHROPIC_API_KEY` real (Alerta #4: diagnostico real generado, causa probable + urgencia
> ALTA + accion recomendada coherentes, notificacion Telegram y cache confirmados). 36/36
> tests pytest en verde (31 + 5 nuevos). Ver D13 en `memory/decisions.md` y el riesgo nuevo
> en `memory/risks.md` (endpoint sin autenticacion). **Commiteado y pusheado**: `103d3da` en
> `main` en GitHub. Se genero ademas un prompt detallado para armar el diagrama de
> arquitectura en Claude Design (entregado en el chat de esta sesion, no guardado como
> archivo en el repo). **Pendiente: hacer `git pull` en la terminal de desarrollo original
> (carpeta `joelo`, ver `memory/risks.md`) para traer estos cambios ahi tambien.**
> `/speckit-implement` corrido de punta a punta: 38/38 tareas de `tasks.md` completas (pre-
> D13; D13 es posterior al MVP formal de Spec Kit, no paso por el loop `/speckit-*`).
> Codigo en `src/` + `herramientas/emulador_motor.py` + `docker-compose.yml` +
> provisioning de Grafana. Ultimo commit pusheado a `main` en GitHub antes de esta sesion:
> `b62b60e`. El 2026-08-30 se cargaron $5 reales en `console.anthropic.com`, se probo
> el diagnostico real de Claude (encontramos y arreglamos un bug real de parseo), se
> cargaron credenciales reales de Telegram (Alerta #16, 75.26C, diagnostico real + envio
> real, ambos HTTP 200 OK) y se encontro/arreglo un bug real en las anotaciones del
> dashboard de Grafana. Ademas se reconcilio `spec.md` con el alcance real (D9) y se
> enmendo la constitucion a v1.1.0 (D12). Metodo de memoria multisesion instalado (D6).

---

## Estado por frente

| Frente | Estado |
|---|---|
| Definicion (arquitectura + caso de uso) | CERRADO — D1, D2, D3, D4 resueltas. Ver `memory/decisions.md` |
| Ubicacion de la carpeta de trabajo (Windows vs WSL2) | RESUELTO (D7) — Windows/OneDrive es la fuente de verdad |
| Repo git local (esta carpeta) | CREADO — `git init -b main` + primer commit (35 archivos). Remote `origin` configurado |
| Push a GitHub | HECHO — `2badaab` en `main` en `github.com/joelobenitez/aiproject` (incluye `fe521e6` anterior), local y remoto identicos |
| Spec Kit — constitucion | HECHO — `.specify/memory/constitution.md` v1.0.0, 5 principios basados en D1-D7 |
| Spec Kit — spec del feature | HECHO — jubilado (D14) en `obs/specs/001-diagnostico-motor-industrial/spec.md`, checklist en verde, sin clarificaciones pendientes |
| Spec Kit — plan/tasks | HECHO — `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `tasks.md` (38 tareas) |
| Spec Kit — implement | COMPLETO — 38/38 tareas de `tasks.md`, incluyendo T037 (validacion en Docker real) |
| Stack objetivo del MVP | REDEFINIDO (D9) — broker MQTT + InfluxDB + Grafana + 1 servicio Python (colapsa Node-RED+n8n+Agent), SQLite en vez de MySQL, Email/Web Report postergados |
| Stack objetivo a escala industrial | Roadmap anotado (D11) — vuelve a separar detector/diagnostico, RUT956 real, EMQX cluster, Postgres/MySQL, dimensionamiento de hardware |
| Contratos de datos (MQTT payload, schema InfluxDB, schema DB, contrato interno del servicio Python) | Implementados en `src/` (fuente de verdad viva). Diseno original jubilado (D14) en `obs/specs/001-diagnostico-motor-industrial/contracts/` + `data-model.md` |
| Codigo del MVP (`src/`, `herramientas/emulador_motor.py`) | IMPLEMENTADO Y COMMITEADO — pipeline completo ingesta→deteccion→diagnostico→notificacion→Grafana. Con D13 (2026-08-31, commit `103d3da`): diagnostico automatico solo en CRITICO + endpoint HTTP `/diagnosticar/<id>` para ALERTA. 36 tests pytest en verde |
| Docker Compose real (version MVP simplificada) | VALIDADO — `docker compose up -d --build` corrido con exito (broker+influxdb+servicio+grafana), pipeline probado end-to-end con el emulador real (ver "Pendientes sueltos") |
| Memoria multi-sesion (este metodo) | INSTALADO — 2026-08-29 |

---

## Problemas abiertos

Ninguno bloqueante. Ver "Pendientes sueltos" abajo para lo que falta cerrar.

---

## Proximos pasos

**Foco de la proxima sesion (default):** hacer `git pull` en la terminal de desarrollo
original (carpeta `joelo`) para traer el commit `103d3da` (D13) — no bloqueante, pero hay
que hacerlo antes de seguir trabajando desde esa terminal para no divergir.

**Anotado como trabajo futuro (no urgente, sin fecha):** escalar la infraestructura de
Telegram a **Nivel 1** (ver D2 en `memory/decisions.md` y el "camino natural siguiente" de
D13) — hoy el bot es solo push (Nivel 0) mas el endpoint HTTP de D13 para pedir diagnosticos
desde afuera de Telegram. Subir a Nivel 1 significa agregar el receptor que D2 ya
anticipaba: webhook (necesita tunel en dev local, ej. cloudflared/ngrok) o long-polling +
allowlist de chat_id, para que el propio Telegram pueda disparar
`diagnosticar_bajo_demanda` (por ejemplo con un boton inline, opcion A del analisis de
D13) en vez de depender de un cliente HTTP externo. Es el paso que mas valor agrega si el
modelo bajo-demanda de D13 resulta util en el uso real.

Los items de la lista de la sesion 2026-08-29/30 (distinta) siguen cerrados. Ver "Pendientes
sueltos" para items de fondo sin apuro (WSL2, secretos de produccion, D5, autenticacion del
endpoint `/diagnosticar`).

Historial de esta lista (todos cerrados 2026-08-30):
1. ~~Commitear el fix de `src/diagnostico/parser.py`~~ — HECHO (`545b34a`, pusheado).
2. ~~Cargar `TELEGRAM_BOT_TOKEN`/`CHAT_ID` reales y confirmar notificacion real~~ — HECHO,
   Alerta #16 confirmada por logs (Claude 200 OK + Telegram 200 OK). Joelo no confirmo
   explicitamente haber visto el mensaje en su telefono, pero el HTTP 200 de la API de
   Telegram es evidencia suficiente de entrega.
3. ~~Mirar el dashboard de Grafana~~ — HECHO, bug real encontrado y arreglado (ver
   "Pendientes sueltos": las anotaciones de alerta no se veian), confirmado visualmente
   por Joelo (linea roja en el timestamp exacto de la Alerta #16).
4. ~~Reconciliar `spec.md` con el alcance real implementado~~ — HECHO: nota post-
   implementacion agregada + Historia 3, mitad de Historia 2 (email), FR-007, FR-008 y
   SC-006 marcados "Diferido (D9)" en `spec.md` (ruta actual: `obs/specs/001-diagnostico-motor-industrial/spec.md`, jubilado por D14).
5. ~~Enmienda de `/speckit-constitution`~~ — HECHO: constitucion 1.0.0 -> 1.1.0, Principio I
   ahora reconoce la excepcion de fase MVP de D9. Registrado como D12 en
   `memory/decisions.md`.

---

## Pendientes sueltos

- **Diagnostico real de Claude confirmado + bug de parseo encontrado y arreglado
  (2026-08-30):** con $5 de credito cargados en `console.anthropic.com`, se probo el
  nucleo de diagnostico contra la API real.
  - **Primer obstaculo (resuelto):** la primera API key generada era de tipo
    "identity-linked" — el servidor de Anthropic devolvia 400 pidiendo un header
    `anthropic-workspace-id` que el codigo no manda. Confirmado con curl/httpx directo
    contra `api.anthropic.com`, sin pasar por nuestro codigo ni el SDK, mismo error. Se
    descarto tocar el codigo (a pedido de Joelo) y en cambio se regenero la key
    seleccionando explicitamente un workspace especifico en la consola (no la vista
    "identity-linked"/personal) — la key nueva autentica sin ese header.
  - **Segundo obstaculo (resuelto, bug real en codigo):** con la key nueva autenticando
    bien (200 OK), la mayoria de las llamadas (~75% en las pruebas) fallaban al hacer
    `json.loads()` en `src/diagnostico/parser.py` con `JSONDecodeError: Expecting value:
    line 1 column 1`. Causa confirmada reproduciendo la llamada 3 veces con el mismo
    input: Claude a veces envuelve la respuesta en un bloque de markdown (` ```json ... ```
    `) a pesar de que el system prompt pide "UNICAMENTE un objeto JSON, sin texto
    adicional" — es un comportamiento intermitente del modelo, no controlable solo por
    prompt. Fix aplicado en `src/diagnostico/parser.py` (linea ~62): si el texto empieza
    con ` ``` `, se le saca el fence antes de parsear. 31/31 tests pytest siguen en verde
    despues del fix. Validado end-to-end con el emulador (escenario A) contra el stack
    Docker real: 2 alertas seguidas (#14, #15), diagnostico generado sin fallos en ambas.
  - **Estado del fix:** commiteado y pusheado como `545b34a` (2026-08-30).
  - Nota operativa: cada vez que se reinicia Windows hay que volver a chequear que el
    mosquitto nativo de Windows (servicio) no este compitiendo por el puerto 1883 antes de
    `docker compose up` — ver `memory/risks.md`. Se repitio este bloqueo en esta sesion,
    se resolvio igual que la vez anterior (`net stop mosquitto`, admin).
- **Bug de anotaciones en Grafana encontrado y arreglado (2026-08-30):** al revisar
  visualmente el dashboard `motor-001-mvp`, los graficos de temperatura/corriente/vibracion
  se veian bien pero las anotaciones de alerta (lineas rojas) no aparecian, a pesar de que
  el datasource estaba sano y el measurement `alertas` en InfluxDB tenia los eventos
  esperados (verificado con una query directa a la API de InfluxDB: 15 alertas en las
  ultimas 6h). Causa: el query Flux de la anotacion
  (`grafana/provisioning/dashboards/motor.json`) devolvia `variable` y `severidad` como
  **labels** de un unico campo `_value` (formato "wide", tipico para paneles de series de
  tiempo) en vez de como columnas de tabla — y `textColumn`/`tagsColumn` de la anotacion
  necesitan columnas reales con esos nombres para funcionar. Confirmado reproduciendo el
  query exacto contra `/api/ds/query` de Grafana y comparando la forma del resultado antes
  y despues del fix. **Fix:** agregar `|> group()` al final del query Flux de la anotacion
  — fuerza el formato "long" (tags como columnas reales en vez de labels). Aplicado en
  `grafana/provisioning/dashboards/motor.json`, recargado solo via el poll de provisioning
  (`updateIntervalSeconds: 30`), confirmado por API que la anotacion ya devuelve las
  columnas `variable`/`severidad` esperadas. Pendiente que Joelo confirme visualmente en el
  navegador (refrescar con F5).
- **Notificacion real de Telegram confirmada (2026-08-30):** con `TELEGRAM_BOT_TOKEN` y
  `TELEGRAM_CHAT_ID` reales cargados en `.env` y el servicio reiniciado, se corrio el
  emulador (Escenario A) contra el stack Docker real. Logs de `servicio` confirman la
  Alerta #16 (temperatura=75.26C): llamada a `api.anthropic.com` → `200 OK`, diagnostico
  generado ("degradacion del sistema de refrigeracion o ambiente de operacion mas
  calido"), llamada a `api.telegram.org/.../sendMessage` → `200 OK`. Primera corrida
  completamente real (sin ningun componente degradado/mockeado) del pipeline completo:
  MQTT → deteccion → Claude real → Telegram real. Verificado tambien con una llamada
  `httpx` directa a la API de Telegram (fuera de Docker/nuestro codigo) antes de esta
  prueba, confirmando que el bot y el chat_id eran validos.
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
- **Facturacion de la API de Claude (2026-08-29, RESUELTO 2026-08-30):** Joelo tenia $90.23
  de credito promocional en su cuenta de Claude.ai, distinto de `console.anthropic.com` (la
  consola de developer que factura `ANTHROPIC_API_KEY`) — son billeteras separadas. El
  2026-08-30 Joelo cargo $5 reales en `console.anthropic.com` y se confirmo funcionando (ver
  entrada de diagnostico real arriba). A esta escala de uso (diagnostico con Haiku 4.5 +
  prompt caching) deberia alcanzar para meses.
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
