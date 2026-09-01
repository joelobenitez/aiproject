# Quickstart — Validacion del plugin LLM de Grafana + panel de diagnostico

Feature: Plugin LLM de Grafana + panel de diagnostico de IA (`002-grafana-llm-diagnostico`)

Escenarios de validacion de punta a punta para las dos historias de `spec.md`.

## Prerrequisitos

- Docker Desktop corriendo (Windows + WSL2, segun `CLAUDE.md`)
- Mosquitto nativo de Windows detenido si se corre el emulador contra `localhost:1883`
  (`memory/risks.md`)
- `.env` con `ANTHROPIC_API_KEY` real (misma cuenta que ya paga los diagnosticos de `src/`)
- Nombres de campo del provisioning de Anthropic ya verificados contra el plugin instalado
  (ver "Bloqueador real encontrado" en `research.md`) — sin esto, Escenario 1 no arranca.

## Setup

```bash
docker compose up -d influxdb grafana broker servicio
```

## Escenario 1 — Claude vivo dentro de Grafana (Historia 1, SC-001)

1. Abrir Grafana (`http://localhost:3000`), entrar a Administration > Plugins > LLM.
2. **Esperado**: el plugin aparece instalado y habilitado, el chequeo de conexion con
   Anthropic es exitoso (sin error de credenciales).
3. Abrir el dashboard `motor-001-mvp`, editar el titulo de cualquier panel, usar el boton
   "✨ Auto generate".
4. **Esperado**: Grafana devuelve un titulo generado por Claude sin error de red ni de
   autenticacion.

## Escenario 2 — Diagnostico automatico visible (Historia 2, SC-002, camino CRITICO)

1. Con el stack completo levantado, correr el emulador (`herramientas/emulador_motor.py`)
   en un escenario que cruce el umbral CRITICO (ver `definicion/caso_de_uso_fase1.md`).
2. **Esperado**: el diagnostico automatico se genera (mismo comportamiento de D13, sin
   cambios), y dentro del ciclo de refresco del dashboard el panel "Diagnostico IA" de
   `motor-001-mvp` muestra causa probable, urgencia y accion recomendada de esa alerta, con
   su timestamp.

## Escenario 3 — Diagnostico on-demand visible (Historia 2, SC-002, camino ALERTA/D13)

1. Forzar una alerta de severidad ALERTA (no CRITICO).
2. **Esperado**: el panel de diagnostico NO se actualiza todavia (nadie pidio el
   diagnostico) — sigue mostrando el ultimo disponible o el estado vacio (Escenario 4).
3. Pedir el diagnostico via `POST /diagnosticar/<alerta_id>` (mismo endpoint de D13).
4. **Esperado**: en el siguiente refresco del dashboard, el panel muestra el diagnostico
   recien generado.

## Escenario 4 — Estado vacio (Edge Case de spec.md, FR-008)

1. Contra una instancia de InfluxDB sin ningun punto en el measurement `diagnosticos`
   todavia (bucket recien creado, o filtrando por un `equipo_id` que nunca tuvo
   diagnostico).
2. **Esperado**: el panel muestra un estado vacio explicito ("sin diagnostico todavia" o
   equivalente) — no un error de query ni un panel en blanco sin explicacion.

## Escenario 5 — Ningun llamado nuevo a Claude desde Grafana (SC-003, verificacion de diseno)

1. Revisar el diff final de este feature.
2. **Esperado**: no aparece codigo TypeScript, ningun plugin/panel custom de Grafana, ni
   ninguna llamada HTTP nueva hacia `api.anthropic.com` fuera de `src/`. Este escenario se
   verifica leyendo el codigo, no corriendo nada.

## Escenario 6 — El endpoint de D13 sigue intacto (SC-004, regresion)

1. Repetir el Escenario 3 (D13) de `obs/specs/001-diagnostico-motor-industrial/quickstart.md`
   si existe, o simplemente confirmar por lectura de codigo que
   `src/main.py::diagnosticar_bajo_demanda` no cambio de firma ni de comportamiento — solo
   `_diagnosticar_y_notificar` gano una linea nueva (la llamada a `escribir_diagnostico`).

## Fuera de este quickstart

El panel/plugin custom con resumen de datos en vivo (descartado en D15) no tiene escenario
de validacion aca porque no se construye.
