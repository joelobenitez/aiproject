# Arquitectura del Sistema IoT con Diagnostico Inteligente

> Definida en Session 02 — 2026-06-04
> Estado: BORRADOR — pendientes de decision marcados con [?]

---

## Vision General

Sistema de punta a punta para monitoreo de activos industriales con diagnostico autonomo.
No es un sistema SCADA tradicional: el diferencial es que Claude genera diagnosticos en
lenguaje natural con causa probable y accion recomendada, sin necesitar un historial previo
de fallas para funcionar.

Referencia conceptual: Deloitte Predictive Maintenance Position Paper (ver investigacion/).
Nuestro sistema implementa las Etapas 1-5 del journey de Deloitte, con Claude reemplazando
la necesidad de 20-30 fallas historicas registradas para arrancar el analisis de causa raiz.

---

## Diagrama de Flujo

```
[Script Python Emulador]
        |
        | MQTT publish
        v
[RUT956]  (en produccion: puente RS485/Modbus → MQTT via 4G)
        |
        | MQTT over internet/local
        v
[EMQX Broker]
  topico: empresa/planta/equipo/sensor/variable
        |
   +----+----+
   |         |
   v         v
[Node-RED] [n8n MQTT Trigger]
(datos)    (eventos/workflows)
   |              |
   |    +---------+
   |    |
   v    v
[InfluxDB]          [MySQL]
series de tiempo    datos relacionales
lecturas raw        equipos, alertas, diagnosticos
historial           config de umbrales, usuarios
   |                     |
   +----------+----------+
              |
         [Claude Agent]
         (proceso en servidor)
              |
    +---------+---------+---------+
    |         |         |         |
[Telegram] [Email]  [Grafana] [Web Report]
Bot        Reportes  Dashboard  HTML/PDF
alertas    diarios   live       ejecutivo
interactivo criticos
              |
         [ML Models]  <-- fase posterior
         anomaly detect
         scikit / LSTM
```

---

## Componentes — Roles y Responsabilidades

### Capa de Campo

**Script Python Emulador (Fase 1)**
- Genera datos sinteticos de un motor industrial: temperatura, corriente, vibracion, horas
- Simula patrones normales + degradacion progresiva + fallas abruptas
- Publica directamente a EMQX via MQTT
- En produccion es reemplazado por el RUT956 leyendo sensores reales por RS485

**Teltonika RUT956 (Produccion)**
- Lee sensores fisicos via RS485/Modbus RTU
- Puente Modbus → MQTT nativo (sin codigo adicional)
- Opcionalmente: OPC-UA Server local para integraciones industriales
- Publica datos al broker via 4G o WiFi

---

### Capa de Ingesta

**EMQX Broker**
- Broker MQTT central
- Estructura de topicos UNS (Unified Namespace):
  `{empresa}/{planta}/{zona}/{equipo}/{sensor}`
  Ejemplo: `demo/planta1/linea_a/motor_001/temperatura`
- Retiene ultimo mensaje por topico (retained messages)
- En desarrollo: corre local en Docker

---

### Capa de Proceso

**Node-RED** — Capa de datos
- Suscribe a todos los topicos MQTT del broker
- Responsabilidades:
  - Validar y normalizar valores (unidades, rangos, tipos)
  - Enriquecer con metadata (equipo_id, timestamp ISO 8601)
  - Escribir en InfluxDB (serie de tiempo)
  - Escribir eventos en MySQL (cuando corresponda)
  - Detectar anomalias simples por regla (cruce de umbral + tasa de cambio en ventana corta) y disparar webhook a n8n [DECIDIDO D1]
  - Mantiene estado de alertas activas (histeresis + deduplicacion) para no re-disparar
  - Limite: NO hace deteccion con historia (tendencias, correlacion). Eso es diagnostico y lo arma el Claude Agent.

**n8n** — Orquestador de workflows
- Responsabilidades:
  - Recibir trigger de anomalia (webhook desde Node-RED o MQTT trigger directo)
  - Invocar Claude Agent con contexto del evento
  - Rutear notificaciones (Telegram / Email segun severidad)
  - Ejecutar workflows programados (reporte diario, resumen semanal)
  - [?] Escribir diagnostico en MySQL tras recibir respuesta de Claude

**InfluxDB v2**
- Almacena todas las lecturas de sensores como series de tiempo
- Measurements: `sensor_readings`
- Tags: equipo_id, planta, sensor_tipo
- Fields: valor (float), unidad
- Politica de retencion: 90 dias raw, 1 año downsampled (definir en spec)

**MySQL**
- Almacena datos relacionales que InfluxDB no puede manejar bien:
  - Tabla `equipos`: id, nombre, planta, instalacion, horas_acumuladas
  - Tabla `alertas`: timestamp, equipo_id, tipo, severidad, valor_trigger
  - Tabla `diagnosticos`: timestamp, alerta_id, texto_claude, accion_recomendada, urgencia
  - Tabla `umbrales`: equipo_id, variable, min_normal, max_normal, min_critico, max_critico

---

### Capa de Inteligencia

**Claude Agent**
- [DECIDIDO D3] Python daemon (contenedor Docker) del lado servidor, expone HTTP. Ver seccion D3.
- Corre junto al stack (misma red interna Docker), NO en el edge/RUT956.
- Dos modos de operacion:
  1. **Reactivo:** invocado por n8n cuando hay anomalia → genera diagnostico puntual
  2. **Proactivo:** cron job cada X horas → analiza tendencias → genera reporte
- Entradas para diagnostico reactivo:
  - Valores actuales del evento que disparo la alerta
  - Historial de las ultimas 24hs desde InfluxDB
  - Metadata del equipo desde MySQL (horas operacion, alertas previas)
  - Umbrales configurados
- Salida:
  - Diagnostico en lenguaje natural (causa probable, urgencia, accion recomendada)
  - Nivel de confianza (alto / medio / bajo)
  - Campos estructurados para guardar en MySQL

**Ejemplo de diagnostico generado:**
```
Equipo: Motor M-01 | Linea A | Planta 1
Alerta: Temperatura 87°C (umbral normal: 75°C)
Tendencia: subio 12°C en las ultimas 3 horas
Corriente: estable en 18A (normal)

Diagnostico Claude:
"El incremento de temperatura sin aumento de corriente sugiere
degradacion del sistema de refrigeracion mas que sobrecarga mecanica.
Causa probable: filtro de enfriamiento obstruido o ventilador con
reduccion de caudal. Urgencia: MEDIA. Accion: inspeccionar circuito
de enfriamiento en las proximas 8 horas antes del proximo turno."

Confianza: ALTA
```

**ML Models (Fase posterior)**
- Complementa a Claude: el modelo ML actua como pre-filtro de anomalias
- Claude interpreta — ML detecta patrones estadisticos
- Algoritmos a evaluar: Isolation Forest, Autoencoder LSTM
- Requisito: minimo 3 meses de datos historicos para entrenar

---

### Capa de Salida

**Telegram Bot**
- [DECIDIDO D2] Modelo bidireccional por niveles. Fase 1 arranca en Nivel 0 (solo push).
  El bot se disena desde el inicio para poder subir de nivel sin rehacer. Ver seccion D2.
- Contexto que inclina la decision: operadores en campo con el telefono a mano (no siempre
  frente a Grafana) → la bidireccionalidad tiene valor temprano.
- Si bidireccional: operador puede escribir "estado motor M-01" y Claude responde
- Alertas por severidad: CRITICA (inmediata) / MEDIA (agrupada cada 15min) / BAJA (solo reporte)

**Email**
- Reporte diario automatico a las 7:00 AM con resumen de alertas y estado de equipos
- Alerta critica: mail instantaneo a lista de contactos configurada
- Generado por Claude Agent y enviado via n8n (SMTP o servicio como Resend)

**Grafana**
- Dashboard operacional en tiempo real
- Lee de InfluxDB
- Paneles: series de temperatura/corriente/vibracion por equipo, estado de alertas activas
- Acceso: http://localhost:3000 en desarrollo

**Web Report (Pagina de Reporte)**
- [DECIDIDO D4] HTML estatico generado periodicamente por el Claude Agent (`/report`, cron n8n).
  Es un snapshot ejecutivo del periodo, NO una pagina con queries live. Ver seccion D4.
- Incluye: resumen de KPIs, alertas del periodo, diagnosticos emitidos, tendencias
- Puede exportarse como PDF
- Servido como archivo estatico (nginx simple) y/o enviado por email. Sin backend de queries live.
- El dashboard operacional en vivo es dominio de Grafana; esto es el reporte ejecutivo narrado.

---

## Decisiones de Diseno

| # | Decision | Opciones | Estado |
|---|----------|----------|--------|
| D1 | Deteccion de anomalia: ¿Node-RED o n8n? | Node-RED con reglas → webhook a n8n / n8n con MQTT trigger directo | RESUELTO: Node-RED |
| D2 | Telegram: ¿unidireccional o bidireccional? | Solo alertas / Bot con consultas interactivas | RESUELTO: bidireccional por niveles (Fase 1 en Nivel 0) |
| D3 | Claude Agent: ¿Python service o n8n workflow? | Python daemon / n8n scheduled + webhook | RESUELTO: Python daemon (contenedor Docker) |
| D4 | Reporte web: ¿estatico o dinamico? | HTML generado y servido / pagina con queries live | RESUELTO: HTML estatico |

### D1 — RESUELTA (Session 03): Node-RED con reglas + webhook a n8n

**Decision:** la deteccion de anomalia vive en Node-RED, no en n8n. Node-RED, que ya ve el
100% del stream para escribir en InfluxDB, compara cada lectura contra el umbral y dispara un
webhook HTTP a n8n con el evento ya calificado. n8n queda enfocado en orquestar (armar contexto,
llamar al Claude Agent, rutear notificaciones, escribir el diagnostico en MySQL).

**Racional:**
- Node-RED ya esta suscrito a todos los topicos → sostener el estado de alertas (histeresis +
  deduplicacion) en `flow context` es natural. Detectar en n8n obligaria a una segunda suscripcion
  MQTT y a manejar estado por-entidad dentro de workflows, donde n8n es fragil.
- Separacion de responsabilidades limpia: Node-RED = datos, n8n = orquestacion.
- Punto de enganche para los ML Models de fase posterior: reemplazan/complementan la regla de
  umbral en Node-RED sin cambiar el contrato del webhook hacia n8n.

**Costo real (no es gratis):** un function node con la histeresis + refresco periodico de los
umbrales cacheados desde la tabla `umbrales` de MySQL.

**Limite de responsabilidad:** Node-RED solo hace deteccion barata y sin historia (cruce de umbral,
tasa de cambio en ventana corta en memoria). Todo lo que requiera consultar el pasado
("subio 12°C en 3h", correlacion entre variables) es diagnostico y lo arma el Claude Agent.

**Validacion de mercado (investigacion Session 03):** el patron Node-RED en el edge + n8n en
orquestacion es el consenso IIoT 2026. n8n NO tiene soporte nativo de MQTT/Modbus, con lo que la
opcion B iba contra la herramienta. Node-RED (OpenJS Foundation, ~4000 conectores, roadmap v5.0) es
apropiado para el horizonte del proyecto MIENTRAS se mantenga como capa de datos/edge y no se le
cargue logica de negocio. Escalado a flota: via FlowFuse (device agents, gestion centralizada, OTA).
Bandera amarilla a resolver como convencion: los flows se guardan como JSON → disciplina de git/CI.

### D2 — RESUELTA (Session 03): Telegram bidireccional por niveles (Fase 1 en Nivel 0)

**Decision:** el bot NO es una eleccion binaria unidireccional/bidireccional. Se adopta un modelo
bidireccional escalonado. Fase 1 arranca en Nivel 0 (solo alertas salientes), pero el bot se
disena desde el inicio para subir de nivel sin rehacer arquitectura.

**Contexto que definio la decision:** hay operadores en campo con el telefono a mano, no siempre
frente a Grafana. Eso adelanta el valor de la bidireccionalidad: la consulta desde el bolsillo pasa
de "lindo" a "util temprano" apenas haya mas de un equipo monitoreado.

**Que decide D2 en realidad:** si Telegram se vuelve un canal de ENTRADA al sistema. Eso abre una
superficie que la version solo-push no tiene: infra de escucha, autenticacion, parseo de intencion
y estado conversacional. Por eso se introduce de a niveles y no de golpe.

**Modelo por niveles:**

| Nivel | Que hace | Que suma respecto al anterior | Cuando |
|-------|----------|-------------------------------|--------|
| 0 | Solo push: alertas salientes con diagnostico de Claude | Nada. n8n hace POST a Telegram sendMessage. Sin receptor. | Fase 1 |
| 1 | Comandos read-only con botones / inline keyboards ("Estado", "Ultimas alertas") | Receptor de mensajes (webhook o long-polling) + allowlist de chat_id. Sin NLU. | Apenas haya >1 equipo |
| 2 | Consultas en lenguaje natural ruteadas a Claude ("¿por que subio la temp anoche?") | Parseo de intencion + contexto de sesion por usuario. El Agent responde. | Cuando el Agent este solido |
| 3 | Acciones: reconocer alerta, silenciar, ajustar umbral | Telegram entra al camino de ESCRITURA → authz fuerte + auditoria de quien hizo que. | Fase posterior, con cuidado |

**Arquitectura de cada modo:**
- Nivel 0 (push): `n8n → POST Telegram Bot API (sendMessage) → chat`. Nada escuchando.
- Nivel 1+ (pull): `operador escribe → Telegram → [webhook publico HTTPS o long-polling getUpdates]
  → receptor → (parseo) → Claude Agent (query InfluxDB/MySQL) → respuesta → Telegram`.
  En dev local el webhook necesita tunel (cloudflared/ngrok); el long-polling necesita proceso vivo.

**Lo reutilizable vs lo nuevo:** el bot (token, registro) y el envio se reusan en todos los niveles.
Lo nuevo al pasar a Nivel 1+ es el receptor + auth; a Nivel 2 el parseo + contexto; a Nivel 3 la authz
de escritura + auditoria.

**Frontera de seguridad clave:** consultar (read-only, Niveles 1-2) es muy distinto de actuar
(write, Nivel 3). El salto a Nivel 3 mete a Telegram en el camino de escritura del sistema y no se
hace sin allowlist estricta, control por usuario y registro de acciones.

**Interaccion con D3:** el modelo por niveles asume que el Claude Agent es un Python daemon
consultable (ver D3). El receptor de Telegram del Nivel 2 le pega al mismo daemon que ya sabe
consultar InfluxDB/MySQL y redactar en lenguaje natural. Si el Agent viviera en n8n, el Nivel 2 seria
mas engorroso. D2 y D3 se refuerzan.

### D3 — RESUELTA (Session 03): Claude Agent como Python daemon (contenedor Docker)

**Decision:** el Agent es un servicio Python propio (FastAPI o similar) empaquetado como un
contenedor mas del docker-compose, que expone HTTP. NO vive dentro de n8n. n8n sigue siendo el
orquestador y le pega por la red interna.

**Que decide D3:** donde vive el cerebro del sistema — el componente que arma contexto, compone el
prompt, llama a Claude, parsea la respuesta y la estructura. Con eso decide que tan testeable,
versionable y evolucionable es la pieza central.

**Racional:**
- El Agent no es "llamar a una API": es recibir evento → query InfluxDB (24h) → query MySQL
  (metadata, umbrales, alertas previas) → componer prompt → llamar Claude → parsear salida
  estructurada (causa/urgencia/accion/confianza) → escribir MySQL → devolver a n8n. Esa cadena en
  nodos de n8n es un workflow largo y fragil; en Python es codigo testeable.
- El prompt es el activo mas critico y va a iterar mucho. En Python vive en git con diffs claros;
  en n8n queda embebido en el JSON del workflow (mismo problema de review que los flows).
- El daemon usa el SDK oficial de Anthropic (paquete `anthropic`, `client.messages.create(...)`):
  tool use, prompt caching, retries, manejo de rate limits. En n8n solo hay HTTP Request node crudo.
- Un cerebro, muchos consumidores: n8n (reactivo), bot Telegram Nivel 2 (D2) y Web Report (D4) le
  pegan al mismo daemon. Una sola fuente de verdad cognitiva, sin duplicar logica.

**Trade-off (el argumento a favor de n8n):** n8n ya corre en el stack, meter la logica ahi seria un
componente menos que mantener y mas rapido para un MVP. Se descarta porque el caso de uso definido
(contexto 24h + salida estructurada + dos modos) cae justo donde n8n se queda corto.

**Evolucion pipeline → agente:** en Fase 1 puede ser un pipeline simple (queries fijas → prompt →
respuesta). A futuro, agente real con tool use donde Claude decide que datos pedir. El daemon Python
permite ambos; n8n congela en el pipeline rigido. Refuerza la eleccion de Python.

**Donde reside, fisicamente:**
- Lado servidor, junto al stack. NO en el edge (RUT956), que solo publica datos por MQTT.
- Fase 1: corre en la maquina local (Windows + WSL2 + Docker Desktop) como contenedor del compose.
- Produccion: identico, pero el compose corre en el servidor remoto (Hetzner/LightNode/mini PC).
- Necesita estar del lado servidor porque consulta InfluxDB y MySQL (locales al stack) y sale a
  internet a la API de Claude.

**Forma del servicio desplegado (ilustrativa, la spec formal va en spec/claude_agent.md):**
- Servicio `claude-agent` en el docker-compose, en la red interna `iot-net`, SIN `ports:` publicados
  (solo lo alcanza n8n por DNS interno de Docker: `http://claude-agent:8000/diagnose`).
- Env: ANTHROPIC_API_KEY, MODEL, INFLUX_URL/TOKEN, MYSQL_HOST/USER/PASSWORD.
- Estructura: `main.py` (endpoints), `context.py` (queries → contexto), `prompt.py` (el prompt,
  versionado), `parser.py` (respuesta → campos estructurados).
- Dos endpoints: `/diagnose` (reactivo, lo llama n8n ante alerta) y `/report` (proactivo, lo dispara
  el cron de n8n para tendencias/reportes). Mas `/health`.
- n8n invoca con HTTP Request node y rutea Telegram/email segun la urgencia de la respuesta.

**Reparto de responsabilidades:** n8n orquesta y agenda (ruteo, cron, notificaciones); el daemon hace
el trabajo cognitivo pesado. Mismo principio del sistema: Node-RED = datos, n8n = orquestacion,
Python = inteligencia.

### D4 — RESUELTA (Session 04): Reporte web ejecutivo como HTML estatico

**Decision:** el Web Report es un HTML estatico generado periodicamente por el Claude Agent
(endpoint `/report`, disparado por el cron de n8n), guardado como archivo y servido/enviado. Es
una foto del periodo, NO una pagina con queries live contra las bases.

**Que decide D4:** como se produce y sirve el reporte ejecutivo — snapshot precocido vs pagina
dinamica que consulta datos frescos en cada apertura.

**Racional:**
- El "en vivo" ya lo cubre Grafana (dashboard operacional que lee InfluxDB y se refresca solo).
  El Web Report NO compite con eso: es el reporte EJECUTIVO — resumen periodico, mas narrado, con
  los diagnosticos que redacto Claude, para mandar por mail o mostrar en una reunion. Para ese rol,
  una foto diaria alcanza y sobra.
- Estatico es simple, sin infra extra, versionable, y encaja natural con el flujo ya definido:
  `cron n8n → Agent /report → HTML → email/servido`. Se reusa el mismo daemon que ya sabe consultar
  InfluxDB/MySQL y redactar en lenguaje natural (refuerza D3).
- Exportable a PDF sin backend adicional.

**Trade-off (el argumento a favor de dinamico):** una pagina con queries live siempre esta al dia y
permite interactividad (filtrar por equipo, elegir rango). Se descarta en Fase 1 porque suma un
backend/servidor que mantener y se pisa con lo que Grafana ya hace. Queda como puerta abierta a
futuro si algun dia se pide interactividad real.

**Limite de responsabilidad:** el Web Report es snapshot ejecutivo periodico. Lo operacional en
tiempo real es dominio de Grafana; lo interactivo/live queda para una fase posterior si se justifica.

---

## Stack Docker Compose (Desarrollo Local)

| Servicio | Puerto | Imagen |
|---------|--------|--------|
| EMQX | 1883 (MQTT), 18083 (dashboard) | emqx/emqx:latest |
| Node-RED | 1880 | nodered/node-red:latest |
| InfluxDB | 8086 | influxdb:2 |
| MySQL | 3306 | mysql:8 |
| n8n | 5678 | n8nio/n8n:latest |
| Grafana | 3000 | grafana/grafana:latest |

---

## Estructura de Topicos MQTT (UNS)

```
{empresa}/{planta}/{zona}/{equipo}/{variable}

Ejemplos:
demo/planta1/linea_a/motor_001/temperatura    → float, °C
demo/planta1/linea_a/motor_001/corriente      → float, A
demo/planta1/linea_a/motor_001/vibracion      → float, mm/s
demo/planta1/linea_a/motor_001/horas_op       → float, h
demo/planta1/linea_a/motor_001/estado         → string, NORMAL|ALERTA|CRITICO
```

Payload JSON estandar:
```json
{
  "timestamp": "2026-06-04T23:00:00Z",
  "equipo_id": "motor_001",
  "variable": "temperatura",
  "valor": 87.3,
  "unidad": "C",
  "calidad": "GOOD"
}
```
