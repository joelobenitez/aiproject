# Investigacion Claude IoT — Sistema de Automatizacion Escalable

> Fecha: 2026-04-08  
> Alcance: Investigacion en GitHub y fuentes tecnicas sobre el stack IoT industrial con IA

---

## 1. Vision General del Negocio

El objetivo es construir un sistema de automatizacion industrial escalable que cubra toda la cadena desde el sensor fisico en campo hasta la toma de decisiones autonoma con IA. El stack propuesto combina tecnologias probadas en industria con las capacidades mas recientes de IA generativa y agentes autonomos.

```
[Sensores en campo]
        |
    [OPC-UA / Modbus / Serial]
        |
    [Edge Gateway]  <-- Node-RED como orquestador
        |
    [MQTT Broker]  <-- Mosquitto / EMQX
        |
    [n8n]  <-- Automatizacion de workflows
        |
    [Claude + Agentes MCP]  <-- Inteligencia y decision
        |
    [ML / Analisis predictivo]
        |
    [Dashboards / Alertas / Acciones]
```

---

## 2. Componentes del Stack y Repositorios GitHub

### 2.1 Broker MQTT — El nucleo de comunicacion

**Que es:** MQTT (Message Queuing Telemetry Transport) es el protocolo ligero de mensajeria publish/subscribe mas usado en IoT industrial. Ideal para redes con ancho de banda limitado y dispositivos de bajo consumo.

**Opciones principales:**

| Broker | GitHub | Notas |
|--------|--------|-------|
| **Mosquitto** (Eclipse) | [eclipse/mosquitto](https://github.com/eclipse/mosquitto) | Mas desplegado del mundo, 10k+ stars, bajo consumo de recursos |
| **EMQX** | [emqx/emqx](https://github.com/emqx/emqx) | Escala a 100M+ dispositivos, 1M msg/s, incluye reglas y bridges |
| **VerneMQ** | [vernemq/vernemq](https://github.com/vernemq/vernemq) | Erlang, distribuido, alta disponibilidad |

**Arquitectura de topicos MQTT recomendada:**
```
empresa/planta/zona/equipo/sensor/tipo_dato
ejemplo: acme/planta1/linea_a/motor_001/temperatura/valor
```

**Sparkplug B:** Extension del protocolo MQTT creada para IIoT. Estandariza payloads con Protocol Buffers, incluye mensajes de estado (birth/death), y es la base del **Unified Namespace (UNS)**.

- Spec: [Sparkplug B Specification - Eclipse Foundation](https://www.eclipse.org/tahu/spec/sparkplug_b_topic_namespace-v1_0-with_appendix_a_1-toc.pdf)
- Node-RED con Sparkplug: [flowfuse.com - MQTT Sparkplug B con Node-RED](https://flowfuse.com/blog/2024/08/using-mqtt-sparkplugb-with-node-red/)

---

### 2.2 Node-RED — Orquestador Edge

**Que es:** Plataforma de programacion visual low-code para conectar hardware, APIs y servicios online. Es el "pegamento" entre sensores, protocolos y sistemas.

**Repositorio oficial:** [node-red/node-red](https://github.com/node-red/node-red)

**Capacidades clave:**
- Conecta OPC-UA, Modbus, Serial, HTTP, MQTT en un mismo flujo visual
- Se ejecuta en edge (Raspberry Pi, gateways industriales, Docker)
- Mas de 4,000 nodos de comunidad disponibles

**Nodos esenciales para IoT industrial:**

| Nodo | Repositorio | Funcion |
|------|-------------|---------|
| node-red-contrib-iiot-opcua | [cacamille3/node-red-contrib-iiot-opcua](https://github.com/cacamille3/node-red-contrib-iiot-opcua) | Lectura/escritura OPC-UA desde Node-RED |
| node-red-contrib-opcua | [mikakaraila/node-red-contrib-opcua](https://github.com/mikakaraila/node-red-contrib-opcua) | Alternativa OPC-UA madura |
| node-red-contrib-mqtt | Incluido en core | MQTT publish/subscribe nativo |
| node-red-node-influxdb | Comunidad | Escritura directa a InfluxDB |

**Stack IoT completo con Docker + Node-RED:**
- [0x1d/balena-iot-gateway](https://github.com/0x1d/balena-iot-gateway): Gateway con Node-RED, MQTT (Mosquitto), Telegraf, InfluxDB y Grafana
- [PacktPublishing/Node-RED-IoT-projects-with-ESP32-MQTT-and-Docker](https://github.com/PacktPublishing/Node-RED-IoT-projects-with-ESP32-MQTT-and-Docker): ESP32 + MQTT + Node-RED + Docker

**Referencia arquitectural:** [josephazar/NODE-RED-IOT-STACK](https://github.com/josephazar/NODE-RED-IOT-STACK)

---

### 2.3 OPC-UA — Protocolo Industrial Estandar

**Que es:** OPC Unified Architecture es el estandar de comunicacion industrial para intercambio de datos entre PLCs, SCADA, robots y sistemas MES/ERP. Provee modelo de datos semantico, seguridad integrada, y opera tanto en modo cliente-servidor como publish/subscribe.

**Ventajas sobre Modbus/otros protocolos:**
- Modelo de datos con contexto semantico (no solo valores crudos)
- Seguridad por diseno (autenticacion, encriptacion)
- Independiente del vendedor
- OPC-UA PubSub = OPC-UA enviando datos via MQTT (lo mejor de ambos mundos)

**Flujo recomendado:**
```
PLC / Sensor --> OPC-UA Server --> Node-RED (bridge) --> MQTT Broker --> Cloud/n8n
```

**Recursos:**
- [FlowFuse: OPC-UA to MQTT con Node-RED](https://flowfuse.com/blog/2024/08/opc-ua-to-mqtt-with-node-red/)
- [NCD.io: OPC-UA Server en Gateway con Node-RED](https://ncd.io/blog/opc-ua-server-on-enterprise-iiot-gateway-with-node-red-2/)

---

### 2.4 Unified Namespace (UNS) — Arquitectura de Referencia

El **Unified Namespace** es el patron arquitectural mas recomendado para IoT industrial moderno. En lugar de integraciones punto-a-punto, todos los sistemas publican y consumen datos de un broker MQTT central con estructura semantica.

```
[PLC]--OPC-UA-->[Edge Node]--Sparkplug B-->[MQTT Broker UNS]
                                                    |
                      +-----------------------------+-----------------------------+
                      |                             |                             |
               [Node-RED]                      [n8n]                     [Historico/DB]
               (procesamiento)             (workflows)                   (InfluxDB/TimescaleDB)
```

**Referencias:**
- [Architecting a Unified Namespace - Corso Systems](https://corsosystems.com/posts/architecting-a-unified-namespace)
- [MQTT vs OPC UA 2025 — Architecture Guide](https://industryx.ai/2025/12/11/mqtt-vs-opc-ua-2025-architecture-guide/)

---

### 2.5 n8n — Automatizacion de Workflows con IA

**Que es:** Plataforma open-source de automatizacion de workflows con capacidades nativas de IA. Similar a Zapier pero self-hosted, con 400+ integraciones y soporte para agentes de IA.

**Repositorio:** [n8n-io/n8n](https://github.com/n8n-io/n8n) — 182,800+ stars

**Capacidades IoT en n8n:**
- Nodo MQTT Trigger: escucha mensajes de sensores en tiempo real
- Nodo MQTT: publica comandos de vuelta a dispositivos
- Workflows de IA: Claude como motor de decision dentro de workflows
- HTTP/Webhook: integra con APIs REST de cualquier plataforma

**Templates de n8n para IoT:**

| Template | Descripcion |
|----------|-------------|
| [Remote IoT Sensor Monitoring via MQTT e InfluxDB](https://n8n.io/workflows/4004-remote-iot-sensor-monitoring-via-mqtt-and-influxdb/) | Lectura DHT22 en ESP32, parseo JSON, ingesta en InfluxDB |
| [IoT Device Control with MQTT and Webhook](https://n8n.io/workflows/4211-iot-device-control-with-mqtt-and-webhook/) | Control ON/OFF de dispositivos desde webhook |

**Integracion Claude + n8n:**
- Claude es el nucleo de decision dentro de los agentes n8n
- n8n expone sus workflows via MCP para que Claude los controle directamente
- [czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp): MCP Server para que Claude Desktop/Claude Code construya workflows n8n desde lenguaje natural

**Articulos relevantes:**
- [Claude Code vs n8n: Agentic Workflows 2026 - MindStudio](https://www.mindstudio.ai/blog/claude-code-vs-n8n-agentic-workflows-comparison)
- [Claude Code + n8n: self-building agents - ability.ai](https://www.ability.ai/blog/claude-code-n8n-workflows)

---

### 2.6 Claude Code y Agentes IA — El Cerebro del Sistema

**Que es Claude Code:** CLI de Anthropic que permite a Claude actuar como agente de codigo autonomo: lee archivos, escribe codigo, ejecuta comandos, coordina subagentes. Se integra al stack IoT via MCP.

**Integracion directa con MQTT:**

EMQX ha desarrollado un servidor MCP que permite a Claude interactuar directamente con brokers MQTT:
- [Integrating Claude with MQTT: EMQX MCP Server](https://www.emqx.com/en/blog/integrating-claude-with-mqtt)
- Claude puede suscribirse a topicos, leer datos de sensores, y publicar comandos en tiempo real

**MCP over MQTT — El futuro del IoT con IA:**
El protocolo MCP (Model Context Protocol) puede correr sobre MQTT, convirtiendo cada dispositivo IoT en un "tool" que Claude puede invocar directamente. Esto crea el paradigma **Agentic IoT**.

- [MCP over MQTT: Connect IoT Devices and AI - IoT For All](https://www.iotforall.com/mcp-over-mqtt-iot-ai-explained)
- [ThingsBoard MCP: Acceso en Lenguaje Natural a la Plataforma IoT](https://thingsboard.io/blog/introducing-thingsboard-mcp-natural-language-access-to-your-iot-platform/)
- [EMQX MCP Server en Medium](https://emqx.medium.com/integrating-claude-with-mqtt-an-introduction-to-emqx-mcp-server-a42fb8f7f121)

**Subagentes Claude Code para IoT:**
- [0xfurai/claude-code-subagents — mqtt-expert.md](https://github.com/0xfurai/claude-code-subagents/blob/main/agents/mqtt-expert.md): Agente especialista en MQTT para Claude Code
- [lodetomasi/agents-claude-code](https://github.com/lodetomasi/agents-claude-code): 100 agentes hiper-especializados incluyendo embedded-engineer y edge-computing-expert
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents): Coleccion de 100+ subagentes para Claude Code
- [wshobson/agents](https://github.com/wshobson/agents): 182 agentes especializados + 16 orquestadores multi-agente

**Caso de uso real — Mantenimiento predictivo con Claude:**
- [LLM Edge Predictive Maintenance — Claude + MCP + Sensores de Vibracion](https://lgdimaggio.github.io/claude-stwinbox-diagnostics/): Sensores IoT en borde conectados a Claude via MCP para diagnostico de rodamientos con clasificacion ISO 10816

---

### 2.7 Machine Learning — Analisis Predictivo

**Casos de uso principales:**
1. **Mantenimiento predictivo:** Detectar fallas antes de que ocurran analizando vibracion, temperatura, corriente
2. **Deteccion de anomalias:** Identificar comportamientos anormales en series de tiempo
3. **Optimizacion de procesos:** Ajustar parametros en tiempo real para maximizar eficiencia
4. **Clasificacion de calidad:** Vision artificial + ML para control de calidad en linea

**Repositorios GitHub relevantes:**

| Repositorio | Descripcion |
|-------------|-------------|
| [fabiog1901/IoT-predictive-maintenance](https://github.com/fabiog1901/IoT-predictive-maintenance) | Workshop EDGE2AI: MQTT broker → MiNiFi → Kafka → Spark Streaming → modelos ML |
| [Nekketsu-GIT/elk-mqtt](https://github.com/Nekketsu-GIT/elk-mqtt) | Mantenimiento predictivo con IoT stack (ELK + MQTT) |
| [mapr-demos/predictive-maintenance](https://github.com/mapr-demos/predictive-maintenance) | Data engineering para ML en IoT industrial |

**Stack de datos recomendado:**
```
Sensores --> MQTT --> Telegraf --> InfluxDB (series de tiempo)
                                      |
                              Python/scikit-learn
                              TensorFlow/PyTorch
                                      |
                              Modelo entrenado
                                      |
                            Inferencia en tiempo real
                                      |
                           Alerta / Accion via n8n/Claude
```

**Tendencias 2025-2026:**
- **Federated Learning:** Modelos entrenados en el borde sin enviar datos crudos a la nube
- **TinyML:** Modelos ultra-compactos para microcontroladores (ESP32, STM32)
- **AIoT (AI + IoT):** Procesamiento de IA directamente en el sensor
- **Edge AI:** Reduccion de latencia y consumo de ancho de banda

**Referencias academicas:**
- [Artificial Intelligence of Things - MDPI Sensors 2025](https://www.mdpi.com/1424-8220/25/24/7636)
- [Enabling Predictive Maintenance with MQTT and Edge Computing - HiveMQ](https://www.hivemq.com/blog/enabling-predictive-maintenance-industry-40-mqtt-edge-computing/)

---

## 3. Arquitectura Escalable Propuesta

### Nivel 0 — Campo (Field Level)
```
Sensores fisicos: temperatura, presion, vibracion, caudal, nivel
Actuadores: valvulas, motores, variadores, PLC
Protocolos: 4-20mA, RS-485/Modbus, OPC-UA, CAN bus
```

### Nivel 1 — Edge Gateway
```
Hardware: Raspberry Pi 4, PC industrial, gateway IIoT comercial
Software: Node-RED + Mosquitto + Agente ML local
Funcion: Adquisicion, normalizacion, filtrado, inferencia local
```

### Nivel 2 — Fog/Planta
```
MQTT Broker central (EMQX o Mosquitto cluster)
InfluxDB / TimescaleDB para series de tiempo
Grafana para dashboards operacionales
n8n para automatizacion de workflows de planta
```

### Nivel 3 — Cloud / IA
```
n8n con agentes Claude para decision de alto nivel
Claude Code para generacion y mantenimiento de codigo
Modelos ML entrenados (scikit-learn, TensorFlow, PyTorch)
APIs de integracion con ERP/MES/CRM
```

---

## 4. Repositorios de Referencia — Lista Curada

### Listas "awesome" para explorar:
- [HQarroum/awesome-iot](https://github.com/HQarroum/awesome-iot): Lista curada de proyectos y recursos IoT
- [phodal/awesome-iot](https://github.com/phodal/awesome-iot): Frameworks, librerias, OS, plataformas IoT
- [Agile-IoT/awesome-open-iot](https://github.com/Agile-IoT/awesome-open-iot): Frameworks open source IoT

### Stacks completos listos para usar:
- [0x1d/balena-iot-gateway](https://github.com/0x1d/balena-iot-gateway): Node-RED + MQTT + Telegraf + InfluxDB + Grafana en Docker
- [josephazar/NODE-RED-IOT-STACK](https://github.com/josephazar/NODE-RED-IOT-STACK): Workshop Node-RED IoT completo
- [PacktPublishing/Node-RED-IoT-projects-with-ESP32-MQTT-and-Docker](https://github.com/PacktPublishing/Node-RED-IoT-projects-with-ESP32-MQTT-and-Docker): ESP32 + MQTT + Docker

### Agentes y automatizacion IA:
- [n8n-io/n8n](https://github.com/n8n-io/n8n): Plataforma de automatizacion con IA nativa
- [czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp): MCP para que Claude controle n8n
- [ruvnet/ruflo](https://github.com/ruvnet/ruflo): Orquestacion de agentes Claude (swarms, RAG, workflows)
- [wshobson/agents](https://github.com/wshobson/agents): 182 agentes especializados Claude Code

---

## 5. Casos de Uso por Industria

### Manufactura / Industria 4.0
- Monitoreo de vibracion en motores (predictivo)
- Control de calidad con vision artificial
- Optimizacion de consumo energetico
- OEE (Overall Equipment Effectiveness) en tiempo real

### Agricultura de Precision
- Sensores de humedad de suelo, temperatura, pH
- Riego automatico via MQTT + Node-RED
- Modelos ML para prediccion de cosechas
- Alertas inteligentes via n8n

### Edificios Inteligentes (BMS)
- Control de HVAC, iluminacion, accesos
- Monitoreo de consumo energetico por zona
- Integracion con protocolos BACnet/Modbus

### Infraestructura y Utilities
- Monitoreo de redes de agua/gas
- Deteccion de fugas con anomaly detection
- Gestion predictiva de activos

---

## 6. Roadmap de Implementacion

### Fase 1 — Fundacion (Mes 1-2)
- [ ] Instalar y configurar EMQX o Mosquitto en Docker
- [ ] Desplegar Node-RED con nodos OPC-UA y MQTT
- [ ] Conectar primeros sensores (ESP32/Arduino o gateway industrial)
- [ ] Almacenar datos en InfluxDB + visualizar en Grafana
- [ ] Establecer estructura de topicos MQTT (UNS)

### Fase 2 — Automatizacion (Mes 3-4)
- [ ] Desplegar n8n y crear primeros workflows MQTT-triggered
- [ ] Integrar Claude via API en n8n para analisis de datos
- [ ] Configurar MCP Server EMQX para acceso de Claude a MQTT
- [ ] Crear agentes Claude Code especializados (mqtt-expert, edge-computing-expert)
- [ ] Implementar alertas inteligentes (email, SMS, Slack)

### Fase 3 — Machine Learning (Mes 5-6)
- [ ] Recolectar dataset historico de sensores (minimo 3 meses)
- [ ] Entrenar modelos de deteccion de anomalias (Isolation Forest, LSTM)
- [ ] Desplegar inferencia en tiempo real en el pipeline MQTT
- [ ] Integrar predicciones en workflows n8n y agentes Claude
- [ ] Implementar feedback loop para reentrenamiento automatico

### Fase 4 — Escala y Productizacion (Mes 7-12)
- [ ] Multi-planta / multi-cliente con tenancy separado
- [ ] CI/CD para flujos Node-RED y n8n (con Claude Code)
- [ ] Dashboard ejecutivo con KPIs y ROI en tiempo real
- [ ] API REST propia para integracion con clientes
- [ ] Certificaciones (IEC 62443 para ciberseguridad industrial)

---

## 7. Herramientas de Desarrollo y DevOps

| Herramienta | Uso |
|-------------|-----|
| Docker / Docker Compose | Containerizar todo el stack |
| Portainer | Gestion visual de contenedores |
| Mosquitto / EMQX | MQTT Broker |
| Node-RED | Orquestacion edge |
| InfluxDB v2 | Base de datos de series de tiempo |
| Grafana | Dashboards y alertas |
| n8n (self-hosted) | Automatizacion de workflows |
| MQTTX | Cliente MQTT de prueba (GUI) |
| Claude Code CLI | Agente IA para desarrollo y automatizacion |
| Python + scikit-learn | Modelos ML |

---

## 8. Consideraciones de Seguridad

- **MQTT:** Usar TLS/SSL, autenticacion por usuario/contrasena o certificados X.509
- **OPC-UA:** Modo de seguridad "Sign & Encrypt", validacion de certificados
- **n8n:** Desplegar detras de reverse proxy (Nginx/Traefik) con HTTPS
- **Claude/API Keys:** Almacenar en variables de entorno o vault (HashiCorp Vault)
- **Red:** Segmentar OT (operacional) de IT en VLANs separadas
- **Actualizaciones:** Pipeline CI/CD para actualizar firmware y software de forma controlada

---

## 9. Costos Estimados de Infraestructura (Stack Open Source)

| Componente | Opcion gratuita / self-hosted | Opcion managed/cloud |
|------------|-------------------------------|----------------------|
| MQTT Broker | Mosquitto (gratis) | EMQX Cloud desde $0/mes (free tier) |
| Node-RED | Gratis (self-hosted) | FlowFuse Cloud desde ~$10/mes |
| n8n | Gratis (self-hosted) | n8n Cloud desde $20/mes |
| InfluxDB | Gratis hasta 30 dias retencion | InfluxDB Cloud desde $0 (free tier) |
| Grafana | Gratis (self-hosted) | Grafana Cloud free tier disponible |
| Claude API | Pago por uso (~$3/M tokens Sonnet) | Anthropic API |
| VPS/Server | ~$20-50/mes (2 vCPU, 4GB RAM) | AWS/GCP/Azure |

**Costo total estimado para MVP:** $50-100/mes (stack completo self-hosted en VPS)

---

## 10. Fuentes y Referencias

### GitHub Repositorios
- [eclipse/mosquitto](https://github.com/eclipse/mosquitto)
- [emqx/emqx](https://github.com/emqx/emqx)
- [node-red/node-red](https://github.com/node-red/node-red)
- [n8n-io/n8n](https://github.com/n8n-io/n8n)
- [cacamille3/node-red-contrib-iiot-opcua](https://github.com/cacamille3/node-red-contrib-iiot-opcua)
- [0x1d/balena-iot-gateway](https://github.com/0x1d/balena-iot-gateway)
- [czlonkowski/n8n-mcp](https://github.com/czlonkowski/n8n-mcp)
- [wshobson/agents](https://github.com/wshobson/agents)
- [ruvnet/ruflo](https://github.com/ruvnet/ruflo)
- [VoltAgent/awesome-claude-code-subagents](https://github.com/VoltAgent/awesome-claude-code-subagents)
- [fabiog1901/IoT-predictive-maintenance](https://github.com/fabiog1901/IoT-predictive-maintenance)
- [HQarroum/awesome-iot](https://github.com/HQarroum/awesome-iot)

### Articulos Tecnicos
- [FlowFuse: MQTT en Node-RED (2026)](https://flowfuse.com/blog/2024/06/how-to-use-mqtt-in-node-red/)
- [FlowFuse: OPC-UA to MQTT con Node-RED](https://flowfuse.com/blog/2024/08/opc-ua-to-mqtt-with-node-red/)
- [FlowFuse: MQTT Sparkplug B con Node-RED](https://flowfuse.com/blog/2024/08/using-mqtt-sparkplugb-with-node-red/)
- [MQTT vs OPC UA 2025 — Guia de Arquitectura](https://industryx.ai/2025/12/11/mqtt-vs-opc-ua-2025-architecture-guide/)
- [Unified Namespace con MQTT Sparkplug - HiveMQ](https://www.hivemq.com/blog/semantic-data-structuring-mqtt-sparkplug-unified-namespace-uns-smart-manufacturing/)
- [Architecting a Unified Namespace - Corso Systems](https://corsosystems.com/posts/architecting-a-unified-namespace)
- [Integrando Claude con MQTT: EMQX MCP Server](https://www.emqx.com/en/blog/integrating-claude-with-mqtt)
- [MCP over MQTT: IoT Devices y AI - IoT For All](https://www.iotforall.com/mcp-over-mqtt-iot-ai-explained)
- [ThingsBoard MCP: Acceso natural language a IoT](https://thingsboard.io/blog/introducing-thingsboard-mcp-natural-language-access-to-your-iot-platform/)
- [LLM Edge Predictive Maintenance con Claude](https://lgdimaggio.github.io/claude-stwinbox-diagnostics/)
- [HiveMQ: Predictive Maintenance con MQTT y Edge Computing](https://www.hivemq.com/blog/enabling-predictive-maintenance-industry-40-mqtt-edge-computing/)
- [Claude Code vs n8n: Agentic Workflows 2026](https://www.mindstudio.ai/blog/claude-code-vs-n8n-agentic-workflows-comparison)
- [n8n + Claude: self-building agents](https://www.ability.ai/blog/claude-code-n8n-workflows)
- [AIoT para Mantenimiento Predictivo - MDPI Sensors 2025](https://www.mdpi.com/1424-8220/25/24/7636)

---

*Documento generado el 2026-04-08 como base de investigacion para el desarrollo de un sistema IoT industrial escalable con IA.*
