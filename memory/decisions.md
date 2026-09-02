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

---

## D12 — Enmienda de la constitucion (v1.1.0): Principio I reconoce la excepcion de fase MVP de D9

**Fecha:** 2026-08-30
**Quien decidio:** Joelo + Claude Code

**Decision:** se enmienda `.specify/memory/constitution.md` (1.0.0 -> 1.1.0, MINOR) para
agregar al Principio I (Separacion de Capas) un parrafo explicito de "Excepcion de fase
MVP" que reconoce que el servicio Python del MVP (`src/`) colapsa deliberadamente los roles
de Node-RED y n8n, tal como ya establecia D9. Se aclara ademas que esta excepcion es
temporal y no aplica a la arquitectura de escala industrial real de D11, donde la
separacion de capas se recupera.

**Por que:** D9 (2026-08-29) ya justificaba y documentaba esta desviacion respecto del
Principio I original, pero la constitucion nunca se actualizo para reflejarla — quedaba la
inconsistencia de que el gate de `/speckit-plan` marcaba a D9 como "violado pero
justificado" en vez de como una excepcion reconocida formalmente. Esta enmienda no crea una
decision nueva de arquitectura: solo formaliza en la constitucion algo que D9, `plan.md` y
`tasks.md` ya reflejaban desde la implementacion del MVP.

**Alcance:** no modifica los Principios II-V ni ninguna otra seccion de la constitucion. No
habilita omitir la separacion de capas fuera del contexto MVP sin una decision equivalente
registrada aca.

---

## D13 — Diagnostico de IA bajo demanda para severidad ALERTA (automatico solo en CRITICO)

**Fecha:** 2026-08-31
**Quien decidio:** Joelo + Claude Code

**Decision:** el diagnostico automatico de Claude deja de dispararse en toda alerta. Ahora:
- **CRITICO:** comportamiento sin cambios — diagnostico automatico + notificacion Telegram
  con causa probable/urgencia/accion.
- **ALERTA:** se manda un mensaje Telegram crudo (variable, valor, umbral, severidad, sin
  IA) que referencia el id de la alerta. El diagnostico queda disponible bajo demanda via
  `POST /diagnosticar/<alerta_id>` contra un servidor HTTP nuevo (`src/api.py`,
  `http.server` de la libreria estandar, puerto `HTTP_PORT`, default 8000, corre en el
  mismo proceso que la suscripcion MQTT via `loop_start()` en vez de `loop_forever()`).
  Idempotente: si ya existe un diagnostico para esa alerta, se devuelve el guardado sin
  volver a llamar a Claude ni a Telegram.

**Por que:** reduce las llamadas a la API de Claude (costo real, pagado por Joelo) al
subconjunto de alertas donde un humano decide que vale la pena, sin perder cobertura en el
caso mas urgente (CRITICO sigue automatico). Investigacion de mercado (sesion 2026-08-31):
la mayoria de las plataformas de AIOps 2026 (PagerDuty, Datadog, Rootly) invierten
automatico-siempre porque su modelo de costo es flat-fee/enterprise; la excepcion relevante
es Splunk, cuyo agente de troubleshooting corre "automatico o on demand segun la alerta" —
el mismo modelo hibrido que adopta esta decision. El patron ChatOps (postear el evento
crudo, dejar que el humano pregunte cuando lo necesita) valida la forma del mensaje crudo.

**Opciones evaluadas (ver sesion 2026-08-31 para el detalle completo):**
- **A. Boton inline en Telegram:** requiere resolver ya el receptor de Nivel 1 completo de
  D2 (webhook/tunel o long-polling + allowlist). Se pospone: es el paso natural siguiente
  si el modelo hibrido resulta util, pero no se paga ese costo de infraestructura todavia.
- **B. Comando de texto en Telegram:** mismo costo de infraestructura que A, se descarta
  por la misma razon.
- **C. Endpoint HTTP (ELEGIDA):** no toca Telegram como canal de entrada — evita el receptor
  de D2 Nivel 1 por ahora. El "on demand" se pide desde afuera (curl/Postman/futuro boton
  en Grafana). Mas barato de validar la idea central antes de invertir en el receptor.
- **D. Automatico solo para CRITICO (ELEGIDA, combinada con C):** aprovecha una distincion
  de severidad que `src/deteccion/detector.py` ya tenia (NORMAL/ALERTA/CRITICO) pero que
  hasta ahora no se usaba para esto.

**Trade-off aceptado:** una alerta ALERTA que nadie pide diagnosticar queda sin diagnostico
indefinidamente — a diferencia del comportamiento anterior (D9 original), donde siempre
habia contexto de IA disponible. Aceptado porque el objetivo es ahorro de costo + control
humano, no cobertura total.

**Riesgo que deja abierto:** el endpoint `/diagnosticar/<id>` no tiene autenticacion —
cualquiera con acceso de red al puerto 8000 puede disparar llamadas a Claude (costo real).
Aceptable en desarrollo local (el puerto no sale de la red Docker salvo el mapeo expreso a
localhost); revisar antes de exponerlo en produccion. Ver `memory/risks.md`.

**Camino natural siguiente (no implementado aun):** opcion A (boton inline de Telegram)
sobre el mismo `diagnosticar_bajo_demanda`, cuando se decida pagar el costo del receptor de
D2 Nivel 1 — no se tira nada de lo hecho aca, `src/api.py` y `main.diagnosticar_bajo_demanda`
se reusan tal cual.

---

## D14 — Jubilar los artefactos del feature 001 (specs/) a obs/, manteniendo Spec Kit activo

**Fecha:** 2026-09-01
**Quien decidio:** Joelo + Claude Code

**Decision:** se mueve `specs/001-diagnostico-motor-industrial/` (spec.md, plan.md, tasks.md,
research.md, quickstart.md, data-model.md, contracts/, checklists/) a
`obs/specs/001-diagnostico-motor-industrial/` via `git mv`, sin editar contenido. La
herramienta Spec Kit en si (`.specify/` — scripts, templates, `constitution.md` v1.1.0, y los
comandos `/speckit-*`) **no se jubila**: queda instalada y activa, disponible para spec-kitear
una etapa futura del proyecto (ej. el roadmap de escalamiento D11, o Telegram Nivel 1) sin
reinstalar nada.

**Por que:** el ciclo SDD del feature 001 esta cerrado (38/38 tareas de `tasks.md`
completadas, MVP validado en Docker real con Claude/Telegram/Grafana reales). Mantenerlo en
`specs/` en la raiz del repo lo dejaba en la ruta que un asistente recorre por default como si
fuera contexto activo, cuando en realidad describe una version anterior/parcial del sistema
(reconciliada parcialmente por D9 pero de todos modos superada por el codigo real en `src/`).
El riesgo concreto que esto evita: que una sesion futura lea `spec.md`/`plan.md` como si
describieran el estado actual y arme respuestas con informacion desactualizada o en conflicto
con `src/` y `memory/decisions.md`.

**Por que no se jubila `.specify/` tambien:** no es contenido que pueda quedar stale — son
plantillas y scripts reutilizables, no una foto de una etapa. Retirarlo hubiera cerrado la
puerta a usar Spec Kit de nuevo sin necesidad; Spec Kit esta pensado justamente para acumular
una carpeta `specs/NNN-slug/` por feature, asi que un futuro `/speckit-specify` simplemente
crearia `specs/002-.../` al lado de la carpeta ahora vacia, sin fricción.

**Por que no se migro contenido a `definicion/` u otro lado:** para evitar la duplicacion de
info que Joelo senalo como riesgo explicito (contratos de datos viviendo en dos lugares que
podrian divergir). `src/` es la unica fuente de verdad viva de lo implementado; los contratos
originales en `obs/specs/001-diagnostico-motor-industrial/contracts/` quedan solo como
registro historico consultable — ver referencia en `memory/inventario.md`.

**Alcance:** esta decision es de organizacion documental, no de arquitectura ni de producto.
No revierte ni reinterpreta D5, D9 ni D12 — solo cambia donde vive el registro del ciclo SDD
ya cerrado del feature 001.

---

## D15 — Alcance del feature 002 (plugin LLM de Grafana): minimo + reusa D13, sin panel custom

**Fecha:** 2026-09-01
**Quien decidio:** Joelo + Claude Code

**Decision:** el feature `002-grafana-llm-diagnostico` (ver `specs/002-grafana-llm-diagnostico/spec.md`)
instala y provisiona el plugin oficial `grafana-llm-app` (proveedor Anthropic, feature
toggle `dashgpt` nativo de Grafana) y agrega un panel al dashboard `motor-001-mvp` que
muestra el ultimo diagnostico de IA que `src/` ya genera (D13) — sin agregar ningun llamado
nuevo a la API de Claude desde Grafana. Se descarta explicitamente la alternativa de un
panel custom (TypeScript + React + `@grafana/llm`) que le pregunte a Claude en vivo por el
estado del motor a partir de las ultimas lecturas — esa era la idea original de la
investigacion que dio pie a este feature.

**Por que:**
- Investigacion propia (verificada contra docs oficiales de Grafana Labs, GitHub del
  plugin y un issue real, sesion 2026-09-01) confirmo dos cosas que la investigacion previa
  no tenia: (a) el plugin no trae de fabrica un panel de "resumen de datos" — es un proxy
  backend + libreria frontend, hay que escribir un panel custom para eso; (b) el unico
  ejemplo publico de Grafana Labs que mostraba ese patron (`grafana-llmexamples-app`) esta
  archivado desde 2026-06-05, ya no se mantiene — mala base para construir sobre eso.
- El Principio III de la constitucion ("Un Cerebro, Muchos Consumidores", D3) exige que el
  Claude Agent sea el unico consumidor de la API de Anthropic para diagnostico. Un panel
  custom en Grafana con su propio prompt seria un segundo camino cognitivo en paralelo a
  `src/` — exactamente lo que D3/Principio III buscan evitar.
- `src/` ya genera el diagnostico real (D13, automatico en CRITICO + on-demand en ALERTA) y
  ya lo persiste (SQLite). Lo unico que falta para verlo en Grafana es espejarlo a InfluxDB
  (mismo patron ya usado para las anotaciones de alerta, `escribir_evento_alerta`) — cero
  llamadas nuevas a Claude, cero desarrollo frontend.
- Se conserva igual la Parte 1 (instalar+provisionar el plugin) porque es de bajo riesgo,
  gratis en OSS, y el boton nativo "Auto generate" (`dashgpt`) alcanza para demostrar que
  Claude esta conectado dentro de Grafana sin escribir codigo propio.

**Alcance:** decision de scope de un feature en desarrollo, registrada antes de
`/speckit-plan`. Si en el futuro se decide construir igual el panel custom con datos en
vivo, requiere una decision nueva y explicita que reconozca y acepte la tension con el
Principio III — no es continuacion natural de este feature.

**Nota operativa (no es la decision, es contexto de la sesion):** `.claude/skills/` esta en
`.gitignore` (correcto, D5-adyacente) y esta era la primera vez que se trabajaba este repo
desde esta terminal — hubo que reinstalar los comandos `/speckit-*` con
`specify init --here --integration claude --force`. Ese comando se colgo dos veces (con y
sin sandbox de red) en el paso de descarga de templates, sin resolverse en la sesion. Se
uso en cambio `.specify/scripts/powershell/create-new-feature.ps1` directamente (100% local,
sin red) para scaffoldear `specs/002-.../spec.md` desde `.specify/templates/spec-template.md`,
y se escribio el contenido a mano siguiendo esa plantilla. Si el hang se repite en una
proxima sesion, no perder tiempo reintentando — ir directo a este camino alternativo.

---

## D16 — Jubilar los artefactos del feature 002 (specs/) a obs/, mismo criterio que D14

**Fecha:** 2026-09-01
**Quien decidio:** Joelo + Claude Code

**Decision:** se mueve `specs/002-grafana-llm-diagnostico/` (spec.md, plan.md, tasks.md,
research.md, data-model.md, quickstart.md, contracts/) a
`obs/specs/002-grafana-llm-diagnostico/` via `git mv`, sin editar contenido. Mismo criterio
que D14: el ciclo SDD del feature 002 esta cerrado (13/13 tareas, validado contra el stack
real, commiteado y pusheado — commit `a456901`).

**Por que:** identico razonamiento a D14 — dejarlo en `specs/` en la raiz lo deja en la ruta
que una sesion futura recorre por default como si fuera trabajo activo/pendiente, cuando en
realidad describe un feature ya implementado y verificado. `src/`, `grafana/provisioning/` y
`docker-compose.yml` son la fuente de verdad viva de lo implementado.

**Alcance:** organizacion documental, no de producto. No reabre ni reinterpreta D15 (la
decision de scope del feature sigue vigente tal cual) — la conversacion posterior a D15
(2026-09-01, "no le veo mucho uso al plugin... sigamos con lo que ya tenemos, no agreguemos
mas IA en Grafana") confirmo que no se agrega mas superficie de IA en Grafana mas alla de lo
ya implementado; esta jubilacion es consecuencia de que el trabajo esta terminado, no una
decision nueva de alcance.

---

## D17 — El nucleo cognitivo deja de diagnosticar (causa/urgencia/accion) y pasa a resumir hechos

**Fecha:** 2026-09-01
**Quien decidio:** Joelo + Claude Code

**Decision:** el contrato de `src/diagnostico/` cambia de 5 claves de interpretacion
(`causa_probable`, `razonamiento`, `urgencia`, `accion_recomendada`, `confianza`) a 2 claves
estrictamente factuales:
- `resumen_ejecutivo`: parrafo de 2 a 4 oraciones que ordena los hechos disponibles (que
  variable cruzo el umbral y por cuanto, tendencia de las 3 variables en 24h, patron de
  alertas previas).
- `hechos_destacados`: lista de 3 a 6 strings cortos, cada uno un hecho puntual tomado
  directo del contexto que ya arma `src/diagnostico/context.py` (sin cambios en el contrato
  de entrada).

El system prompt (`src/diagnostico/prompt.py`) ahora prohibe explicitamente causa probable,
hipotesis de falla, urgencia, confianza y accion recomendada — el rol de Claude es organizar
y presentar hechos, no interpretarlos.

**Por que:** confianza/responsabilidad. Joelo no quiere que la IA tome decisiones de causa o
urgencia por su cuenta en un entorno industrial real — esa interpretacion (el "por que" y el
"que hacer") queda a cargo de un operador humano. Este cambio reformula el diferencial
central del proyecto descripto en `CLAUDE.md` (que antes decia que el sistema "dice POR QUE
y QUE HACER") — se actualizo `CLAUDE.md` en las dos secciones que describian el
comportamiento viejo para que el contrato del proyecto siga siendo preciso.

**Alcance:**
- Reemplaza el diagnostico anterior en TODOS los casos (CRITICO automatico y ALERTA bajo
  demanda via D13) — no coexisten dos modos.
- Los nombres tecnicos de plumbing se mantuvieron deliberadamente sin cambios (modulo
  `src/diagnostico/`, funcion `diagnosticar_bajo_demanda`, endpoint
  `POST /diagnosticar/<id>`, tabla SQLite `diagnostico`, measurement InfluxDB
  `diagnosticos`) — decision explicita de Joelo para minimizar superficie de cambio, ya que
  son detalles de implementacion que no se ven en Telegram/Grafana.
- Impacto en almacenamiento: la tabla SQLite `diagnostico` cambio de columnas (ver
  `src/almacenamiento/sqlite_repo.py`); como `CREATE TABLE IF NOT EXISTS` no migra columnas,
  el archivo `data/aiproject.db` existente tuvo que borrarse para recrearse con el schema
  nuevo — no hay perdida de datos de valor (SQLite en el MVP es un artefacto de desarrollo
  desechable, ver D9).
- No se tocaron `definicion/arquitectura_sistema.md` ni `definicion/caso_de_uso_fase1.md`
  (docs de diseno pre-D9 ya divergentes del codigo implementado en otros aspectos, nunca
  reconciliados) ni `investigacion/sistema_src_funcionamiento_detallado.md` (doc de estudio
  para NotebookLM escrito el mismo dia, queda desactualizado en las secciones que describen
  el diagnostico viejo hasta que se regenere aparte).

---

## D18 — El RUT956 publica al Mosquitto local del proyecto, no a un broker cloud externo

**Fecha:** 2026-09-02
**Quien decidio:** Joelo + Claude Code

**Decision:** la coleccion "Data to Server" del RUT956 (`Rut_Mqtt`) se reconfiguro para
publicar al Mosquitto de `docker-compose.yml` (IP LAN de la PC, `192.168.1.195:1883`, sin
TLS, sin credenciales — coherente con `allow_anonymous true` de `mosquitto/mosquitto.conf`)
en vez del broker EMQX Cloud externo (`ka819ef9.ala.us-east-1.emqxsl.com:8883`, TLS +
credenciales) al que ya venia apuntando de una configuracion previa no documentada. Se dejo
el periodo de publicacion en 60s (se probo en 15s para la validacion, se subio despues para
no floodear).

**Por que:** validar el tramo real de arquitectura que faltaba probar (RUT956 -> broker del
proyecto) sin depender de un servicio cloud de terceros ni de sensores reales todavia (D11
sigue bloqueado por falta del adaptador USB-RS485). Mantener el gateway dentro del mismo
broker que usa el resto del stack es ademas coherente con la arquitectura definida en
`CLAUDE.md` (EMQX/Mosquitto como broker central unico).

**Alcance:**
- Prueba de conectividad confirmada de punta a punta: `mosquitto_sub` contra
  `aiproject-broker` recibio mensajes reales del router en el topico de prueba
  `rut956/prueba_conectividad`. El firewall de Windows no bloqueo la conexion — no hizo
  falta abrir el puerto 1883 manualmente.
- El payload que arma "Data to Server" (`{"GPS": {...}, "input1": [...]}`) es el formato
  propio de Teltonika, **no** el contrato `{valor, unidad, timestamp}` por topico de variable
  que espera `src/ingesta` — no hay integracion con el pipeline de deteccion/diagnostico
  todavia. Normalizar ese mapeo queda pendiente para cuando haya datos reales via Modbus
  RTU/RS485 (D11).
- El dato publicado hoy sigue siendo el auto-sondeo Modbus TCP del router sobre si mismo
  (ver `input1` en la config, definido antes de esta sesion) mas GPS — no es un sensor real.
