# Contrato: Notificacion por Telegram (Nivel 0)

Interfaz externa de salida hacia el operador (FR-006, Historia de Usuario 2). Nivel 0 segun
D2: solo push, sin comandos entrantes ni acciones de escritura.

## Disparador

Se envia un mensaje cuando `diagnostico-modulo.md` devuelve un resultado (exitoso o
fallido) para una alerta nueva (no en cooldown).

## Formato del mensaje

```
[SEVERIDAD] Motor M-01 | Linea A | Planta 1
Variable: temperatura = 87.3 C (umbral: 75 C)

Causa probable: degradacion del sistema de refrigeracion (filtro obstruido o ventilador con caudal reducido)
Urgencia: MEDIA | Confianza: ALTA

Accion recomendada: Inspeccionar circuito de enfriamiento antes de las proximas 8 horas de operacion.
```

Si el diagnostico fallo (`fallo: true`, FR-013), se envia igual la alerta cruda sin la
seccion de causa/accion, con una nota explicita de que el diagnostico no pudo generarse:

```
[ALERTA] Motor M-01 | Linea A | Planta 1
Variable: temperatura = 87.3 C (umbral: 75 C)

Diagnostico no disponible (fallo temporal del servicio de IA). Revisar manualmente.
```

## Transporte

Llamada HTTP directa a la Bot API de Telegram (`https://api.telegram.org/bot<token>/
sendMessage`) via `httpx` (ver `research.md`). Token del bot y `chat_id` del canal
operativo via variables de entorno (`.env`, D8).

## Manejo de errores

Si la llamada a la Bot API falla, se reintenta con backoff simple (hasta 3 intentos); si
sigue fallando, se loguea el error pero no se bloquea el resto del pipeline — la `Alerta` y
el `Diagnostico` ya quedaron persistidos independientemente del resultado de la
notificacion.
