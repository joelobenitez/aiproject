# Modelo de Datos — Fase 1

Feature: Robustez y seguridad del servicio de deteccion (`003-robustez-seguridad`)

Una tabla nueva en SQLite (persistir el estado del detector, H4) y un cambio de
comportamiento (no de schema) en la tabla `diagnostico` existente (H5).

---

## Tabla nueva: `detector_estado` (SQLite)

Reemplaza el diccionario `Detector._estado` (hoy solo en memoria) como fuente de verdad del
cooldown, para que sobreviva a un reinicio del proceso/contenedor.

| Columna | Tipo | Notas |
|---|---|---|
| `equipo_id` | TEXT | Parte de la clave primaria compuesta, junto con `variable`. |
| `variable` | TEXT | Idem. |
| `severidad` | TEXT | `NORMAL` / `ALERTA` / `CRITICO` — el ultimo estado clasificado para esta clave. |
| `cooldown_hasta` | TEXT | ISO 8601, o `NULL` si no hay cooldown activo (severidad `NORMAL`). |

```sql
CREATE TABLE IF NOT EXISTS detector_estado (
    equipo_id TEXT NOT NULL,
    variable TEXT NOT NULL,
    severidad TEXT NOT NULL,
    cooldown_hasta TEXT,
    PRIMARY KEY (equipo_id, variable)
);
```

**Lectura**: una sola vez, al arrancar el proceso (`Detector.__init__` o una funcion de carga
en `main.py` que popula `self._estado` antes del primer `evaluar()`). No hay una consulta a
SQLite por cada lectura MQTT (Principio II).

**Escritura**: `INSERT OR REPLACE` cada vez que `evaluar()` cambia el estado de una clave
(nueva alerta, escalada, o vuelta a `NORMAL` cruzando la banda muerta) — no en cada lectura,
solo en cada cambio de estado. Mismo criterio de frecuencia que ya tiene `crear_alerta`.

**Que NO se persiste**: el contador de lecturas consecutivas de la confirmacion de H3
(`lecturas_consecutivas` en memoria) — es efimero a proposito (ver `plan.md`, seccion H3);
perderlo en un reinicio como mucho retrasa unos segundos la proxima confirmacion.

**Migracion**: `data/aiproject.db` se borra y se recrea al desplegar esta spec (D20,
FR-016) — mismo patron que D17. `inicializar_schema()` sigue siendo idempotente
(`CREATE TABLE IF NOT EXISTS`).

---

## Tabla existente: `diagnostico` — cambio de comportamiento, no de schema

Las columnas no cambian (siguen siendo las de D17: `resumen_ejecutivo`, `hechos_destacados`,
`fallo`, `generado_en`, mas `alerta_id UNIQUE`). Lo que cambia es la operacion de escritura:

- **Antes (H5):** `crear_diagnostico` hace `INSERT`. Un segundo intento para el mismo
  `alerta_id` viola la restriccion `UNIQUE` — por eso `diagnosticar_bajo_demanda` nunca
  reintentaba, solo devolvia el registro existente (exitoso o fallido) como "cacheado".
- **Despues:** `crear_diagnostico` hace `INSERT ... ON CONFLICT(alerta_id) DO UPDATE SET
  resumen_ejecutivo = excluded.resumen_ejecutivo, hechos_destacados =
  excluded.hechos_destacados, fallo = excluded.fallo, generado_en = excluded.generado_en`
  (sintaxis `UPSERT` de SQLite, disponible desde 3.24). `diagnosticar_bajo_demanda` solo
  trata como "cacheado" (`cacheado: true`, sin llamar a Claude) un registro con `fallo = 0`;
  un registro con `fallo = 1` dispara el mismo camino que si no existiera ninguno.

---

## Credenciales nuevas (no son datos de dominio, son configuracion — `.env`)

No se agregan tablas para esto; viven en variables de entorno, mismo patron que las
credenciales existentes (D8):

| Variable | Uso |
|---|---|
| `MQTT_USERNAME` / `MQTT_PASSWORD` | Cliente MQTT del `servicio` y del emulador, contra el broker autenticado (H7). |
| `API_TOKEN` | Header que debe presentar un cliente HTTP para ejecutar `POST /diagnosticar/<alerta_id>` (H7). |
| `GRAFANA_ADMIN_PASSWORD` | Ya existia; pierde su fallback inseguro `:-admin` (FR-012). |
