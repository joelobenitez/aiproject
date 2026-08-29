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

---

## D7 — Resolver la duplicacion de carpetas: Windows (OneDrive) queda como fuente de verdad

**Fecha:** 2026-08-29
**Quien decidio:** Joelo

**Decision:** se cierra el riesgo abierto desde Session 05 (ver D6 y `memory/risks.md`).
Esta carpeta (`C:\Users\joelo\OneDrive\Documentos\Claude\Projects\aiproject`, Windows) pasa
a ser la fuente de verdad del repo. Se corrio `git init -b main`, se hizo el primer commit
(35 archivos: investigacion/, definicion/, Spec Kit, memory/, obs/) y se conecto
`origin -> https://github.com/joelobenitez/aiproject.git`. El push (con force, porque el
remote tiene historial viejo de la copia WSL2 desactualizada) lo hace Joelo desde su propia
terminal, no desde esta sesion — la VM puente de este bridge no tiene credenciales de
GitHub configuradas (sin `gh`, sin SSH, sin token).

**Por que Windows y no WSL2:** esta carpeta tiene todo el contenido vigente (investigacion/,
definicion/, Spec Kit instalado, memory/ recien armado); la copia WSL2
(`/home/joelo/aiproject`) esta desactualizada (ultimo commit visto: "cierre sesion 02", sin
`definicion/` ni Spec Kit). Migrar el contenido nuevo a WSL2 hubiera sido mas trabajo y mas
riesgo de perder algo en la copia.

**Efecto:** la copia WSL2 queda obsoleta una vez hecho el force-push — no se volvio a tocar
ni a verificar su estado en esta sesion (no es alcanzable desde la VM puente). Si se sigue
usando WSL2 para algo, hay que resincronizarla manualmente (clone limpio del remote
actualizado) o abandonarla.

**Pendiente:** Joelo tiene que correr el push (`git push -u origin main --force`, o
`--force-with-lease` si prefiere una verificacion mas segura) desde su terminal con sus
credenciales de GitHub ya configuradas.

---

## D8 — Camino de implementacion del Claude Agent: script standalone antes de contenedor

**Fecha:** 2026-08-29
**Quien decidio:** Joelo + Claude Code

**Decision:** antes de construir el Claude Agent en su forma final segun D3 (contenedor
Docker, FastAPI, red `iot-net`, docker-compose), se construye primero como script Python
standalone, sin contenedor, alimentado con contexto JSON hardcodeado (los 4 escenarios A-D
de `definicion/caso_de_uso_fase1.md`) en lugar de queries reales a InfluxDB/MySQL. Secretos
en esta etapa: `.env` local + `.gitignore` (no vault ni Docker secrets todavia). Modelo por
defecto: Haiku 4.5 con prompt caching (barato); escalar a Sonnet 5 solo si la calidad del
diagnostico no alcanza contra los 4 escenarios.

**Por que:** D3 fija la forma final del servicio (contenedor, endpoints HTTP, red interna)
pero esa forma depende de decisiones aun no resueltas — manejo de secretos en produccion,
docker-compose armado, InfluxDB/MySQL corriendo (ver `memory/risks.md`). Esperar a que esas
piezas esten listas bloquea sin necesidad el desarrollo del nucleo cognitivo (prompt +
parser), que es la pieza que realmente hay que iterar y la unica que se puede validar contra
los escenarios de falla ya definidos sin depender del resto del stack.

**Alcance:** este camino NO reemplaza D3 ni resuelve la decision pendiente de manejo de
secretos en produccion — las pospone deliberadamente para esta etapa de desarrollo
temprano. Una vez validado el prompt/parser contra los 4 escenarios, se envuelve en FastAPI
+ contenedor segun la forma ya definida en D3, y ahi se retoma la decision de secretos real.

**Riesgo que deja abierto:** el manejo de secretos de produccion (`ANTHROPIC_API_KEY`,
credenciales DB) sigue sin decision — ver `memory/risks.md`.

---

## D9 — MVP simplificado: colapsar Node-RED + n8n en un unico servicio Python

**Fecha:** 2026-08-29
**Quien decidio:** Joelo + Claude Code

**Decision:** para la fase de MVP demostrativo (no para la arquitectura final de escala,
ver D11), se colapsan los roles de Node-RED (datos) y n8n (orquestacion) en un unico
servicio Python de vida larga: se suscribe a MQTT, escribe en InfluxDB, evalua el umbral
con estado en memoria (histeresis), arma el contexto, llama al Claude Agent y notifica por
Telegram. Ademas: SQLite reemplaza a MySQL para el MVP (un archivo, sin contenedor ni
credenciales); se postergan Email y Web Report (D4) a una fase posterior; se mantiene un
broker MQTT liviano (EMQX o Mosquitto) y Grafana porque son baratos de levantar y dan alto
impacto visual para demostrar la interconexion en vivo.

**Por que:** el stack completo definido en D1-D4 (~9 piezas: EMQX+InfluxDB+MySQL+Node-RED+
n8n+Grafana+Claude Agent+Telegram+Email+Web Report) es realista para produccion pero pesado
para un MVP cuyo objetivo es demostrar la interconexion del sistema y el potencial de
programar con Claude Code — Node-RED y n8n son herramientas de bajo-codigo (flows/workflows
armados por UI, guardados como JSON, ya senalado como riesgo de versionado en
`memory/risks.md`), y no hay nada ahi que Claude Code pueda escribir, revisar o testear.
Email y Web Report no suman a demostrar interconexion (Telegram ya cubre notificacion sin
SMTP ni generacion de HTML). MySQL agrega un contenedor y credenciales para un volumen de
datos que, en la escala de una demo de un solo motor, no lo justifica.

**Alcance:** esta decision es especifica de la fase MVP. NO invalida el razonamiento de D1
(separacion de capas) ni de D3 (Agent como servicio propio) para cuando el sistema escale a
una estructura industrial real — ver D11, donde la separacion detector/orquestador vuelve a
aparecer como necesidad tecnica (no de UI) al crecer en volumen y numero de equipos.

---

## D10 — Modelo de ejecucion del servicio Python del MVP: proceso de vida larga, no serverless

**Fecha:** 2026-08-29
**Quien decidio:** Joelo + Claude Code

**Decision:** el servicio Python de D9 corre como un proceso de vida larga (un contenedor
mas del mismo docker-compose en desarrollo; el mismo contenedor sin cambios en produccion),
no como funciones serverless.

**Por que:** el nucleo del servicio es una suscripcion MQTT persistente (tiene que estar
siempre escuchando) mas un estado en memoria para la histeresis del umbral (evitar
diagnosticos duplicados, ver D1). Serverless es event-per-invocation y stateless, con
cold-starts — exactamente lo contrario de lo que necesita este componente. Meterlo en
serverless obligaria a un puente externo que sostenga la conexion MQTT y reinyecte el
estado en cada invocacion, sumando complejidad en vez de sacarla.

---

## D11 — Roadmap de escalamiento a estructura industrial real: stack, integracion de hardware y dimensionamiento

**Fecha:** 2026-08-29
**Quien decidio:** Joelo + Claude Code

**Decision (roadmap, no implementacion inmediata):** cuando el sistema pase de la demo de
un motor a una estructura industrial real, se preve:

- **Escalamiento del servicio Python (D9):** separar de nuevo lo que D9 colapso por
  simplicidad — un componente de **ingesta + deteccion** (stateful, tiene que ver el 100%
  del stream, sostiene la histeresis por equipo en memoria) y uno o mas **workers de
  diagnostico** (consumen de una cola, escalan horizontalmente sin tocar el detector). Los
  topicos ya estan pensados para esto desde `CLAUDE.md` (patron UNS
  `empresa/planta/equipo/sensor`): escalar es pasar de un topico fijo a un wildcard
  (`empresa/+/+/+`). Los umbrales estaticos hardcodeados en el MVP pasan a vivir en una
  tabla y cargarse dinamicamente por tipo de equipo (ya anotado en D1). El enganche de
  modelos ML (fase posterior, ver tabla de roles en `CLAUDE.md`) entra dentro del detector,
  sin cambiar el contrato hacia el diagnostico.
- **Integracion con hardware real:** el emulador Python se reemplaza por el RUT956
  (hardware ya confirmado) hablando Modbus RTU/RS485 con sensores reales (temperatura,
  corriente via pinza, vibracion) y publicando por su cliente MQTT nativo al broker central
  con la misma estructura de topicos — el pipeline de deteccion/diagnostico no cambia,
  solo cambia el origen del dato. Multi-sitio: un RUT956 (o varios) por planta/linea; su 4G
  dual SIM permite publicar directo desde sitios sin conectividad fija.
- **Stack sugerido a esa escala:** EMQX en cluster (motivo por el que se eligio EMQX y no
  Mosquitto para el largo plazo — escala horizontalmente), InfluxDB para series de tiempo,
  Postgres/MySQL para lo relacional (reemplazando el SQLite de D9), el par
  detector+workers de diagnostico detras de una cola, Grafana igual que en el MVP.
- **Hardware sugerido:** el computo pesado (inferencia del LLM) corre en la API de Claude,
  no en infraestructura propia — a diferencia de un proyecto de ML/edge tradicional, sumar
  equipos no exige mas GPU/CPU, solo mas I/O y orquestacion. Alcanza un servidor modesto
  (VM cloud chica de pocos vCPU y 8-16GB RAM, o un mini PC on-prem — mismas opciones ya
  anotadas en D3: Hetzner/LightNode/mini PC). La decision de produccion sigue diferida
  (ver D3), esto solo fija el criterio de dimensionamiento cuando se tome.

**Por que queda como roadmap y no como decision ejecutable ya:** ninguna de estas piezas es
necesaria para el MVP (D9-D10). Se registra ahora como referencia a futuro para no perder
el razonamiento de la sesion, y para que D9 (simplificacion del MVP) no se lea como un
abandono permanente de la separacion de capas de D1/D3 — es una postergacion tecnica, no un
cambio de dirección.
