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

## Riesgos resueltos, decantados en el barrido de stores del 2026-09-02

Tres riesgos que estaban marcados `[RESUELTO]` en `memory/risks.md` (o efectivamente resueltos
sin marcar) se sacaron de ese store para no ocupar lugar en algo que se lee on-demand por
riesgo activo:
- **Duplicacion de carpeta Windows/WSL2** (abierta desde Session 05): resuelta por **D7**
  (2026-08-29) — Windows/OneDrive quedo como fuente de verdad, `git init` + primer commit +
  push a `github.com/joelobenitez/aiproject`. La copia WSL2 (`/home/joelo/aiproject`) quedo
  obsoleta sin resincronizar (accion pendiente de Joelo, sin apuro, ver `progress.md`).
- **`.claude/` sin excluir de git**: quedo anotado como riesgo pendiente en Session 05, pero
  nunca se marco resuelto. Verificado en el barrido de 2026-09-02: `.gitignore` ya excluye
  `.claude/` (primera linea del archivo) desde que se inicializo el repo (D7) — no hay ni
  hubo filtracion.
- **`constitution.md` de Spec Kit vacio**: resuelto el 2026-08-29 (`/speckit-constitution`
  ratifico v1.0.0 con 5 principios basados en D1-D8). La enmienda que quedaba pendiente
  (Principio I reconociendo la excepcion de fase MVP de D9) se cerro despues como **D12**
  (2026-08-30, v1.1.0).

## Sesion 2026-08-29 (tarde) — Implementacion del MVP completa (T001-T038)

`/speckit-implement` corrido de punta a punta: 38/38 tareas de `tasks.md`. Codigo completo en
`src/` (ingesta, deteccion, diagnostico, notificacion, almacenamiento, `main.py`),
`herramientas/emulador_motor.py` (4 escenarios A-D), `docker-compose.yml`
(broker+influxdb+servicio+grafana), provisioning de Grafana, 31 tests
(contract+integration+unit). T037 valido el stack real end-to-end (Docker Desktop,
`docker compose up -d --build`): MQTT -> deteccion -> SQLite -> InfluxDB -> Grafana, con un
bloqueo resuelto en el camino (mosquitto nativo de Windows compitiendo por el puerto 1883, ver
`memory/risks.md`). Commit y push a `github.com/joelobenitez/aiproject` como `2badaab`.
Facturacion de la API de Claude aclarada: los $90.23 de credito en Claude.ai son una billetera
distinta de `console.anthropic.com` (la que factura `ANTHROPIC_API_KEY`) — resuelto al dia
siguiente cargando $5 reales. Cerrada — decantada de `memory/progress.md` en el barrido del
2026-09-02.

## Sesion 2026-08-30 — Validacion real end-to-end + 2 bugs reales arreglados

Con $5 reales cargados en `console.anthropic.com`, se probo el nucleo de diagnostico contra la
API real. **Bug real arreglado** en `src/diagnostico/parser.py` (linea ~62): Claude a veces
envuelve la respuesta en fence de markdown (` ```json `) pese a pedirsele JSON puro — fix:
detectar y sacar el fence antes de `json.loads()`. Commiteado `545b34a`. Con
`TELEGRAM_BOT_TOKEN`/`CHAT_ID` reales, primera corrida 100% real del pipeline completo (MQTT
-> deteccion -> Claude real -> Telegram real, Alerta #16). **Bug real arreglado** en las
anotaciones de Grafana (`grafana/provisioning/dashboards/motor.json`): el query Flux devolvia
`variable`/`severidad` como labels en vez de columnas — fix: agregar `|> group()` para forzar
formato "long". Confirmado visualmente por Joelo (linea roja en el timestamp exacto de la
Alerta #16). Ademas se cerraron los dos items que `/speckit-plan` habia dejado diferidos:
`spec.md` reconciliado con el alcance real (Historia 3/email marcados diferidos por D9) y
`/speckit-constitution` enmendado a v1.1.0 (**D12**). Metodo de memoria multisesion instalado
(**D6**). Cerrada — decantada de `memory/progress.md` en el barrido del 2026-09-02.

## Sesion 2026-08-31 — D13: diagnostico de IA bajo demanda

Implementado y validado **D13** (ver `memory/decisions.md`): diagnostico automatico solo en
CRITICO; servidor HTTP nuevo (`src/api.py`, puerto 8000) para pedirlo bajo demanda en ALERTA
via `POST /diagnosticar/<alerta_id>`, con cache (no vuelve a llamar a Claude si ya existe).
Validado con `ANTHROPIC_API_KEY` real (Alerta #4). 36/36 tests en verde. Commiteado y pusheado
`103d3da`. Cerrada — decantada de `memory/progress.md` en el barrido del 2026-09-02.

## Sesion 2026-09-01 — Organizacion documental + feature 002 completo (D14, D15, D16)

- **D14**: jubilados los artefactos de `specs/001-diagnostico-motor-industrial/` a
  `obs/specs/001-diagnostico-motor-industrial/` (ciclo SDD cerrado, 38/38 tareas). Spec Kit
  (`.specify/`) sigue activo. Commiteado `b17ae3e`.
- **D15/D16**: investigado e implementado el feature `002-grafana-llm-diagnostico` (plugin
  `grafana-llm-app` + panel "Diagnostico IA" en Grafana que muestra el diagnostico que `src/`
  ya genera via D13, sin llamados nuevos a Claude desde Grafana — evita duplicar el "un
  cerebro" del Principio III). 13/13 tareas, incluido un bug real arreglado (el plugin v1.0.8
  trae hardcodeado un modelo Anthropic descontinuado, pisado con `jsonData.models.mapping`).
  39/39 tests en verde. Commiteado `a456901`. Jubilados los artefactos de
  `specs/002-grafana-llm-diagnostico/` a `obs/` (D16), mismo criterio que D14. Commiteado
  `b406366`. Confirmado con Joelo que no se agrega mas superficie de IA en Grafana ("no le
  veo mucho uso al plugin").

Cerrada — decantada de `memory/progress.md` en el barrido del 2026-09-02.

## Sesion 2026-09-01 (terminal `joelo`) — 2 bugs de contenedores Docker viejos + D17

Al arrancar la integracion del RUT956 (D11), Joelo no pudo acceder a `http://192.168.1.1` (sin
diagnosticar la causa especifica, sesion cortada por tiempo). Aparte, dos bugs reales
encontrados y arreglados, mismo patron: contenedores Docker creados antes de un cambio de
codigo/config no se recreaban solos con `docker compose up -d` sin `--build`/
`--force-recreate` (ver riesgo en `memory/risks.md`):
- Grafana no arrancaba (plugin `grafana-llm-app` no registrado, contenedor de antes de D15).
  Fix: `docker compose up -d grafana --force-recreate`.
- El panel "Diagnostico IA" quedaba vacio (contenedor `servicio` con codigo de antes de
  D13/feature 002). Fix: `docker compose up -d --build servicio`.

**D17 (cambio de fondo, misma sesion):** el nucleo cognitivo dejo de diagnosticar (causa
probable/razonamiento/urgencia/accion recomendada/confianza) y paso a devolver un resumen de
hechos puramente factual (`resumen_ejecutivo` + `hechos_destacados`) — decision de Joelo por
confianza/responsabilidad, no delegar juicio de causa/urgencia a la IA en un entorno industrial
real. Tocó `prompt.py`, `parser.py`, `sqlite_repo.py` (schema), `influx_repo.py`, `main.py`,
`telegram.py`, el panel de Grafana y 6 archivos de test. 39/39 tests en verde, validado en vivo
(incluyo borrar y recrear `data/aiproject.db` porque `CREATE TABLE IF NOT EXISTS` no migra
columnas). `CLAUDE.md` actualizado en las 2 menciones que describian el comportamiento viejo.
Commiteado `8d72852`. El doc de estudio
`investigacion/sistema_src_funcionamiento_detallado.md` se actualizo en paralelo para reflejar
D17 (commiteado `fd06a4b`). Ver D17 en `memory/decisions.md` para el detalle completo. Cerrada
— decantada de `memory/progress.md` en el barrido del 2026-09-02.

## Sesion 2026-09-02 (terminal `jbenitez`) — Primer contacto con el RUT956 real + D18

Bloqueador de la sesion anterior resuelto: acceso confirmado a `http://192.168.1.1`. Relevamiento
de solo lectura encontro configuracion previa no documentada en el equipo: un Modbus TCP
Client que se auto-consulta a si mismo (loopback, no sensor real) y un "Data to Server"
publicando a un broker EMQX Cloud externo. Bibliografia oficial de Teltonika (RutOS Web API,
JSON-RPC, Modbus, MQTT, SSH) investigada y guardada como referencia en la memoria del
asistente (no en este repo).

**D18:** el RUT956 se reconfiguro para publicar al Mosquitto local del proyecto en vez del
cloud externo — validado de punta a punta con `mosquitto_sub`, sin bloqueo de firewall. Ver D18
en `memory/decisions.md` (incluye el riesgo de que la IP del broker esta atada a esta PC
especifica, ver `memory/risks.md`).

Escrito `herramientas/simulador_modbus_rtu.py` (esclavo Modbus RTU simulado, listo para cuando
llegue el adaptador USB-RS485 que Joelo todavia no tiene — el frente de hardware real sigue en
pausa, ver `memory/progress.md`). Se fijo `pymodbus[serial]==3.7.4` en `requirements.txt` (la
3.8+ rompe la API clasica, ver riesgo en `memory/risks.md`).

**Bug real encontrado y arreglado:** el panel "Resumen de IA" de Grafana rompia (crash de
frontend, a veces freeze del tab completo) porque el measurement `diagnosticos` en InfluxDB
tenia datos pre-D17 mezclados con el schema nuevo — D17 solo habia migrado SQLite, no InfluxDB.
Limpiados los puntos viejos en esta maquina (`influx delete`); registrado el riesgo para
revisar tambien la terminal `joelo`. De paso se corrigio una referencia residual a
"EMQX/Mosquitto" en `investigacion/sistema_src_funcionamiento_detallado.md` (el broker real
desde D9 es solo Mosquitto).

Commits de la sesion: `2db7cf7` (RUT956/D18/simulador + memoria), `7c76e47` (fix de
terminologia + riesgo de migracion InfluxDB). Cerrada — decantada de `memory/progress.md` en el
barrido del mismo dia, salvo el pendiente real (adaptador RS485) que sigue vivo ahi.

---

## Sesion 2026-09-02 (terminal `jbenitez`) — Implementacion completa de la spec 003 (robustez y seguridad)

Continuacion de la sesion anterior del mismo dia (auditoria + apertura de la spec 003, D19/D20
ya cerrados/decantados). Esta sesion implemento las 37 tareas de codigo/validacion de
`tasks.md` de punta a punta, fase por fase, validando cada una tanto con tests automatizados
como en vivo contra el stack Docker real (nunca solo mocks) — subiendo la suite de 39 a 49
tests en verde.

**Fase 1 (H1+H2, ingesta resiliente y no bloqueante):** el callback MQTT pasa a normalizar y
encolar unicamente; un worker en hilo aparte consume la cola y corre el pipeline completo bajo
un `try/except` de ultimo recurso. `GET /health` suma `ultima_lectura_en`. Validado con
`docker compose stop/start influxdb` en vivo.

**Fase 2 (H3, banda muerta + confirmacion):** `Detector` exige 3 lecturas consecutivas antes
de generar un evento nuevo (primera alerta o escalada — una escalada ya confirmada dispara
inmediato, el contador no se resetea mientras el equipo siga fuera de NORMAL) y una banda
muerta del 5% para volver a NORMAL. Se reescribio `tests/unit/test_detector.py` completo (los
tests viejos asumian alerta inmediata de una lectura, comportamiento ya no vigente).

**Fase 3 (H4, cooldown persistido + skew):** severidad/cooldown del detector se persisten en
SQLite (`detector_estado`) y sobreviven a un reinicio de contenedor (validado con
`docker compose restart servicio` en vivo); un timestamp desfasado >5min ya no silencia el
equipo — se evalua igual usando el reloj del servidor.

**Fase 4 (H7, seguridad):** broker Mosquitto autenticado (`allow_anonymous false` +
password/ACL), `POST /diagnosticar` exige header `X-API-Token` (fail-closed, comparacion en
tiempo constante), puertos `8000`/`8086` atados a `127.0.0.1`, Grafana sin password default.
Validado en vivo: un cliente MQTT real y ajeno a la sesion (aparentemente una herramienta de
inspeccion en la LAN de Joelo) quedo rechazandose en loop, confirmando que la autenticacion
funciona — riesgo anotado para que Joelo la identifique y actualice.

**Fase 5 (H5+H6, reintento + concurrencia):** `crear_diagnostico` paso a `UPSERT`; un
diagnostico con `fallo=1` ya no bloquea el reintento. Un lock global serializa
`diagnosticar_bajo_demanda` — dos pedidos concurrentes de la misma alerta generan una sola
llamada real a Claude (validado en vivo con `curl ... &` x2).

**Dos bugs reales preexistentes encontrados y arreglados en el camino (no anticipados en
`plan.md`), ambos registrados como decisiones D21/D22:**
- **D21:** correr `python src/main.py` directo duplicaba la instancia del modulo `main.py`
  (una bajo `__main__`, otra bajo `src.main` via `api.py`) — cualquier estado en memoria
  (como el `_detector` singleton o `ultima_lectura_en`) quedaba desincronizado del proceso
  real. Fix: `src/__main__.py` nuevo, el servicio arranca con `python -m src`.
- **D22:** el bind-mount de `mosquitto/passwd` desde Windows/Docker Desktop no preservaba el
  permiso 600 que exige mosquitto — el broker moria al arrancar. Fix: `mosquitto/Dockerfile`
  nuevo, el broker pasa de `image:` a `build: ./mosquitto`.

Tambien se movio el fixture `entorno_aislado` de `tests/integration/conftest.py` a
`tests/conftest.py` (raiz) para que `tests/unit/test_detector.py` pudiera compartirlo — de
paso corrigio un problema de aislamiento preexistente (el `Detector`/`_detector` de
`src/main.py` era, sin querer, un singleton compartido entre TODOS los tests de la sesion de
pytest).

**Hallazgo positivo:** `data/aiproject.db` no necesito borrarse pese a que D20/FR-016 lo
aceptaba como valido — `inicializar_schema()` sumo la tabla `detector_estado` nueva a la DB
existente sin tocar alertas/diagnosticos previos.

Commits de la sesion: `49c2eee`..`2ce05bc` (11 commits: uno de codigo por fase + su
actualizacion de `progress.md`, mas el commit final de Polish). Ver `memory/decisions.md`
D21/D22 y `specs/003-robustez-seguridad/tasks.md` para el detalle completo tarea por tarea.
Cerrada — decantada de `memory/progress.md` en este barrido; quedan vivos ahi solo los dos
pendientes manuales genuinos (T024 rotar `ANTHROPIC_API_KEY`, T025 credenciales MQTT nuevas en
el RUT956).
