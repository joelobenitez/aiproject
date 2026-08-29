# Risks — aiproject

Precondiciones y "no romper". Consultar on-demand antes de tocar el area asociada.

---

## Duplicacion de carpeta de trabajo (Windows OneDrive vs WSL2)

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

---

## `constitution.md` de Spec Kit sigue siendo el template vacio

**Area que protege:** cualquier uso de los comandos `/speckit-*` que dependan de la
constitucion (por ejemplo `/speckit-plan`, `/speckit-analyze`).

**Detalle:** instalado en Session 05, nunca completado. Correr `/speckit-specify` o
`/speckit-plan` antes de llenar `constitution.md` puede generar artefactos sin las
convenciones del proyecto (idioma sin tildes, separacion Node-RED=datos / n8n=orquestacion /
Python=inteligencia, disciplina git) incorporadas.
