"""Errores del módulo grupo."""

from __future__ import annotations

from tarjeta.shared.domain.errors import (
    BusinessRuleViolation,
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
)


class NoPuedeCrearGrupo(BusinessRuleViolation):
    """Solo un Black por mérito propio y al día puede crear grupo (§10.1)."""

    code = "no_puede_crear_grupo"


class YaPerteneceAGrupo(ConflictError):
    """Una persona, un grupo (§10.2): no puede estar en dos a la vez."""

    code = "ya_pertenece_a_grupo"


class GrupoInexistente(NotFoundError):
    code = "grupo_inexistente"


class MiembroInexistente(NotFoundError):
    code = "miembro_inexistente"


class NoEsTitular(PermissionDeniedError):
    code = "no_es_titular"


class InvitacionInvalida(BusinessRuleViolation):
    code = "invitacion_invalida"


class InvitacionVencida(BusinessRuleViolation):
    code = "invitacion_vencida"
