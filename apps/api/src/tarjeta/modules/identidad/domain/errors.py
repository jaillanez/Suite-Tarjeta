"""Errores del dominio de identidad."""

from __future__ import annotations

from tarjeta.shared.domain.errors import (
    AuthenticationError,
    BusinessRuleViolation,
    ConflictError,
    PermissionDeniedError,
    ValidationError,
)


class TransicionIdentidadInvalida(BusinessRuleViolation):
    code = "transicion_identidad_invalida"


class PerfilDuplicado(ConflictError):
    code = "perfil_duplicado"


class PersonaYaRegistrada(ConflictError):
    code = "persona_ya_registrada"


class PerfilNoAsignado(PermissionDeniedError):
    code = "perfil_no_asignado"


class CredencialesInvalidas(AuthenticationError):
    code = "credenciales_invalidas"


class MfaRequerido(AuthenticationError):
    code = "mfa_requerido"


class DispositivoNoRegistrado(PermissionDeniedError):
    code = "dispositivo_no_registrado"


class MfaNoEnrolado(PermissionDeniedError):
    code = "mfa_no_enrolado"


class OtpInvalido(ValidationError):
    code = "otp_invalido"


class ConsentimientoObligatorioFaltante(BusinessRuleViolation):
    code = "consentimiento_obligatorio_faltante"


class ReusoDeRefreshToken(AuthenticationError):
    code = "reuso_de_refresh_token"
