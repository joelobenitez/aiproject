# Plan de Implementacion: Robustez y seguridad del servicio de deteccion

**Branch**: `003-robustez-seguridad` | **Fecha**: 2026-09-02 | **Spec**: [spec.md](./spec.md)

**Input**: Especificacion de feature en `specs/003-robustez-seguridad/spec.md`

**Nota**: las 9 `NEEDS CLARIFICATION` de la spec ya se resolvieron como **D20** en
`memory/decisions.md` antes de este plan — no hay resolucion de ambiguedad pendiente aca,
solo diseno tecnico concreto de como implementar cada decision.

## Resumen

Requisito principal (spec, H1-H7): que el servicio de deteccion no pueda quedar "sano por
fuera, muerto por dentro" (ingesta que muere en silencio, pipeline que se bloquea, alertas
por ruido, cooldown que no sobrevive un reinicio, resumen fallido irrecuperable, race
condition) y que la superficie de red (broker, endpoint, puertos, password de Grafana) deje
de estar mas abierta de lo documentado. Enfoque tecnico: (a) un `try/except` de ultimo
recurso alrededor del procesamiento de cada lectura (H1); (b) mover ese procesamiento a un
worker en un hilo separado, consumiendo de una `queue.Queue`, para que el callback MQTT solo
normalice y encole (H2); (c) extender `Detector` con banda muerta + confirmacion por lecturas
consecutivas (H3) y con persistencia del estado en SQLite + validacion de skew (H4); (d) un
`UPSERT` en vez de `INSERT` para el diagnostico + un lock para serializar pedidos concurrentes
del mismo endpoint (H5, H6); (e) credenciales en Mosquitto, token en el endpoint, puertos
atados a `127.0.0.1` donde no hacen falta, y password de Grafana sin default inseguro (H7).

## Contexto Tecnico

**Lenguaje/Version**: Python 3.11+ (igual que el resto de `src/`). Sin dependencias nuevas —
`queue.Queue` y `threading.Lock` son de la libreria estandar.

**Dependencias principales**: ninguna libreria Python nueva. Mosquitto: se agrega
`password_file` y `acl_file` (soportados nativamente por `eclipse-mosquitto:2`, sin plugin
extra).

**Storage**: SQLite gana una tabla nueva, `detector_estado` (equipo_id, variable, severidad,
cooldown_hasta) — ver `data-model.md`. `data/aiproject.db` se borra y recrea al desplegar
(D20/FR-016), mismo patron que D17. InfluxDB no cambia de schema en esta spec.

**Testing**: `pytest`, extendiendo los archivos existentes (`test_detector.py`,
`test_diagnostico_bajo_demanda.py`, `test_escenario_*.py`) mas tests nuevos por historia (ver
`tasks.md`). El worker/cola se testea con un `Queue` real y un `time.sleep` corto simulando
latencia de IA (mismo patron que ya usan los tests de integracion existentes contra un stack
mockeado). Piso: 39/39 en verde + tests nuevos de cada historia (SC-007).

**Plataforma objetivo**: mismo `docker-compose.yml`, mismos 4 contenedores. No se agrega
ningun servicio nuevo.

**Tipo de proyecto**: extension de lo existente (single project) — ningun modulo nuevo bajo
`src/`, se tocan los modulos que ya existen.

**Objetivos de performance**: sin objetivo numerico nuevo — el criterio es cualitativo (SC-002:
ninguna lectura se pierde durante una llamada de IA de 10s). El volumen sigue siendo el de un
motor (lecturas cada pocos segundos), por lo que un worker de un solo hilo alcanza; no hace
falta un pool.

**Restricciones**: FR-014 (no romper contratos existentes: topico MQTT, endpoint, nombres de
tabla/measurement) es una restriccion dura para todas las tareas. El mecanismo de
cola+worker (H2) MUST quedar dentro del mismo proceso — no es un servicio nuevo, es la misma
excepcion de fase MVP de D9 aplicada con un hilo mas.

**Escala/Alcance**: mismo volumen bajo del MVP. La cola interna tiene un limite de tamano
(1000 items) con descarte del mas viejo + warning si se llena — a este volumen es un caso
extremo, no el comun (ver Edge Cases de la spec).

## Constitution Check

*GATE: debe pasar antes de la Fase 0. Re-chequeado despues del diseno de la Fase 1.*

| Principio | Evaluacion | Estado |
|---|---|---|
| I. Separacion de Capas | El worker de H2 es un hilo dentro del mismo proceso Python (`src/main.py`), no un servicio ni un contenedor nuevo — sigue dentro de la excepcion de fase MVP de D9/D12. No reabre la separacion detector/workers de D11 (eso implica procesos distintos escalando horizontalmente; aca es un solo consumidor secuencial de una cola en memoria, preservando el orden que el detector stateful necesita). | PASS |
| II. Deteccion Barata, Diagnostico con Contexto | La banda muerta y el contador de lecturas consecutivas (H3) son comparaciones aritmeticas en memoria, no consultas nuevas. La persistencia del cooldown (H4) se lee una sola vez al arrancar el proceso (`Detector.__init__`) y se escribe solo cuando el estado cambia — no hay una consulta a SQLite por cada lectura MQTT, igual que ya exige este principio para los umbrales. | PASS |
| III. Un Cerebro, Muchos Consumidores | No aplica cambio — esta spec no toca quien llama a la API de Claude ni agrega un segundo camino cognitivo. El lock de H6 serializa pedidos concurrentes al mismo `diagnosticar_bajo_demanda`, no agrega una fuente nueva de diagnostico. | PASS |
| IV. Seguridad por Niveles en Canales de Entrada | Es el principio que mas se toca: el broker pasa de anonimo a autenticado (FR-009), el endpoint pasa de sin auth a requerir token (FR-010), y el manejo de las credenciales nuevas (password de Mosquitto, token del endpoint, password de Grafana) sigue el mismo patron ya establecido por D8: `.env` local + `.gitignore`, sin vault ni Docker secrets todavia — la decision de secretos de produccion sigue diferida (D8, FR-017, "Fuera de alcance" de la spec). No se agrega ningun canal de entrada nuevo (Telegram sigue en Nivel 0). | PASS (con nota: FR-017 no resuelve produccion, ver Complexity Tracking) |
| V. Documentacion y Decisiones Trazables | Spec, D19, D20 y este plan en espanol sin tildes, registrados en `memory/decisions.md` antes/junto con el codigo. | PASS |

Sin violaciones que requieran justificacion mas alla de la nota de la fila IV (ya cubierta
por D8/D20, no es una violacion nueva).

## Diseno tecnico por hallazgo

### H1 — Ingesta que no muere en silencio

`src/main.py`, `_al_recibir_mensaje` (o su equivalente dentro del worker tras H2): todo el
cuerpo de la funcion queda envuelto en un `try/except Exception` de ultimo recurso que loguea
con `logger.exception(...)` y retorna — nunca deja escapar la excepcion hacia
`_thread_main` de paho-mqtt (ver evidencia H1 del handoff). `GET /health` (`src/api.py`)
agrega un campo `ultima_lectura_en` (ISO 8601) leido de una variable compartida que el worker
actualiza despues de procesar cada lectura con exito (FR-002) — protegida por un lock simple
o, mas sencillo, por la atomicidad de la asignacion de una referencia en Python (un solo
escritor, el worker).

### H2 — Pipeline no bloqueante

`src/main.py`: se crea una `queue.Queue(maxsize=1000)` al arrancar. El callback MQTT
(`al_recibir_mensaje` que hoy le pasa `mqtt_client.py`) pasa a: normalizar el payload
(`normalizador.normalizar`, ya es rapido) y hacer `queue.put_nowait(lectura)`; si la cola esta
llena, descarta el item mas viejo (`queue.get_nowait()` seguido de un nuevo `put_nowait`) y
loguea un warning (Edge Case de backpressure). Un hilo worker (`threading.Thread(daemon=True)`,
arrancado junto al cliente MQTT) hace `queue.get()` en loop y ejecuta ahi todo lo que hoy
corre en el callback: escritura a InfluxDB, deteccion, y si corresponde, `_procesar_evento`
completo (incluido el camino de diagnostico/notificacion). El orden se preserva porque hay un
unico worker consumiendo la cola secuencialmente — el detector stateful sigue viendo el 100%
del stream en orden.

### H3 — Banda muerta y confirmacion por lecturas consecutivas

`src/deteccion/detector.py`: `Detector._estado` gana dos campos por clave (equipo,variable):
`lecturas_consecutivas` (contador, se resetea a 0 si una lectura no supera el umbral) y se
usa junto a la constante `CONFIRMACION_LECTURAS = 3` (D20) — un evento nuevo solo se genera
cuando el contador llega a ese valor. `_clasificar` no cambia (sigue comparando contra
`valor_alerta`/`valor_critico`); lo que cambia es la vuelta a NORMAL: en vez de
`valor < valor_alerta`, se compara contra `valor_alerta * (1 - 0.05)` (banda muerta del 5%,
D20) — mientras el valor este entre esa banda y el umbral, el estado NO vuelve a NORMAL. El
contador de lecturas consecutivas es efimero (no se persiste, a diferencia de la severidad y
el cooldown de H4) — perderlo en un reinicio como mucho retrasa unos segundos la proxima
confirmacion, no genera falsos negativos ni falsos positivos.

### H4 — Cooldown persistido + validacion de skew

`src/almacenamiento/sqlite_repo.py`: tabla nueva `detector_estado` (ver `data-model.md`).
`Detector.__init__` (o una funcion `main.py` que lo instancia) carga el contenido de esa
tabla en `self._estado` al arrancar. Cada vez que `evaluar()` cambia el estado de una clave
(nueva alerta, escalada, vuelta a NORMAL), hace un `INSERT OR REPLACE` en la misma
transaccion logica — no hay una escritura por cada lectura, solo por cada cambio de estado
(consistente con el Principio II). Validacion de skew: antes de usar el timestamp del
payload para calcular `cooldown_hasta`, se compara contra `datetime.now(timezone.utc)`; si la
diferencia absoluta supera 5 minutos (D20), se usa el reloj del servidor en su lugar y se
loguea un warning con ambos valores.

### H5 — Resumen fallido reintentable

`src/almacenamiento/sqlite_repo.py`, `crear_diagnostico`: pasa de `INSERT` a
`INSERT ... ON CONFLICT(alerta_id) DO UPDATE SET ...` (SQLite soporta `ON CONFLICT` con la
sintaxis `UPSERT` desde 3.24, ya disponible en la imagen Python usada). `src/main.py`,
`diagnosticar_bajo_demanda`: el chequeo de cache (`sqlite_repo.obtener_diagnostico`) pasa a
tratar como "cacheado" solo un registro con `fallo=0` — un registro con `fallo=1` dispara el
mismo camino que si no existiera ninguno (reintento real contra la API).

### H6 — Race condition del endpoint

`src/main.py`: un `threading.Lock()` a nivel modulo, adquirido al principio de
`diagnosticar_bajo_demanda` y liberado al final (con `try/finally`). Dado el volumen (un
operador humano pidiendo diagnosticos, no trafico alto), un lock global unico es
suficientemente granular — no hace falta un lock por `alerta_id`. El segundo pedido
concurrente espera a que el primero termine y despues encuentra el resultado ya cacheado
(camino normal de idempotencia de D13), en vez de pasar el chequeo de cache antes de que el
primero escriba.

### H7 — Superficie de seguridad

- **Broker (`mosquitto/mosquitto.conf`)**: `allow_anonymous false`, `password_file
  /mosquitto/config/passwd`, `acl_file /mosquitto/config/acl.conf`. El archivo `passwd` se
  genera una vez con `mosquitto_passwd -c` (no se commitea en texto plano — hash bcrypt, pero
  igual queda fuera de git por prudencia, mismo criterio que `.env`). ACL minima: el usuario
  del RUT956/emulador con `topic write demo/planta1/linea_a/motor_001/#`; el usuario del
  `servicio` con `topic read demo/planta1/linea_a/motor_001/#`. `src/config.py` gana
  `MQTT_USERNAME`/`MQTT_PASSWORD`; `src/ingesta/mqtt_client.py` llama
  `client.username_pw_set(...)` antes de conectar. `herramientas/emulador_motor.py` hace lo
  mismo. TLS queda fuera de esta spec (D20).
- **Endpoint (`src/api.py`)**: nueva env var `API_TOKEN`. `do_POST` valida un header
  (`X-API-Token`) contra ese valor antes de llamar a `servicio.diagnosticar_bajo_demanda`;
  si no coincide, responde 401 sin ejecutar nada. `do_GET /health` no cambia (sin auth).
- **Puertos (`docker-compose.yml`)**: `servicio` pasa de `"8000:8000"` a
  `"127.0.0.1:8000:8000"`; `influxdb` pasa de `"8086:8086"` a `"127.0.0.1:8086:8086"`.
  `broker` (1883) y `grafana` (3000) no cambian su mapeo.
- **Grafana**: se saca el fallback `:-admin` de `GF_SECURITY_ADMIN_PASSWORD` — si
  `GRAFANA_ADMIN_PASSWORD` no esta seteada en `.env`, Grafana arranca con la variable vacia
  (falla visible en vez de un default inseguro silencioso). `.env.example` se actualiza con
  un placeholder que deja claro que hay que elegir un valor propio.
- **Rotacion de `ANTHROPIC_API_KEY`**: tarea operativa (consola de Anthropic + `.env`), no de
  codigo — se documenta como paso manual en `quickstart.md` y en `tasks.md`, no tiene test
  automatizado posible.

## Estructura del Proyecto

### Documentacion (este feature)

```text
specs/003-robustez-seguridad/
├── spec.md               # Especificacion (D19, D20 — sin NEEDS CLARIFICATION pendientes)
├── plan.md                # Este archivo
├── data-model.md           # Fase 1 (tabla detector_estado)
├── quickstart.md           # Fase 1 (escenarios de validacion manual + rotacion de API key)
└── tasks.md                # Fase 2 (/speckit-tasks, no generado por este comando)
```

No hace falta `research.md`: a diferencia del feature 002 (que dependia de verificar
empiricamente el schema de un plugin de terceros), esta spec no tiene incognitas tecnicas
pendientes — D20 ya resolvio las 9 `NEEDS CLARIFICATION` con valores concretos.

### Codigo fuente (raiz del repositorio) — archivos existentes que se tocan

```text
src/config.py                        # + MQTT_USERNAME, MQTT_PASSWORD, API_TOKEN

src/ingesta/
└── mqtt_client.py                   # + client.username_pw_set(...)

src/deteccion/
└── detector.py                      # + banda muerta (5%), + confirmacion 3 lecturas
                                      # consecutivas, + carga/guardado de estado persistido

src/almacenamiento/
├── sqlite_repo.py                   # + tabla detector_estado, + funciones de
                                      # cargar/guardar estado, crear_diagnostico -> UPSERT
└── (influx_repo.py sin cambios)

src/api.py                           # + validacion de API_TOKEN en do_POST,
                                      # /health + ultima_lectura_en

src/main.py                          # + queue.Queue + worker thread (H2), + try/except
                                      # de ultimo recurso (H1), + lock para
                                      # diagnosticar_bajo_demanda (H6)

herramientas/emulador_motor.py       # + client.username_pw_set(...) (mismas credenciales
                                      # que servicio, para seguir probando local)

mosquitto/
├── mosquitto.conf                   # allow_anonymous false, + password_file, + acl_file
├── passwd                           # NUEVO — generado con mosquitto_passwd (no texto plano)
└── acl.conf                         # NUEVO — ACL minima por topico

docker-compose.yml                   # servicio: puerto 8000 -> 127.0.0.1; influxdb: puerto
                                      # 8086 -> 127.0.0.1; grafana: saca default inseguro de
                                      # GF_SECURITY_ADMIN_PASSWORD

.env.example                         # + MQTT_USERNAME/PASSWORD, API_TOKEN, placeholder de
                                      # GRAFANA_ADMIN_PASSWORD sin default inseguro

tests/unit/test_detector.py          # + tests de banda muerta, lecturas consecutivas,
                                      # persistencia de estado, skew
tests/unit/test_sqlite_repo.py       # + tests de detector_estado y UPSERT de diagnostico
tests/integration/                   # + test de ingesta sobreviviendo a InfluxDB caido (H1),
                                      # + test de que una lectura no espera al worker (H2),
                                      # + test de reintento tras fallo (H5),
                                      # + test de pedido concurrente sin doble llamada (H6)
tests/contract/test_notificacion_telegram.py  # sin cambios de contrato
```

No se crean modulos nuevos bajo `src/` ni contenedores nuevos en `docker-compose.yml` — todo
el trabajo es extension de lo existente, consistente con el Principio I (excepcion de fase
MVP).

**Decision de estructura**: extension minima de lo existente, mismo criterio que el feature
002 — se lista el set concreto de archivos tocados en vez del arbol generico del template.

## Complexity Tracking

*Vacio a proposito — el Constitution Check no encontro violaciones que requieran
justificacion mas alla de la nota ya cubierta por D8/D20 en la fila del Principio IV.*
