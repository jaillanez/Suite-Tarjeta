"""Errores del módulo contenido."""

from __future__ import annotations

from tarjeta.shared.domain.errors import (
    BusinessRuleViolation,
    ConflictError,
    NotFoundError,
)


class CuotaAgotada(ConflictError):
    """No quedan créditos de generación este mes (§11.9)."""

    code = "cuota_agotada"


class ProveedorNoConfigurado(BusinessRuleViolation):
    """El adaptador real de IA no se puede activar sin configuración explícita (§11.2)."""

    code = "proveedor_no_configurado"


class GeneracionFallida(BusinessRuleViolation):
    """Falló la generación en el proveedor; el crédito se devuelve (§11.9)."""

    code = "generacion_fallida"


class PiezaInexistente(NotFoundError):
    code = "pieza_inexistente"


class PiezaNoPublicable(BusinessRuleViolation):
    """Una pieza rechazada (o no aprobada) no puede publicarse por ningún camino (§11.6)."""

    code = "pieza_no_publicable"


class TransicionPiezaInvalida(BusinessRuleViolation):
    code = "transicion_pieza_invalida"
