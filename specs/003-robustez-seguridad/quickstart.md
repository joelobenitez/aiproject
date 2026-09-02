# Quickstart — Validacion de robustez y seguridad del servicio

Feature: Robustez y seguridad del servicio de deteccion (`003-robustez-seguridad`)

Escenarios de validacion de punta a punta para las 6 historias de `spec.md`. Requiere el
codigo de esta spec ya implementado (`tasks.md`).

## Prerrequisitos

- Docker Desktop corriendo, Mosquitto nativo de Windows detenido si se corre el emulador
  contra `localhost:1883` (`memory/risks.md`).
- `mosquitto/passwd` generado (`README.md` — gitignoreado, D20/D22; el `broker` ahora es
  `build: ./mosquitto`, no una imagen con bind-mounts, ver D22).
- `.env` con las credenciales nuevas: `MQTT_USERNAME`/`MQTT_PASSWORD`, `API_TOKEN`,
  `GRAFANA_ADMIN_PASSWORD` (ya no tiene default inseguro — el stack no arranca sano sin
  setearla).
- `docker compose up -d --build` (no un `up -d` simple — hay cambios de codigo y de
  `docker-compose.yml`, ver riesgo conocido en `memory/risks.md`).
- `data/aiproject.db` borrado antes de arrancar, para que se recree con la tabla
  `detector_estado` nueva (D20, FR-016).

## Escenario 1 — La ingesta sobrevive a InfluxDB caido (Historia 1, SC-001)

1. Con el stack levantado, `docker compose stop influxdb`.
2. Correr el emulador (`herramientas/emulador_motor.py`, cualquier escenario).
3. **Esperado**: los logs de `servicio` muestran la excepcion de escritura a InfluxDB
   capturada (no una traza que termine el proceso), y `GET /health` sigue respondiendo `ok`.
4. `docker compose start influxdb`, seguir publicando con el emulador.
5. **Esperado**: las lecturas nuevas se escriben en InfluxDB sin reiniciar `servicio`, y el
   campo `ultima_lectura_en` de `/health` se actualiza con cada lectura procesada.

## Escenario 2 — Una alerta lenta no bloquea la ingesta (Historia 2, SC-002)

1. Forzar (o mockear temporalmente) una llamada al nucleo de IA con latencia alta.
2. Durante esa ventana, publicar lecturas de otras variables con el emulador.
3. **Esperado**: esas lecturas quedan registradas en InfluxDB y evaluadas por el detector
   sin esperar a que termine el diagnostico en curso — confirmar por timestamp que no hay un
   salto/hueco en la serie de tiempo.

## Escenario 3 — El ruido no genera alertas de mas (Historia 3, SC-003)

1. Correr el escenario D del emulador (operacion normal con ruido) 3 veces seguidas.
2. **Esperado**: 0 alertas generadas en las 3 corridas (`SELECT count(*) FROM alerta` sin
   crecer).
3. Correr el escenario A (temperatura sube sostenido).
4. **Esperado**: exactamente 1 alerta por cruce sostenido — no una por cada lectura ruidosa
   una vez que ya esta arriba del umbral.

## Escenario 4 — El cooldown sobrevive a un reinicio (Historia 4, SC-004)

1. Generar una alerta (cualquier escenario), confirmar que `detector_estado` tiene la fila
   correspondiente con `cooldown_hasta` en el futuro.
2. `docker compose restart servicio`.
3. Seguir publicando lecturas que sigan cruzando el mismo umbral.
4. **Esperado**: no se genera un evento de alerta nuevo mientras el cooldown original siga
   vigente (comparar timestamps contra el `cooldown_hasta` guardado antes del reinicio).
5. Publicar una lectura con un `timestamp` adelantado mas de 5 minutos respecto del reloj
   real.
6. **Esperado**: el log muestra el warning de skew, y el cooldown calculado usa el reloj del
   servidor (no queda un `cooldown_hasta` absurdamente en el futuro).

## Escenario 5 — Nadie sin credenciales inyecta datos ni gasta la API (Historia 5, SC-006)

1. Con un cliente MQTT sin usuario/password, intentar publicar al broker.
2. **Esperado**: la conexion o la publicacion es rechazada por Mosquitto.
3. Con `curl`, llamar `POST /diagnosticar/<id>` sin el header `X-API-Token` (o con un valor
   incorrecto).
4. **Esperado**: respuesta 401, y los logs de `servicio` confirman que NO se llamo a
   `api.anthropic.com` para ese pedido.
5. Confirmar que `netstat`/`docker port servicio` ya no expone `8000` ni `8086` mas alla de
   `127.0.0.1`.
6. Confirmar en `console.anthropic.com` que la key vieja (expuesta el 2026-09-01) esta
   revocada y la key en `.env` es una nueva.

## Escenario 6 — Un resumen fallido se puede reintentar (Historia 6, SC-005)

1. Forzar un fallo del nucleo de IA (ej. `ANTHROPIC_API_KEY` invalida temporalmente, o mock).
2. Pedir el diagnostico de una alerta ALERTA via `POST /diagnosticar/<id>` — queda
   `fallo: true`.
3. Restaurar la key valida, pedir el mismo `POST /diagnosticar/<id>` de nuevo.
4. **Esperado**: esta vez se genera un resumen exitoso (`fallo: false`), sobrescribiendo el
   registro anterior — sin tocar la base a mano.
5. Disparar dos `POST /diagnosticar/<id>` simultaneos para una alerta sin diagnostico previo
   (ej. con `curl` en paralelo o un script con `threading`).
6. **Esperado**: los logs muestran una sola llamada a `api.anthropic.com` para esa alerta, y
   ninguna de las dos respuestas HTTP es un error crudo sin manejar.

## Regresion — contratos que no cambian (FR-014)

1. Confirmar que el topico MQTT sigue siendo de 5 partes con el mismo payload
   `{valor, unidad, timestamp}` (el emulador y el simulador Modbus RTU no cambian de
   contrato).
2. Confirmar que `POST /diagnosticar/<alerta_id>` sigue siendo la misma ruta (ahora con el
   header de token adicional).
3. Confirmar que las tablas/measurements siguen llamandose `diagnostico`/`diagnosticos` (D17)
   y que el formato del mensaje de Telegram no cambio.
4. Suite completa: `pytest` en verde (39/39 como piso + los tests nuevos de esta spec).
