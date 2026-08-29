# Investigacion — Fase 0

Feature: Monitoreo de Motor Industrial con Diagnostico Inteligente via Claude
(`001-diagnostico-motor-industrial`)

Todas las decisiones tecnologicas de fondo (Python, servicio de vida larga sin serverless,
SQLite en vez de MySQL, Haiku 4.5 con prompt caching) ya estaban resueltas antes de este
plan (D8-D10, ver `memory/decisions.md`). Lo que sigue resuelve las decisiones de
implementacion que quedaban abiertas al nivel de detalle de un plan tecnico.

---

### Cliente MQTT

**Decision**: `paho-mqtt` (cliente sincrono).

**Rationale**: proyecto oficial de la Eclipse Foundation, es el estandar de facto en
Python para MQTT; una sola conexion persistente y bajo volumen de mensajes (una lectura
cada 30s por variable) no justifica un cliente asincrono.

**Alternativas consideradas**: `gmqtt`/`asyncio-mqtt` — descartadas por complejidad
innecesaria dado el volumen del MVP (Principio de no sobre-disenar para requisitos
hipoteticos).

---

### Cliente InfluxDB

**Decision**: InfluxDB 2.x con el cliente oficial `influxdb-client`.

**Rationale**: la version 2.x incluye UI de administracion y el modelo org/bucket, mas
simple de operar para un MVP de un solo equipo que la version 1.x orientada a
multi-usuario via bases separadas.

**Alternativas consideradas**: InfluxDB 1.x — descartada porque no aporta ventaja para
esta escala y el cliente 2.x es el que se sigue manteniendo activamente.

---

### Notificacion Telegram

**Decision**: llamadas HTTP directas a la Bot API de Telegram via `httpx`, sin libreria de
framework de bots.

**Rationale**: Telegram esta en Nivel 0 (D2) — solo push, unidireccional, sin comandos ni
manejo de actualizaciones entrantes. Una libreria como `python-telegram-bot` esta pensada
para manejar polling/webhooks y estado conversacional (Niveles 1-2), que no hacen falta
todavia.

**Alternativas consideradas**: `python-telegram-bot` — se revisita cuando el bot suba a
Nivel 1-2 (D2), momento en el que sostener actualizaciones entrantes si justifica la
dependencia.

---

### Acceso a SQLite

**Decision**: modulo `sqlite3` de la libreria estandar, sin ORM.

**Rationale**: el esquema es chico (equipos, umbrales, alertas, diagnosticos — ver
`data-model.md`) y hay un unico proceso escritor. Un ORM (SQLAlchemy) agregaria una capa de
abstraccion sin necesidad real a esta escala.

**Alternativas consideradas**: SQLAlchemy — descartado por ahora; si el esquema crece o se
migra a Postgres/MySQL en la fase de escala (D11), se reevalua en ese momento.

---

### Broker MQTT para el MVP

**Decision**: Mosquitto (imagen oficial `eclipse-mosquitto`), no EMQX, para esta fase.

**Rationale**: D9 dejaba abierto "EMQX o Mosquitto"; Mosquitto es mas liviano y su
configuracion es un unico archivo `.conf`, suficiente para un broker de un solo nodo con
un equipo publicando. EMQX se justifica por su capacidad de cluster (D11), que no aplica
todavia al MVP.

**Alternativas consideradas**: EMQX — se adopta en la fase de escala (D11) cuando haga
falta clustering multi-sitio.

---

### Ventana de enfriamiento (cooldown) para evitar diagnosticos duplicados

**Decision**: 15 minutos por combinacion equipo+variable, configurable por variable de
entorno (`COOLDOWN_MINUTOS`).

**Rationale**: `spec.md` (Supuestos) ya dejaba este valor abierto para ajustarse en
implementacion sin impacto en el alcance. 15 minutos evita notificar de nuevo mientras una
lectura oscila justo alrededor del umbral (caso limite de la spec) sin retrasar de forma
significativa la deteccion de un agravamiento real.

**Alternativas consideradas**: ventana fija mas corta (ej. 5 min) — descartada por generar
mas ruido en escenarios de oscilacion; ventana mas larga (ej. 1h) — descartada porque
podria ocultar una escalada real de severidad (ej. de ALERTA a CRITICO) durante ese lapso.
Mitigacion: el cooldown se reinicia si la severidad escala (de alerta a critico), no
solo por tiempo.

---

### Provisioning de Grafana

**Decision**: dashboard y datasource de Grafana definidos como archivos versionados en git
(provisioning YAML + JSON de dashboard), cargados automaticamente al levantar el
contenedor, no creados a mano en la UI.

**Rationale**: consistente con el mismo criterio que motivo D9 (preferir configuracion
como codigo, versionable y revisable, por sobre configuracion hecha a mano en una UI que
no deja rastro en git).

**Alternativas consideradas**: configurar el dashboard manualmente en la UI de Grafana
post-arranque — descartado porque no es reproducible ni versionable, y el proyecto ya
identifico ese mismo problema como riesgo para los flows de Node-RED (`memory/risks.md`).

---

## Items explicitamente fuera de esta investigacion

Email/SMTP (FR-007, FR-008, Historia 3) y Web Report quedaron fuera de alcance de este plan
(ver "Alcance de este plan" en `plan.md`, conflicto spec vs. D9) — no se investigo libreria
de envio de correo en esta pasada.
