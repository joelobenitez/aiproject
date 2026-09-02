"""Entrypoint real del servicio (`python -m src`).

No poner logica aca: `src/main.py` debe importarse siempre como `src.main` (nunca ejecutarse
directo con `python src/main.py`), o `api.py` (`from src import main as servicio`) termina
importando una SEGUNDA instancia del modulo con su propio estado en memoria — `_detector`,
`_cola`, `_ultima_lectura_en` quedarian duplicados y desincronizados del proceso real
(hallazgo del barrido de robustez, T005/FR-002: `ultima_lectura_en` en /health nunca se
actualizaba por esto).
"""
from src.main import main

if __name__ == "__main__":
    main()
