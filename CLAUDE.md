# CLAUDE.md

Este archivo es el **contrato** del proyecto: lo que casi nunca cambia. El estado actual NO
esta aca — leer siempre `memory/progress.md` primero al abrir una sesion.

## Contexto del Proyecto

Sistema de automatizacion IoT industrial escalable con diagnostico inteligente via IA.
El objetivo: capturar datos de sensores industriales en campo, procesarlos en tiempo real,
detectar anomalias y generar diagnosticos en lenguaje natural via Claude Agent.

**Problema central a resolver:** la brecha entre "alerta de anomalia" y "informacion accionable".
Los sistemas SCADA tradicionales dicen QUE algo esta mal, sin mas contexto. Nuestro sistema
ordena y presenta los hechos relevantes (valores, umbrales, tendencias, historial de alertas)
en un resumen ejecutivo — la interpretacion (el POR QUE y el QUE HACER) queda a cargo de un
operador humano (D17).

## Hardware Confirmado

**Edge Gateway:** Teltonika RUT956
- Interfaces: RS232, RS485 (Modbus RTU/TCP), 6 I/O digitales/analogicos, GPS, WiFi, 4G dual SIM
- Protocolos nativos: MQTT (Mosquitto), OPC-UA Client+Server, Modbus TCP+RTU
- Rol en el sistema: publicar datos de sensores via MQTT hacia el broker central

**Sensores Fase 1:** simulados via script Python (emulador de motor industrial)

## Entorno de Desarrollo

- **Local:** Windows + WSL2 (`/home/joelo/aiproject`) + Docker Desktop
- **Stack en Docker Compose:** EMQX + InfluxDB + MySQL + Node-RED + n8n + Grafana
- **Produccion:** decision diferida — se evalua al finalizar Fase 1
- **Ojo:** hay dos carpetas de trabajo posiblemente desincronizadas (Windows/OneDrive donde
  vive este archivo, y WSL2). Ver `memory/risks.md` antes de tocar git.

## Estructura del Repositorio

```
aiproject/
├── CLAUDE.md                # este archivo — contrato estable (leer siempre)
├── memory/
│   ├── progress.md          # estado vivo — SE LEE SIEMPRE al abrir sesion
│   ├── decisions.md         # decisiones D1-D6, numeradas, con el porque
│   ├── risks.md             # precondiciones y "no romper"
│   ├── inventario.md        # mapa de todos los artefactos del proyecto
│   └── historico.md         # hitos cerrados, sesiones pasadas
├── definicion/
│   ├── caso_de_uso_fase1.md      # caso de uso: motor + diagnostico Claude
│   └── arquitectura_sistema.md   # arquitectura completa con roles de cada componente
├── investigacion/
│   ├── investigacion_claude_iot.md   # stack completo, repos GitHub, roadmap
│   ├── Resumen_investigacion.md      # top 3 proyectos GitHub identificados
│   └── Proyecto_explicado.md         # analisis Mic-360
├── .specify/                 # Spec Kit — constitution, templates, scripts (instalado, sin usar)
├── .claude/skills/speckit-*/ # comandos /speckit-*
└── obs/                      # archivos jubilados (checkpoint viejo, GEMINI.md, CLAUDE.md previo)
```

## Arquitectura del Sistema (definida en Session 02, ver `definicion/arquitectura_sistema.md`)

```
[Script Python / RUT956]
        | MQTT
        v
[EMQX Broker]  <-- broker central, topicos UNS
        |
   +-----------+
   |           |
[Node-RED]   [n8n]
(datos)    (workflows)
   |           |
   +-----+-----+
         |
    [InfluxDB]  <-- series de tiempo (lecturas de sensores)
    [MySQL]     <-- datos relacionales (equipos, alertas, diagnosticos)
         |
    [Claude Agent]  <-- corre en servidor, diagnostica en lenguaje natural
         |
   +-----+--------+----------+
   |              |           |
[Telegram Bot] [Email]  [Web Report]
(alertas RT)  (reportes) (dashboard ejecutivo)
         |
    [Grafana]  <-- visualizacion de series de tiempo
```

## Roles de Cada Componente

| Componente | Rol | Notas |
|------------|-----|-------|
| EMQX | MQTT Broker central | Topicos UNS: `empresa/planta/equipo/sensor` |
| Node-RED | Capa de datos | MQTT → normalizar → InfluxDB + MySQL |
| n8n | Orquestador de workflows | Detecta anomalia → llama Claude → notifica |
| InfluxDB | Series de tiempo | Lecturas raw de sensores, historial |
| MySQL | Datos relacionales | Equipos, alertas, diagnosticos, usuarios |
| Claude Agent | Cerebro del sistema | Diagnostico NL, reportes periodicos, tendencias |
| Telegram Bot | Interfaz operativa | Alertas salientes + consultas interactivas |
| Email | Reportes programados | Diario/semanal + alertas criticas |
| Grafana | Dashboard live | Lee InfluxDB, visualizacion operacional |
| Web Report | Reporte ejecutivo | HTML/PDF generado por Claude Agent |
| ML Models | Deteccion de anomalias | Fase posterior — complementa a Claude |

## Caso de Uso Fase 1

Motor industrial simulado con 4 variables: temperatura (°C), corriente electrica (A, proxy
de carga mecanica), vibracion (mm/s) o presion de descarga (bar), horas de operacion
acumuladas.

El diferencial: cuando se detecta anomalia, Claude no solo alerta — genera un resumen
ejecutivo de los hechos relevantes (valores, umbrales, tendencias, historial), sin
interpretar causa ni recomendar accion (D17).

Ver `definicion/caso_de_uso_fase1.md` para la spec completa.

## Convenciones de Documentacion

- Idioma: espanol sin tildes (compatibilidad maxima entre sistemas)
- Formato: Markdown con tablas, diagramas ASCII, referencias con links directos
- Antes de agregar investigacion nueva: verificar que los repos GitHub existen

## Decisiones de Diseno

Todas las decisiones (D1-D4 de arquitectura, D5 Spec Kit, D6 metodo de memoria) estan en
`memory/decisions.md`, numeradas y con el porque de cada una. No se repiten aca para no
duplicar la fuente de verdad — si una decision cambia, se agrega ahi como nueva entrada que
supera a la anterior, nunca se edita este archivo para reflejarlo.

## Donde leer segun lo que vas a tocar

| Vas a... | Leer primero |
|---|---|
| Retomar la sesion | `memory/progress.md` |
| Entender por que se eligio algo | `memory/decisions.md` |
| Tocar git, secretos, o Node-RED flows | `memory/risks.md` |
| Buscar un archivo o saber si algo ya existe | `memory/inventario.md` |
| Entender el pasado de una sesion vieja | `memory/historico.md` |
| Escribir contratos de datos o el Claude Agent | `definicion/arquitectura_sistema.md` |
| Escribir el caso de uso / spec de Spec Kit | `definicion/caso_de_uso_fase1.md` |
