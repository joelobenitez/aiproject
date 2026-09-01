# Risks — aiproject

Precondiciones y "no romper". Consultar on-demand antes de tocar el area asociada.

---

## [RESUELTO 2026-08-29, ver D7] Duplicacion de carpeta de trabajo (Windows OneDrive vs WSL2)

**Area que protege:** cualquier operacion de git (init, commit, push) y cualquier decision
sobre "donde vive el codigo".

**Detalle:** hay dos carpetas separadas y NO sincronizadas:
- `C:\Users\joelo\OneDrive\Documentos\Claude\Projects\aiproject` (Windows) — tiene todo el
  contenido actual (investigacion/, definicion/, memory/, Spec Kit) pero **no es un repo
  git** todavia, nunca se conecto a GitHub.
- `/home/joelo/aiproject` (WSL2) — **si es** un repo git con remote a
  `github.com/joelobenitez/aiproject`, pero esta desactualizada (ultimo commit "cierre
  sesion 02", estructura plana, sin `definicion/`, sin Spec Kit).

**Chequeado en Session 05:** confirmado que son carpetas separadas. Se le pregunto a Joelo
como resolverlo (copiar Windows -> WSL2 y pushear ahi / git init nuevo en Windows con
force-push / no hacer nada todavia). Decision de esa sesion: "lo dejamos asi" — no se hizo
push, no se toco git. **Sigue sin resolver al 2026-08-29.**

**No romper:** no correr `git init` + push en ninguna de las dos carpetas sin retomar esta
decision con Joelo primero — cualquiera de las dos opciones (Windows como fuente de verdad,
o migrar a WSL2) puede pisar el historial del remote existente si se hace a las apuradas.

**Resolucion (D7, 2026-08-29):** se eligio Windows (esta carpeta) como fuente de verdad.
`git init` + primer commit ya hechos aca. Falta el `git push --force` a
`github.com/joelobenitez/aiproject`, que Joelo corre desde su propia terminal (la VM puente
de este bridge no tiene credenciales de GitHub). La copia WSL2 queda obsoleta sin
resincronizar. Detalle: `memory/decisions.md` D7.

---

## `.claude/` sin excluir de git

**Area que protege:** el futuro `git init` en la carpeta de trabajo.

**Detalle:** Spec Kit recomienda agregar `.claude/` a `.gitignore` por posibles
credenciales/tokens de agentes guardados ahi. Todavia no existe `.gitignore` en el proyecto
(la carpeta no es repo git aun), asi que esto queda pendiente para el momento en que se
resuelva el riesgo anterior y se inicialice git.

---

## Flows de Node-RED como JSON sin disciplina de versionado (D1)

**Area que protege:** la capa de datos (Node-RED) una vez que se empiece a implementar.

**Detalle:** documentado en `definicion/arquitectura_sistema.md` seccion D1 como "bandera
amarilla a resolver como convencion": los flows de Node-RED se guardan como JSON, lo que
requiere disciplina de git/CI para no perder cambios o pisarlos entre sesiones/personas. Sin
definir todavia como se van a versionar.

---

## Telegram Nivel 3 (acciones de escritura) — superficie de riesgo futura (D2)

**Area que protege:** cualquier implementacion futura del bot de Telegram mas alla del
Nivel 0/1.

**Detalle:** documentado en `definicion/arquitectura_sistema.md` seccion D2. El salto a
Nivel 3 (reconocer alerta, silenciar, ajustar umbral desde Telegram) mete a Telegram en el
camino de ESCRITURA del sistema. No implementar sin allowlist estricta, control por usuario
y auditoria de quien hizo que. No es un riesgo activo en Fase 1 (que arranca en Nivel 0),
pero queda anotado para cuando se suba de nivel.

---

## Manejo de secretos del Claude Agent (D3) — sin decision documentada

**Area que protege:** el servicio `claude-agent` cuando se implemente.

**Detalle:** `definicion/arquitectura_sistema.md` seccion D3 lista las env vars que va a
necesitar el contenedor (`ANTHROPIC_API_KEY`, `MODEL`, `INFLUX_URL`/`TOKEN`,
`MYSQL_HOST`/`USER`/`PASSWORD`), pero no hay decision registrada sobre como se van a
gestionar esos secretos (`.env` + gitignore, vault, secrets de Docker, etc.). Confirmar
antes de escribir el `docker-compose.yml` real.

**Actualizacion (D8, 2026-08-29):** para la etapa de desarrollo del Agent como script
standalone (sin contenedor), se usa `.env` local + `.gitignore` como solucion temporal —
esto NO es la decision de produccion, solo destraba el desarrollo temprano. La decision de
manejo de secretos en produccion sigue abierta y hay que resolverla antes de escribir el
`docker-compose.yml` real.

---

## Mosquitto nativo de Windows compite por el puerto 1883 con el broker de Docker

**Area que protege:** levantar `docker-compose.yml` y correr `herramientas/emulador_motor.py`
o cualquier cliente MQTT desde el host (fuera de Docker).

**Detalle:** la maquina de Joelo tiene instalado el servicio de Windows "Mosquitto Broker"
(`C:\Program Files\mosquitto`, instalado 22/7/2025 — anterior a la decision de usar Docker
Compose, D9), corriendo como `LocalSystem` en modo Automatic. Escucha en el puerto 1883 del
host igual que el broker `eclipse-mosquitto` del `docker-compose.yml`. Cuando ambos estan
activos, el proceso de Windows gana la conexion (los clientes que publican a
`localhost:1883` desde fuera de Docker nunca llegan al broker del contenedor, sin ningun
error visible — el publish() de paho-mqtt devuelve OK igual). Diagnosticado en Session
2026-08-29 comparando `netstat -ano` con `docker port aiproject-broker` (dos PIDs distintos
escuchando el mismo puerto).

**No romper:** antes de correr el emulador (o cualquier script MQTT) contra `localhost:1883`
con el stack Dockerizado levantado, verificar que el servicio de Windows este detenido
(`net stop mosquitto`, requiere terminal como Administrador — esta sesion de Claude Code no
tiene permisos para hacerlo sola). Esta en modo Automatic, asi que vuelve a arrancar solo si
se reinicia Windows. Si se vuelve un problema recurrente, la alternativa sin tocar el
servicio es remapear el puerto host del broker en `docker-compose.yml` (ej. `11883:1883`) y
ajustar `MQTT_PORT` en `.env` para clientes que corren fuera de Docker.

---

## [RESUELTO 2026-08-29] `constitution.md` de Spec Kit sigue siendo el template vacio

**Area que protege:** cualquier uso de los comandos `/speckit-*` que dependan de la
constitucion (por ejemplo `/speckit-plan`, `/speckit-analyze`).

**Detalle:** instalado en Session 05, nunca completado. Correr `/speckit-specify` o
`/speckit-plan` antes de llenar `constitution.md` puede generar artefactos sin las
convenciones del proyecto (idioma sin tildes, separacion Node-RED=datos / n8n=orquestacion /
Python=inteligencia, disciplina git) incorporadas.

**Resolucion (2026-08-29):** `/speckit-constitution` corrido, `.specify/memory/constitution.md`
ratificado en v1.0.0 con 5 principios basados en D1-D8. `/speckit-specify`, `/speckit-plan`,
`/speckit-tasks` e `/speckit-implement` ya corrieron todos sobre esta constitucion. Queda
pendiente (no bloqueante) una enmienda futura para que el Principio I reconozca la excepcion
de fase MVP introducida por D9 — ver `memory/progress.md`.

---

## Endpoint `POST /diagnosticar/<alerta_id>` sin autenticacion (D13)

**Area que protege:** el servidor HTTP embebido (`src/api.py`) que expone el diagnostico
bajo demanda, y cualquier decision de exponer el puerto `HTTP_PORT` (default 8000) mas alla
de `localhost`.

**Detalle:** el endpoint no valida ningun token/credencial. Quien tenga acceso de red al
puerto puede disparar una llamada real a la API de Claude (costo pagado por Joelo) por cada
alerta existente. En desarrollo local el `docker-compose.yml` mapea `8000:8000` en el host,
asi que cualquier proceso en la misma maquina (o en la misma LAN si el firewall no lo
bloquea) puede pegarle.

**No romper:** no exponer este puerto a internet (port-forward del router, tunel publico,
deploy en un servidor con IP publica) sin agregar autenticacion (token compartido en el
header, o allowlist de IP) primero. Ver D13 en `memory/decisions.md` para el detalle
completo de la decision que introdujo este endpoint.

---

## `ANTHROPIC_API_KEY` materializada en dos lugares (feature 002, D15)

**Area que protege:** el provisioning del plugin `grafana-llm-app`
(`grafana/provisioning/plugins/apps.yaml`, feature `002-grafana-llm-diagnostico`).

**Detalle:** el plugin de Grafana necesita la misma `ANTHROPIC_API_KEY` que ya usa `src/`.
Se reutiliza via sustitucion de variable de entorno en el YAML de provisioning (mismo
mecanismo que `influxdb.yml` ya usa para `INFLUX_TOKEN`), pero Grafana la cifra y la guarda
en su propio secret store interno — el valor queda materializado en tiempo de ejecucion en
dos procesos distintos (`src/`, `grafana`) en vez de uno solo.

**No romper:** aceptado mientras ambos procesos sigan dentro del mismo perimetro de
confianza (`docker-compose.yml` unico, red Docker local, sin exponer Grafana mas alla de
`localhost:3000`). Si se expone Grafana fuera de ese perimetro (deploy real, acceso
remoto), revisar esta superficie junto con la del endpoint `/diagnosticar/<id>` de arriba —
mismo tipo de decision, no independiente. Ver `research.md` del feature 002 para el detalle
completo.

---

## `specify init` se cuelga al reinstalar los comandos `/speckit-*` en una terminal nueva

**Area que protege:** cualquier sesion que necesite `.claude/skills/speckit-*/` (esta en
`.gitignore`, no viaja con el repo — hay que reinstalarlo por terminal/maquina).

**Detalle:** `uvx --from git+https://github.com/github/spec-kit.git specify init --here
--integration claude --force` se colgo dos veces (con y sin sandbox de red deshabilitado)
justo despues de imprimir el panel "Specify Project Setup", sin avanzar en 17+ minutos, sin
error visible. La causa exacta no se diagnostico (no parece ser alcance de red — `curl`
directo a `api.github.com`/`github.com` respondio rapido durante el mismo cuelgue). Detalle
completo en D15 (`memory/decisions.md`).

**No romper (o mejor, no perder tiempo de nuevo):** si esto se repite, no reintentar en
loop.

---

## `grafana-llm-app` v1.0.8 trae el modelo default de Anthropic descontinuado (feature 002)

**Area que protege:** cualquier reinstalacion o upgrade de version de `grafana-llm-app`
(`GF_INSTALL_PLUGINS` en `docker-compose.yml`, hoy pinneado a `1.0.8`).

**Detalle:** el plugin v1.0.8 trae hardcodeado `"claude-4-sonnet-20250514"` como modelo
default para Anthropic (Base y Large) — la API real de Anthropic ya no lo reconoce (404).
Se piso con `jsonData.models.mapping` en `apps.yaml` (`base: claude-haiku-4-5-20251001`,
`large: claude-sonnet-5`), verificado funcionando (2026-09-01) contra la API real. Detalle
completo en `specs/002-grafana-llm-diagnostico/research.md`.

**No romper:** si se sube la version pinneada de `grafana-llm-app` en el futuro, volver a
correr `GET /api/plugins/grafana-llm-app/health` (con `curl -u admin:<password>`) antes de
asumir que sigue funcionando — una version nueva puede arreglar el default (el override
queda redundante, no rompe nada dejarlo) o cambiarlo a otro ID igual de roto. El rodeo que funciono: `.specify/scripts/powershell/create-new-feature.ps1` /
`setup-plan.ps1` / `setup-tasks.ps1` son 100% locales (no bajan nada de red) y alcanzan para
scaffoldear `specs/NNN-.../{spec,plan,tasks}.md` desde `.specify/templates/`; el contenido
se completa a mano siguiendo esa plantilla, sin necesidad del comando `/speckit-*`
reinstalado.

---

## `docker compose up -d` no recrea contenedores viejos tras un `git pull` — corren con codigo/config desactualizada sin ningun error visible

**Area que protege:** cualquier sesion que haga `git pull` (o cualquier cambio a
`docker-compose.yml`/`src/`) con el stack Docker ya levantado desde antes.

**Detalle:** confirmado dos veces en la misma sesion (2026-09-01, terminal `joelo`) despues
de traer commits de `a456901`/D15 con `git pull`:
- **Grafana:** el contenedor `aiproject-grafana` (creado 2 dias antes del pull, sin
  recrearse) no tenia `GF_INSTALL_PLUGINS` en su entorno (`docker inspect` lo confirmo vacio)
  a pesar de que el `docker-compose.yml` en disco ya lo declaraba desde D15 — quedaba en
  `Exited (1)` con `plugin not installed: "grafana-llm-app"`.
- **servicio:** el contenedor `aiproject-servicio` (mismo caso, sin rebuild) seguia
  corriendo la imagen construida ANTES de D13 y del feature 002/Historia 2 — sin la funcion
  `escribir_diagnostico` (el panel "Diagnostico IA" quedaba vacio sin ningun error) y sin la
  logica de D13 que limita el diagnostico automatico a severidad `CRITICO` (diagnosticaba
  automatico en toda alerta, incluida `ALERTA`, comportamiento viejo). El contenedor estaba
  "Up" y sano — nada indicaba que corria codigo viejo salvo comparar el comportamiento real
  contra lo que el codigo en disco dice que deberia pasar.

**Por que pasa:** `docker compose up -d` (sin `--build` ni `--force-recreate`) solo recrea un
servicio si detecta que su seccion en `docker-compose.yml` cambio respecto de lo que uso para
crear el contenedor existente — pero no reconstruye la imagen para tomar cambios de codigo
fuente (`COPY src/ ...` en el `Dockerfile`) si la imagen ya existe y el `docker-compose.yml`
no cambio en si mismo. Un contenedor creado antes de un cambio de codigo puede seguir "Up"
indefinidamente sirviendo la version vieja.

**No romper:** despues de cualquier `git pull` (o cualquier edicion local a `src/` o
`docker-compose.yml`), antes de asumir que el stack corre el codigo actual, correr
`docker compose up -d --build` (reconstruye imagenes y recrea los contenedores que cambiaron)
en vez de un `up -d` simple. Si hay dudas sobre un contenedor puntual, comparar codigo
adentro (`docker compose exec -T <servicio> grep -n "<algo del codigo actual>"
/app/<archivo>`, con `MSYS_NO_PATHCONV=1` delante si se corre desde Git Bash en Windows para
que no traduzca la ruta `/app/...`) contra el archivo real en disco.
