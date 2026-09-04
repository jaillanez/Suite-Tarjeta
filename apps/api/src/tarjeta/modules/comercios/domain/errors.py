"""Errores del módulo comercios."""

from __future__ import annotations

from tarjeta.shared.domain.errors import (
    BusinessRuleViolation,
    ConflictError,
    PermissionDeniedError,
    ValidationError,
)


class NoEsComerciante(BusinessRuleViolation):
    code = "no_es_comerciante"


class TransicionComercioInvalida(BusinessRuleViolation):
    code = "transicion_comercio_invalida"


class TransicionSucursalInvalida(BusinessRuleViolation):
    code = "transicion_sucursal_invalida"


class ConvenioNoAceptado(BusinessRuleViolation):
    code = "convenio_no_aceptado"


class PermisoComercioDenegado(PermissionDeniedError):
    code = "permiso_comercio_denegado"


class ComercioNoHabilitado(PermissionDeniedError):
    """§12.1: el comercio no está aprobado; solo puede usar funciones de solicitud."""

    code = "comercio_no_habilitado"


class InvitacionInvalida(ValidationError):
    code = "invitacion_invalida"


class InvitacionExpirada(BusinessRuleViolation):
    code = "invitacion_expirada"


class PinInvalido(ValidationError):
    code = "pin_invalido"


class CajeroBloqueado(BusinessRuleViolation):
    code = "cajero_bloqueado"


class DispositivoNoRegistrado(PermissionDeniedError):
    code = "dispositivo_no_registrado"


class UbicacionRequerida(ValidationError):
    code = "ubicacion_requerida"


class ComercioDuplicado(ConflictError):
    code = "comercio_duplicado"


class TurnoAbiertoExistente(ConflictError):
    code = "turno_abierto_existente"
