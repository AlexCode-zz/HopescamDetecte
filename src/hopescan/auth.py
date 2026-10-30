"""Autenticación de la búsqueda de pacientes.

Contraseña leída de secrets/env con fallback de desarrollo; comparación
segura con ``hmac.compare_digest``.
"""

from __future__ import annotations

import hmac
from .config import get_search_password


def verify_search_password(input_password: str) -> bool:
    """Retorna True si ``input_password`` coincide con la contraseña activa.

    Usa ``hmac.compare_digest`` para comparación segura contra timing attacks.
    """
    active = get_search_password()
    return bool(hmac.compare_digest(active, str(input_password)))
