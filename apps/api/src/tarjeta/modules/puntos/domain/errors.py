"""Errores del módulo puntos."""

from __future__ import annotations

from tarjeta.shared.domain.errors import (
    BusinessRuleViolation,
    ConflictError,
)


class SaldoInsuficiente(BusinessRuleViolation):
    code = "saldo_insuficiente"


class ItemNoDisponible(BusinessRuleViolation):
    code = "item_no_disponible"


class StockAgotado(ConflictError):
    code = "stock_agotado"


class MonedasNoConvertibles(BusinessRuleViolation):
    """PC y PM no se convierten entre sí por ningún camino (§09.1)."""

    code = "monedas_no_convertibles"


class CanjeContraTasasDeshabilitado(BusinessRuleViolation):
    """El canje contra tasas requiere ordenanza; el feature flag está apagado (§09.1)."""

    code = "canje_contra_tasas_deshabilitado"
