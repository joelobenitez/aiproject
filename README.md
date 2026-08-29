# aiproject — Monitoreo de Motor Industrial con Diagnostico Inteligente via Claude

MVP del feature `001-diagnostico-motor-industrial`. Ver `specs/001-diagnostico-motor-industrial/`
para la spec, el plan y las decisiones de diseno completas, y `memory/decisions.md` para el
historial de decisiones (D1-D11).

## Entorno de desarrollo

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # completar con tus valores (ver abajo)
```

## Variables de entorno

Ver `.env.example` para la lista completa. Resumen:

| Variable | Uso |
|---|---|
| `ANTHROPIC_API_KEY` | credencial de la API de Claude |
| `MODEL` | modelo usado por el nucleo de diagnostico (default: Haiku 4.5, D8) |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` | notificacion Nivel 0 (D2) |
| `INFLUX_URL` / `INFLUX_TOKEN` / `INFLUX_ORG` / `INFLUX_BUCKET` | series de tiempo (lecturas del motor) |
| `COOLDOWN_MINUTOS` | ventana anti-duplicados de alertas (default 15, `research.md`) |
| `MQTT_HOST` / `MQTT_PORT` / `MQTT_TOPIC_BASE` | broker y topico base (`contracts/mqtt-topico.md`) |

`.env` esta en `.gitignore` — es la solucion de desarrollo (D8), no la decision de gestion de
secretos de produccion (pendiente, ver `memory/risks.md`).

## Levantar el stack

```bash
docker compose up -d broker influxdb
python src/main.py &
python herramientas/emulador_motor.py
```

Para validar de punta a punta los 6 escenarios, ver
`specs/001-diagnostico-motor-industrial/quickstart.md`.

## Tests

```bash
pytest
```

## Estructura

Ver `specs/001-diagnostico-motor-industrial/plan.md` (seccion "Estructura del Proyecto") para
el detalle de cada modulo bajo `src/`.
