# Investigacion — Fase 0

Feature: Plugin LLM de Grafana + panel de diagnostico de IA (`002-grafana-llm-diagnostico`)

La decision de alcance de fondo (que construir y que descartar) ya esta resuelta en D15
(`memory/decisions.md`), a partir de investigacion propia contra fuentes oficiales de
Grafana Labs durante la sesion que abrio este feature (2026-09-01). Lo que sigue resuelve
las decisiones de implementacion que quedaban abiertas.

---

### Instalacion del plugin

**Decision**: `GF_INSTALL_PLUGINS: grafana-llm-app` en el `environment:` del servicio
`grafana` de `docker-compose.yml` — mismo mecanismo que documenta el ejemplo oficial de
Grafana Labs (`grafana-llmexamples-app/docker-compose.yaml`, verificado 2026-09-01).

**Rationale**: es el plugin oficial mantenido por Grafana Labs (no un fork community), no
requiere licencia, y el mecanismo `GF_INSTALL_PLUGINS` es el mismo patron ya usado en el
proyecto para el resto del stack (nada nuevo que aprender operacionalmente).

**Version minima de Grafana requerida**: 9.5.2. La imagen del proyecto es `grafana/grafana:11.3.0`
(ver `docker-compose.yml`) — sobra margen.

---

### Feature toggle `dashgpt`

**Decision**: `GF_FEATURE_TOGGLES_ENABLE: dashgpt` en el mismo `environment:`.

**Rationale**: es el toggle que habilita el boton nativo "Auto generate" de titulo/
descripcion en paneles y dashboards (confirmado en el anuncio oficial "Use AI to generate
titles and descriptions for panels and dashboards", Grafana Labs, 2024-03-13, y en la
documentacion de "Configure panel options"). Sin este toggle el plugin queda instalado pero
sin ninguna superficie de UI nativa para probarlo (Historia 1 de `spec.md`).

**Actualizacion (2026-09-01, T001)**: en el contenedor descartable usado para verificar el
schema de Anthropic (`grafana/grafana:11.3.0`, sin ningun `GF_FEATURE_TOGGLES_ENABLE`
seteado), el log de arranque ya lista `dashgpt=true` entre los feature toggles activos por
default — no hace falta habilitarlo a mano en esta version. Se deja igual explicito en
`docker-compose.yml` (no cuesta nada y protege contra que una version futura de Grafana
cambie ese default), pero FR-003 ya esta satisfecho "gratis" por la version pinneada del
proyecto.

---

### Provisioning del proveedor Anthropic — verificacion pendiente de campos exactos

**Decision**: provisionar via `grafana/provisioning/plugins/apps.yaml` (carpeta nueva),
apiVersion 1, `apps: [{type: grafana-llm-app, jsonData: {...}, secureJsonData: {...}}]` —
mismo patron de provisioning por archivo YAML que ya usa el proyecto para datasources y
dashboards (`grafana/provisioning/datasources/influxdb.yml`).

**Bloqueador real encontrado (2026-09-01)**: la documentacion oficial y los ejemplos
publicos de Grafana Labs son **inconsistentes entre si** sobre el nombre/casing exacto de
los campos para el proveedor:
- El README de `grafana-llmexamples-app` (repo real, verificado) usa `jsonData.openai`
  (minuscula) para OpenAI.
- Un issue real del repo `grafana-llm-app` (#369, Grafana OSS 11.0.0, plugin v0.10.4) usa
  `jsonData.openAI` (con mayusculas) para el mismo proveedor.
- No se encontro ningun ejemplo publico con el proveedor Anthropic mostrando el nombre
  exacto del campo (`jsonData.anthropic` vs `jsonData.anthropicProvider` vs otro) ni el
  nombre de la clave en `secureJsonData` (`anthropicKey` es la convencion mas probable por
  analogia con `openAIKey`, pero no esta confirmado).

**FR-009 (marcado NEEDS CLARIFICATION en spec.md) — RESUELTO 2026-09-01 (T001)**: en vez de
confiar en documentacion, se instalo el plugin en un contenedor Grafana descartable
(`docker run` standalone, imagen `grafana/grafana:11.3.0` — misma que usa el proyecto,
`GF_INSTALL_PLUGINS=grafana-llm-app` sin pin) y se inspecciono el bundle real instalado
(`module.js`, minificado pero con los nombres de campo literales) via `docker exec` +
`docker cp` + `grep`. Version instalada: **`grafana-llm-app v1.0.8`** (confirmado en logs:
`"Starting plugin process" version=1.0.8`).

**Schema confirmado (evidencia: literales encontrados en `module.js` — `SecretInput` con
`name="anthropicKey"`, `Input` con `name="url"` dentro del componente de settings de
Anthropic, y el selector de proveedor que setea `{provider:"anthropic", disabled:!1}`):**

```yaml
apiVersion: 1
apps:
  - type: 'grafana-llm-app'
    disabled: false
    jsonData:
      provider: anthropic
      disabled: false          # <- NO es solo `apps[].disabled` de arriba. Sin este, el
                                #    plugin instala pero las funciones de LLM quedan
                                #    apagadas (mismo comportamiento "disabled by default"
                                #    que documenta el README para Grafana Cloud, confirmado
                                #    aca tambien para OSS via el codigo del selector de
                                #    proveedor en el bundle).
      anthropic:
        url: https://api.anthropic.com   # default que trae el propio formulario; se puede
                                          # omitir y confiar en el default del plugin, pero
                                          # se deja explicito por trazabilidad.
    secureJsonData:
      anthropicKey: ${ANTHROPIC_API_KEY}
```

**Hallazgo que NO estaba en ninguna fuente publica revisada:** el campo `jsonData.disabled`
(top-level, junto a `provider`) es el que efectivamente prende las funciones de LLM — es
distinto del `disabled: false` del nivel `apps[]` (ese solo controla si el plugin como tal
esta habilitado/deshabilitado en Grafana, no si sus funciones de LLM estan activas). Sin
`jsonData.disabled: false` explicito, el plugin queda instalado y "configurado" pero inerte
— exactamente el tipo de fallo silencioso que el Edge Case de `spec.md` ya anticipaba
("MUST fallar de forma visible... no silenciosamente"; en este caso no falla, simplemente
no hace nada, asi que hay que probarlo con el Escenario 1 de `quickstart.md`, no asumir que
"sin error en los logs" significa "funciona").

**Pendiente para T002/T003:** pinnear la version (`grafana-llm-app 1.0.8` en
`GF_INSTALL_PLUGINS`, no `:latest`) para que una reinstalacion futura no cambie este schema
por sorpresa — mismo criterio que la imagen de Grafana (`grafana/grafana:11.3.0`).

---

### Bug real encontrado en T004: el modelo default de Anthropic del plugin esta descontinuado

**Sintoma**: con el provisioning de T003 aplicado (`provider: anthropic`, key real),
`GET /api/plugins/grafana-llm-app/health` devolvia `"ok":false` con
`"error":"error, status code: 404, status: 404 Not Found, message: model:
claude-4-sonnet-20250514"` — la conexion/autenticacion funcionaba (`"configured":true`), el
modelo pedido no.

**Causa confirmada** (inspeccion del `module.js` instalado, v1.0.8): el plugin trae
hardcodeado el mismo literal `"claude-4-sonnet-20250514"` como modelo default tanto para el
preset "Base" como "Large" del proveedor Anthropic — un ID de modelo con fecha (mediados
2025) que la API real de Anthropic ya no reconoce (404, no error de auth ni de rate limit).

**Fix aplicado**: el plugin expone `jsonData.models.mapping` (objeto `{base: "<model-id>",
large: "<model-id>"}`) y `jsonData.models.default` (`"base"` o `"large"`) — mismo mecanismo
que usa para "Model mappings" en general, no especifico de Azure. Se pisa explicitamente en
`apps.yaml`:

```yaml
models:
  default: large
  mapping:
    base: claude-haiku-4-5-20251001
    large: claude-sonnet-5
```

**Verificado** (2026-09-01, contra el stack real del proyecto, `ANTHROPIC_API_KEY` real):
`GET /api/plugins/grafana-llm-app/health` devuelve `"models":{"base":{"ok":true},
"large":{"ok":true}},"ok":true"` — el plugin habla con Claude real (Haiku 4.5 y Sonnet 5,
los mismos modelos que ya usa `src/`, D8) sin error.

**Riesgo a futuro** (anotar en `memory/risks.md`): esto es un bug/staleness del plugin, no
de nuestra configuracion — si se actualiza la version pinneada de `grafana-llm-app` mas
adelante, hay que volver a correr este chequeo (`/api/plugins/grafana-llm-app/health`)
porque una version nueva podria corregir el default (volviendo redundante el override) o
cambiarlo de nuevo a otro ID roto.

**Nota de riesgo evaluada durante esta investigacion**: `uvx`/`specify init` se colgo dos
veces esta sesion en una descarga de red distinta (templates de Spec Kit, no de Grafana) —
ver nota operativa en D15. No hay evidencia de que el mismo problema afecte
`GF_INSTALL_PLUGINS` (que descarga desde el catalogo de Grafana, un CDN distinto), pero
tenerlo presente si la instalacion del plugin tambien se cuelga: no reintentar en loop, cortar
y reportar.

---

### Reutilizacion de `ANTHROPIC_API_KEY` sin duplicar el valor en texto plano

**Decision**: `secureJsonData` del YAML de provisioning referencia `${ANTHROPIC_API_KEY}`,
Grafana la sustituye al leer el archivo de provisioning (mismo mecanismo ya validado en
`influxdb.yml` para `INFLUX_TOKEN`) y la cifra en su propio secret store interno.

**Rationale**: no hay forma de que Grafana "lea" el secreto directamente desde `.env` de
`src/` en tiempo de ejecucion sin pasar por su propio provisioning — son procesos separados.
La sustitucion de variable de entorno es el minimo acoplamiento posible: un solo lugar
(`.env`) define el valor, dos consumidores (`src/`, Grafana) lo reciben via su propio
mecanismo de inyeccion, ninguno lo hardcodea en un archivo versionado.

**Efecto secundario aceptado (a documentar en `memory/risks.md`)**: el valor de la key
queda materializado en dos lugares en tiempo de ejecucion: el proceso de `src/` (via
variable de entorno) y el secret store cifrado de Grafana (via provisioning). Mismo valor,
dos superficies de exposicion si alguna de las dos se compromete. Aceptado por ahora porque
ambas superficies ya estan dentro del mismo perimetro de confianza (red Docker local,
`docker-compose.yml` unico) — revisar si el perimetro cambia (ver el riesgo ya documentado
del endpoint `/diagnosticar/<id>` sin autenticacion, mismo tipo de consideracion).

---

### Measurement de InfluxDB para el espejo del diagnostico

**Decision**: measurement nuevo `diagnosticos`, separado del measurement `alertas` ya
existente. Ver detalle completo del schema en `data-model.md` y `contracts/diagnostico-influxdb.md`.

**Rationale**: `alertas` ya tiene un query Flux especifico para las anotaciones del
dashboard (`|> group()` forzando formato "long" para que `textColumn`/`tagsColumn`
funcionen — bug real encontrado y arreglado en Session 2026-08-30). Agregar campos de texto
largo (causa probable, razonamiento) a ese mismo measurement arriesga romper ese query ya
validado, o forzar tags nuevos (aumentando cardinalidad sin necesidad — InfluxDB penaliza
tags de alta cardinalidad). Un measurement separado mantiene cada query simple y no toca
nada que ya funciona.

**Alternativa descartada**: extender `alertas` con campos opcionales de diagnostico —
descartada por el riesgo de romper el query de anotaciones ya en produccion, sin ningun
beneficio real (el panel nuevo va a hacer su propio query de cualquier forma).

---

## Items explicitamente fuera de esta investigacion

- El panel/plugin custom con `@grafana/llm` (resumen de datos en vivo): descartado en D15,
  no se investigo implementacion (TypeScript/React, build pipeline, `mage`) porque no se va
  a construir.
- Grafana ML, Grafana Assistant, Grafana Sift: confirmado en la investigacion previa a este
  feature que son Cloud/Enterprise, no aplican a Grafana OSS — no se volvio a investigar en
  esta pasada.
