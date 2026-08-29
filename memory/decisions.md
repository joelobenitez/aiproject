# Decisions — aiproject

Registro append-only. Las decisiones no se borran ni se reescriben: si una decision cambia,
se agrega una nueva que la reemplaza y la anterior se marca `superseded por Dnn`.

---

## D1 — Deteccion de anomalia: Node-RED con reglas + webhook a n8n

**Fecha:** Session 03 (posterior a 2026-06-04, fecha exacta no registrada)
**Quien decidio:** Joelo + Claude (sesion de definicion)

**Decision:** la deteccion de anomalia vive en Node-RED, no en n8n. Node-RED, que ya ve el
100% del stream para escribir en InfluxDB, compara cada lectura contra el umbral y dispara
un webhook HTTP a n8n con el evento ya calificado. n8n queda enfocado en orquestar (armar
contexto, llamar al Claude Agent, rutear notificaciones, escribir el diagnostico en MySQL).

**Por que (alternativa descartada: n8n con MQTT trigger directo):**
- Detectar en n8n obligaria a una segunda suscripcion MQTT y a manejar estado por-entidad
  (histeresis + deduplicacion) dentro de workflows, donde n8n es fragil.
- Node-RED ya esta suscrito a todos los topicos -> sostener el estado de alertas en `flow
  context` es natural.
- Separacion de responsabilidades limpia: Node-RED = datos, n8n = orquestacion.
- Punto de enganche para ML Models de fase posterior: reemplazan/complementan la regla de
  umbral en Node-RED sin cambiar el contrato del webhook hacia n8n.
- Validacion de mercado (investigacion Session 03): el patron Node-RED en el edge + n8n en
  orquestacion es el consenso IIoT 2026. n8n no tiene soporte nativo de MQTT/Modbus.

**Costo aceptado:** un function node con histeresis + refresco periodico de umbrales
cacheados desde la tabla `umbrales` (MySQL).

**Limite de responsabilidad:** Node-RED solo detecta barato y sin historia (cruce de umbral,
tasa de cambio en ventana corta en memoria). Todo lo que requiera consultar el pasado
("subio 12°C en 3h", correlacion entre variables) es diagnostico y lo arma el Claude Agent.

**Riesgo que deja abierto:** ver risks.md — disciplina git/CI para los flows JSON de Node-RED.

Detalle completo: `definicion/arquitectura_sistema.md` seccion D1.

---

## D2 — Telegram bidireccional por niveles (Fase 1 en Nivel 0)

**Fecha:** Session 03 (posterior a 2026-06-04, fecha exacta no registrada)
**Quien decidio:** Joelo + Claude

**Decision:** el bot no es una eleccion binaria unidireccional/bidireccional. Se adopta un
modelo de 4 niveles (0=solo push, 1=comandos read-only, 2=NLU via Claude, 3=acciones de
escritura). Fase 1 arranca en Nivel 0, pero el bot se disena desde el inicio para subir de
nivel sin rehacer arquitectura.

**Por que:**
- Contexto que definio la decision: operadores en campo con el telefono a mano, no siempre
  frente a Grafana -> la bidireccionalidad tiene valor temprano, no es solo "lindo".
- Lo que decide D2 en el fondo: si Telegram se vuelve un canal de ENTRADA al sistema, lo cual
  abre superficie (infra de escucha, autenticacion, parseo de intencion, estado
  conversacional). Por eso se introduce de a niveles y no de golpe.
- Frontera de seguridad clave: consultar (Niveles 1-2, read-only) es muy distinto de actuar
  (Nivel 3, write). El salto a Nivel 3 no se hace sin allowlist estricta, control por usuario
  y auditoria de quien hizo que.
- Interaccion con D3: el receptor de Telegram del Nivel 2 le pega al mismo daemon Python que
  ya sabe consultar InfluxDB/MySQL. Si el Agent viviera en n8n, el Nivel 2 seria mas engorroso.

Detalle completo (arquitectura de cada nivel, tabla push vs pull): `definicion/arquitectura_sistema.md` seccion D2.

---

## D3 — Claude Agent como Python daemon (contenedor Docker)

**Fecha:** Session 03 (posterior a 2026-06-04, fecha exacta no registrada)
**Quien decidio:** Joelo + Claude

**Decision:** el Agent es un servicio Python propio (FastAPI o similar) empaquetado como un
contenedor mas del docker-compose, que expone HTTP (`/diagnose`, `/report`, `/health`). No
vive dentro de n8n; n8n lo orquesta via HTTP interno (red Docker `iot-net`).

**Por que (alternativa descartada: logica del Agent como workflow de n8n):**
- La cadena real (evento -> query InfluxDB 24h -> query MySQL metadata/umbrales/alertas
  previas -> componer prompt -> llamar Claude -> parsear salida estructurada -> escribir
  MySQL -> devolver a n8n) es un workflow largo y fragil en nodos de n8n; en Python es
  codigo testeable.
- El prompt es el activo mas critico y va a iterar mucho -> en Python vive en git con diffs
  claros; en n8n queda embebido en el JSON del workflow.
- El daemon usa el SDK oficial de Anthropic (tool use, prompt caching, retries, rate
  limits); en n8n solo hay un HTTP Request node crudo.
- Un cerebro, muchos consumidores: n8n (reactivo), bot Telegram Nivel 2 (D2) y Web Report
  (D4) le pegan al mismo daemon. Una sola fuente de verdad cognitiva.
- Trade-off reconocido a favor de n8n: un componente menos que mantener, mas rapido para un
  MVP. Se descarto porque el caso de uso (contexto 24h + salida estructurada + dos modos)
  supera lo que n8n resuelve bien.
- La evolucion pipeline simple -> agente real con tool use queda abierta en Python; n8n
  congelaria en un pipeline rigido.

Detalle completo (endpoints, env vars, estructura de archivos del servicio): `definicion/arquitectura_sistema.md` seccion D3.

---

## D4 — Reporte web ejecutivo como HTML estatico

**Fecha:** Session 04 (posterior a Session 03, fecha exacta no registrada)
**Quien decidio:** Joelo + Claude

**Decision:** el Web Report es un HTML estatico generado periodicamente por el Claude Agent
(`/report`, disparado por el cron de n8n), guardado como archivo y servido/enviado. Es una
foto del periodo, no una pagina con queries live contra las bases.

**Por que:**
- El "en vivo" ya lo cubre Grafana (dashboard operacional que lee InfluxDB y se refresca
  solo). El Web Report no compite: es el reporte EJECUTIVO narrado, para mail o reunion ->
  una foto diaria alcanza y sobra.
- Estatico es simple, sin infra extra, versionable, y reusa el mismo daemon del Agent
  (refuerza D3). Exportable a PDF sin backend adicional.
- Trade-off reconocido a favor de dinamico: siempre al dia, permite filtrar/interactuar. Se
  descarta en Fase 1 porque suma un backend a mantener y se pisa con lo que Grafana ya hace.
  Queda como puerta abierta a futuro si se justifica interactividad real.

Detalle completo: `definicion/arquitectura_sistema.md` seccion D4.

---

## D5 — Adoptar Spec Kit (Spec Driven Development) para el desarrollo

**Fecha:** 2026-08-10 (Session 05)
**Quien decidio:** Joelo + Claude Code

**Decision:** usar Spec Kit (`specify-cli`, instalado via `uv`) para pasar de la fase de
definicion a desarrollo, con el loop `/speckit-constitution -> /speckit-specify ->
/speckit-plan -> /speckit-tasks -> /speckit-implement`. Instalado con
`specify init --here --integration claude --force` en la carpeta Windows/OneDrive, en modo
merge (no sobreescribio `definicion/` ni `CLAUDE.md`).

**Por que:** no quedo registrado un "por que" explicito mas alla de la mencion en el
checkpoint de cierre ("arrancar SDD"). Inferido del contexto: dar estructura formal
(constitution/spec/plan/tasks) al desarrollo una vez cerrada la fase de definicion (D1-D4).
**Pendiente de confirmar con Joelo si hubo una razon adicional no documentada** (por ejemplo,
por que Spec Kit puntualmente y no otro framework).

**Efecto:** dejo scaffoldeado `.specify/` (constitution.md como template vacio, templates,
scripts powershell) y `.claude/skills/speckit-*/` (9 comandos). `constitution.md` sigue sin
completar al dia de esta migracion.

---

## D6 — Adoptar el metodo de memoria multi-sesion (gestion-memoria-multisesion)

**Fecha:** 2026-08-29
**Quien decidio:** Joelo

**Decision:** reemplazar el mecanismo ad-hoc de `CHECKPOINT.md` (un archivo de estado +
prompt de reanudacion, reescrito manualmente sesion a sesion) por la estructura fija de
memoria de archivos: `CLAUDE.md` pasa a ser el contrato estable, y `memory/` (progress,
decisions, risks, inventario, historico) pasa a ser la memoria viva. `CHECKPOINT.md`,
`GEMINI.md` y la version anterior de `CLAUDE.md` se jubilan a `obs/` como registro
historico, sin borrarlos.

**Por que:** el proyecto ya lleva 5 sesiones espaciadas en el tiempo y va a seguir asi
durante el desarrollo (D5). El formato anterior mezclaba en un solo archivo (CHECKPOINT.md)
estado presente, decisiones ya resueltas y proximos pasos sin separacion por tipo de
informacion -> costo de arranque de contexto creciente, y riesgo de desincronizacion con
`CLAUDE.md` (que tambien tenia su propia seccion "Proximos Pasos", desactualizada respecto
al checkpoint).

**Alcance de esta migracion:** solo reorganizacion de conocimiento ya existente en
`CHECKPOINT.md`, `CLAUDE.md`, `GEMINI.md` y `definicion/` hacia la nueva estructura. No se
agrego informacion nueva ni se tomaron decisiones de producto/arquitectura en este paso.
