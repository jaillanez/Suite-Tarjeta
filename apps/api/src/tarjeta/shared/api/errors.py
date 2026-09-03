"""Traducción de errores de dominio a respuestas HTTP.

El dominio lanza `DomainError`; acá (y solo acá) se decide el código HTTP. Ningún
otro lugar mezcla reglas de negocio con detalles de transporte.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from tarjeta.shared.domain.errors import (
    AuthenticationError,
    BusinessRuleViolation,
    ConflictError,
    DomainError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)

_STATUS_BY_TYPE: dict[type[DomainError], int] = {
    ValidationError: 422,
    NotFoundError: 404,
    ConflictError: 409,
    BusinessRuleViolation: 409,
    PermissionDeniedError: 403,
    AuthenticationError: 401,
}


def _status_for(exc: DomainError) -> int:
    for klass in type(exc).__mro__:
        if klass in _STATUS_BY_TYPE:
            return _STATUS_BY_TYPE[klass]
    return 400


async def _domain_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)
    return JSONResponse(
        status_code=_status_for(exc),
        content={"error": {"code": exc.code, "message": exc.message}},
    )


def register_error_handlers(app: FastAPI) -> None:
    app.add_exception_handler(DomainError, _domain_error_handler)
