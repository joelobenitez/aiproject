# Funcionamiento detallado del sistema (src/)

> Documento de referencia tecnica completo, escrito el 2026-09-01 a partir de la lectura
> directa del codigo en `src/` (fuente de verdad viva del proyecto, ver `CLAUDE.md`). Pensado
> para estudio (NotebookLM u otra herramienta), no para mantenerse actualizado — si el codigo
> cambia, este documento puede quedar desactualizado. Idioma: espanol sin tildes (convencion
> del proyecto).

---

## 1. Que es el sistema, en una frase

Un servicio Python de vida larga que escucha lecturas de sensores de un motor industrial via
MQTT, detecta cuando una variable cruza un umbral, y cuando la severidad lo amerita le pide a
Claude (Anthropic) un diagnostico en lenguaje natural — causa probable, urgencia, accion
recomendada — que despues persiste, muestra en un dashboard y notifica por Telegram.

## 2. El problema que resuelve

Los sistemas SCADA tradicionales dicen QUE esta mal (una alerta, un umbral cruzado). Este
sistema agrega el POR QUE y el QUE HACER: en vez de solo avisar "temperatura alta", devuelve
algo como "degradacion del sistema de refrigeracion, revisar filtros en las proximas 8
horas".

## 3. Vista de conjunto del pipeline

```
[Sensores / emulador]
        | MQTT (topico: empresa/planta/linea/equipo/variable)
        v
[EMQX/Mosquitto broker]  <-- puerto 1883
        |
        v
[src/main.py]  <-- UN SOLO proceso Python de vida larga (D9, D10)
        |
        +--> Normaliza el payload (src/ingesta/normalizador.py)
        +--> Escribe la lectura cruda en InfluxDB (src/almacenamiento/influx_repo.py)
        +--> Evalua umbral con histeresis/cooldown en memoria (src/deteccion/detector.py)
        |
        | (si hay evento de alerta)
        v
[src/main.py: _procesar_evento]
        +--> Persiste la Alerta en SQLite (src/almacenamiento/sqlite_repo.py)
        +--> Espeja el evento en InfluxDB measurement "alertas" (para anotaciones Grafana)
        |
        +-- severidad == CRITICO -----> diagnostico AUTOMATICO
        |         |
        |         v
        |    [src/diagnostico/context.py]  arma el contexto (equipo + tendencia 24h + historial)
        |         v
        |    [src/diagnostico/prompt.py]   arma los mensajes (system + few-shot + contexto real)
        |         v
        |    [src/diagnostico/parser.py]   llama a la API de Claude, parsea la respuesta JSON
        |         v
        |    Persiste Diagnostico en SQLite + espejo en InfluxDB measurement "diagnosticos"
        |         v
        |    Notifica por Telegram (mensaje con causa/urgencia/accion)
        |
        +-- severidad == ALERTA -------> mensaje CRUDO por Telegram (sin IA)
                  |
                  v
             diagnostico queda disponible BAJO DEMANDA via
             POST /diagnosticar/<alerta_id>  (src/api.py, puerto 8000)
             -- dispara el mismo camino de arriba, pero cuando alguien lo pide --
```

```
                                    [Grafana :3000]
                                    lee InfluxDB (lecturas, alertas, diagnosticos)
                                    + plugin grafana-llm-app (feature 002, no forma
                                      parte del pipeline de deteccion, es independiente)
```

## 4. Los tres "cerebros" del sistema y por que estan separados

El diseno original (D1-D4, `definicion/arquitectura_sistema.md`) preveia Node-RED (capa de
datos) + n8n (orquestacion) + un Claude Agent como tres componentes separados. Para el MVP
(D9) se colapsaron en un solo proceso Python porque, a la escala de una demo de un motor, la
separacion no aportaba nada que Claude Code pudiera escribir/testear/revisar (Node-RED/n8n
son low-code, flows en JSON). El roadmap de escala industrial real (D11) preve volver a
separarlos: un detector stateful (tiene que ver el 100% del stream para sostener la
histeresis) y workers de diagnostico stateless detras de una cola, que si pueden escalar
horizontalmente.

Dentro del proceso unico actual, la separacion logica en modulos SI se mantiene (Principio II
de la constitucion del proyecto): ingesta, deteccion, diagnostico, notificacion y
almacenamiento son paquetes Python independientes que se importan desde `src/main.py`.

---

## 5. Ingesta (`src/ingesta/`)

### 5.1 `mqtt_client.py`

Crea un cliente MQTT (libreria `paho-mqtt`, API v2) que se conecta a
`MQTT_HOST:MQTT_PORT` y se suscribe a un topico con wildcard: `{MQTT_TOPIC_BASE}/+`. Por
defecto `MQTT_TOPIC_BASE = demo/planta1/linea_a/motor_001`, asi que en la practica escucha
`demo/planta1/linea_a/motor_001/+` — cualquier variable publicada bajo ese equipo. El
wildcard `+` es deliberado: cuando escale a multiples equipos (D11), el patron UNS completo
(`empresa/planta/equipo/sensor`) permite pasar a un wildcard mas amplio
(`empresa/+/+/+`) sin cambiar el codigo de suscripcion.

Cada mensaje que llega dispara un callback (`al_recibir_mensaje`, inyectado desde
`main.py`) con el topico y el payload crudo en bytes.

### 5.2 `normalizador.py`

Valida y convierte el payload MQTT crudo en un objeto `Lectura` tipado. Reglas de
validacion, todas con fallo silencioso (loguea un warning y descarta, nunca tumba la
suscripcion):
- El topico tiene que tener exactamente 5 partes separadas por `/` (el equipo_id es la
  parte 4, la variable es la parte 5).
- El payload tiene que ser JSON valido, y ser un objeto (no una lista/string/numero suelto).
- Tiene que traer `valor` (numerico, no booleano), `unidad` (uno de `C`, `A`, `mm/s`, `h`)
  y `timestamp` (string parseable como ISO 8601).

El formato esperado del payload (ver `_publicar()` en el emulador para el ejemplo real):
```json
{"valor": 76.45, "unidad": "C", "timestamp": "2026-09-01T23:40:37Z"}
```

---

## 6. Deteccion (`src/deteccion/`)

### 6.1 `umbrales.py`

Carga umbrales por `(tipo_equipo, variable)` desde SQLite, con cache en memoria (Principio
II: la deteccion tiene que ser barata, no puede pegarle a la base en cada lectura). Los
umbrales del MVP (motor de induccion):

| Variable | Umbral ALERTA | Umbral CRITICO | Unidad |
|---|---|---|---|
| temperatura | 75.0 | 90.0 | C |
| corriente | 22.0 | 26.0 | A |
| vibracion | 4.5 | 7.1 | mm/s |

### 6.2 `detector.py` — el corazon con estado del sistema

La clase `Detector` mantiene un diccionario en memoria `_estado`, con una entrada por cada
par `(equipo_id, variable)`. Esto es lo que lo hace "stateful" y lo que impide que corra como
funciones serverless (D10) — necesita sobrevivir entre lecturas.

Logica de clasificacion (`_clasificar`): si `valor >= valor_critico` => `CRITICO`; si
`valor >= valor_alerta` => `ALERTA`; si no, `NORMAL`.

**Histeresis + cooldown** (evita alertas duplicadas cada vez que llega una lectura mientras
el valor sigue arriba del umbral):
- Cuando se genera un evento de alerta para `(equipo, variable)`, se guarda su severidad y un
  `cooldown_hasta = timestamp + COOLDOWN_MINUTOS` (15 min por defecto, configurable).
- Mientras el cooldown esta activo, nuevas lecturas que sigan en la misma severidad (o mas
  baja) NO generan un evento nuevo.
- **Excepcion — escalada:** si la severidad sube (de `ALERTA` a `CRITICO`) durante el
  cooldown, SI se genera un evento nuevo y el cooldown se reinicia con la severidad mas
  alta. Esto es lo que marca el campo `es_escalada` del `EventoAlerta`.
- Cuando el valor vuelve a `NORMAL`, el estado se resetea (`cooldown_hasta = None`) — la
  proxima vez que cruce el umbral, es un evento nuevo desde cero.

`evaluar()` devuelve `None` si no corresponde generar un evento (valor normal, o en cooldown
sin escalada), o un `EventoAlerta` (equipo, variable, valor, severidad, timestamp,
es_escalada) cuando si corresponde.

---

## 7. Diagnostico (`src/diagnostico/`) — el nucleo de IA

### 7.1 `context.py` — que datos ve Claude

`armar_contexto()` junta, para la alerta puntual que dispara el diagnostico:
- **Metadata del equipo** (SQLite): id, nombre, horas de operacion acumuladas.
- **La alerta en si**: variable disparadora, valor, unidad, severidad, timestamp.
- **Tendencia de 24h** (InfluxDB, `tendencia_24h()` en `influx_repo.py`) de las 3 variables
  del motor (temperatura, corriente, vibracion) — un resumen en texto tipo "incremento de
  12.3 en las ultimas 24 horas" o "estable" (delta < 0.5) o "sin datos suficientes".
- **Las ultimas 5 alertas previas** del mismo equipo (SQLite), cada una con variable, valor,
  severidad y timestamp.

Esto se devuelve como un dict, que luego se serializa a JSON. El sistema arma este paquete
completo — Claude nunca consulta las bases de datos directamente, solo recibe lo que
`context.py` le prepara.

### 7.2 `prompt.py` — el prompt versionado

**System prompt** (fijo, ver seccion 9 para el texto completo): le indica a Claude su rol
("nucleo de diagnostico de un sistema de monitoreo industrial"), y le impone reglas
estrictas de formato: responder UNICAMENTE un objeto JSON con 5 claves exactas
(`causa_probable`, `razonamiento`, `urgencia`, `accion_recomendada`, `confianza`), donde
`urgencia`/`confianza` son `ALTA`/`MEDIA`/`BAJA`, `razonamiento` tiene que descartar otras
causas (no solo repetir el dato), `accion_recomendada` tiene que ser concreta y con plazo, y
si el contexto no alcanza, decirlo con `confianza: BAJA` en vez de inventar.

**Few-shot fijo**: 3 ejemplos completos (entrada + salida esperada) que anclan formato y
estilo:
1. Temperatura sube sola, sin aumento de corriente => degradacion de refrigeracion (urgencia
   MEDIA).
2. Corriente + temperatura + vibracion suben juntas => sobrecarga/desalineamiento mecanico
   (urgencia ALTA).
3. Vibracion sube sola y progresiva => desgaste de rodamiento (urgencia MEDIA).

`construir_mensajes()` arma la lista de mensajes: los 3 pares user/assistant del few-shot,
mas un ultimo mensaje `user` con el contexto real (JSON de `context.py` serializado con
`json.dumps(..., ensure_ascii=False)`, sin indentar).

### 7.3 `parser.py` — la llamada real a la API

- Cliente: SDK oficial `anthropic` (Python), instanciado una sola vez (patron singleton
  perezoso) con `ANTHROPIC_API_KEY`.
- Modelo por defecto: **`claude-haiku-4-5-20251001`** (Haiku 4.5), configurable via env var
  `MODEL`. Elegido por costo — el diagnostico no necesita el modelo mas grande.
- **Prompt caching**: tanto el `system` prompt como el ultimo mensaje `assistant` del
  few-shot fijo se marcan con `cache_control: {"type": "ephemeral"}`. Como ese contenido
  (~2.5K tokens) es identico en cada llamada, Anthropic lo cachea del lado del servidor y
  cobra una fraccion del costo normal en llamadas subsiguientes dentro de la ventana de
  cache — es la razon por la que el diagnostico sale barato pese a mandar el prompt +
  3 ejemplos completos en cada llamada.
- `max_tokens=1024`, `timeout=10.0` segundos.
- **Parseo defensivo**: la respuesta de Claude a veces (~intermitente, confirmado
  empiricamente) viene envuelta en un fence de markdown (` ```json ... ``` `) a pesar de que
  el prompt pide texto plano sin nada mas. El parser detecta si el texto empieza con
  ` ``` ` y le saca el fence antes de hacer `json.loads()`.
- Si la respuesta no tiene las 5 claves esperadas, o cualquier excepcion ocurre (timeout,
  error HTTP, JSON invalido), la funcion **nunca lanza** — devuelve `{"fallo": True}`. La
  Alerta que origino el pedido ya quedo persistida en SQLite independientemente de si el
  diagnostico sale bien o mal (FR-013 del contrato original).

---

## 8. Orquestacion — como se conecta todo (`src/main.py`)

Es el punto de entrada del proceso (`python -u src/main.py`). Al arrancar:
1. Configura logging (nivel INFO, formato con timestamp).
2. Inicializa el esquema de SQLite (`sqlite_repo.inicializar_schema()`) — crea las tablas si
   no existen y siembra los umbrales/equipo por defecto (`INSERT OR IGNORE`, idempotente).
3. Crea y arranca el cliente MQTT en un loop de fondo (`cliente.loop_start()`).
4. Levanta el servidor HTTP embebido (`src/api.py`) en el puerto `HTTP_PORT` (default 8000)
   y lo deja corriendo en primer plano (`serve_forever()`).

### 8.1 `_al_recibir_mensaje` — el callback MQTT

Por cada mensaje MQTT que llega:
1. Normaliza el payload (`normalizador.normalizar`) — si es invalido, se descarta ahi.
2. Escribe la lectura cruda en InfluxDB (measurement `lecturas_motor`), **siempre**,
   independientemente de si dispara alerta o no — esto es lo que alimenta los graficos del
   dashboard de Grafana.
3. Caso especial: si la variable es `horas_operacion`, solo actualiza el contador en la
   tabla `equipo` de SQLite y termina ahi (no pasa por deteccion — no tiene umbral).
4. Busca el equipo en SQLite; si no existe, descarta la lectura con un warning (equipo
   desconocido).
5. Llama a `Detector.evaluar()`. Si devuelve `None`, no hay nada mas que hacer con esta
   lectura.
6. Si devuelve un `EventoAlerta`, lo pasa a `_procesar_evento`.

### 8.2 `_procesar_evento` — que pasa cuando hay una alerta real

1. Crea el registro `Alerta` en SQLite (`sqlite_repo.crear_alerta`) — esto le asigna un
   `alerta_id` autoincremental, que es la clave que se usa despues para pedir el diagnostico
   bajo demanda.
2. Espeja el evento en InfluxDB (measurement `alertas`, best-effort — un fallo aca no tumba
   el pipeline) para que Grafana pueda dibujar la anotacion (linea vertical) en el momento
   exacto de la alerta.
3. Loguea la alerta.
4. **Bifurca segun severidad (D13):**
   - `CRITICO` => `_diagnosticar_y_notificar()` — dispara todo el camino de IA automatico.
   - Cualquier otra cosa (en la practica, `ALERTA`) => `_notificar_crudo()` — Telegram con
     los datos crudos y una instruccion de como pedir el diagnostico manualmente.

### 8.3 `_diagnosticar_y_notificar` — el camino completo de IA

Es la funcion compartida entre el camino automatico (CRITICO) y el bajo demanda
(`diagnosticar_bajo_demanda`, ver 8.4). Hace, en orden:
1. `context.armar_contexto(...)` — arma el paquete de datos para Claude.
2. `parser.diagnosticar(entrada)` — la llamada real a la API.
3. Persiste el resultado en SQLite (`sqlite_repo.crear_diagnostico`) — tabla `diagnostico`,
   con `alerta_id` UNIQUE (una alerta tiene a lo sumo un diagnostico).
4. Espeja el resultado en InfluxDB (measurement `diagnosticos`, best-effort) — lo que lee el
   panel "Diagnostico IA" del dashboard de Grafana.
5. Loguea exito o fallo.
6. Llama a `_notificar()` para mandar el mensaje por Telegram (exitoso o de fallback segun
   corresponda).

### 8.4 `diagnosticar_bajo_demanda` — la pieza D13

Expuesta via el endpoint HTTP `POST /diagnosticar/<alerta_id>`. Logica:
1. Busca la alerta en SQLite. Si no existe, devuelve `{"error": "alerta_no_encontrada"}`.
2. **Idempotencia/cache:** si ya existe un diagnostico para esa alerta (alguien ya lo pidio
   antes), lo devuelve directamente marcado `cacheado: true`, **sin volver a llamar a
   Claude** — evita pagar dos veces el mismo diagnostico.
3. Si no existe, reconstruye los datos de la alerta original desde SQLite (variable, valor,
   umbral, timestamp) y llama a `_diagnosticar_y_notificar()` — el mismo camino que usa
   CRITICO. El resultado queda marcado `cacheado: false`.

### 8.5 `_notificar` / `_notificar_crudo` — armado del mensaje final

`_notificar` arma el mensaje de Telegram segun si el diagnostico salio bien
(`formatear_mensaje_exitoso`: causa probable, urgencia, confianza, accion recomendada) o mal
(`formatear_mensaje_fallback`: "diagnostico no disponible, revisar manualmente").
`_notificar_crudo` (solo para `ALERTA`) arma un mensaje sin IA: variable, valor, umbral, y la
instruccion de como pedir el diagnostico via el endpoint.

---

## 9. Decision D13 en detalle — por que ALERTA y CRITICO se tratan distinto

Antes de D13 (2026-08-31), toda alerta (ALERTA o CRITICO) disparaba diagnostico automatico.
El cambio: **el diagnostico de IA cuesta dinero real** (llamada a la API de Anthropic) y una
alerta de severidad `ALERTA` es, por definicion, menos urgente — no siempre vale la pena
pagar el diagnostico completo de inmediato. Con D13:
- `CRITICO` sigue siendo automatico (la urgencia justifica el costo sin preguntar).
- `ALERTA` manda un aviso barato (Telegram con los datos crudos) y deja el diagnostico
  completo como una accion explicita que alguien (un operador, o cualquier cliente HTTP)
  puede pedir cuando decida que vale la pena.

El "camino natural siguiente" (anotado como trabajo futuro, no implementado) es que el propio
bot de Telegram pueda disparar ese pedido con un boton inline, en vez de depender de un
cliente HTTP externo — ver `memory/progress.md` y D2/D13 en `memory/decisions.md`.

---

## 10. Notificacion (`src/notificacion/telegram.py`)

Cliente HTTP directo a la Bot API de Telegram (`https://api.telegram.org/bot<token>/sendMessage`),
sin libreria de terceros especifica de Telegram — usa `httpx`. Nivel 0 de la escala de
integracion definida en D2 (`definicion/arquitectura_sistema.md`): **solo push**, el sistema
manda mensajes pero no procesa respuestas ni comandos entrantes desde Telegram (eso seria
Nivel 1+, ver seccion "trabajo futuro" en `memory/progress.md`).

`enviar()` reintenta hasta 3 veces con backoff simple (`1s, 2s`), y **nunca lanza excepcion**
— si Telegram no responde, solo loguea el error. La misma filosofia que el resto del sistema:
un fallo en la notificacion no debe tumbar el pipeline, porque la Alerta y el Diagnostico ya
quedaron persistidos en la base antes de llegar a este paso.

Si faltan `TELEGRAM_BOT_TOKEN` o `TELEGRAM_CHAT_ID` en la config, el envio se omite
silenciosamente (con un warning) — util para desarrollo sin credenciales reales.

---

## 11. Almacenamiento — dos bases, cada una con su rol

### 11.1 SQLite (`src/almacenamiento/sqlite_repo.py`) — la fuente de verdad relacional

Reemplaza a MySQL (decision D9, para simplificar el MVP: un archivo, sin contenedor ni
credenciales). Cuatro tablas:

- **`equipo`**: id, nombre, planta, linea, tipo_equipo, horas_operacion_acumuladas. Sembrada
  con un unico motor (`motor_001`) al inicializar el esquema.
- **`umbral`**: `(tipo_equipo, variable)` como clave primaria compuesta, con
  `valor_alerta`/`valor_critico`/`unidad`. Sembrada con los 3 umbrales del motor de induccion
  (ver tabla en la seccion 6.1).
- **`alerta`**: cada cruce de umbral detectado, con `estado_cooldown` (campo presente pero
  no consultado activamente por el codigo actual mas alla de guardarse siempre como
  `'en_cooldown'` al crearse).
- **`diagnostico`**: resultado del nucleo de IA, `alerta_id` UNIQUE (relacion 1:1 con
  alerta), incluye `fallo` (booleano, si la llamada a Claude fallo) y `generado_en`
  (timestamp de cuando se genero, no el de la alerta original).

`inicializar_schema()` es idempotente (`CREATE TABLE IF NOT EXISTS` + `INSERT OR IGNORE`) —
se puede correr en cada arranque del servicio sin duplicar datos.

### 11.2 InfluxDB (`src/almacenamiento/influx_repo.py`) — series de tiempo + espejos para Grafana

Tres measurements distintos dentro del mismo bucket (`lecturas_motor` por defecto):

- **`lecturas_motor`**: la serie de tiempo real, una escritura por cada lectura MQTT valida
  que llega (tags: `equipo_id`, `variable`; fields: `valor`, `unidad`). Es lo que dibuja las
  curvas de temperatura/corriente/vibracion en el dashboard.
- **`alertas`**: espejo liviano de cada `Alerta` creada en SQLite, solo para que Grafana
  pueda anotar (linea vertical) el momento exacto de cada alerta sobre las curvas. Escritura
  **best-effort**: envuelta en try/except, un fallo aca no debe afectar el pipeline principal
  porque la Alerta ya esta segura en SQLite.
- **`diagnosticos`** (agregado en el feature 002, Historia 2): espejo liviano de cada
  `Diagnostico`, con todos sus campos como fields de InfluxDB (incluida la confianza como
  string). Tambien best-effort. Es lo que lee el panel "Diagnostico IA" del dashboard — sin
  este measurement, el panel queda vacio sin ningun error visible (bug real encontrado y
  arreglado el 2026-09-01, ver `memory/risks.md`: un contenedor Docker viejo sin este codigo
  dejaba el panel vacio silenciosamente).

**Por que dos bases en vez de una:** InfluxDB esta optimizado para series de tiempo de alto
volumen (lecturas cada pocos segundos) y consultas de rango/tendencia; SQLite es mejor para
datos relacionales de bajo volumen con relaciones 1:1/1:N (una alerta, su diagnostico, sus
umbrales). Los measurements `alertas`/`diagnosticos` en InfluxDB son deliberadamente
espejos/read-models para Grafana, no la fuente de verdad — la fuente de verdad de esos datos
es siempre SQLite. Motivo tecnico adicional: Grafana no trae plugin de SQLite instalado por
defecto, asi que sin este espejo no tendria como leer alertas/diagnosticos.

`tendencia_24h()` hace una query Flux simple (rango de 24h, filtrada por measurement +
equipo + variable + field `valor`) y devuelve un resumen en texto (no los datos crudos) —
es lo que consume `context.py` para dar contexto historico a Claude sin mandarle miles de
puntos de datos.

---

## 12. API HTTP embebida (`src/api.py`)

Servidor minimalista con `http.server.ThreadingHTTPServer` de la libreria estandar de
Python — sin framework (FastAPI, Flask), decision explicita por volumen bajo (D9: MVP
simplificado, no se justifica la dependencia extra todavia). Dos rutas:

- **`GET /health`**: siempre devuelve `{"status": "ok"}` con 200 — health check simple.
- **`POST /diagnosticar/<alerta_id>`**: la unica ruta de accion, deliberadamente POST porque
  dispara un efecto secundario con costo real (llamada a Claude). Delega en
  `main.diagnosticar_bajo_demanda(alerta_id)`. Devuelve 404 si la alerta no existe, 200 en
  cualquier otro caso (incluido cuando el diagnostico mismo fallo — el `fallo: true` va
  dentro del cuerpo, no como codigo HTTP).

**Riesgo conocido (documentado en `memory/risks.md`):** este endpoint no tiene ninguna
autenticacion. En desarrollo local el puerto 8000 esta mapeado al host — cualquier proceso
con acceso de red puede disparar una llamada real a la API de Claude (costo real) por
cualquier alerta existente. No exponer este puerto fuera de `localhost` sin agregar
autenticacion primero.

---

## 13. El emulador (`herramientas/emulador_motor.py`) — no es parte del sistema

Publica lecturas MQTT simuladas para probar el pipeline sin sensores/RUT956 reales. Cumple el
rol que en produccion (D11 roadmap) ocupara el gateway Teltonika RUT956 (hardware ya
confirmado, integracion todavia sin arrancar al 2026-09-01) hablando Modbus RTU/RS485 con
sensores fisicos y publicando por su cliente MQTT nativo.

Cuatro escenarios, cada uno interpola linealmente entre un valor inicial y uno final a lo
largo de los `--ticks` (mas ruido aleatorio superpuesto):

| Escenario | Que simula | Temperatura | Corriente | Vibracion |
|---|---|---|---|---|
| A | Degradacion de refrigeracion | 60 -> 88 C (sube) | ~15 A (estable) | ~2.0 mm/s (estable) |
| B | Sobrecarga mecanica | 60 -> 80 C (sube) | 15 -> 24 A (sube) | 2.0 -> 5.0 mm/s (sube) |
| C | Falla de rodamiento incipiente | 60 -> 72 C (casi estable) | 15 -> 18 A (casi estable) | 2.0 -> 6.0 mm/s (sube) |
| D | Operacion normal | ~55 C (ruido, sin tendencia) | ~15 A | ~2.5 mm/s |

Los escenarios A/B/C estan disenados para que cada uno cruce el umbral por una combinacion
distinta de variables (justo lo que despues el nucleo de diagnostico tiene que distinguir en
su "razonamiento" — ver los 3 ejemplos few-shot de `prompt.py`, que son casi un calco de
estos mismos tres escenarios). El escenario D no deberia disparar ninguna alerta — sirve para
confirmar que el sistema no genera falsos positivos.

Ademas de las 3 variables del motor, publica `horas_operacion` (incrementando segun el
intervalo entre ticks) — la unica variable que no pasa por deteccion de umbral, solo
actualiza el contador del equipo en SQLite.

---

## 14. Configuracion (`src/config.py`)

Carga variables desde `.env` (parser simple manual, sin libreria `python-dotenv`) mas
`os.environ`, con `setdefault` — las variables de entorno del sistema tienen prioridad sobre
`.env` si ya estan seteadas. Variables relevantes:

| Variable | Default | Para que |
|---|---|---|
| `ANTHROPIC_API_KEY` | vacio | Autenticacion con la API de Claude |
| `MODEL` | `claude-haiku-4-5-20251001` | Modelo usado para el diagnostico |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | vacio | Notificaciones push |
| `INFLUX_URL` / `TOKEN` / `ORG` / `BUCKET` | `http://localhost:8086` / vacio / `aiproject` / `lecturas_motor` | Conexion a InfluxDB |
| `COOLDOWN_MINUTOS` | 15 | Ventana de histeresis del detector |
| `MQTT_HOST` / `PORT` / `TOPIC_BASE` | `localhost` / 1883 / `demo/planta1/linea_a/motor_001` | Conexion y topico MQTT |
| `SQLITE_DB_PATH` | `<raiz>/data/aiproject.db` | Ubicacion del archivo SQLite |
| `HTTP_PORT` | 8000 | Puerto del servidor HTTP embebido |

Dentro de Docker Compose, `MQTT_HOST` e `INFLUX_URL` se pisan explicitamente
(`environment:` en `docker-compose.yml`) para apuntar a los hostnames de la red interna
(`broker`, `influxdb`) en vez de `localhost` — el `.env` esta pensado para correr
`src/main.py` fuera de Docker, en desarrollo local.

---

## 15. Infraestructura Docker (`docker-compose.yml`)

Cuatro servicios en una red bridge comun (`iot-net`):

1. **`broker`** (`eclipse-mosquitto:2`): broker MQTT liviano, puerto 1883 expuesto al host.
2. **`influxdb`** (`influxdb:2`): auto-configurado al primer arranque
   (`DOCKER_INFLUXDB_INIT_MODE=setup`) con org/bucket/token/admin desde variables de entorno.
   Puerto 8086 expuesto, volumen nombrado para persistencia.
3. **`servicio`**: build local desde el `Dockerfile` del proyecto (copia `src/` +
   `requirements.txt`, corre `python -u src/main.py`). Puerto 8000 expuesto (API D13).
   Bind mount `./data:/app/data` — asi el archivo SQLite es accesible desde el host tambien.
4. **`grafana`** (`grafana/grafana:11.3.0`): puerto 3000, provisioning montado como
   read-only (`./grafana/provisioning`), con el plugin `grafana-llm-app` (feature 002)
   instalado via `GF_INSTALL_PLUGINS` y el feature toggle `dashgpt` habilitado.

**Nota operativa importante** (aprendida el 2026-09-01, ver `memory/risks.md`): `docker
compose up -d` sin `--build`/`--force-recreate` NO reconstruye la imagen de `servicio` ni
recrea contenedores existentes si el `docker-compose.yml` no cambio literalmente — un
contenedor creado antes de un cambio de codigo fuente puede seguir corriendo indefinidamente
la version vieja, sin ningun error visible. Despues de cualquier `git pull` que toque
`src/` o `docker-compose.yml`, correr `docker compose up -d --build`.

---

## 16. El texto exacto que ve Claude en cada llamada

### 16.1 System prompt (fijo, cacheado)

```
Sos el nucleo de diagnostico de un sistema de monitoreo industrial. Recibis el contexto de una alerta de un motor industrial de induccion (lectura que cruzo un umbral, tendencia de las ultimas 24 horas y alertas previas del mismo equipo) y devolves un diagnostico en lenguaje natural, en espanol sin tildes.

Reglas:
- Respondes UNICAMENTE con un objeto JSON, sin texto adicional antes o despues.
- El JSON tiene exactamente estas claves: causa_probable, razonamiento, urgencia, accion_recomendada, confianza.
- "urgencia" y "confianza" son uno de: ALTA, MEDIA, BAJA.
- "razonamiento" explica por que se descartan otras causas posibles, no solo repite el valor de la alerta.
- "accion_recomendada" es una accion concreta y ejecutable, con un plazo cuando aplique.
- Si el contexto no alcanza para un diagnostico confiable, decilo en "causa_probable" y usa confianza BAJA en vez de inventar una causa especifica.
```

### 16.2 Few-shot (3 ejemplos fijos, el ultimo tambien cacheado)

Los 3 pares user(JSON de entrada)/assistant(JSON de salida) descriptos en la seccion 7.2 —
ver `src/diagnostico/prompt.py` para el JSON completo de cada uno (temperatura sola,
corriente+temperatura+vibracion juntas, vibracion sola).

### 16.3 Ejemplo real de contexto (ultimo mensaje `user`, no cacheado — cambia en cada llamada)

Capturado en vivo el 2026-09-01 para una alerta real (`ALERTA`, corriente=22.12A):

```json
{"equipo": {"id": "motor_001", "nombre": "Motor M-01 | Linea A | Planta 1", "horas_operacion_acumuladas": 4820.01}, "alerta": {"variable_disparadora": "corriente", "valor": 22.12, "unidad": "A", "severidad": "ALERTA", "timestamp": "2026-09-01T23:40:10Z"}, "tendencia_24h": {"temperatura": "incremento de 19.2 en las ultimas 24 horas", "corriente": "incremento de 8.8 en las ultimas 24 horas", "vibracion": "incremento de 2.7 en las ultimas 24 horas"}, "alertas_previas": [{"variable_disparadora": "vibracion", "valor": 4.82, "severidad": "ALERTA", "timestamp": "2026-09-01T23:40:13.927031Z"}, {"variable_disparadora": "corriente", "valor": 22.89, "severidad": "ALERTA", "timestamp": "2026-09-01T23:40:11.918418Z"}, {"variable_disparadora": "vibracion", "valor": 4.65, "severidad": "ALERTA", "timestamp": "2026-09-01T23:40:10.916013Z"}, {"variable_disparadora": "temperatura", "valor": 75.44, "severidad": "ALERTA", "timestamp": "2026-09-01T23:40:10.915116Z"}, {"variable_disparadora": "corriente", "valor": 22.12, "severidad": "ALERTA", "timestamp": "2026-09-01T23:40:09.914227Z"}]}
```

### 16.4 Ejemplo real de respuesta de Claude, para ese mismo contexto

```json
{
  "causa_probable": "falla multifactorial critica: probable desalineamiento severo o rotura parcial de eje combinado con sobrecarga",
  "razonamiento": "El aumento simultaneo y proporcional de las tres variables (temperatura +17.6C, corriente +7.9A, vibracion +2.8mm/s) en 24 horas, junto con alertas multiples en cascada en los ultimos segundos, descarta causas aisladas. Este patron indica una degradacion estructural del sistema de transmision mecanica.",
  "urgencia": "ALTA",
  "accion_recomendada": "DETENER INMEDIATAMENTE el motor. Inspeccionar alineamiento del eje, acoples y rodamientos antes de cualquier reinicio. Si se detecta deformacion del eje o juego excesivo, no operar hasta reparacion completa.",
  "confianza": "ALTA",
  "fallo": false
}
```

---

## 17. Testing (`tests/`)

39 tests pytest, organizados en contract/integration/unit (estructura estandar del proyecto,
ver `memory/progress.md`). Cubren: normalizacion de payloads MQTT invalidos, clasificacion e
histeresis del detector, parseo de respuestas de Claude (incluido el caso del fence de
markdown), los 4 escenarios del emulador end-to-end contra un stack mockeado, el endpoint de
diagnostico bajo demanda (incluida la idempotencia/cache), y las funciones de escritura a
InfluxDB. Todos en verde al 2026-09-01.

---

## 18. Glosario rapido de decisiones referenciadas

Ver `memory/decisions.md` para el detalle completo de cada una:

- **D1-D4**: arquitectura original con Node-RED/n8n/Claude Agent separados.
- **D9**: colapso a un unico servicio Python para el MVP (motivo de casi toda la estructura
  descripta en este documento).
- **D10**: el servicio corre como proceso de vida larga, no serverless (por el estado en
  memoria del detector y la conexion MQTT persistente).
- **D11**: roadmap de escalamiento a estructura industrial real (separar detector/workers,
  RUT956 real, EMQX cluster, Postgres/MySQL).
- **D13**: diagnostico automatico solo para CRITICO, bajo demanda para ALERTA (seccion 9 de
  este documento).
- **D15**: integracion (luego evaluada como agotada) del plugin `grafana-llm-app` — un
  componente aparte, no forma parte del pipeline de deteccion/diagnostico descripto arriba.
