"""Autenticación de la búsqueda de pacientes.

La contraseña se lee de ``SEARCH_PASSWORD`` (env o ``st.secrets``). No hay
contraseña por defecto: si no está configurada, la búsqueda queda deshabilitada.
La comparación usa ``hmac.compare_digest`` y se limita el número de intentos.
"""

from __future__ import annotations

import hmac
import time
from dataclasses import dataclass, field

from .config import get_search_password, is_search_enabled

__all__ = [
    "AttemptLimiter",
    "get_search_password",
    "is_search_enabled",
    "verify_search_password",
]


def verify_search_password(input_password: str) -> bool:
    """Retorna True si ``input_password`` coincide con la contraseña activa.

    Si no hay contraseña configurada devuelve ``False`` (nunca autentica por
    defecto). Usa ``hmac.compare_digest`` para evitar timing attacks.
    """
    active = get_search_password()
    if active is None:
        return False
    return bool(hmac.compare_digest(active, str(input_password or "")))


@dataclass
class AttemptLimiter:
    """Limitador de intentos en memoria (por sesión de Streamlit).

    No es un sistema de autenticación completo: es una barrera adicional
    contra fuerza bruta accidental. Para producción se recomienda un proveedor
    de identidad (OIDC) o una tabla de usuarios con argon2/bcrypt.
    """

    max_attempts: int = 5
    window_seconds: int = 300
    _attempts: list[float] = field(default_factory=list)

    def _prune(self, now: float) -> None:
        cutoff = now - self.window_seconds
        self._attempts = [t for t in self._attempts if t > cutoff]

    def is_blocked(self) -> bool:
        now = time.monotonic()
        self._prune(now)
        return len(self._attempts) >= self.max_attempts

    def register_failure(self) -> None:
        now = time.monotonic()
        self._prune(now)
        self._attempts.append(now)

    def reset(self) -> None:
        self._attempts.clear()

    def remaining(self) -> int:
        now = time.monotonic()
        self._prune(now)
        return max(0, self.max_attempts - len(self._attempts))
