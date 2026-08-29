# Quickstart — Validacion del MVP

Feature: Monitoreo de Motor Industrial con Diagnostico Inteligente via Claude
(`001-diagnostico-motor-industrial`)

Escenarios de validacion de punta a punta para las historias en alcance de este plan
(Historia 1, Historia 2-Telegram, Historia 4 — ver "Alcance de este plan" en `plan.md`).

## Prerrequisitos

- Docker Desktop corriendo (Windows + WSL2, segun `CLAUDE.md`)
- Archivo `.env` con: `ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`,
  `INFLUX_TOKEN` (D8: `.env` local, no es la decision de secretos de produccion)
- Python 3.11+ si se corre `src/main.py` fuera de contenedor durante desarrollo

## Setup

```bash
docker compose up -d broker influxdb grafana
python -m venv .venv && source .venv/bin/activate   # o .venv\Scripts\activate en Windows
pip install -r requirements.txt
python src/main.py &
python herramientas/emulador_motor.py
```

## Escenario 1 — Flujo feliz de deteccion + diagnostico (Historia 1, SC-001 a SC-004)

1. Con el emulador en "Escenario A" (degradacion de refrigeracion — ver
   `definicion/caso_de_uso_fase1.md`), dejarlo correr hasta que la temperatura supere 75°C.
2. **Esperado**: dentro de 5s la lectura aparece en InfluxDB (SC-001); dentro de 10s desde
   la deteccion, el diagnostico queda generado con causa probable apuntando a
   refrigeracion, urgencia MEDIA (SC-003, SC-004).
3. Repetir con Escenario B (sobrecarga mecanica) y Escenario C (falla de rodamiento
   incipiente) — verificar que la causa probable coincide con cada escenario (SC-004).

## Escenario 2 — Sin falsos positivos (Historia 1, SC-005)

1. Correr el emulador en "Escenario D" (operacion normal con variacion) por al menos 10
   minutos.
2. **Esperado**: cero filas nuevas en la tabla `Alerta` durante ese periodo.

## Escenario 3 — Notificacion por Telegram (Historia 2, SC-002)

1. Repetir el Escenario 1.
2. **Esperado**: el chat de Telegram configurado recibe el mensaje (ver formato en
   `contracts/notificacion-telegram.md`) dentro de los 90 segundos desde que la lectura
   cruzo el umbral.

## Escenario 4 — Sin duplicados durante oscilacion (caso limite, FR-010)

1. Forzar (via el emulador o inyectando lecturas de prueba) que la variable oscile
   alrededor del umbral de alerta varias veces en menos de 15 minutos (ventana de cooldown,
   `research.md`).
2. **Esperado**: una sola `Alerta`/`Diagnostico`/notificacion para ese evento, no una por
   cada cruce individual.

## Escenario 5 — Resiliencia ante fallo del diagnostico (caso limite, FR-013)

1. Apuntar `ANTHROPIC_API_KEY` a un valor invalido temporalmente y repetir el Escenario 1.
2. **Esperado**: la `Alerta` se persiste igual; la notificacion de Telegram llega con el
   mensaje de "diagnostico no disponible" (ver `contracts/notificacion-telegram.md`); el
   proceso no se cae.

## Escenario 6 — Dashboard en vivo (Historia 4, SC-007)

1. Abrir Grafana (`http://localhost:3000`, dashboard provisionado — ver `research.md`).
2. **Esperado**: la serie de tiempo de temperatura/corriente/vibracion se actualiza sin
   recargar la pagina, y el punto de la alerta del Escenario 1 aparece anotado en el
   grafico.

## Fuera de este quickstart

Reporte diario por email e Historia 3 completa quedan fuera de alcance de este plan (ver
`plan.md`) — no tienen escenario de validacion aca.
