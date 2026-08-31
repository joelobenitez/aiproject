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
