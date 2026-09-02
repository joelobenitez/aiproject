# Risks — aiproject

Precondiciones y "no romper". Consultar on-demand antes de tocar el area asociada.

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

---

## `pymodbus` >=3.8 reescribio el datastore sobre el motor de simulador — rompe la API clasica

**Area que protege:** `herramientas/simulador_modbus_rtu.py` y `requirements.txt`
(`pymodbus[serial]==3.7.4`, pin deliberado).

**Detalle:** se probo empiricamente (2026-09-02) instalando la ultima version (3.15.0):
`ModbusSlaveContext` ya no existe (renombrado `ModbusDeviceContext`), y
`ModbusSequentialDataBlock` paso a delegar en `pymodbus.simulator.simdata.SimData` con reglas
de direccionamiento distintas (`address - 1`, chequeo `0 <= address < 65535`) — no es un
cambio menor de firma, es una arquitectura interna nueva. La 3.7.4 todavia tiene la API
clasica documentada en la mayoria de ejemplos/tutoriales (`ModbusSlaveContext(hr=...)`,
`ModbusServerContext(slaves={id: ctx}, single=False)`, `bloque.setValues(address, values)`).

**No romper:** no correr `pip install -U pymodbus` (ni quitar el pin de `requirements.txt`)
sin releer la API nueva primero — el codigo actual de `simulador_modbus_rtu.py` asume la API
clasica de 3.7.x y va a fallar con `ImportError`/`TypeError` contra 3.8+.

---

## El "Data to Server" del RUT956 (D18) apunta a una IP de PC especifica, no a un destino estable

**Area que protege:** la coleccion `Rut_Mqtt` del RUT956 (Services -> Data to Server) y
cualquier decision de "que maquina es el gateway del stack".

**Detalle:** D18 configuro el router para publicar al Mosquitto local usando
`192.168.1.195` — la IP que la terminal `jbenitez` obtuvo por DHCP en la red del RUT956 via
el adaptador USB-Ethernet en la sesion 2026-09-02. Esta IP es especifica de **esta PC en esta
conexion**, no un valor estable:
- Si se retoma el trabajo desde la terminal `joelo` (otra maquina fisica), esa IP no le
  pertenece — el RUT956 seguiria publicando hacia la PC `jbenitez`, no hacia donde este
  corriendo el stack Docker en ese momento.
- Aunque sea la misma maquina, si la IP vino de DHCP (no confirmado si el RUT956 la fijo o
  no), puede cambiar en la proxima reconexion/reinicio, y el router quedaria publicando a una
  IP que ya no existe **sin ningun error visible** — mismo patron silencioso que el riesgo de
  los contenedores Docker viejos.

**No romper:** antes de dar por valida la conectividad RUT956 -> broker en una sesion futura,
confirmar que la IP en la config de "Data to Server" sigue siendo la de la maquina que
efectivamente tiene el stack Docker levantado. Pendiente de decision (no resuelta todavia):
asignarle IP fija a la PC que oficie de gateway del stack, o resolverlo distinto si el plan
final es correr el stack en un servidor fijo en vez de una laptop de desarrollo.

---

## Migraciones de schema en InfluxDB rompen paneles de Grafana si no se limpian los datos viejos

**Area que protege:** cualquier cambio de campos/tipos en un measurement de InfluxDB que ya
tiene escrituras con el esquema anterior (ej. D17: `diagnosticos` paso de
`causa_probable/razonamiento/urgencia/accion_recomendada/confianza` a
`resumen_ejecutivo/hechos_destacados`), leido por un panel de Grafana con rango amplio
(`range(start: -30d)` en este caso).

**Detalle:** confirmado 2026-09-02 en la maquina `jbenitez`. El measurement `diagnosticos`
tenia puntos viejos (pre-D17) mezclados con el formato nuevo dentro de la ventana de 30 dias
que consulta el panel "Resumen de IA". Flux agrupa internamente por el conjunto de
campos/tags de cada punto — `pivot(rowKey: ["_time"]) |> limit(n: 1)` NO garantiza una sola
fila global cuando coexisten esquemas distintos, produce resultados con columnas
mezcladas/vacias segun el grupo. Esto rompio el render del panel de tabla en el frontend de
Grafana (`TypeError: Cannot read properties of null (reading 'length')`; a veces solo el
panel quedaba vacio, otras veces se congelaba la pestaña entera) — es un bug de Grafana
procesando datos con forma inconsistente, no un bug de nuestro codigo.

Cuando se implemento D17 (2026-09-01, terminal `joelo`) se borro y recreo `data/aiproject.db`
(SQLite) para el schema nuevo, pero **nadie limpio los puntos viejos de `diagnosticos` en
InfluxDB** — ese paso de la migracion quedo incompleto. Es probable que la maquina `joelo`
tenga el mismo problema latente sin haberlo notado todavia (se valido una sola vez y puede no
haberse repetido el patron exacto que dispara el crash del frontend).

**Fix aplicado (`jbenitez`, 2026-09-02):**
```
influx delete --bucket lecturas_motor --org aiproject \
  --predicate '_measurement="diagnosticos"' \
  --start 1970-01-01T00:00:00Z --stop 2026-09-02T00:00:00Z
```
Borra todo lo anterior a la fecha de hoy, dejando solo datos post-D17.

**No romper:** ante cualquier cambio de schema futuro en un measurement de InfluxDB que ya
tiene datos, limpiar (o migrar) los puntos viejos ahi tambien, no solo en SQLite — es el mismo
tipo de paso de migracion, en dos lugares distintos que hay que recordar por separado. Revisar
tambien la maquina `joelo` por las dudas (correr la misma query de deteccion: filtrar
`diagnosticos` por rango amplio y ver si aparecen mas de un set de campos).

---

## El bind-mount de `mosquitto/passwd` no preserva permisos en Windows/Docker Desktop

**Area que protege:** cualquier archivo de config de un contenedor que corre como usuario
no-root y exige un permiso restrictivo (ej. `passwd` de mosquitto, que mosquitto rechaza
abrir si no es legible por su propio usuario).

**Detalle (D22, 2026-09-02):** bind-montear `mosquitto/passwd` desde el host (esta terminal,
Windows + Docker Desktop) siempre lo expone dentro del contenedor como `-rw------- root:root`
sin importar el `chmod` hecho del lado Windows (probado 600 y 644, mismo resultado) — el
proceso `mosquitto` corre como usuario no-root y no puede leer un archivo 600 de otro dueño,
asi que el broker moria en el arranque (`Unable to open pwfile`). Fix: `mosquitto/Dockerfile`
nuevo que copia el archivo al build y fija dueño/permiso con `RUN chown/chmod` — reproducible
sin depender de como Docker Desktop traduce permisos POSIX sobre un bind-mount de Windows.

**No romper:** el broker (`docker-compose.yml`, servicio `broker`) ahora es `build: ./mosquitto`,
no `image: eclipse-mosquitto:2` con bind-mounts. Un cambio a `mosquitto/passwd` o
`mosquitto/acl.conf` requiere `docker compose up -d --build broker` — reiniciar el contenedor
solo no alcanza (mismo patron de riesgo ya conocido para `servicio`, ver seccion de
`docker compose up -d` sin `--build`). `mosquitto/passwd` sigue fuera de git (`.gitignore`) —
un clone nuevo del repo necesita generarlo antes del primer build o el `COPY` del Dockerfile
falla (instrucciones en `README.md`).

---

## Cliente MQTT desconocido en la LAN quedo rechazandose en loop tras activar autenticacion

**Area que protege:** cualquier herramienta/proceso que hable con el broker Mosquitto fuera
de este repo (dashboards de terceros, scripts sueltos, apps de inspeccion MQTT).

**Detalle (2026-09-02, validando T026):** al activar `allow_anonymous false` (D20/FR-009), un
cliente MQTT identificado como `37` (no es un client-id de `paho`, que usa `auto-XXXX`) desde
la IP del host (`172.18.0.1`) quedo reconectando y siendo rechazado ("not authorised") varias
veces por segundo durante toda la sesion de validacion. No es el emulador ni el servicio (ya
actualizados con credenciales) — es una herramienta ajena a este repo corriendo en la maquina
o la LAN de Joelo (sospecha: una app de inspeccion MQTT tipo MQTT Explorer/MQTTX con una
conexion guardada y auto-reconexion).

**No romper / accion pendiente:** identificar que herramienta es (revisar apps con conexiones
MQTT guardadas apuntando a `localhost:1883` o a la IP de esta PC) y actualizarle usuario/password
nuevos (ver `.env`, `MQTT_USERNAME`/`MQTT_PASSWORD`) o cerrarla si ya no hace falta. No es un
bug del servicio — es la seguridad nueva funcionando como se espera, pero genera ruido
constante en los logs del broker si se deja así.

---

## `docker run -v` con rutas Unix en Git Bash (Windows) necesita `MSYS_NO_PATHCONV=1`

**Area que protege:** cualquier comando `docker run`/`docker exec` corrido desde esta
terminal (Git Bash en Windows) que use un bind-mount con ruta estilo Unix (`-v
"$(pwd)/carpeta:/ruta/en/el/contenedor"`).

**Detalle (2026-09-02, generando `mosquitto/passwd` para T019):** Git Bash reescribe
automaticamente argumentos que parecen paths Unix (`/mosquitto/config`) a paths de Windows
antes de pasarlos al proceso — rompe la mitad `:/mosquitto/config` de un `-v` de Docker,
que termina buscando `C:/Users/.../mosquitto/config` en vez del path DENTRO del contenedor.
Sintoma: `Error: Unable to open file .../mosquitto/config/passwd for writing. No such file or
directory` (el path completo aparece mezclado, mitad host, mitad container).

**Fix:** prefijar el comando con `MSYS_NO_PATHCONV=1` (deshabilita esa conversion para ese
comando puntual):
```bash
MSYS_NO_PATHCONV=1 docker run --rm -v "$(pwd)/mosquitto:/mosquitto/config" eclipse-mosquitto:2 \
  mosquitto_passwd -b -c /mosquitto/config/passwd <usuario> <password>
```
`docker compose` (usado para levantar el stack normalmente) NO tiene este problema — parsea
los `volumes:` del YAML directamente, sin pasar por la reescritura de argumentos de Git Bash.
Solo aplica a invocaciones sueltas de `docker run`/`docker exec` con `-v` desde esta terminal.
