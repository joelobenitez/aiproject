# aiproject — Monitoreo de Motor Industrial con Diagnostico Inteligente via Claude

MVP del feature `001-diagnostico-motor-industrial` (cerrado — spec/plan jubilados en
`obs/specs/001-diagnostico-motor-industrial/`, D14) mas el feature
`002-grafana-llm-diagnostico` (cerrado — spec/plan jubilados en
`obs/specs/002-grafana-llm-diagnostico/`, D16). Ver `memory/decisions.md` para el historial
completo de decisiones.

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

El broker MQTT requiere credenciales (D20/FR-009) — generar `mosquitto/passwd` una vez antes
del primer build (el archivo esta en `.gitignore`, no viaja con el repo, D22):

```bash
docker run --rm -v "$(pwd)/mosquitto:/mosquitto/config" eclipse-mosquitto:2 \
  mosquitto_passwd -b -c /mosquitto/config/passwd <usuario> <password>
```

Completar `MQTT_USERNAME`/`MQTT_PASSWORD` en `.env` con ese mismo usuario/password.

```bash
docker compose up -d --build broker influxdb
python -m src &
python herramientas/emulador_motor.py
```

Para validar de punta a punta los 6 escenarios del MVP, ver
`obs/specs/001-diagnostico-motor-industrial/quickstart.md`.

### Plugin LLM de Grafana (feature 002)

`docker-compose.yml` instala y provisiona el plugin oficial `grafana-llm-app` en el
servicio `grafana` (`GF_INSTALL_PLUGINS`, version pinneada; `GF_FEATURE_TOGGLES_ENABLE:
dashgpt`) — no son variables de `.env`, estan fijadas directamente en el compose. Reusa
`ANTHROPIC_API_KEY` de `.env` via `grafana/provisioning/plugins/apps.yaml`. Detalle completo
(schema verificado a mano, bug del modelo default del plugin y su fix) en
`obs/specs/002-grafana-llm-diagnostico/research.md`; escenarios de validacion en
`obs/specs/002-grafana-llm-diagnostico/quickstart.md`.

## Tests

```bash
pytest
```

## Estructura

Ver `obs/specs/001-diagnostico-motor-industrial/plan.md` (seccion "Estructura del Proyecto")
para el detalle de cada modulo bajo `src/`.
