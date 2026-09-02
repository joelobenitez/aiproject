# Feature Specification: Robustez y seguridad del servicio de deteccion

**Feature Branch**: `003-robustez-seguridad`

**Created**: 2026-09-02

**Status**: Draft

**Input**: User description: "Robustez y seguridad del servicio de deteccion: ingesta que no
muere en silencio, pipeline no bloqueante, deteccion con banda muerta, cooldown persistente,
y superficie de seguridad (broker, endpoint, puertos)."

**Contexto previo:** auditoria de arquitectura del 2026-09-02 sobre el codigo real de `src/`
(commit `7c76e47`), documentada completa en `investigacion/handoff_spec_003_robustez.md` — 7
hallazgos (H1-H7) verificados linea por linea (incluido el comportamiento real de la libreria
`paho-mqtt` instalada, no su documentacion), 5 menores (M1-M5) para Polish, y 6 historias de
usuario sugeridas con su test independiente. Alcance ya decidido por Joelo (ver "Fuera de
alcance" y D19 en `memory/decisions.md`): cubre H1-H7 completos, el estado del detector se
persiste (no se difiere a una 004), y la sesion de auditoria no implemento nada — el codigo se
hace en el ciclo SDD que abre este documento.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El servicio nunca deja de mirar el motor en silencio (Priority: P1)

Como responsable de operar el sistema, quiero que una falla transitoria de InfluxDB (o
cualquier excepcion en el camino de una lectura) no apague la ingesta de forma permanente y
silenciosa, para no perder visibilidad del motor sin ningun error visible.

**Why this priority**: es el hallazgo mas critico (H1) — el sistema hoy queda "Up" y
`/health` sigue respondiendo `ok` mientras dejo de escuchar el broker. Sin esto, todo el
resto de robustez es sobre un pipeline que puede estar muerto sin que nadie lo sepa.

**Independent Test**: con el stack levantado, `docker compose stop influxdb`, publicar una
lectura con el emulador, volver a levantar InfluxDB, y confirmar que las lecturas siguientes
se ingestan y evaluan sin reiniciar `servicio`.

**Acceptance Scenarios**:

1. **Given** el servicio corriendo y conectado a MQTT, **When** una escritura a InfluxDB
   falla (excepcion de red, timeout, servicio caido), **Then** el sistema loguea el error,
   descarta esa lectura puntual, y sigue procesando las lecturas siguientes.
2. **Given** que InfluxDB estuvo caido durante N lecturas, **When** vuelve a estar
   disponible, **Then** las lecturas nuevas se escriben normalmente sin intervencion manual
   ni reinicio del servicio.
3. **Given** el hilo/loop de ingesta MQTT, **When** ocurre cualquier excepcion no
   contemplada dentro del callback de mensaje, **Then** el proceso NO termina el hilo de
   ingesta — la suscripcion sigue viva.

---

### User Story 2 - Una alerta lenta no hace perder lecturas (Priority: P1)

Como responsable de operar el sistema, quiero que una llamada lenta a la API de Claude (o a
Telegram) no bloquee la recepcion de nuevas lecturas MQTT, para no perder datos justo en el
momento en que el motor esta en alerta.

**Why this priority**: hallazgo H2 — hoy todo el pipeline (persistencia, IA, notificacion)
corre dentro del callback de red de MQTT; el peor caso conocido bloquea el cliente MQTT mas
de 25 segundos, con la suscripcion en QoS 0 (sin garantia de entrega mientras no se lee la
red).

**Independent Test**: forzar una llamada de IA lenta (timeout o mock con delay) y verificar
que las lecturas MQTT publicadas durante esa ventana quedan igual registradas y evaluadas
por el detector.

**Acceptance Scenarios**:

1. **Given** una alerta CRITICO en curso disparando el camino de diagnostico/notificacion,
   **When** llegan lecturas MQTT nuevas de otras variables durante ese lapso, **Then** esas
   lecturas se ingestan y evaluan sin esperar a que termine el diagnostico en curso.
2. **Given** el diseno resultante, **When** se revisa contra el Principio I de la
   constitucion (excepcion de fase MVP, D9), **Then** el mecanismo elegido (ej. cola +
   worker interno al mismo proceso) se declara explicitamente en el Constitution Check de
   `plan.md` como compatible con la excepcion existente, sin reabrir la separacion de capas
   de D11.

---

### User Story 3 - El ruido del sensor no genera alertas ni gasto de mas (Priority: P2)

Como responsable de operar el sistema, quiero que una unica lectura ruidosa no dispare una
alerta CRITICO (con su llamada paga a la API), ni que un valor oscilando justo en el umbral
genere una alerta nueva cada vez que expira el cooldown, para que las alertas reflejen una
condicion real y sostenida del motor.

**Why this priority**: hallazgo H3. El emulador ya superpone ruido aleatorio; un sensor real
por RS485 (D11/D18) va a tener mas. Sin banda muerta ni confirmacion por lecturas
consecutivas, el sistema es propenso a "chattering" (ANSI/ISA-18.2).

**Independent Test**: el escenario D del emulador (operacion normal con ruido) no genera
ninguna alerta en varias corridas; una muestra aislada por encima del umbral critico
tampoco dispara CRITICO por si sola.

**Acceptance Scenarios**:

1. **Given** una lectura que cruza el umbral de ALERTA/CRITICO por una unica muestra
   ruidosa, **When** la lectura siguiente vuelve a estar por debajo del umbral, **Then** el
   sistema NO genera un evento de alerta.
2. **Given** un valor que efectivamente se sostiene arriba del umbral, **When** se confirma
   por la cantidad de lecturas consecutivas configurada, **Then** el sistema genera el
   evento de alerta.
3. **Given** una alerta activa, **When** el valor baja pero se mantiene dentro de la banda
   muerta alrededor del umbral, **Then** el sistema NO vuelve a NORMAL todavia (evita
   reactivar-desactivar en cada lectura).

---

### User Story 4 - El silencio de una alerta sobrevive al reinicio y no depende del reloj del sensor (Priority: P2)

Como responsable de operar el sistema, quiero que el cooldown de una alerta no se pierda si
el servicio se reinicia (deploy, `--build`, caida), y que un reloj desfasado en el
gateway/sensor no silencie una variable indefinidamente, para no sufrir tormentas de
notificaciones ni alertas mudas sin ningun error visible.

**Why this priority**: hallazgo H4. Es la decision de alcance explicita de Joelo (no se
difiere a una 004): el estado del detector se persiste, y se valida el skew del timestamp
del sensor contra el reloj del servidor.

**Independent Test**: con una variable en alerta, reiniciar el servicio y confirmar que no
se genera un evento nuevo mientras el cooldown original siga vigente; publicar una lectura
con timestamp muy adelantado respecto del reloj real y confirmar que no silencia el equipo
indefinidamente.

**Acceptance Scenarios**:

1. **Given** una variable en cooldown activo, **When** el proceso del servicio se reinicia,
   **Then** al volver a arrancar el cooldown sigue vigente hasta su vencimiento original —
   no se genera un evento nuevo para esa variable en ese lapso.
2. **Given** una lectura cuyo timestamp esta fuera de una ventana aceptable respecto del
   reloj del servidor, **When** el sistema la recibe, **Then** aplica la politica definida
   [NEEDS CLARIFICATION: descartar la lectura, o aceptarla usando el reloj del servidor en
   vez del timestamp del payload — pregunta 2 de `investigacion/handoff_spec_003_robustez.md`]
   y lo deja registrado en el log.

---

### User Story 5 - Nadie sin credenciales puede inyectar datos ni gastar la API (Priority: P2)

Como responsable de operar el sistema, quiero que publicar al broker o llamar al endpoint de
diagnostico requiera autenticacion, para que nadie en la misma red pueda inyectar lecturas
falsas ni generar llamadas facturables a la API de Claude sin autorizacion.

**Why this priority**: hallazgo H7. Hoy el broker es anonimo y sin TLS, el endpoint no tiene
auth y escucha en todas las interfaces, y hay 4 puertos publicados al host — una cadena de
ataque concreta y sin credenciales, desde la misma LAN, ya identificada. El riesgo crece en
cuanto el RUT956 y la PC del stack compartan la red de planta (D18).

**Independent Test**: publicar al broker sin credenciales falla; llamar al endpoint sin la
credencial definida falla; ninguna de las dos cosas dispara una llamada a la API de Claude.

**Acceptance Scenarios**:

1. **Given** el broker configurado con autenticacion, **When** un cliente publica sin
   credenciales validas, **Then** el broker rechaza la conexion/publicacion.
2. **Given** el endpoint `POST /diagnosticar/<alerta_id>`, **When** se llama sin la
   credencial definida [NEEDS CLARIFICATION: token en header, allowlist de IP, o dejar de
   publicar el puerto — pregunta 3 del handoff], **Then** el sistema responde 401/403 y NO
   llama a la API de Claude.
3. **Given** la lista de puertos publicados al host (1883, 8086, 8000, 3000), **When** se
   revisa cada uno contra su necesidad real, **Then** los que no la tengan quedan atados a
   `127.0.0.1` o dejan de publicarse [NEEDS CLARIFICATION: cuales exactamente — pregunta 5
   del handoff].
4. **Given** `ANTHROPIC_API_KEY` expuesta en un transcript de una sesion anterior
   (2026-09-01), **When** se cierra esta historia, **Then** la key fue rotada en
   `console.anthropic.com` y el valor viejo ya no es valido.

---

### User Story 6 - Un resumen que fallo se puede volver a pedir (Priority: P3)

Como operador que pide un diagnostico via `POST /diagnosticar/<id>`, quiero poder reintentar
un pedido cuyo resumen fallo (timeout, error transitorio de la API), y que dos pedidos
simultaneos de la misma alerta no generen dos llamadas pagas ni un error crudo, para que el
mecanismo bajo demanda de D13 funcione como se penso originalmente.

**Why this priority**: hallazgos H5 y H6, severidad MEDIA — molesto pero no critico, ultima
prioridad del alcance.

**Independent Test**: forzar un fallo del nucleo de IA, pedir el resumen de nuevo para la
misma alerta y obtener un resumen exitoso; disparar dos pedidos simultaneos de la misma
alerta y confirmar una sola llamada a Claude y ninguna excepcion sin capturar.

**Acceptance Scenarios**:

1. **Given** un diagnostico previo marcado `fallo: true`, **When** se pide de nuevo via el
   endpoint, **Then** el sistema reintenta la llamada a Claude en vez de devolver el fallo
   cacheado indefinidamente [NEEDS CLARIFICATION: sobrescribir el registro fallido o
   guardar historial de intentos, y si hay tope de reintentos — pregunta 6 del handoff].
2. **Given** dos `POST /diagnosticar/<id>` simultaneos para la misma alerta, **When** ambos
   llegan practicamente al mismo tiempo, **Then** solo uno dispara la llamada a Claude y el
   otro espera/devuelve el mismo resultado — nunca dos llamadas pagas ni una excepcion sin
   capturar expuesta al cliente HTTP.

### Edge Cases

- Que pasa si SQLite devuelve `database is locked` (M2) durante una escritura del camino de
  ingesta: MUST tratarse igual que cualquier otra excepcion de H1 — loguear, descartar esa
  operacion puntual, seguir vivo. NO MUST propagarse y matar el hilo de ingesta.
- Que pasa con una lectura cuyo `equipo_id` no existe: el comportamiento actual (se descarta
  con warning) se mantiene, pero MUST verificarse ANTES de escribir en InfluxDB (hoy se
  escribe primero, se valida despues — ver H7, tabla de superficie de seguridad).
- Que pasa si la cola interna de US2 se llena mas rapido de lo que el worker puede procesar
  (backpressure) [NEEDS CLARIFICATION: no cubierto explicitamente por el handoff — decidir
  en `plan.md` si hace falta un limite de tamano y que pasa al alcanzarlo, dado que a la
  escala actual (un motor, lecturas cada pocos segundos) es un caso extremo].
- Que pasa si se persiste el cooldown pero `data/aiproject.db` no existe todavia (primer
  arranque): el comportamiento actual de `inicializar_schema()` (idempotente) se mantiene —
  NO MUST requerir un paso manual adicional.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST capturar cualquier excepcion en el camino de procesamiento de
  una lectura MQTT individual (normalizacion, escritura a InfluxDB, deteccion, persistencia
  de alerta) sin terminar el hilo/loop de suscripcion MQTT — la ingesta MUST seguir viva
  ante un fallo puntual. (H1)
- **FR-002**: El sistema MUST exponer un estado de salud que distinga "el proceso responde"
  de "la ingesta esta efectivamente viva" [NEEDS CLARIFICATION: que forma toma esto —
  timestamp de la ultima lectura procesada en `/health`, metrica separada, o log
  estructurado — no especificado en el handoff, decidir en `plan.md`].
- **FR-003**: El trabajo que puede demorar (persistencia, llamada al nucleo de IA,
  notificacion Telegram) MUST salir del callback que recibe el mensaje MQTT, de forma que
  una alerta lenta no bloquee la recepcion de lecturas nuevas. (H2)
- **FR-004**: La deteccion MUST aplicar una banda muerta para volver de ALERTA/CRITICO a
  NORMAL y MUST requerir una cantidad configurable de lecturas consecutivas por encima del
  umbral antes de generar el evento de alerta [NEEDS CLARIFICATION: valor de la banda
  (absoluto por variable o porcentaje del umbral) y cantidad de lecturas consecutivas —
  pregunta 1 del handoff]. (H3)
- **FR-005**: El estado del cooldown del detector (severidad activa y `cooldown_hasta` por
  equipo+variable) MUST persistir mas alla de un reinicio del proceso/contenedor. (H4)
- **FR-006**: El sistema MUST validar que el timestamp de una lectura entrante este dentro
  de una ventana aceptable respecto del reloj del servidor, y MUST aplicar una politica
  explicita cuando no lo este [NEEDS CLARIFICATION: tamano de la ventana y que hacer al
  excederla — pregunta 2 del handoff]. (H4)
- **FR-007**: Un diagnostico marcado `fallo: true` MUST poder reintentarse en un pedido
  posterior al mismo endpoint, en vez de devolver el fallo cacheado para siempre
  [NEEDS CLARIFICATION: politica de reintento — pregunta 6 del handoff]. (H5)
- **FR-008**: Dos pedidos simultaneos de `POST /diagnosticar/<alerta_id>` para la misma
  alerta MUST resultar en una sola llamada a la API de Claude y NO MUST generar una
  excepcion sin capturar expuesta al cliente HTTP. (H6)
- **FR-009**: El broker MQTT MUST requerir autenticacion (usuario/password por cliente como
  minimo) para publicar o suscribirse [NEEDS CLARIFICATION: si TLS entra en el alcance de
  esta spec o queda para despues, y si hace falta ACL por topico ademas de autenticacion —
  pregunta 4 del handoff]. (H7)
- **FR-010**: El endpoint `POST /diagnosticar/<alerta_id>` MUST requerir una credencial para
  ejecutar el diagnostico [NEEDS CLARIFICATION: mecanismo — token compartido, allowlist de
  IP, o dejar de publicar el puerto — pregunta 3 del handoff]. `GET /health`
  [NEEDS CLARIFICATION: queda abierto o requiere la misma credencial].
- **FR-011**: De los 4 puertos publicados al host (1883, 8086, 8000, 3000), el sistema MUST
  publicar solo los que el flujo de trabajo real necesita expuestos mas alla de
  `127.0.0.1` [NEEDS CLARIFICATION: cuales exactamente — pregunta 5 del handoff].
- **FR-012**: Grafana NO MUST arrancar con el password de administrador por defecto
  (`admin`) en ningun entorno mas alla de un `.env` local no commiteado.
- **FR-013**: `ANTHROPIC_API_KEY` MUST rotarse en `console.anthropic.com` — el valor que
  quedo expuesto en un transcript el 2026-09-01 MUST dejar de ser valido.
- **FR-014**: El sistema MUST seguir aceptando el mismo contrato de topico MQTT (5 partes,
  payload `{valor, unidad, timestamp}`), la misma ruta `POST /diagnosticar/<alerta_id>`, y
  los mismos nombres de tabla/measurement `diagnostico`/`diagnosticos` — ningun cambio de
  esta spec MUST romper estos contratos (ver D13, D17, D18).

*Items que quedan para `/speckit-plan` (research.md), no se fijan en este spec:*

- **FR-015**: El mecanismo concreto para sacar el trabajo pesado del callback MQTT (cola en
  memoria + worker, u otra alternativa) MUST declararse explicitamente en el Constitution
  Check del plan como compatible con la excepcion de fase MVP de D9 (Principio I) — no
  reabre la separacion de capas de D11. (US2, pregunta 9 del handoff)
- **FR-016**: La migracion del schema de SQLite para persistir el cooldown MUST decidir si
  se acepta borrar y recrear `data/aiproject.db` (mismo patron que D17) o si hace falta una
  migracion real que preserve el historial de alertas [NEEDS CLARIFICATION: pregunta 8 del
  handoff].
- **FR-017**: El manejo de secretos de produccion (mas alla de `.env` local, D8) sigue
  diferido — esta spec NO lo resuelve (ver pregunta 7 del handoff y "Fuera de alcance").

### Key Entities *(include if feature involves data)*

- **Estado del detector (persistido)**: por equipo+variable, la severidad activa y el
  `cooldown_hasta`. Hoy vive solo en memoria (`Detector._estado`); pasa a sobrevivir un
  reinicio del proceso.
- **Credencial del endpoint**: el mecanismo de autenticacion que el cliente HTTP debe
  presentar para llamar a `POST /diagnosticar/<alerta_id>` — su forma exacta es una
  NEEDS CLARIFICATION de esta spec (FR-010).
- **Credencial del broker MQTT**: usuario/password (y opcionalmente TLS/ACL) que un cliente
  debe presentar para publicar/suscribirse — reemplaza el `allow_anonymous true` actual.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Con InfluxDB caido durante 5 minutos, el servicio sigue detectando y
  notificando alertas, y reanuda la escritura al volver, sin intervencion manual.
- **SC-002**: Ninguna lectura publicada durante una llamada al nucleo de IA de 10 segundos
  se pierde del camino de deteccion.
- **SC-003**: El escenario D del emulador (operacion normal con ruido) genera 0 alertas en 3
  corridas consecutivas; el escenario A genera exactamente 1 alerta por cruce sostenido.
- **SC-004**: Reiniciar el servicio con una variable en alerta no genera ningun evento nuevo
  mientras el cooldown original siga vigente.
- **SC-005**: Una alerta cuyo resumen fallo obtiene un resumen exitoso en un pedido
  posterior, sin tocar la base a mano.
- **SC-006**: Un cliente sin credenciales no logra escribir en el broker, ni disparar el
  endpoint, ni provocar ninguna llamada facturable a la API.
- **SC-007**: La suite de tests queda en verde (39/39 como piso), sumando tests propios por
  cada historia de usuario.

## Assumptions

- El estado del detector se persiste en SQLite (misma base que ya existe), no en un store
  nuevo — coherente con el Principio II (deteccion barata: lectura en el arranque o
  cacheada, no una consulta por cada lectura MQTT).
- El escenario tipico de reinicio (deploy, `--build`, caida corta) es el caso que importa
  cubrir — no se asume alta disponibilidad ni failover entre multiples instancias del
  servicio (sigue siendo un unico proceso, D9/D10).
- El volumen actual (un motor, lecturas cada pocos segundos) hace que el backpressure de una
  cola interna sea un caso extremo, no el caso comun — ver Edge Cases.
- Esta spec resuelve autenticacion de aplicacion (broker, endpoint) como parte de H7, pero
  NO resuelve gestion de secretos de produccion como practica de infraestructura — eso sigue
  diferido desde D8 (ver "Fuera de alcance").

## Fuera de alcance

- **Separar detector y workers en procesos distintos**: es el roadmap de D11 (escala
  industrial real). Esta spec resuelve el bloqueo del callback (H2) dentro del proceso unico
  de D9 — con una cola/worker interno al mismo proceso, no un servicio separado.
- **Telegram Nivel 1 o superior** (D2): el receptor de comandos/botones inline sigue siendo
  trabajo futuro, no depende de esta spec.
- **Integracion real del RUT956 por RS485**: en pausa hasta que llegue el adaptador
  USB-RS485 (ver `memory/progress.md`). Esta spec asume que las lecturas siguen llegando por
  el mismo contrato MQTT que ya existe, sin importar el origen.
- **Reemplazar SQLite por Postgres/MySQL**: roadmap de D11, no de esta spec.
- **Deteccion de anomalias por ML**: roadmap de D11 (tabla de roles en `CLAUDE.md`), no de
  esta spec.
- **Gestion de secretos de produccion mas alla de `.env` local**: D8 solo resolvio la etapa
  de desarrollo; esta spec no toma esa decision (ver pregunta 7 del handoff). FR-009/FR-010
  de esta spec resuelven autenticacion de aplicacion (broker, endpoint), no gestion de
  secretos como practica de infraestructura.
