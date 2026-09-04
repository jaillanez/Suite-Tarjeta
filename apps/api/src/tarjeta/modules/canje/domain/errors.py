"""Errores del módulo canje."""

from __future__ import annotations

from tarjeta.shared.domain.errors import (
    BusinessRuleViolation,
    ConflictError,
    PermissionDeniedError,
    ValidationError,
)


class TokenInvalido(ValidationError):
    code = "token_invalido"


class TokenVencido(BusinessRuleViolation):
    code = "token_vencido"


class TokenYaUsado(ConflictError):
    code = "token_ya_usado"


class TransicionCanjeInvalida(BusinessRuleViolation):
    code = "transicion_canje_invalida"


class ConfirmacionVencida(BusinessRuleViolation):
    code = "confirmacion_vencida"


class ConfirmadorInvalido(PermissionDeniedError):
    code = "confirmador_invalido"


class FueraDeVentanaAnulacion(PermissionDeniedError):
    code = "fuera_de_ventana_anulacion"


class MontoInvalido(ValidationError):
    code = "monto_invalido"


class LimiteSinConexion(BusinessRuleViolation):
    code = "limite_sin_conexion"


class CiudadanoNoIdentificado(ValidationError):
    code = "ciudadano_no_identificado"
