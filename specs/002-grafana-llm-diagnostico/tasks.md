---

description: "Task list para 002-grafana-llm-diagnostico"

---

# Tasks: Plugin LLM de Grafana + panel de diagnostico de IA

**Input**: documentos de diseno en `specs/002-grafana-llm-diagnostico/`
(`plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`)

**Tests**: incluidos, pero acotados — `plan.md` solo compromete un test unitario para la
funcion nueva de `influx_repo.py` (mismo nivel que ya tiene el resto del modulo, que hoy no
tiene tests dedicados para `escribir_evento_alerta`). El plugin/panel de Grafana no tiene
tests automatizados en este proyecto (ninguna parte de `grafana/provisioning/` los tiene
hoy) — se valida a mano contra `quickstart.md`.

**Organizacion**: dos historias de usuario (P1, P2 de `spec.md`), sin fase Foundational
separada — a diferencia del feature 001, US1 (plugin) y US2 (panel de diagnostico) no
comparten ninguna infraestructura nueva entre si: US1 toca `docker-compose.yml` +
`grafana/provisioning/plugins/`, US2 toca `src/almacenamiento/`, `src/main.py` y
`grafana/provisioning/dashboards/motor.json`. Se pueden implementar en cualquier orden o en
paralelo.

## Formato: `[ID] [P?] [Story] Descripcion`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: a que historia de usuario pertenece (US1, US2)
- Cada tarea incluye la ruta de archivo exacta, segun la estructura de `plan.md`

---

## Fase 1: Historia de Usuario 1 - Claude vivo dentro de Grafana (Priority: P1) 🎯 MVP

**Goal**: el plugin `grafana-llm-app` instalado y provisionado con el proveedor Anthropic,
demostrado con el boton nativo "Auto generate" (`dashgpt`).

**Independent Test**: `quickstart.md` Escenario 1 — no depende de que Historia 2 este
implementada.

- [X] T001 [US1] Verificar empiricamente el schema real de provisioning del proveedor
      Anthropic contra la version del plugin que se instale. **Hecho 2026-09-01**: contenedor
      descartable (`grafana/grafana:11.3.0` + `GF_INSTALL_PLUGINS=grafana-llm-app` sin pin),
      inspeccion del bundle instalado (`module.js`) via `docker exec`/`docker cp`/`grep`.
      Version instalada: `v1.0.8`. Schema confirmado y `dashgpt=true` por default en 11.3.0
      — ver detalle completo en `research.md`.
- [ ] T002 [US1] Agregar `GF_INSTALL_PLUGINS` (version pinneada segun lo confirmado en
      T001, no `:latest`) y `GF_FEATURE_TOGGLES_ENABLE: dashgpt` al `environment:` del
      servicio `grafana` en `docker-compose.yml` (depende de T001)
- [ ] T003 [US1] Crear `grafana/provisioning/plugins/apps.yaml` (carpeta nueva) con el
      proveedor Anthropic, usando los nombres de campo de T001 y `secureJsonData` referenciando
      `${ANTHROPIC_API_KEY}` — sin hardcodear el valor (FR-002 de `spec.md`) (depende de T001)
- [X] T004 [US1] Validar `quickstart.md` Escenario 1. **Hecho 2026-09-01 (parcial + bug
      real encontrado y arreglado)**: contra el stack real (`ANTHROPIC_API_KEY` real),
      `GET /api/plugins/grafana-llm-app/health` (mismo endpoint que renderiza Administration
      > Plugins > LLM) primero devolvio error 404 — modelo default del plugin descontinuado,
      ver `research.md` y el riesgo nuevo en `memory/risks.md`. Fix aplicado
      (`jsonData.models.mapping` en `apps.yaml`), reverificado: `"ok":true` para Base y
      Large, plugin habla con Claude real. **No hecho**: el click literal del boton "Auto
      generate" en la UI — la extension de Chrome no estaba conectada en esta sesion. La
      mecanica que ese boton dispara (completions reales via el proveedor Anthropic
      configurado) ya quedo probada de punta a punta por el chequeo de arriba; el click en
      si queda como verificacion visual pendiente, de bajo riesgo.

**Checkpoint**: Historia 1 funcional e independientemente demostrable.

---

## Fase 2: Historia de Usuario 2 - Ver el ultimo diagnostico en el dashboard (Priority: P2)

**Goal**: el dashboard `motor-001-mvp` muestra el ultimo diagnostico de IA que `src/` ya
genera (D13), sin ningun llamado nuevo a Claude desde Grafana.

**Independent Test**: `quickstart.md` Escenarios 2, 3 y 4 — no depende de que Historia 1
este implementada (el panel lee InfluxDB, no el plugin LLM).

### Tests para Historia 2

- [X] T005 [P] [US2] Test unitario de `escribir_diagnostico()` (mock del `write_api`, mismo
      patron que `tests/unit/test_detector.py`) en `tests/unit/test_influx_repo.py` — cubre
      el caso `fallo=True` (campos en blanco, `fallo=true` igual se escribe, ver
      `data-model.md`). **Hecho 2026-09-01**: 3 tests, los 3 en verde
      (`.venv/Scripts/python.exe -m pytest tests/unit/test_influx_repo.py`); suite completa
      39/39 en verde (36 previos + 3 nuevos), sin regresiones.

### Implementacion de Historia 2

- [X] T006 [US2] Implementar `escribir_diagnostico(equipo_id, alerta_id, resultado, fallo,
      timestamp=None)` en `src/almacenamiento/influx_repo.py`, measurement `diagnosticos`
      nuevo, best-effort (`try/except` que loguea, no relanza — mismo patron que
      `escribir_evento_alerta`) segun `contracts/diagnostico-influxdb.md`. **Hecho.**
- [X] T007 [US2] Integrar la llamada a `escribir_diagnostico()` en
      `src/main.py::_diagnosticar_y_notificar()`, junto a `sqlite_repo.crear_diagnostico()`
      (linea ~59) — cubre automaticamente los dos caminos que llegan a esa funcion
      (CRITICO automatico y ALERTA on-demand via D13) (depende de T006). **Hecho** (1 linea
      nueva).
- [X] T008 [P] [US2] Agregar el panel "Diagnostico IA" (Text o Table) a
      `grafana/provisioning/dashboards/motor.json`, con el query Flux de `data-model.md`
      (pivot + sort + limit 1 sobre el measurement `diagnosticos`) — MUST distinguir
      visualmente el caso `fallo=true` del caso exitoso (Edge Case de `spec.md`). **Hecho**:
      panel `table` (id 4), value mapping en el campo `fallo` (rojo/verde + texto), columnas
      renombradas y ordenadas via transformacion `organize`. JSON validado (`node -e
      "JSON.parse(...)"`).
- [X] T009 [US2] Validar `quickstart.md` Escenarios 2 (CRITICO automatico), 3 (ALERTA
      on-demand via D13) y 4 (estado vacio, FR-008) (depende de T007, T008). **Hecho
      2026-09-01, contra el stack real completo (`ANTHROPIC_API_KEY` real):**
      - Escenario 2: publicado un evento sintetico de temperatura CRITICO por MQTT (Alerta
        #6). Diagnostico real generado (Claude 200 OK), verificado el punto en InfluxDB con
        el query exacto del panel — `alerta_id=6`, los 5 campos poblados, `fallo=false`.
      - Escenario 3: publicado un evento de corriente ALERTA (Alerta #7, sin diagnostico
        automatico, confirmado por logs). Pedido `POST /diagnosticar/7` — diagnostico real
        generado, `cacheado:false`, verificado en InfluxDB como el mas reciente
        (`alerta_id=7`) via el query exacto del panel.
      - Escenario 4: query del panel contra un `equipo_id` inexistente — 0 filas, sin error
        (Grafana renderiza "No Data" nativamente, no hace falta logica extra).
      - **Bug real encontrado y arreglado en el camino** (no de este feature, sino
        introducido por T006/T007 en la suite de tests existente): `test_escenario_a/b/c.py`
        y `test_diagnostico_bajo_demanda.py` ya mockeaban `escribir_evento_alerta` pero no
        conocian la funcion nueva `escribir_diagnostico` — al correr la suite completa con
        el contenedor real de InfluxDB levantado (durante T004), esos tests escribieron un
        diagnostico de prueba real (`alerta_id=1`, textos "prueba") a la base real. Fix:
        agregado el mismo mock (`escribir_diagnostico`) en los 4 archivos. Verificado: suite
        completa 39/39 en verde sin tocar la InfluxDB real; los 2 puntos de contaminacion se
        borraron a mano (`influx delete`, rango acotado a su timestamp exacto).

**Checkpoint**: Historia 1 y 2 funcionan juntas — dashboard completo (curvas + anotaciones
de alerta ya existentes + diagnostico) mas el plugin LLM nativo probado.

---

## Fase Final: Polish y Validacion

**Proposito**: cierre de calidad que cruza las dos historias — en este feature, sobre todo
verificar que no se violo el Principio III (FR-006).

- [X] T010 Revisar el diff final del feature completo: confirmar que no aparece codigo
      TypeScript, ningun plugin/panel custom de Grafana, ni ninguna llamada HTTP nueva hacia
      `api.anthropic.com` fuera de `src/` (`quickstart.md` Escenario 5, SC-003). **Hecho**:
      `git diff --stat` (12 archivos, todos esperados: `docker-compose.yml`, `motor.json`,
      `influx_repo.py`, `main.py`, 4 tests, memory/) + `git status --short` (2 carpetas
      nuevas: `grafana/provisioning/plugins/`, `specs/`) — sin `.ts`/`.tsx`, sin plugin
      custom. `grep -r "anthropic" src/` confirma que solo `config.py` y
      `diagnostico/parser.py` (preexistentes) referencian Anthropic — cero call sites
      nuevos.
- [X] T011 Confirmar por lectura de codigo que `src/main.py::diagnosticar_bajo_demanda` y el
      endpoint `POST /diagnosticar/<alerta_id>` (D13) no cambiaron de firma ni de
      comportamiento (`quickstart.md` Escenario 6, SC-004 — regresion). **Hecho**:
      `git diff src/main.py` muestra una sola linea agregada (la llamada a
      `escribir_diagnostico`), fuera de `diagnosticar_bajo_demanda`; `src/api.py` no aparece
      en el diff (intacto). Reforzado por la prueba en vivo de T009 Escenario 3
      (`POST /diagnosticar/7` devolvio la misma forma de siempre: causa_probable, urgencia,
      accion_recomendada, confianza, fallo, cacheado).
- [X] T012 Si T001 revelo algo no anticipado en `research.md` (ej. el plugin requiere una
      variable de entorno adicional tipo `PluginAppClientSecret`, visto en el issue #369
      real durante la investigacion), documentarlo en `memory/risks.md`. **Hecho** durante
      T001/T004: `jsonData.disabled` no documentado y el modelo default roto ya estan en
      `memory/risks.md`. No aparecio `PluginAppClientSecret` en los logs reales (ese warning
      es de una feature distinta, LLM Gateway de Grafana Cloud, no usada aca).
- [X] T013 Documentar en `README.md` las variables de entorno nuevas (`GF_INSTALL_PLUGINS`
      ya pinneado, `GF_FEATURE_TOGGLES_ENABLE`) si `README.md` ya documenta las de
      `docker-compose.yml` (ver T036 del feature 001). **Hecho**: seccion nueva "Plugin LLM
      de Grafana (feature 002)" en `README.md`. De paso se corrigieron 3 referencias
      obsoletas a `specs/001-diagnostico-motor-industrial/` (deberian apuntar a
      `obs/specs/001-diagnostico-motor-industrial/` desde D14, nunca se habian actualizado)
      — bug preexistente encontrado al editar el mismo archivo, no parte del alcance
      original de este feature pero trivial de corregir de paso.

---

## Dependencias y Orden de Ejecucion

### Entre historias

- **Historia 1 (Fase 1)** y **Historia 2 (Fase 2)** son independientes entre si — se pueden
  hacer en cualquier orden, o en paralelo si hay dos personas.

### Dentro de Historia 1

- T001 bloquea a T002 y T003 (necesitan los nombres de campo confirmados)
- T004 depende de T002 y T003

### Dentro de Historia 2

- T006 bloquea a T007 (necesita la funcion para llamarla) y a T005 (necesita la funcion
  para testearla)
- T008 no depende de T006/T007 en terminos de escritura (el JSON del panel se puede
  escribir en paralelo), pero **validarlo** (T009) si depende de que T007 ya este generando
  datos reales

### Oportunidades de paralelismo

- T005 y T008 se pueden escribir en paralelo con T006/T007 (archivos distintos)
- Historia 1 completa se puede hacer en paralelo con Historia 2 completa

---

## Estrategia de Implementacion

### MVP minimo (solo Historia 1)

1. Completar Fase 1 (T001-T004)
2. **PARAR Y VALIDAR**: `quickstart.md` Escenario 1
3. Ya demuestra que Claude esta conectado nativamente dentro de Grafana OSS — valor
   independiente de si Historia 2 se hace o no.

### Entrega incremental

1. Historia 1 → validar independientemente → Claude vivo en Grafana, demostrable
2. Historia 2 → validar independientemente → diagnostico visible en el dashboard sin salir
   de Grafana

### Fuera de esta lista de tareas

El panel/plugin custom con resumen de datos en vivo (`@grafana/llm`, TypeScript/React) no
tiene tareas — descartado en D15 (`memory/decisions.md`), no es parte de este feature.
