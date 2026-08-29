<!--
Sync Impact Report
==================
Version change: [TEMPLATE] -> 1.0.0 (ratificacion inicial)
Bump rationale: primera version completa de la constitucion (no habia contenido previo mas
alla del template vacio) -> MAJOR/inicial 1.0.0 segun convencion semver para primera release.

Principios definidos (nuevos, no hay renombres porque no existia contenido previo):
- I. Separacion de Capas (Datos / Orquestacion / Inteligencia)
- II. Deteccion Barata, Diagnostico con Contexto
- III. Un Cerebro, Muchos Consumidores
- IV. Seguridad por Niveles en Canales de Entrada
- V. Documentacion y Decisiones Trazables

Secciones agregadas:
- Requisitos Tecnicos (SECTION_2)
- Flujo de Trabajo de Desarrollo (SECTION_3)
- Governance

Secciones removidas: ninguna (se reemplazo el scaffold vacio).

Placeholders sin resolver: ninguno. RATIFICATION_DATE se fija en 2026-08-29 (fecha de esta
sesion) porque no hay una fecha de ratificacion formal anterior registrada; las decisiones
D1-D7 que sostienen estos principios son anteriores mais no constituyen una "ratificacion"
de constitucion per se.

Templates dependientes: no se modificaron en este comando (fuera de alcance de
/speckit-constitution). Revisar en el proximo /speckit-plan que las referencias a capas
(Node-RED/n8n/Claude Agent) y al idioma sin tildes sigan siendo consistentes con esta
version.
-->

# Aiproject Constitution

## Core Principles

### I. Separacion de Capas (Datos / Orquestacion / Inteligencia)
El sistema MUST mantener tres capas con responsabilidad unica y sin superposicion:
Node-RED es la capa de datos (ingesta MQTT, normalizacion, escritura en InfluxDB/MySQL);
n8n es la capa de orquestacion (arma contexto, dispara al Claude Agent, rutea
notificaciones); el Claude Agent es la capa de inteligencia (diagnostico en lenguaje
natural, reportes). Ningun componente MUST asumir la responsabilidad de otro: no se
implementa logica de diagnostico en n8n, ni orquestacion de workflows dentro de Node-RED,
ni ingesta de datos crudos en el Claude Agent.

**Por que:** es la arquitectura ya validada en D1 y D3 (`memory/decisions.md`). Mezclar
capas fue evaluado y descartado explicitamente porque cada herramienta es fragil fuera de
su rol natural (n8n sin soporte nativo de MQTT/Modbus, Node-RED sin capacidad de sostener
logica compleja de negocio).

### II. Deteccion Barata, Diagnostico con Contexto
La deteccion de anomalias (cruce de umbral, tasa de cambio en ventana corta) vive en
Node-RED y MUST resolverse sin consultar historia extensa ni bases externas mas alla del
`flow context` en memoria y umbrales cacheados. Todo analisis que requiera contexto
historico (tendencias de horas/dias, correlacion entre variables, causa probable) MUST
delegarse al Claude Agent, nunca implementarse como regla ad-hoc en Node-RED o n8n.

**Por que:** D1 fija esta frontera explicitamente para que el punto de enganche de ML
Models futuros (reemplazar la regla de umbral) no rompa el contrato del webhook hacia n8n,
y para que Node-RED no crezca en complejidad de negocio que no le corresponde.

### III. Un Cerebro, Muchos Consumidores
El Claude Agent MUST ser un unico servicio Python (contenedor propio, HTTP interno en la
red Docker) consumido por todos los canales — n8n, bot de Telegram, Web Report — sin
logica de diagnostico duplicada en ninguno de ellos. Cualquier nuevo canal de salida
(email, futuros dashboards) MUST integrarse llamando al mismo daemon, no reimplementando
prompts o parsing de salida estructurada por su cuenta.

**Por que:** D3 establece esto para que el prompt (el activo mas critico del sistema) viva
en un solo lugar versionado en git, testeable, y no se fragmente entre workflows de n8n y
otros consumidores.

### IV. Seguridad por Niveles en Canales de Entrada
Todo canal que pueda actuar sobre el sistema (no solo leer) MUST clasificarse por nivel
explicito antes de implementarse: solo-push, comandos read-only, consulta con NLU, y
acciones de escritura. El salto a un nivel de escritura (ej. Telegram Nivel 3: silenciar
alertas, ajustar umbrales) MUST NOT implementarse sin allowlist estricta por usuario y
auditoria de quien hizo que accion y cuando. El manejo de secretos (`ANTHROPIC_API_KEY`,
credenciales de InfluxDB/MySQL) MUST decidirse y documentarse antes de escribir cualquier
`docker-compose.yml` que los consuma.

**Por que:** D2 establece el modelo de niveles para Telegram; la superficie de riesgo
crece con cada nivel y la frontera consultar-vs-actuar es la que protege el sistema de
acciones no auditadas. El riesgo de secretos sin resolver esta documentado en
`memory/risks.md` y bloquea la escritura de infraestructura real.

### V. Documentacion y Decisiones Trazables
Toda documentacion del proyecto MUST escribirse en espanol sin tildes (compatibilidad
maxima entre sistemas). Las decisiones de arquitectura o alcance MUST registrarse en
`memory/decisions.md` en formato append-only (nunca se edita una decision existente; si
cambia, se agrega una nueva marcada como reemplazo de la anterior), con el "por que" y las
alternativas descartadas. Cualquier sesion de trabajo MUST leer `memory/progress.md` antes
de proponer proximos pasos, y `memory/risks.md` antes de tocar git, secretos, o flows de
Node-RED.

**Por que:** el proyecto se desarrolla en sesiones espaciadas en el tiempo (D6); sin este
registro trazable, cada sesion nueva pierde el contexto de por que se tomo cada decision y
corre el riesgo de repetir alternativas ya descartadas.

## Requisitos Tecnicos

El stack de Fase 1 MUST correr sobre Docker Compose local (Windows + WSL2 durante
desarrollo) con estos servicios: EMQX (broker MQTT central, topicos UNS
`empresa/planta/equipo/sensor`), InfluxDB (series de tiempo), MySQL (datos relacionales:
equipos, alertas, diagnosticos), Node-RED, n8n, Grafana (dashboard operacional), y el
contenedor `claude-agent`. El hardware de referencia es el Teltonika RUT956 (RS232, RS485,
Modbus RTU/TCP, MQTT nativo); en Fase 1 los sensores MUST simularse via script Python
(emulador de motor industrial) sin depender del hardware fisico. La decision de entorno de
produccion queda diferida hasta el cierre de Fase 1 y no MUST anticiparse en el diseno de
componentes de esta fase.

## Flujo de Trabajo de Desarrollo

El desarrollo de features nuevas MUST seguir el loop de Spec Kit:
`/speckit-constitution -> /speckit-specify -> /speckit-plan -> /speckit-tasks ->
/speckit-implement`. Ningun `/speckit-plan` MUST ejecutarse sin que esta constitucion este
completa (no en estado de template vacio). Los flows de Node-RED (JSON) MUST versionarse en
git como cualquier otro artefacto de codigo — no se dejan cambios sin commitear entre
sesiones. Antes de cualquier operacion de git con riesgo de sobreescribir historial (force
push, reset), MUST consultarse `memory/risks.md` y confirmarse con Joelo.

## Governance

Esta constitucion prevalece sobre cualquier practica ad-hoc de sesiones anteriores
(incluyendo el metodo `CHECKPOINT.md` jubilado en D6). Toda enmienda MUST registrarse
primero como una entrada nueva en `memory/decisions.md` con su "por que", y luego
reflejarse aca incrementando la version segun semver: MAJOR para remocion o redefinicion
incompatible de un principio existente, MINOR para agregar un principio o seccion nueva,
PATCH para aclaraciones de redaccion sin cambio de sentido. Toda sesion que proponga un
`/speckit-plan` o `/speckit-tasks` MUST verificar cumplimiento de los principios I-V antes
de generar artefactos. `CLAUDE.md` y `memory/` son las fuentes de guia operativa en tiempo
de ejecucion; esta constitucion es la fuente de las reglas no negociables que esa guia
operativa MUST respetar.

**Version**: 1.0.0 | **Ratified**: 2026-08-29 | **Last Amended**: 2026-08-29
