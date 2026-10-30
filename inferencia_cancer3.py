"""Shim de compatibilidad del punto de entrada original.

El proyecto original se ejecutaba como ``streamlit run inferencia_cancer3.py``.
Tras el refactor (FASE 2), la app real vive en ``app.py`` y este archivo es solo
un *shim* delgado que importa y ejecuta su ``main()``.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Raíz del proyecto (por si se ejecuta este fichero directamente)
root = Path(__file__).resolve().parent
sys.path.insert(0, str(root / "src"))
sys.path.insert(0, str(root))

from app import main  # noqa: E402


if __name__ == "__main__":
    main()
