"""Errores del módulo padron."""

from __future__ import annotations

from tarjeta.shared.domain.errors import BusinessRuleViolation, DomainError


class PadronNoDisponible(DomainError):
    """El endpoint municipal no respondió. Se usa el último estado conocido."""

    code = "padron_no_disponible"


class RespuestaPadronInvalida(BusinessRuleViolation):
    """La respuesta del endpoint no respeta el contrato acordado."""

    code = "respuesta_padron_invalida"
