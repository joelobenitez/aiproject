---

description: "Task list para 003-robustez-seguridad"

---

# Tasks: Robustez y seguridad del servicio de deteccion

**Input**: documentos de diseno en `specs/003-robustez-seguridad/`
(`plan.md`, `spec.md`, `data-model.md`, `quickstart.md`)

**Tests**: incluidos — a diferencia del feature 002, esta spec toca logica de dominio real
(deteccion, persistencia, concurrencia), no solo configuracion/espejos de lectura. Cada
historia con codigo nuevo suma tests propios (unitarios donde el archivo ya tiene esa
costumbre — `test_detector.py`, `test_sqlite_repo.py` — de integracion donde el
comportamiento cruza el pipeline completo).

**Organizacion**: 6 historias de usuario, en el orden de prioridad de `spec.md` (P1: US1+US2;
P2: US3, US4, US5; P3: US6). **A diferencia del feature 002, aca SI hay acoplamiento real de
archivos entre historias** (ver `plan.md`): US1 y US2 tocan la misma reestructuracion de
`src/main.py` (cola + worker) y se implementan juntas; US6 depende de esa misma estructura
para el lock de concurrencia; US3 y US4 comparten `src/deteccion/detector.py`. Las
dependencias explicitas estan marcadas en cada tarea.

## Formato: `[ID] [P?] [Story] Descripcion`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: a que historia de usuario pertenece (US1-US6)
- **[manual]**: no es codigo — accion humana fuera de este repo (rotar una key, tocar la
  config del RUT956)
- Cada tarea incluye la ruta de archivo exacta, segun la estructura de `plan.md`

---

## Fase 1: Historias 1 y 2 - Ingesta resiliente + pipeline no bloqueante (Priority: P1) 🎯 MVP

**Goal**: ninguna excepcion puntual mata la ingesta (H1), y ninguna llamada lenta de IA
bloquea la recepcion de lecturas nuevas (H2).

**Independent Test**: `quickstart.md` Escenarios 1 y 2 — no dependen de las demas historias.

### Tests para Historia 1 y 2

- [x] T001 [P] [US1] Test de integracion: con `influx_repo.escribir_lectura` mockeado para
      lanzar una excepcion, publicar una lectura y confirmar que el proceso sigue vivo y
      procesa la lectura siguiente sin reiniciar — `tests/integration/test_robustez_ingesta.py`
      (nuevo)
- [x] T002 [P] [US2] Test de integracion: con el nucleo de IA mockeado con un delay
      artificial, publicar lecturas de otra variable durante esa ventana y confirmar que
      quedan registradas y evaluadas sin esperar — mismo archivo que T001

### Implementacion de Historia 1 y 2

- [x] T003 [US1] [US2] Crear `queue.Queue(maxsize=1000)` y un hilo worker
      (`threading.Thread(daemon=True)`) en `src/main.py`; el callback MQTT
      (`_al_recibir_mensaje`) pasa a solo normalizar el payload y encolarlo — el resto de la
      logica que hoy tiene (escritura InfluxDB, deteccion, `_procesar_evento`) se mueve al
      loop del worker. Implementa H2.
- [x] T004 [US1] Envolver el cuerpo del worker en un `try/except Exception` de ultimo
      recurso (`logger.exception(...)`, sin relanzar) — el worker nunca debe terminar por una
      excepcion de una lectura puntual. Implementa H1. (depende de T003)
- [x] T005 [US1] Variable compartida `ultima_lectura_en` (ISO 8601), actualizada por el
      worker despues de procesar cada lectura con exito; exponerla en `GET /health`
      (`src/api.py`) — FR-002. (depende de T003)
- [x] T006 [US2] Manejo de backpressure: si `queue.put_nowait` lanza `queue.Full`, descartar
      el item mas viejo (`get_nowait`) y loguear un warning antes de reintentar el `put` —
      Edge Case de `spec.md`. (depende de T003)
- [x] T007 [US1] [US2] Validar `quickstart.md` Escenarios 1 y 2 contra el stack real.
      (depende de T004, T005, T006) — Escenario 1 validado en vivo contra Docker real
      (`docker compose stop/start influxdb` + emulador; ver hallazgo D21). Escenario 2
      validado via el test de integracion T002 (Queue real + delay simulado, mismo patron que
      ya usan los tests existentes, `plan.md`) — no se disparo una llamada real a Claude para
      no gastar API en esta validacion.

**Checkpoint**: ingesta resiliente y no bloqueante, demostrable independientemente del resto
de las historias.

---

## Fase 2: Historia 3 - El ruido del sensor no genera alertas de mas (Priority: P2)

**Goal**: banda muerta para volver a NORMAL + confirmacion por lecturas consecutivas antes
de generar un evento nuevo.

**Independent Test**: `quickstart.md` Escenario 3 — no depende de las demas historias
(usa el `Detector` en memoria, sin persistencia todavia).

- [x] T008 [P] [US3] Tests unitarios en `tests/unit/test_detector.py`: una lectura aislada
      por encima del umbral no genera evento; 3 lecturas consecutivas si; el estado no
      vuelve a NORMAL mientras el valor este dentro de la banda muerta del 5%. (se
      reescribieron ademas los tests existentes que asumian alerta inmediata de una sola
      lectura — ya no es el comportamiento vigente, ver D20/FR-004)
- [x] T009 [US3] Agregar `lecturas_consecutivas` a `Detector._estado` y la constante
      `CONFIRMACION_LECTURAS = 3` (D20) — un evento nuevo solo se genera cuando el contador
      llega a ese valor; se resetea a 0 si una lectura no supera el umbral —
      `src/deteccion/detector.py`.
- [x] T010 [US3] Cambiar la condicion de vuelta a `NORMAL`: de `valor < valor_alerta` a
      `valor < valor_alerta * 0.95` (banda muerta del 5%, D20) — `src/deteccion/detector.py`.
      (depende de T009, mismo bloque de codigo)
- [x] T011 [US3] Validar `quickstart.md` Escenario 3 (escenario D del emulador sin alertas,
      escenario A con exactamente 1 alerta). (depende de T009, T010) — validado con 3
      semillas distintas del escenario D (0 alertas cada vez) + escenario A (exactamente 1
      alerta, severidad ALERTA). Nota de diseno no anticipada en `plan.md`: una escalada
      (ALERTA -> CRITICO) dispara de inmediato sin esperar 3 lecturas nuevas, porque el
      contador de confirmacion sigue vivo mientras el equipo no vuelve a NORMAL — evita
      retrasar una escalada real y mantiene verde el test existente de escalada.

**Checkpoint**: deteccion filtra ruido, independiente del resto.

---

## Fase 3: Historia 4 - El cooldown sobrevive al reinicio y no depende del reloj del sensor (Priority: P2)

**Goal**: el estado del detector (severidad + cooldown) persiste en SQLite, y una lectura
con el reloj desfasado no silencia el equipo indefinidamente.

**Independent Test**: `quickstart.md` Escenario 4 — depende de que Historia 3 ya haya
definido la forma de `Detector._estado` (T009), pero no de Historia 1/2/5/6.

- [x] T012 [P] [US4] Test unitario: instanciar un `Detector`, generar una alerta, crear un
      `Detector` nuevo compartiendo el mismo `data/aiproject.db` y confirmar que hereda el
      cooldown del primero — `tests/unit/test_detector.py`.
- [x] T013 [P] [US4] Test unitario de skew: una lectura con timestamp adelantado mas de 5
      minutos se evalua igual (no se descarta) usando el reloj del servidor para el
      cooldown, y queda un warning logueado — `tests/unit/test_detector.py`.
- [x] T014 [US4] Tabla `detector_estado` en `src/almacenamiento/sqlite_repo.py` (schema de
      `data-model.md`) + funciones `cargar_estado_detector()` / `guardar_estado_detector(...)`.
- [x] T015 [US4] El punto donde `src/main.py` instancia `Detector` pasa a cargar el estado
      inicial desde `cargar_estado_detector()`; cada cambio de estado dentro de `evaluar()`
      llama a `guardar_estado_detector(...)` — `src/deteccion/detector.py`,
      `src/almacenamiento/sqlite_repo.py`. (depende de T009, T014) — se instancia dentro de
      `Detector.__init__` (carga) y `Detector._actualizar_estado` (graba solo si cambia
      severidad/cooldown). `src/main.py` movio la creacion del `_detector` singleton de
      import-time a `main()`, despues de `inicializar_schema()` (ver nota de riesgo abajo).
- [x] T016 [US4] Validacion de skew: comparar el timestamp del payload contra
      `datetime.now(timezone.utc)`; si la diferencia absoluta supera 5 minutos (D20), usar el
      reloj del servidor para el calculo de `cooldown_hasta` y loguear un warning con ambos
      valores — `src/deteccion/detector.py`.
- [x] T017 [US4] Validar `quickstart.md` Escenario 4 (cooldown sobrevive a
      `docker compose restart servicio`; timestamp adelantado no silencia el equipo).
      (depende de T015, T016) — validado en vivo: alerta real generada con escenario A,
      `docker compose restart servicio`, `detector_estado` confirmado intacto post-restart
      (cooldown_hasta sin cambios); lectura con timestamp +3h logueo el warning de skew y
      calculo `cooldown_hasta` a partir del reloj del servidor (verificado con match exacto
      de segundos), no del timestamp adelantado.

**Nota de riesgo no anticipada en `plan.md`:** `Detector.__init__` ahora lee SQLite
(`cargar_estado_detector`), asi que ya no puede vivir a nivel de modulo en `src/main.py`
(se creaba en el import, antes de `inicializar_schema()` — hubiera fallado o cargado un
estado inconsistente). Se movio a `main()`. Para que los tests de integracion (que nunca
llaman a `main()`) sigan teniendo un `_detector` valido y aislado por test, el fixture
`entorno_aislado` ahora vive en `tests/conftest.py` (antes en `tests/integration/conftest.py`,
invisible para `tests/unit/`) y reconstruye `servicio._detector` despues de inicializar el
schema de la DB temporal — de paso corrige un problema de aislamiento preexistente (el
`_detector` era un singleton compartido entre tests de todo el proceso de pytest).

**Checkpoint**: cooldown persistente, independiente de Historia 1/2/5/6.

---

## Fase 4: Historia 5 - Nadie sin credenciales inyecta datos ni gasta la API (Priority: P2)

**Goal**: broker MQTT autenticado, endpoint con token, puertos innecesarios atados a
`127.0.0.1`, password de Grafana sin default inseguro, `ANTHROPIC_API_KEY` rotada.

**Independent Test**: `quickstart.md` Escenario 5 — independiente en codigo del resto de las
historias (toca config/infra, no la logica de deteccion/persistencia).

- [ ] T018 [P] [US5] Agregar `MQTT_USERNAME`, `MQTT_PASSWORD`, `API_TOKEN` a
      `src/config.py`, con placeholders nuevos en `.env.example`.
- [ ] T019 [P] [US5] Generar `mosquitto/passwd` (`mosquitto_passwd -c`, hash — no texto
      plano) y `mosquitto/acl.conf` (credencial del RUT956/emulador: `write` en
      `demo/planta1/linea_a/motor_001/#`; credencial del `servicio`: `read` en el mismo
      namespace); actualizar `mosquitto/mosquitto.conf` (`allow_anonymous false`,
      `password_file`, `acl_file`).
- [ ] T020 [US5] `src/ingesta/mqtt_client.py`: `client.username_pw_set(...)` antes de
      conectar, usando `config.MQTT_USERNAME`/`MQTT_PASSWORD`. (depende de T018, T019)
- [ ] T021 [P] [US5] `herramientas/emulador_motor.py`: mismo `username_pw_set` para seguir
      probando localmente contra el broker autenticado. (depende de T018, T019)
- [ ] T022 [US5] `src/api.py`: `do_POST` valida un header (`X-API-Token`) contra
      `config.API_TOKEN` antes de llamar a `diagnosticar_bajo_demanda`; responde 401 si
      falta o no coincide. `GET /health` no cambia. (depende de T018)
- [ ] T023 [US5] `docker-compose.yml`: `servicio` pasa de `"8000:8000"` a
      `"127.0.0.1:8000:8000"`; `influxdb` de `"8086:8086"` a `"127.0.0.1:8086:8086"`; sacar
      el fallback `:-admin` de `GF_SECURITY_ADMIN_PASSWORD`.
- [ ] T024 [US5] [manual] Rotar `ANTHROPIC_API_KEY` en `console.anthropic.com` (pendiente
      desde el 2026-09-01, ver `memory/progress.md`); actualizar `.env`.
- [ ] T025 [US5] [manual] Actualizar la coleccion "Data to Server" del RUT956 (D18) con las
      credenciales MQTT nuevas de T019 — sin este paso el router deja de poder publicar en
      cuanto el broker deje de aceptar conexiones anonimas.
- [ ] T026 [US5] Validar `quickstart.md` Escenario 5 completo (broker rechaza sin
      credenciales, endpoint responde 401 sin token, puertos confirmados en `127.0.0.1`,
      key vieja revocada). (depende de T020-T025)

**Checkpoint**: superficie de seguridad cerrada. Los pasos T024/T025 son manuales — no hay
test automatizado posible para "la key vieja fue revocada" ni para "el RUT956 tiene las
credenciales nuevas".

---

## Fase 5: Historia 6 - Un resumen que fallo se puede volver a pedir (Priority: P3)

**Goal**: reintentar un diagnostico fallido sin tocar la base a mano; dos pedidos
simultaneos de la misma alerta generan una sola llamada a Claude.

**Independent Test**: `quickstart.md` Escenario 6 — depende de la estructura de `main.py` de
la Fase 1 (T003), pero no de Historia 3/4/5.

- [ ] T027 [P] [US6] Test de integracion: forzar un fallo del nucleo de IA (mock), pedir el
      mismo `alerta_id` de nuevo, confirmar que reintenta y sobrescribe con un resultado
      exitoso — `tests/integration/test_diagnostico_bajo_demanda.py`.
- [ ] T028 [P] [US6] Test de concurrencia: dos hilos llamando `diagnosticar_bajo_demanda`
      para la misma alerta al mismo tiempo (con la llamada a Claude mockeada), confirmar una
      sola invocacion del mock y ninguna excepcion sin capturar — mismo archivo que T027.
- [ ] T029 [US6] `crear_diagnostico` en `src/almacenamiento/sqlite_repo.py` pasa de `INSERT`
      a `INSERT ... ON CONFLICT(alerta_id) DO UPDATE SET ...` (ver `data-model.md`).
- [ ] T030 [US6] `diagnosticar_bajo_demanda` en `src/main.py`: el chequeo de cache solo
      trata como "cacheado" un registro con `fallo = 0`; envolver el bloque
      check-cache/llamar-a-Claude/persistir en un `threading.Lock()` a nivel modulo
      (`try/finally`). (depende de T029, y de la estructura de `main.py` de T003)
- [ ] T031 [US6] Validar `quickstart.md` Escenario 6 (reintento exitoso, doble pedido
      concurrente sin doble llamada). (depende de T029, T030)

**Checkpoint**: el endpoint bajo demanda es robusto a fallos transitorios y a concurrencia.

---

## Fase Final: Polish y Validacion

**Proposito**: cierre de calidad que cruza las 6 historias.

- [ ] T032 Correr la suite completa (`pytest`), confirmar 39/39 previos + todos los tests
      nuevos de T001, T002, T008, T012, T013, T027, T028 en verde (SC-007).
- [ ] T033 Confirmar por lectura de codigo (FR-014) que el contrato de topico MQTT (5
      partes, payload `{valor, unidad, timestamp}`), la ruta `POST /diagnosticar/<alerta_id>`
      y los nombres `diagnostico`/`diagnosticos` no cambiaron — solo se agrego el header de
      autenticacion.
- [ ] T034 Documentar en `README.md` las variables de entorno nuevas (`MQTT_USERNAME`,
      `MQTT_PASSWORD`, `API_TOKEN`) y el cambio de puertos publicados al host.
- [ ] T035 Registrar en `memory/risks.md` cualquier hallazgo nuevo del proceso de
      implementacion que no estuviera anticipado en `plan.md` (ej. detalles especificos de
      `mosquitto_passwd` en el entorno Windows de esta terminal).
- [ ] T036 Validar `quickstart.md` completo de punta a punta, incluido el escenario
      "Regresion — contratos que no cambian".
- [ ] T037 Confirmar que `data/aiproject.db` se borro y se recreo limpiamente con la tabla
      `detector_estado` nueva (FR-016) — en esta terminal y, si aplica, avisar que la
      terminal `joelo` va a necesitar el mismo paso al traer estos cambios.

---

## Dependencias y Orden de Ejecucion

### Entre historias

- **Historia 1+2 (Fase 1)** es la base estructural: introduce la cola/worker en
  `src/main.py` que **Historia 6 (Fase 5)** reutiliza para el lock de concurrencia. Hacerla
  primero.
- **Historia 3 (Fase 2)** y **Historia 4 (Fase 3)** comparten `src/deteccion/detector.py` —
  Historia 3 define la forma de `_estado` (con `lecturas_consecutivas`), Historia 4 la
  persiste tal cual. Hacer Historia 3 antes que Historia 4.
- **Historia 5 (Fase 4)** es independiente en codigo de las demas (config/infra, no logica
  de dominio) — se puede hacer en paralelo con cualquier otra, salvo que sus dos tareas
  manuales (T024, T025) conviene dejarlas para el final, cuando el resto ya este validado y
  no haga falta repetir la rotacion de credenciales por otro cambio.
- **Historia 6 (Fase 5)** depende de Historia 1+2 (misma zona de `main.py`).

### Orden sugerido

1. Fase 1 (Historia 1+2) — base estructural
2. Fase 2 (Historia 3) — independiente, se puede intercalar en paralelo con Fase 1 si hay
   mas de una persona
3. Fase 3 (Historia 4) — depende de Fase 2
4. Fase 4 (Historia 5) — independiente, dejar T024/T025 para el final
5. Fase 5 (Historia 6) — depende de Fase 1
6. Polish

### Oportunidades de paralelismo

- Los tests marcados `[P]` dentro de cada fase se pueden escribir antes o junto con la
  implementacion de esa misma fase (archivos de test distintos de los de codigo).
- Fase 2 (Historia 3) es independiente de Fase 1 y Fase 4 — se puede hacer en paralelo si
  hay mas de una persona trabajando.

---

## Estrategia de Implementacion

### MVP minimo (solo Fase 1)

1. Completar Fase 1 (T001-T007).
2. **PARAR Y VALIDAR**: `quickstart.md` Escenarios 1 y 2.
3. Ya resuelve el hallazgo mas critico (H1) y el segundo mas critico (H2) — el resto de las
   historias son mejoras incrementales sobre una base que ya no muere en silencio ni se
   bloquea.

### Entrega incremental

1. Fase 1 → validar → ingesta resiliente y no bloqueante, demostrable.
2. Fase 2 → validar → sin alertas por ruido.
3. Fase 3 → validar → cooldown persistente.
4. Fase 4 → validar → superficie de seguridad cerrada (salvo los dos pasos manuales).
5. Fase 5 → validar → resumen bajo demanda robusto.
6. Polish → cierre.

### Fuera de esta lista de tareas

Los items M1-M5 (menores) del handoff no tienen tareas propias — no forman parte del
alcance de D19. Separar detector/workers en procesos, Telegram Nivel 1+, RS485 real y
reemplazar SQLite quedan fuera (ver "Fuera de alcance" en `spec.md`).
