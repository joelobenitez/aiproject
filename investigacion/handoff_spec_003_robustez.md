# Handoff — entrada para la spec 003 (robustez + seguridad del servicio)

> **Que es esto:** el insumo completo para arrancar el ciclo Spec Kit del feature
> `003`, escrito para que una sesion nueva (con la estructura de memoria del proyecto
> cargada) pueda correr el equivalente de `/speckit-specify` sin volver a auditar el codigo.
> **No es** la spec. Es la evidencia + el alcance ya decidido + las restricciones + las
> preguntas que la spec tiene que cerrar.
>
> **Origen:** auditoria de arquitectura del 2026-09-02 sobre el codigo real de `src/`
> (commit `7c76e47`), no sobre la documentacion. Cada hallazgo se verifico leyendo el
> archivo citado; los que dependen del comportamiento de una libreria se verificaron contra
> el codigo de la libreria instalada en `.venv/`, no contra su documentacion.
>
> **Idioma:** espanol sin tildes (Principio V de la constitucion).

---

## 0. Como usar este documento

1. Leer `memory/progress.md` y `memory/risks.md` primero, como siempre.
2. Leer este documento entero (secciones 1 a 7).
3. Correr el equivalente de `/speckit-specify` con el prompt de la seccion 9.
4. Registrar el alcance de la seccion 3 como decision nueva (**D19** sugerido) en
   `memory/decisions.md`, en formato append-only, antes o junto con la spec.

**Nota operativa:** en la terminal `jbenitez` los comandos `/speckit-*` no estan instalados
(`.claude/` esta en `.gitignore` y `specify init` se cuelga — ver `memory/risks.md`). El
rodeo ya usado en el feature 002 es escribir `spec.md`/`plan.md`/`research.md`/`tasks.md` a
mano desde `.specify/templates/`, opcionalmente scaffoldeando la carpeta con
`.specify/scripts/powershell/create-new-feature.ps1` (100% local, no baja nada de red).
Ojo: `.specify/feature.json` todavia apunta a `specs\002-grafana-llm-diagnostico`, que ya
fue jubilada a `obs/` por D16 — hay que actualizarlo. La carpeta `specs/` hoy no existe.

---

## 1. Decisiones ya tomadas por Joelo (no re-litigar)

| # | Decision | Detalle |
|---|---|---|
| 1 | La 003 cubre **robustez + seguridad** | Los hallazgos H1 a H7 de la seccion 2. Los menores (M1-M5) entran como Polish, no como historia propia |
| 2 | El estado del detector **se persiste** | El cooldown sobrevive a reinicios del contenedor, y se valida el skew del reloj del sensor. No se difiere a una 004 |
| 3 | Esta sesion **no implementa nada** | El entregable de la sesion de auditoria es este documento. El ciclo SDD y el codigo se hacen en la sesion con estructura de memoria |

---

## 2. Hallazgos (evidencia verificada)

Resumen. El detalle de cada uno esta abajo.

| ID | Hallazgo | Impacto | Evidencia |
|---|---|---|---|
| H1 | El hilo de ingesta muere en silencio ante cualquier excepcion | CRITICO | `src/main.py:137`, `paho/mqtt/client.py:877` |
| H2 | Todo el pipeline corre adentro del callback MQTT (bloqueante) | ALTO | `src/main.py:132-155`, `src/ingesta/mqtt_client.py:18` |
| H3 | Deteccion sin banda muerta ni retardo de activacion | ALTO | `src/deteccion/detector.py:44,69` |
| H4 | Cooldown solo en RAM y con el reloj del sensor | ALTO | `src/deteccion/detector.py:48`, `src/main.py:37,153` |
| H5 | Un resumen fallido queda cacheado para siempre | MEDIO | `src/main.py:60,83-86` |
| H6 | Race en el endpoint bajo demanda | MEDIO | `src/api.py:29-36`, `src/main.py:83` |
| H7 | Superficie de seguridad mas ancha de lo documentado | ALTO | `mosquitto/mosquitto.conf`, `docker-compose.yml`, `src/main.py:171` |

---

### H1 — El hilo de ingesta muere en silencio ante cualquier excepcion

**Sintoma:** el servicio queda "Up", `GET /health` sigue devolviendo `{"status":"ok"}`, y no
se ingesta ni una lectura mas. Sin ningun error visible en el estado del contenedor.

**Evidencia:**
- `src/main.py:137` — `_al_recibir_mensaje` llama a `influx_repo.escribir_lectura(...)` sin
  `try/except`. Es la unica escritura a InfluxDB del sistema que **no** es best-effort: los
  espejos de alerta y de resumen si estan envueltos (`influx_repo.py:41`, `:65`).
- `.venv/Lib/site-packages/paho/mqtt/client.py:877` — `self.suppress_exceptions = False` es
  el valor por defecto.
- `.venv/.../client.py:4467` (`_handle_on_message`) — captura la excepcion del callback,
  la loguea por el canal de log interno de paho y, si `suppress_exceptions` es False,
  **la vuelve a lanzar** (`raise`).
- `.venv/.../client.py:4521` (`_thread_main`) — el thread que arranca `loop_start()` corre
  `loop_forever()` dentro de un `try/finally` **sin `except`**: la excepcion se propaga y el
  thread termina.
- `src/main.py:171-175` — el thread principal se queda en `servidor.serve_forever()`, asi
  que el proceso sigue vivo y sano a los ojos de Docker.

**Por que importa:** cualquier hipo de InfluxDB, un `database is locked` de SQLite (ver M2),
o un payload que rompa de una forma no contemplada, apaga la ingesta de forma permanente y
silenciosa. Es exactamente el patron de fallo que ya aparece tres veces en
`memory/risks.md` (contenedores viejos, panel vacio de Grafana, IP del RUT956): el sistema
dice que esta sano mientras dejo de mirar el motor.

**Como confirmarlo en vivo:** levantar el stack, `docker compose stop influxdb`, publicar
una lectura con el emulador, y ver que despues de eso ninguna lectura mas llega — ni
siquiera con InfluxDB de vuelta arriba — hasta reiniciar `servicio`.

---

### H2 — Todo el pipeline corre adentro del callback MQTT

**Sintoma:** durante una alerta CRITICO, el cliente MQTT deja de leer la red por decenas de
segundos.

**Evidencia:** `src/main.py:132-155` (`_al_recibir_mensaje`) encadena, en el hilo de red de
paho: escritura sincrona a InfluxDB (`SYNCHRONOUS`), varias aperturas de SQLite, y para
severidad CRITICO todo `_diagnosticar_y_notificar` — que incluye la llamada a la API de
Claude (`timeout=10.0` en `src/diagnostico/parser.py:18`) y el envio a Telegram (hasta 3
intentos con backoff 1s+2s, `src/notificacion/telegram.py:17-18,72`). Peor caso conocido: mas
de 25 segundos con el hilo de red bloqueado.

Ademas `src/ingesta/mqtt_client.py:18` hace `client.subscribe(topico)` sin `qos`, o sea
**QoS 0**: lo que el broker publique mientras el cliente no lee no tiene garantia de
entrega, y no hay cola propia que amortigue.

**Por que importa:** a 1 lectura por segundo del emulador el sintoma es leve; con un
RUT956 real publicando varias variables y periodos cortos (D18), o con el cliente
bloqueado mas que el keepalive, se pierden lecturas justo en el momento en que el motor
esta en alerta. Es el momento en que menos se quiere perder datos.

**Direccion sugerida (no vinculante para la spec):** una `queue.Queue` y un worker
dedicado; el callback solo normaliza y encola. Es tambien el primer escalon concreto hacia
la separacion detector/workers que D11 ya preve para la escala industrial.

---

### H3 — Deteccion sin banda muerta ni retardo de activacion

**Evidencia:** `src/deteccion/detector.py:69` (`_clasificar`) compara `valor >= umbral`,
sin banda muerta; `detector.py:44` resetea el estado a NORMAL con **una sola** lectura por
debajo del umbral de alerta.

**Por que importa:** dos consecuencias distintas.
1. Una unica muestra ruidosa que cruce el umbral critico dispara `CRITICO` y con el una
   llamada paga a la API. El emulador ya superpone ruido aleatorio
   (`herramientas/emulador_motor.py`), y un sensor real via RS485 va a tener mas.
2. Un valor que oscile alrededor del umbral vuelve a NORMAL y vuelve a cruzar, generando un
   evento nuevo cada vez que expira el cooldown de 15 minutos, indefinidamente.

**Fundamento externo:** ANSI/ISA-18.2 (equivalente IEC 62682) trata esto de frente: una
banda muerta en cero es senalada como causa directa de comportamiento "chattering", y el
estandar da guia no obligatoria sobre el uso correcto de deadband y de tiempos de retardo;
"chattering and fleeting alarms" y los "alarm floods" son analisis recomendados en la etapa
de monitoreo del ciclo de vida de alarmas. El cooldown que hay hoy es una mitigacion
parcial de la tasa de alarmas, no una banda muerta ni un retardo de activacion.

---

### H4 — Cooldown solo en RAM y con el reloj del sensor

**Evidencia:** `Detector._estado` es un diccionario en memoria del proceso
(`detector.py:31`), y no hay ninguna persistencia. `docker-compose.yml` no declara
`restart:` en ningun servicio. El cooldown se compara contra el timestamp que viene en el
payload MQTT (`src/main.py:37` y `:153`), no contra el reloj del servidor, y no hay ninguna
validacion de cuan lejos esta ese timestamp del ahora real (`src/ingesta/normalizador.py`
solo verifica que sea ISO 8601 parseable).

**Por que importa:**
1. Un reinicio del contenedor (deploy, `--build`, caida) borra los cooldowns: la proxima
   lectura de cada variable que siga arriba del umbral genera un evento nuevo. Si varias
   variables estan en alerta, es una tormenta de notificaciones apenas vuelve el servicio.
2. Un gateway con el reloj adelantado (escenario real: el RUT956 sin NTP, o un sensor con
   RTC desfasado) fija un `cooldown_hasta` en el futuro lejano y **silencia** ese
   equipo+variable hasta que el tiempo real lo alcance. Sin ningun error visible: otra vez
   el patron de H1.

**Decision ya tomada:** entra en el alcance de la 003 (persistir + validar skew).

---

### H5 — Un resumen fallido queda cacheado para siempre

**Evidencia:** `src/main.py:60` persiste el registro tambien cuando `fallo` es True, y
`src/main.py:83-86` (`diagnosticar_bajo_demanda`) devuelve **cualquier** registro existente
marcandolo `cacheado: true`, sin distinguir exito de fallo.

**Por que importa:** un timeout de 10 segundos o un 429 transitorio deja esa alerta sin
resumen de forma permanente. Los `POST /diagnosticar/<id>` siguientes devuelven el fallo
cacheado sin reintentar nunca. La unica salida hoy es tocar la base a mano. Justo lo
contrario de lo que D13 buscaba: que el operador pueda pedir el resumen cuando lo necesite.

---

### H6 — Race en el endpoint bajo demanda

**Evidencia:** `src/api.py:50` usa `ThreadingHTTPServer` (un hilo por request) y
`diagnosticar_bajo_demanda` no toma ningun lock por `alerta_id`. Dos POST simultaneos para
la misma alerta pasan los dos por el chequeo de cache de `main.py:83` antes de que
cualquiera escriba.

**Consecuencia:** dos llamadas pagas a la API por el mismo resumen, y un `IntegrityError`
por la restriccion `UNIQUE` de `diagnostico.alerta_id` en el segundo INSERT — excepcion que
nadie captura ni en `do_POST` ni en `_diagnosticar_y_notificar`, asi que el cliente recibe
un error crudo del `BaseHTTPRequestHandler`.

---

### H7 — Superficie de seguridad mas ancha de lo documentado

`memory/risks.md` documenta la falta de autenticacion del endpoint `/diagnosticar/<id>`.
Es correcto, pero es una parte del cuadro:

| Punto | Evidencia | Estado en risks.md |
|---|---|---|
| Broker MQTT anonimo y sin TLS | `mosquitto/mosquitto.conf`: `allow_anonymous true`, listener 1883 plano | No documentado |
| Endpoint sin auth escuchando en todas las interfaces | `src/main.py:171` (`crear_servidor("0.0.0.0", ...)`) | Documentado (parcial: dice el puerto, no el bind) |
| Cuatro puertos publicados al host | `docker-compose.yml:6,16,43,53` — 1883, 8086, 8000, 3000 | No documentado |
| Grafana con password por defecto | `docker-compose.yml:57` — `${GRAFANA_ADMIN_PASSWORD:-admin}` | No documentado |
| Lecturas escritas antes de validar el equipo | `src/main.py:137` escribe a InfluxDB; recien `:143-145` verifica que el equipo exista | No documentado |

**Cadena de ataque concreta, sin credenciales, desde la misma LAN:** publicar al broker
anonimo lecturas con `equipo_id` arbitrario (se escriben en InfluxDB igual, y cada valor
nuevo de tag infla la cardinalidad de la serie) o con el `equipo_id` real y valores por
encima del umbral critico, lo que genera alertas y dispara llamadas pagas a la API de
Claude; en paralelo, golpear `POST /diagnosticar/<id>` para forzar mas llamadas. El costo lo
paga la cuenta de Joelo.

**Nota:** sigue pendiente de sesiones anteriores rotar `ANTHROPIC_API_KEY`, que quedo
expuesta en el transcript de una sesion el 2026-09-01 (ver `memory/progress.md`). Conviene
cerrarlo dentro de esta 003 y no como un pendiente suelto mas.

**Marco de referencia:** IEC 62443 (zonas y conductos) y NIST SP 800-82r3 (guia de
seguridad para OT) coinciden en que un servicio de este tipo no se expone en la misma red
que la planta sin autenticacion ni segmentacion. Mientras el stack viva en una red de
laboratorio aislada el riesgo es acotado; el problema aparece el dia que el RUT956 y la PC
del stack compartan la red de planta, que es exactamente hacia donde va D18.

---

### Menores (Polish, no historia propia)

| ID | Detalle | Archivo |
|---|---|---|
| M1 | Se crea un `write_api` nuevo en cada escritura, en vez de reutilizarlo o batchear | `influx_repo.py:33,50,75` |
| M2 | SQLite sin WAL ni `timeout`, con acceso desde el hilo MQTT y los hilos HTTP a la vez: candidato natural a `database is locked`, que por H1 mata la ingesta | `sqlite_repo.py:66-74` |
| M3 | La query Flux se arma por f-string con valores que llegan del topico MQTT | `influx_repo.py:83` |
| M4 | El contenedor corre como root, sin usuario sin privilegios ni `HEALTHCHECK` | `Dockerfile` |
| M5 | Ningun servicio declara `restart:`, asi que nada se levanta solo despues de una caida | `docker-compose.yml` |

---

## 3. Alcance de la 003

**Dentro:**

- H1 a H7 completos.
- M1 a M5 como tareas de Polish al final, no como historia independiente.
- Rotacion de `ANTHROPIC_API_KEY` (pendiente arrastrado, encaja en H7).

**Fuera (explicito, para que la spec lo diga y nadie lo re-abra):**

- Separar detector y workers en procesos distintos: eso es D11, escala industrial. La 003
  se queda dentro del proceso unico de D9.
- Telegram Nivel 1 o superior (D2): sigue siendo trabajo futuro.
- Integracion real del RUT956 por RS485 (en pausa hasta que llegue el adaptador USB-RS485).
- Reemplazar SQLite por Postgres/MySQL.
- Deteccion de anomalias por ML.

---

## 4. Restricciones que la spec MUST respetar

**Constitucion (`.specify/memory/constitution.md` v1.1.0):**

- **Principio I** — el MVP corre bajo la excepcion de fase de D9 (un solo proceso). Meter
  una cola interna y un worker **no** vuelve a separar capas ni rompe la excepcion, pero el
  Constitution Check del plan tiene que decirlo explicitamente en vez de dejarlo implicito.
- **Principio II** — la deteccion tiene que seguir siendo barata: banda muerta, retardo y
  estado del cooldown se resuelven con lo que ya esta en memoria o cacheado. Si el estado se
  persiste en SQLite, la lectura tiene que ser en el arranque (o cacheada), no una consulta
  por cada lectura MQTT.
- **Principio IV** — cualquier cambio de canal de entrada se clasifica por nivel, y el
  manejo de secretos se decide y documenta **antes** de tocar `docker-compose.yml`. Esto
  choca de frente con la pregunta abierta 7: la decision de secretos de produccion sigue sin
  tomarse desde D8. La spec tiene que resolverla o acotar explicitamente su perimetro.
- **Principio V** — todo en espanol sin tildes; la decision de alcance va como entrada nueva
  append-only en `memory/decisions.md` (D19 sugerido).

**Contratos que NO se rompen:**

| Contrato | Por que |
|---|---|
| Topico MQTT de 5 partes y payload `{valor, unidad, timestamp}` | El RUT956 ya publica contra este broker (D18); cambiar el contrato mueve trabajo ya hecho |
| Ruta `POST /diagnosticar/<alerta_id>` | D13; es la unica interfaz de accion que existe |
| Nombres de tabla y measurement `diagnostico` / `diagnosticos` | D17 decidio explicitamente no renombrar el plumbing para minimizar superficie de cambio |
| Formato del mensaje de Telegram post-D17 | `resumen_ejecutivo` + `hechos_destacados`, sin causa, urgencia ni accion recomendada |

**Riesgos operativos vigentes (`memory/risks.md`) que afectan la validacion:**

- Despues de cualquier cambio de codigo hay que correr `docker compose up -d --build`. Un
  `up -d` simple deja corriendo la imagen vieja sin ningun error visible.
- El mosquitto nativo de Windows compite por el puerto 1883; verificar antes de probar.
- Un cambio de schema hay que migrarlo en los **dos** lados (SQLite e InfluxDB). Datos
  viejos mezclados con el schema nuevo rompieron paneles de Grafana el 2026-09-02.
- Hay antecedente de tests de integracion escribiendo a la InfluxDB real: cualquier test
  nuevo que toque el camino de escritura tiene que mockearlo igual que los existentes.
- La suite queda en 39/39 en verde como piso; las historias nuevas suman tests propios.

---

## 5. Historias de usuario sugeridas (insumo, no la spec final)

Cada una es independientemente implementable y testeable. El orden es la prioridad
sugerida; la spec puede reordenarlas con justificacion.

**US1 (P1) — El servicio nunca deja de mirar el motor en silencio.** Cubre H1 y M2. Ante
una excepcion en el camino de una lectura, el sistema loguea, descarta esa lectura y sigue
ingiriendo. El estado de salud que expone el servicio refleja si la ingesta esta viva, no
solo si el proceso responde. *Test independiente:* con InfluxDB detenido, publicar lecturas,
volver a levantar InfluxDB y confirmar que la ingesta y la deteccion siguieron funcionando
sin reiniciar el servicio.

**US2 (P1) — Una alerta lenta no hace perder lecturas.** Cubre H2. El trabajo pesado
(persistencia, llamada al nucleo de IA, notificacion) sale del camino de recepcion de
mensajes. *Test independiente:* forzar una llamada de IA lenta y verificar que las lecturas
publicadas durante esa ventana igual quedan registradas y evaluadas.

**US3 (P2) — El ruido del sensor no genera alertas ni gasto.** Cubre H3. Banda muerta para
volver a normal y confirmacion por lecturas consecutivas antes de anunciar. *Test
independiente:* escenario D (operacion normal con ruido) no genera ninguna alerta; una
muestra aislada por encima del umbral critico tampoco.

**US4 (P2) — El silencio de una alerta sobrevive al reinicio y no depende del reloj del
sensor.** Cubre H4. *Test independiente:* con una variable en alerta, reiniciar el servicio
y confirmar que no se genera un evento nuevo mientras el cooldown original siga vigente;
publicar una lectura con timestamp muy adelantado y confirmar que no silencia el equipo.

**US5 (P2) — Nadie sin credenciales puede inyectar datos ni gastar la API.** Cubre H7.
*Test independiente:* publicar al broker sin credenciales falla; llamar al endpoint sin
token falla; ninguna de las dos cosas genera una llamada a la API de Claude.

**US6 (P3) — Un resumen que fallo se puede volver a pedir.** Cubre H5 y H6. *Test
independiente:* forzar un fallo del nucleo de IA, pedir el resumen de nuevo y obtenerlo;
dos pedidos simultaneos de la misma alerta generan una sola llamada y ninguna excepcion.

---

## 6. Criterios de exito sugeridos (medibles)

- **SC-001:** con InfluxDB caido durante 5 minutos, el servicio sigue detectando y
  notificando alertas, y reanuda la escritura al volver, sin intervencion manual.
- **SC-002:** ninguna lectura publicada durante una llamada al nucleo de IA de 10 segundos
  se pierde del camino de deteccion.
- **SC-003:** el escenario D (operacion normal con ruido) genera 0 alertas en 3 corridas
  consecutivas; el escenario A genera exactamente 1 alerta por cruce sostenido.
- **SC-004:** reiniciar el servicio con una variable en alerta no genera ningun evento
  nuevo mientras el cooldown original siga vigente.
- **SC-005:** una alerta cuyo resumen fallo obtiene un resumen exitoso en un pedido
  posterior, sin tocar la base a mano.
- **SC-006:** un cliente sin credenciales no logra escribir en el broker, ni disparar el
  endpoint, ni provocar ninguna llamada facturable a la API.
- **SC-007:** la suite de tests queda en verde, incluyendo tests nuevos por cada historia.

---

## 7. Preguntas abiertas (candidatas a NEEDS CLARIFICATION)

1. **Banda muerta y retardo:** valor de la banda (absoluto en unidades de cada variable, o
   porcentaje del umbral) y cantidad de lecturas consecutivas para confirmar. Por variable
   en la tabla `umbral`, o global por variable de entorno.
2. **Skew del reloj del sensor:** ventana aceptable, y que hacer al excederla — descartar la
   lectura, o aceptarla usando el reloj del servidor y loguear.
3. **Autenticacion del endpoint:** token compartido en un header, allowlist de IP, o
   simplemente dejar de publicar el puerto al host. Definir tambien si `/health` queda
   abierto.
4. **Credenciales del broker:** usuario/password por cliente mas ACL por topico, y si TLS
   entra ahora o despues. Impacta directamente la configuracion "Data to Server" del RUT956,
   que hoy publica en claro (D18).
5. **Puertos publicados al host:** dejar de publicarlos rompe el flujo de trabajo actual
   (emulador desde el host, curl al endpoint, Grafana en `localhost:3000`). Decidir cuales
   se cierran y cuales se atan a `127.0.0.1`.
6. **Politica de reintento del resumen fallido:** sobrescribir el registro fallido, o
   guardar historial de intentos (rompe la relacion 1:1 con `alerta_id UNIQUE`). Definir si
   hay tope de reintentos para acotar el gasto.
7. **Secretos de produccion:** D8 solo resolvio la etapa de desarrollo y el Principio IV
   exige la decision antes de tocar `docker-compose.yml`. Decidir si la 003 la toma o si
   acota su alcance al perimetro de desarrollo de forma explicita.
8. **Migracion del schema:** persistir el cooldown cambia SQLite, y `CREATE TABLE IF NOT
   EXISTS` no migra. Definir si se acepta borrar y recrear `data/aiproject.db` como se hizo
   en D17, o si hace falta una migracion real que preserve el historial de alertas.
9. **Constitucion:** confirmar que la cola interna cae dentro de la excepcion de fase de D9
   y no necesita enmienda, o si el Principio I merece una aclaracion nueva.

---

## 8. Fuentes verificadas de la auditoria

- ANSI/ISA-18.2 (IEC 62682), via el white paper de ISA "Understanding and Applying the
  ANSI/ISA-18.2 Alarm Management Standard": banda muerta en cero como causa de chattering,
  guia sobre deadband y tiempos de retardo, chattering/fleeting alarms y alarm floods como
  analisis recomendados de monitoreo.
  https://www.isa.org/getmedia/55b4210e-6cb2-4de4-89f8-2b5b6b46d954/PAS-Understanding-ISA-18-2.pdf
- NIST SP 800-82r3, Guide to Operational Technology (OT) Security.
  https://csrc.nist.gov/pubs/sp/800/82/r3/ipd
- Comportamiento de paho-mqtt: verificado leyendo el codigo instalado en
  `.venv/Lib/site-packages/paho/mqtt/client.py` (lineas 877, 4467, 4521), no la
  documentacion — la doc oficial no cubre que pasa con una excepcion no suprimida en
  `on_message`.

---

## 9. Prompt de arranque para la sesion nueva

Para pegar como argumento del equivalente de `/speckit-specify`:

```
Feature 003: robustez y seguridad del servicio de deteccion.

Leer primero investigacion/handoff_spec_003_robustez.md — tiene la auditoria completa
del codigo de src/ con evidencia por archivo y linea, el alcance ya decidido por Joelo,
las restricciones de la constitucion y de los contratos que no se rompen, las historias
de usuario sugeridas con su criterio de test independiente, los criterios de exito y las
9 preguntas abiertas que esta spec tiene que cerrar.

Alcance: los hallazgos H1 a H7 de ese documento (el hilo de ingesta que muere en
silencio, el pipeline bloqueante dentro del callback MQTT, la falta de banda muerta y
retardo en la deteccion, el estado del detector en RAM y atado al reloj del sensor, el
resumen fallido cacheado para siempre, el race del endpoint bajo demanda, y la
superficie de seguridad del broker anonimo mas los puertos publicados). Los menores M1
a M5 van como Polish. Queda fuera todo lo que sea D11 (separar detector y workers en
procesos), Telegram Nivel 1+, la integracion RS485 del RUT956 y cambiar de base de datos.

El estado del detector se persiste (decision de Joelo), junto con validacion del skew
del reloj del sensor.
```
