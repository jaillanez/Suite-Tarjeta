"""Errores del módulo promociones."""

from __future__ import annotations

from tarjeta.shared.domain.errors import (
    BusinessRuleViolation,
    ConflictError,
    ValidationError,
)


class TransicionPromocionInvalida(BusinessRuleViolation):
    code = "transicion_promocion_invalida"


class PromocionActivaInmutable(BusinessRuleViolation):
    code = "promocion_activa_inmutable"


class SucursalAjena(BusinessRuleViolation):
    code = "sucursal_ajena"


class TopeInvalido(ValidationError):
    code = "tope_invalido"


class MecanicaInvalida(ValidationError):
    code = "mecanica_invalida"


class SegmentoNoAplica(BusinessRuleViolation):
    code = "segmento_no_aplica"


class TopeAgotado(ConflictError):
    code = "tope_agotado"
