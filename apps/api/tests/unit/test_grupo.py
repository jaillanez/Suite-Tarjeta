"""Unit: dominio del grupo familiar y herencia de nivel (§10)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from tarjeta.modules.ciudadania.domain.nivel import Nivel, NivelOrigen
from tarjeta.modules.ciudadania.domain.perfil_ciudadano import PerfilCiudadano
from tarjeta.modules.grupo.domain.errors import InvitacionVencida
from tarjeta.modules.grupo.domain.grupo import Grupo
from tarjeta.modules.grupo.domain.invitacion import TEXTO_DECLARACION, Invitacion
from tarjeta.modules.grupo.domain.miembro import Miembro
from tarjeta.modules.grupo.domain.tipos import (
    EstadoGrupo,
    EstadoMiembro,
    ModoBilletera,
    RolGrupo,
)
from tarjeta.shared.domain.types import EntityId


def _perfil() -> PerfilCiudadano:
    return PerfilCiudadano.crear(EntityId.new())  # PLATINO / PROPIO


# --------------------------------------------------------------- herencia de nivel


def test_black_propio_no_cae_cuando_cae_el_titular() -> None:
    p = _perfil()
    p.recalcular(al_dia=True, excepcion_black_vigente=False, motivo="propio")
    assert p.nivel is Nivel.BLACK and p.nivel_origen is NivelOrigen.PROPIO
    # El titular cae (hereda_black=False), pero este miembro está al día por su cuenta.
    p.recalcular(al_dia=True, excepcion_black_vigente=False, hereda_black=False, motivo="titular")
    assert p.nivel is Nivel.BLACK and p.nivel_origen is NivelOrigen.PROPIO


def test_heredado_sube_y_cae_con_el_titular() -> None:
    p = _perfil()  # PLATINO
    p.recalcular(al_dia=False, excepcion_black_vigente=False, hereda_black=True, motivo="ingreso")
    assert p.nivel is Nivel.BLACK and p.nivel_origen is NivelOrigen.HEREDADO_GRUPO
    p.recalcular(al_dia=False, excepcion_black_vigente=False, hereda_black=False, motivo="cae")
    assert p.nivel is Nivel.PLATINO and p.nivel_origen is NivelOrigen.PROPIO


def test_al_dia_pisa_a_la_herencia() -> None:
    # Estar al día da PROPIO aunque también herede: el mérito propio manda.
    p = _perfil()
    p.recalcular(al_dia=True, excepcion_black_vigente=False, hereda_black=True, motivo="ambos")
    assert p.nivel is Nivel.BLACK and p.nivel_origen is NivelOrigen.PROPIO


# --------------------------------------------------------------- agregado Grupo


def test_grupo_crear_cambiar_modo_disolver() -> None:
    g = Grupo.crear(id_titular="t1", modo_billetera=ModoBilletera.COMUN)
    assert g.estado is EstadoGrupo.ACTIVO and g.activo
    anterior = g.cambiar_modo(ModoBilletera.INDIVIDUAL)
    assert anterior is ModoBilletera.COMUN and g.modo_billetera is ModoBilletera.INDIVIDUAL
    g.suceder_titular("t2")
    assert g.id_titular == "t2"
    g.disolver(id_miembros=["m1", "m2"])
    assert g.estado is EstadoGrupo.DISUELTO and not g.activo


def test_miembro_estados() -> None:
    m = Miembro.crear(id_grupo=EntityId.new(), id_persona="p", rol=RolGrupo.MIEMBRO)
    assert m.activo
    m.suspender()
    assert m.estado is EstadoMiembro.SUSPENDIDO and not m.activo
    m.reactivar()
    assert m.activo
    m.dar_de_baja()
    assert m.estado is EstadoMiembro.BAJA


# --------------------------------------------------------------- invitación


def test_invitacion_declaracion_y_aceptacion() -> None:
    inv = Invitacion.crear(id_grupo=EntityId.new(), id_titular="t", ip_titular="1.2.3.4")
    assert inv.texto_declaracion == TEXTO_DECLARACION
    assert inv.vigente(datetime.now(UTC))
    inv.aceptar(id_invitado="inv", ahora=datetime.now(UTC))
    assert inv.aceptada_por == "inv"


def test_invitacion_vencida_no_se_acepta() -> None:
    inv = Invitacion.crear(id_grupo=EntityId.new(), id_titular="t", ip_titular="1.2.3.4")
    futuro = inv.vence_en + timedelta(seconds=1)
    with pytest.raises(InvitacionVencida):
        inv.aceptar(id_invitado="inv", ahora=futuro)
