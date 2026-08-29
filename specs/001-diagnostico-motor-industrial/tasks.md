---

description: "Task list para 001-diagnostico-motor-industrial"
---

# Tasks: Monitoreo de Motor Industrial con Diagnostico Inteligente via Claude

**Input**: documentos de diseno en `specs/001-diagnostico-motor-industrial/`
(`plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)

**Tests**: incluidos. `plan.md` compromete pytest con foco en tests de contrato e
integracion que reproducen los 4 escenarios A-D — no es TDD estricto pedido por Joelo, pero
son parte del alcance tecnico ya decidido, no un agregado opcional de este comando.

**Organizacion**: tareas agrupadas por historia de usuario, en el alcance que `plan.md` fijo
para este MVP (D9). **Historia 3 (reporte diario) y la mitad de Historia 2 que depende de
correo (FR-007, FR-008) NO tienen tareas aca** — quedaron fuera de alcance de `plan.md` por
el conflicto spec-vs-D9 ya documentado y confirmado por Joelo como diferido intencional.

## Formato: `[ID] [P?] [Story] Descripcion`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: a que historia de usuario pertenece (US1, US2, US4 — no hay US3 en este plan)
- Cada tarea incluye la ruta de archivo exacta, segun la estructura de `plan.md`

---

## Fase 1: Setup

**Proposito**: inicializacion del proyecto, sin logica de negocio todavia.

- [X] T001 Crear la estructura de carpetas del proyecto (`src/ingesta/`, `src/deteccion/`,
      `src/diagnostico/`, `src/notificacion/`, `src/almacenamiento/`, `herramientas/`,
      `tests/contract/`, `tests/integration/`, `tests/unit/`) segun `plan.md`
- [X] T002 Crear `requirements.txt` con `paho-mqtt`, `anthropic`, `influxdb-client`, `httpx`,
      `pytest` (ver `research.md`) e instrucciones de entorno virtual en `README.md`
- [X] T003 [P] Crear `.env.example` (`ANTHROPIC_API_KEY`, `MODEL`, `TELEGRAM_BOT_TOKEN`,
      `TELEGRAM_CHAT_ID`, `INFLUX_URL`, `INFLUX_TOKEN`, `COOLDOWN_MINUTOS`) y confirmar que
      `.env` esta en `.gitignore` (D8)
- [X] T004 [P] Crear `docker-compose.yml` con los servicios `broker` (Mosquitto),
      `influxdb` y el servicio Python (build local, sin `grafana` todavia — se agrega en
      Fase 5) segun `research.md` (Mosquitto elegido sobre EMQX para el MVP)
- [X] T005 [P] Crear `Dockerfile` para el servicio Python con entrypoint `src/main.py`

**Checkpoint**: estructura y entorno listos, sin logica de negocio aun.

---

## Fase 2: Foundational (bloqueante para todas las historias)

**Proposito**: infraestructura compartida que todas las historias necesitan.

**⚠️ CRITICO**: ninguna historia de usuario arranca hasta que esta fase este completa.

- [X] T006 Implementar creacion de esquema SQLite (`Equipo`, `Umbral`, `Alerta`,
      `Diagnostico` segun `data-model.md`) en `src/almacenamiento/sqlite_repo.py`
- [X] T007 [P] Implementar setup de bucket/measurement `lecturas_motor` en InfluxDB en
      `src/almacenamiento/influx_repo.py` (`data-model.md`)
- [X] T008 [P] Implementar conexion y suscripcion MQTT (topico
      `demo/planta1/linea_a/motor_001/{variable}`) en `src/ingesta/mqtt_client.py`
      (`contracts/mqtt-topico.md`)
- [X] T009 Implementar validacion/normalizacion del payload MQTT (descartar payloads
      invalidos sin tumbar la suscripcion) en `src/ingesta/normalizador.py`
      (depende de T008)
- [X] T010 Cargar los valores iniciales de `Umbral` (temperatura 75/90°C, corriente 22/26A,
      vibracion 4.5/7.1mm/s — `data-model.md`) en `src/almacenamiento/sqlite_repo.py`
      (depende de T006)
- [X] T011 [P] Implementar carga de configuracion desde `.env` en `src/config.py`
- [X] T012 [P] Implementar configuracion de logging en `src/main.py`
- [X] T013 [P] Construir `herramientas/emulador_motor.py` con los 4 escenarios A-D de
      `definicion/caso_de_uso_fase1.md`, publicando segun `contracts/mqtt-topico.md`

**Checkpoint**: ingesta, almacenamiento y emulador listos — las historias de usuario pueden
empezar.

---

## Fase 3: Historia de Usuario 1 - Diagnostico accionable ante una anomalia (Priority: P1) 🎯 MVP

**Goal**: ante un cruce de umbral, generar un diagnostico en lenguaje natural (causa
probable, urgencia, accion, confianza) en vez de una alerta generica.

**Independent Test**: correr los 4 escenarios del emulador (`herramientas/emulador_motor.py`)
y verificar que el diagnostico generado sea coherente con la causa simulada, sin depender de
Telegram ni Grafana (`spec.md`, Historia 1).

### Tests para Historia 1

> **NOTA**: escribir y ver fallar antes de implementar, segun el compromiso de testing de
> `plan.md`.

- [X] T014 [P] [US1] Test de contrato del modulo de diagnostico (entrada/salida segun
      `contracts/diagnostico-modulo.md`) en `tests/contract/test_diagnostico_modulo.py`
- [X] T015 [P] [US1] Test de contrato del payload MQTT (`contracts/mqtt-topico.md`) en
      `tests/contract/test_mqtt_payload.py`
- [X] T016 [P] [US1] Test de integracion Escenario A - degradacion de refrigeracion
      (`quickstart.md` Escenario 1) en `tests/integration/test_escenario_a.py`
- [X] T017 [P] [US1] Test de integracion Escenario B - sobrecarga mecanica en
      `tests/integration/test_escenario_b.py`
- [X] T018 [P] [US1] Test de integracion Escenario C - falla de rodamiento incipiente en
      `tests/integration/test_escenario_c.py`
- [X] T019 [P] [US1] Test de integracion Escenario D - operacion normal, cero falsos
      positivos (`quickstart.md` Escenario 2, SC-005) en `tests/integration/test_escenario_d.py`

### Implementacion de Historia 1

- [X] T020 [P] [US1] Implementar carga de `Umbral` por tipo de equipo en
      `src/deteccion/umbrales.py`
- [X] T021 [US1] Implementar deteccion de cruce de umbral con histeresis/cooldown de 15 min
      (reinicio del cooldown si escala de ALERTA a CRITICO — `research.md`) en
      `src/deteccion/detector.py` (depende de T020)
- [X] T022 [US1] Implementar armado de contexto: tendencia 24h desde InfluxDB + alertas
      previas y metadata del equipo desde SQLite en `src/diagnostico/context.py` (depende de
      T006, T007)
- [X] T023 [P] [US1] Implementar el prompt versionado (system prompt + ejemplos few-shot con
      los 4 escenarios) en `src/diagnostico/prompt.py`
- [X] T024 [US1] Implementar la llamada a Claude (Haiku 4.5, prompt caching, timeout) y el
      parseo de la respuesta estructurada, con manejo de fallo (FR-013: no lanzar excepcion,
      devolver resultado marcado `fallo: true`) en `src/diagnostico/parser.py` (depende de
      T023)
- [X] T025 [US1] Implementar persistencia de `Alerta` y `Diagnostico` en
      `src/almacenamiento/sqlite_repo.py` (depende de T006)
- [X] T026 [US1] Orquestar el pipeline completo (ingesta → deteccion → contexto →
      diagnostico → persistencia) en `src/main.py` (depende de T009, T021, T022, T024, T025)

**Checkpoint**: Historia 1 funcional e independientemente testeable (validar con
`quickstart.md` Escenarios 1 y 2).

---

## Fase 4: Historia de Usuario 2 - Notificacion inmediata por Telegram (Priority: P1)

**Goal**: el operador recibe el diagnostico por Telegram dentro de los 90 segundos del
evento. **Alcance reducido respecto a `spec.md`**: solo el canal Telegram (FR-006); el
respaldo por correo para diagnosticos criticos (FR-007) queda fuera de este plan (D9).

**Independent Test**: generar un diagnostico de prueba y verificar que llega al chat de
Telegram configurado (`quickstart.md` Escenario 3).

### Tests para Historia 2

- [X] T027 [P] [US2] Test de contrato del formato de mensaje Telegram
      (`contracts/notificacion-telegram.md`) en `tests/contract/test_notificacion_telegram.py`
- [X] T028 [P] [US2] Test de integracion de notificacion, incluyendo el mensaje de fallback
      cuando el diagnostico fallo (`quickstart.md` Escenarios 3 y 5) en
      `tests/integration/test_notificacion.py`

### Implementacion de Historia 2

- [X] T029 [US2] Implementar cliente Telegram (envio via Bot API con `httpx`, reintentos con
      backoff simple) y el formato de mensaje (exitoso y fallback "diagnostico no
      disponible") en `src/notificacion/telegram.py`
- [X] T030 [US2] Integrar el envio de notificacion en `src/main.py` inmediatamente despues
      de persistir el `Diagnostico` (depende de T026, T029)

**Checkpoint**: Historias 1 y 2 funcionan juntas (validar `quickstart.md` Escenario 3).

---

## Fase 5: Historia de Usuario 4 - Visualizacion en tiempo real (Priority: P3)

**Goal**: dashboard en vivo de temperatura/corriente/vibracion con anotaciones en los
puntos donde ocurrieron alertas.

**Independent Test**: apuntar el dashboard a datos historicos ya cargados en InfluxDB, sin
depender de que las demas historias esten corriendo en ese momento (`spec.md`, Historia 4).

- [X] T031 [P] [US4] Provisionar el datasource de InfluxDB como codigo en
      `grafana/provisioning/datasources/influxdb.yml`
- [X] T032 [P] [US4] Crear el dashboard (temperatura, corriente, vibracion + anotaciones
      sobre `Alerta`) como JSON versionado en `grafana/provisioning/dashboards/motor.json`
      (`research.md`: Grafana como codigo, no configurado a mano). Las anotaciones se arman
      desde un espejo liviano de `Alerta` escrito en InfluxDB (measurement `alertas`,
      `src/almacenamiento/influx_repo.py::escribir_evento_alerta`, best-effort) ya que
      Grafana no tiene plugin de SQLite por defecto.
- [X] T033 [US4] Agregar el servicio `grafana` (con los volumes de provisioning) a
      `docker-compose.yml` (depende de T031, T032, T004). De paso se corrigio `servicio`
      para que `MQTT_HOST`/`INFLUX_URL` apunten a los hostnames de la red de Docker
      (`broker`/`influxdb`) en vez de los valores de `.env` pensados para desarrollo local
      fuera de Docker.

**Checkpoint**: las 3 historias en alcance de este plan (US1, US2, US4) funcionan juntas.

---

## Fase Final: Polish y Validacion

**Proposito**: cierre de calidad que cruza todas las historias.

- [X] T034 [P] Tests unitarios del detector/histeresis en `tests/unit/test_detector.py`
- [X] T035 [P] Tests unitarios del normalizador de payload en
      `tests/unit/test_normalizador.py`
- [X] T036 [P] Documentar variables de entorno y pasos de arranque en `README.md`
      (referenciando `quickstart.md`)
- [ ] T037 Ejecutar de punta a punta los 6 escenarios de `quickstart.md` — **NO ejecutado
      en esta sesion**: requiere Docker Desktop corriendo (no disponible en este entorno) y
      credenciales reales (`ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`/`CHAT_ID`). La suite de
      pytest (31 tests) valida la logica equivalente a los Escenarios 1, 2, 3, 4(D) y 5
      mockeando Claude/Telegram; el Escenario 6 (Grafana en vivo) no tiene equivalente
      automatizado. Pendiente que Joelo lo corra manualmente siguiendo `quickstart.md`.
- [X] T038 Revisar que no haya secretos commiteados (`.env` efectivamente ignorado por git —
      D8, riesgo de secretos en `memory/risks.md`) — verificado: `.env` no esta trackeado
      (`git ls-files` no lo lista) y `.gitignore` cubre `.env`, `.env.*` y `data/`

---

## Dependencias y Orden de Ejecucion

### Dependencias de fase

- **Setup (Fase 1)**: sin dependencias, arranca de inmediato
- **Foundational (Fase 2)**: depende de Setup — BLOQUEA todas las historias
- **Historia 1 (Fase 3)**: depende de Foundational; es la unica historia sin la cual no hay
  MVP (`spec.md`)
- **Historia 2 (Fase 4)**: depende de Foundational y del `Diagnostico` que genera Historia 1
  (T026) — no es independiente de datos, pero si de implementacion (se puede escribir el
  cliente Telegram en paralelo, integrarlo requiere que T026 exista)
- **Historia 4 (Fase 5)**: depende de Foundational (datos en InfluxDB) y de que Historia 1
  genere `Alerta` para las anotaciones — el trabajo de provisioning (T031, T032) puede
  arrancar en paralelo con la Fase 3
- **Polish (Fase Final)**: depende de que las historias que se vayan a incluir esten
  completas

### Oportunidades de paralelismo

- T003, T004, T005 (Setup) en paralelo
- T007, T008, T011, T012, T013 (Foundational) en paralelo entre si (T009 y T010 dependen de
  T008 y T006 respectivamente)
- Los tests de Historia 1 (T014-T019) en paralelo entre si, antes de la implementacion
- T020 y T023 (Historia 1) en paralelo; T021 depende de T020, T024 depende de T023
- T027 y T028 (Historia 2) en paralelo
- T031 y T032 (Historia 4) en paralelo, y toda la Fase 5 puede correr en paralelo con la
  Fase 3/4 si hay capacidad, porque solo depende de Foundational + los `Alerta` que ya vaya
  generando Historia 1

---

## Ejemplo de Paralelismo: Historia 1

```bash
# Tests de Historia 1 en paralelo:
Task: "Test de contrato del modulo de diagnostico en tests/contract/test_diagnostico_modulo.py"
Task: "Test de contrato del payload MQTT en tests/contract/test_mqtt_payload.py"
Task: "Test de integracion Escenario A en tests/integration/test_escenario_a.py"
Task: "Test de integracion Escenario B en tests/integration/test_escenario_b.py"
Task: "Test de integracion Escenario C en tests/integration/test_escenario_c.py"
Task: "Test de integracion Escenario D en tests/integration/test_escenario_d.py"

# Implementacion de Historia 1 en paralelo (antes de integrar):
Task: "Carga de Umbral en src/deteccion/umbrales.py"
Task: "Prompt versionado en src/diagnostico/prompt.py"
```

---

## Estrategia de Implementacion

### MVP minimo (solo Historia 1)

1. Completar Fase 1 (Setup) y Fase 2 (Foundational)
2. Completar Fase 3 (Historia 1)
3. **PARAR Y VALIDAR**: correr `quickstart.md` Escenarios 1 y 2 de forma independiente
4. Con esto ya se demuestra el diferencial central del proyecto (diagnostico accionable) sin
   depender de notificacion ni dashboard

### Entrega incremental

1. Setup + Foundational → base lista
2. Historia 1 → validar independientemente → esto ya es demostrable
3. Historia 2 → validar independientemente → ahora el diagnostico llega solo, sin mirar logs
4. Historia 4 → validar independientemente → dashboard visual sumado

### Fuera de esta lista de tareas

Historia 3 (reporte diario por correo) y el respaldo por correo de Historia 2 (FR-007,
FR-008) no tienen tareas — decision de alcance de `plan.md`, confirmada por Joelo como
diferida intencionalmente. Se generan tareas nuevas para esto cuando se retome esa
decision, no hace falta re-correr `/speckit-tasks` completo.
