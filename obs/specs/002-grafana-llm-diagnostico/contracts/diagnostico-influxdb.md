# Contrato: espejo de Diagnostico en InfluxDB (measurement `diagnosticos`)

Feature: `002-grafana-llm-diagnostico`. Ver `data-model.md` para el detalle campo por campo
y la justificacion de diseno; este archivo es el contrato formal que consumen tanto
`src/almacenamiento/influx_repo.py` (escritor) como el panel de Grafana en `motor.json`
(lector) — si uno de los dos lados cambia, el otro se rompe.

## Interfaz de escritura

```python
def escribir_diagnostico(
    equipo_id: str,
    alerta_id: int,
    resultado: dict,
    fallo: bool,
    timestamp: str | None = None,
) -> None:
    """Espejo liviano de un Diagnostico en InfluxDB, solo para mostrarlo en el dashboard de
    Grafana (Historia 2, research.md). Best-effort: un fallo aca no debe afectar el
    pipeline de diagnostico/notificacion, que ya persistio el Diagnostico en SQLite."""
```

- `resultado`: el mismo dict que devuelve `src/diagnostico/parser.py::diagnosticar()` —
  claves esperadas `causa_probable`, `razonamiento`, `urgencia`, `accion_recomendada`,
  `confianza` (ver `_CLAVES_ESPERADAS` en `parser.py`). Si `fallo=True`, estas claves pueden
  venir vacias/`None` — la funcion las escribe igual, no las omite.
- `timestamp`: si no se pasa, usa `datetime.now(timezone.utc)` (mismo default que
  `sqlite_repo.crear_diagnostico`, que genera `generado_en` internamente).

## Punto de InfluxDB resultante

```
diagnosticos,equipo_id=<equipo_id> alerta_id=<alerta_id>i,causa_probable="...",razonamiento="...",urgencia="...",accion_recomendada="...",confianza="...",fallo=<true|false> <timestamp>
```

## Contrato de lectura (panel de Grafana)

El panel "Diagnostico IA" en `motor.json` MUST usar el query Flux documentado en
`data-model.md` (pivot + sort + limit 1) contra este mismo measurement/bucket. Si
`escribir_diagnostico` cambia el nombre de un field, el panel deja de mostrar ese dato
silenciosamente (Flux no tira error por un field ausente en un pivot) — cualquier cambio de
nombre de campo en la funcion de escritura MUST reflejarse en el mismo commit en el query
del panel.

## Casos borde cubiertos por este contrato

- **Sin ningun diagnostico todavia para el equipo**: el query no devuelve filas — el panel
  MUST mostrar un estado vacio explicito (FR-008 de `spec.md`), no un error.
- **`fallo=true`**: el punto se escribe con los campos de texto en blanco/`None` y
  `fallo=true` — el panel MUST distinguir este caso (ej. "diagnostico no disponible, fallo
  del nucleo cognitivo") de un diagnostico exitoso, en vez de mostrar campos vacios sin
  explicacion.
- **Falla la escritura a InfluxDB en si** (best-effort, ver `data-model.md`): el panel
  simplemente sigue mostrando el ultimo diagnostico que si se escribio con exito —
  comportamiento identico al de las anotaciones de `alertas` cuando `escribir_evento_alerta`
  falla.
