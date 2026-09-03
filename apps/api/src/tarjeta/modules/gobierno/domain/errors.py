"""Errores del módulo gobierno."""

from __future__ import annotations

from tarjeta.shared.domain.errors import (
    BusinessRuleViolation,
    PermissionDeniedError,
    ValidationError,
)


class PermisoDenegado(PermissionDeniedError):
    code = "permiso_denegado"


class MfaNoEnrolado(PermissionDeniedError):
    code = "mfa_no_enrolado"


class AutoaprobacionProhibida(BusinessRuleViolation):
    code = "autoaprobacion_prohibida"


class SolicitudNoAprobable(BusinessRuleViolation):
    code = "solicitud_no_aprobable"


class RangoInsuficiente(PermissionDeniedError):
    code = "rango_insuficiente"


class ParametroFueraDeRango(ValidationError):
    code = "parametro_fuera_de_rango"


class ParametroInexistente(ValidationError):
    code = "parametro_inexistente"
