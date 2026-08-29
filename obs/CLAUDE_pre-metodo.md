# CLAUDE.md

This file provides guidance to Claude when working with code in this repository.

## Contexto del Proyecto

Sistema de automatizacion IoT industrial escalable con diagnostico inteligente via IA.
El objetivo: capturar datos de sensores industriales en campo, procesarlos en tiempo real,
detectar anomalias y generar diagnosticos en lenguaje natural via Claude Agent.

**Problema central a resolver:** la brecha entre "alerta de anomalia" y "diagnostico accionable".
Los sistemas SCADA tradicionales dicen QUE algo esta mal. Nuestro sistema dice POR QUE y QUE HACER.

## Hardware Confirmado

**Edge Gateway:** Teltonika RUT956
- Interfaces: RS232, RS485 (Modbus RTU/TCP), 6 I/O digitales/analogicos, GPS, WiFi, 4G dual SIM
- Protocolos nativos: MQTT (Mosquitto), OPC-UA Client+Server, Modbus TCP+RTU
- Rol en el sistema: publicar datos de sensores via MQTT hacia el broker central

**Sensores Fase 1:** simulados via script Python (emulador de motor industrial)

## Entorno de Desarrollo

- **Local:** Windows + WSL2 (/home/joelo/aiproject) + Docker Desktop
- **Stack en Docker Compose:** EMQX + InfluxDB + MySQL + Node-RED + n8n + Grafana
- **Produccion:** decision diferida — se evalua al finalizar Fase 1

## Estructura del Repositorio

```
aiproject/
├── CLAUDE.md                         # este archivo
├── CHECKPOINT.md                     # estado de sesion y prompt de reanudacion
├── GEMINI.md                         # referencia historica
├── investigacion/
│   ├── investigacion_claude_iot.md   # stack completo, repos GitHub, roadmap
│   ├── Resumen_investigacion.md      # top 3 proyectos GitHub identificados
│   └── Proyecto_explicado.md         # analisis Mic-360
└── definicion/
    ├── caso_de_uso_fase1.md          # caso de uso: motor + diagnostico Claude
    └── arquitectura_sistema.md       # arquitectura completa con roles de cada componente
```

## Arquitectura del Sistema (decidida en Session 02)

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

Motor industrial simulado con 4 variables:
- Temperatura (°C)
- Corriente electrica (A) — proxy de carga mecanica
- Vibracion (mm/s) o presion de descarga (bar)
- Horas de operacion acumuladas

El diferencial: cuando se detecta anomalia, Claude no solo alerta —
genera un diagnostico contextual con causa probable, urgencia y accion recomendada.

Ver `definicion/caso_de_uso_fase1.md` para la spec completa.

## Convenciones de Documentacion

- Idioma: espanol sin tildes (compatibilidad maxima entre sistemas)
- Formato: Markdown con tablas, diagramas ASCII, referencias con links directos
- Antes de agregar investigacion nueva: verificar que los repos GitHub existen

## Decisiones de Diseno (estado)

- **D1 (deteccion de anomalia): RESUELTA** → Node-RED con reglas + webhook a n8n.
- **D2 (Telegram): RESUELTA** → bidireccional por niveles, Fase 1 en Nivel 0 (solo push).
- **D3 (Claude Agent): RESUELTA** → Python daemon (contenedor Docker) del lado servidor.
- **D4 (reporte web): RESUELTA** → HTML estatico generado por el Agent (`/report`, cron n8n). Grafana cubre el live; el Web Report es el ejecutivo narrado.

Ver `definicion/arquitectura_sistema.md` (secciones D1-D4) para el detalle de cada decision.

## Proximos Pasos (Session 05)

1. Arrancar SDD (Spec Driven Development) — crear carpeta `spec/`
2. Definir contratos de datos: estructura MQTT, schema InfluxDB, schema MySQL
3. Escribir spec del Claude Agent (entradas, salidas, formato de diagnostico)
4. Definir Docker Compose inicial con todos los servicios (incluido `claude-agent`)
