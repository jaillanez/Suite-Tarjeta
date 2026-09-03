"""Jerarquía de errores de dominio.

`DomainError` y sus subclases son independientes de HTTP. La capa `api` las traduce
a respuestas (ver `shared/api/errors.py`). El dominio nunca conoce códigos HTTP.
"""

from __future__ import annotations


class DomainError(Exception):
    """Error base del dominio. Todo error de negocio hereda de acá."""

    code: str = "domain_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code


class ValidationError(DomainError):
    """Un value object o invariante recibió datos inválidos."""

    code = "validation_error"


class BusinessRuleViolation(DomainError):
    """Se intentó una operación que viola una regla de negocio."""

    code = "business_rule_violation"


class NotFoundError(DomainError):
    """No existe el agregado o entidad solicitada."""

    code = "not_found"


class ConflictError(DomainError):
    """Conflicto de estado (p. ej. unicidad o concurrencia)."""

    code = "conflict"


class PermissionDeniedError(DomainError):
    """El actor no tiene permiso para esta operación."""

    code = "permission_denied"


class AuthenticationError(DomainError):
    """Credenciales o segundo factor inválidos. Nunca revela si el usuario existe."""

    code = "authentication_failed"
