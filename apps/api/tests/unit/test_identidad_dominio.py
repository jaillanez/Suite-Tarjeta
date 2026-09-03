"""Tests unitarios del dominio de identidad."""

from __future__ import annotations

import dataclasses

import pytest

from tarjeta.modules.identidad.domain.consentimiento import Consentimiento, TipoConsentimiento
from tarjeta.modules.identidad.domain.errors import (
    PerfilDuplicado,
    TransicionIdentidadInvalida,
)
from tarjeta.modules.identidad.domain.events import PersonaRegistrada
from tarjeta.modules.identidad.domain.perfil import Perfil, TipoPerfil
from tarjeta.modules.identidad.domain.persona import (
    EstadoIdentidad,
    MetodoVerificacion,
    Persona,
)
from tarjeta.modules.identidad.domain.value_objects import Celular, Email
from tarjeta.shared.domain.errors import ValidationError
from tarjeta.shared.domain.types import Cuil, Dni, EntityId


def _persona() -> Persona:
    return Persona.registrar(
        dni=Dni("12345678"),
        cuil=Cuil("20123456786"),
        apellido="Gómez",
        nombre="Ana",
        celular=Celular("2644123456"),
    )


def test_registrar_emite_evento_y_estado_pendiente() -> None:
    p = _persona()
    assert p.estado_identidad is EstadoIdentidad.PENDIENTE
    assert not p.puede_canjear
    eventos = p.pull_events()
    assert any(isinstance(e, PersonaRegistrada) for e in eventos)


def test_verificar_identidad_habilita_canje() -> None:
    p = _persona()
    p.verificar_identidad(MetodoVerificacion.RENAPER)
    assert p.estado_identidad is EstadoIdentidad.VERIFICADA
    assert p.puede_canjear


def test_transicion_invalida_lanza_domain_error() -> None:
    p = _persona()
    p.verificar_identidad(MetodoVerificacion.RENAPER)
    with pytest.raises(TransicionIdentidadInvalida):
        p.verificar_identidad(MetodoVerificacion.RENAPER)  # ya verificada
    with pytest.raises(TransicionIdentidadInvalida):
        p.reintentar_identidad()  # no está rechazada


def test_ciclo_rechazo_y_reintento() -> None:
    p = _persona()
    p.rechazar_identidad("documento ilegible")
    assert p.estado_identidad is EstadoIdentidad.RECHAZADA
    p.reintentar_identidad()
    assert p.estado_identidad is EstadoIdentidad.PENDIENTE


def test_suspender_solo_desde_verificada() -> None:
    p = _persona()
    with pytest.raises(TransicionIdentidadInvalida):
        p.suspender("fraude")
    p.verificar_identidad(MetodoVerificacion.RENAPER)
    p.suspender("fraude")
    assert p.estado_identidad is EstadoIdentidad.SUSPENDIDA
    p.reactivar()
    assert p.estado_identidad is EstadoIdentidad.VERIFICADA


def test_no_dos_perfiles_ciudadano() -> None:
    p = _persona()
    with pytest.raises(PerfilDuplicado):
        p.agregar_perfil(Perfil(tipo=TipoPerfil.CIUDADANO))


def test_agregar_perfil_comercio() -> None:
    p = _persona()
    p.agregar_perfil(Perfil(tipo=TipoPerfil.COMERCIO, id_comercio=EntityId.new(), rol="CAJERO"))
    assert any(perf.tipo is TipoPerfil.COMERCIO for perf in p.perfiles)


def test_consentimiento_es_inmutable() -> None:
    c = Consentimiento.registrar(
        id_persona=EntityId.new(),
        tipo=TipoConsentimiento.TRATAMIENTO_DATOS,
        version_texto="v1",
        otorgado=True,
        ip="1.2.3.4",
        user_agent="pytest",
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        c.otorgado = False  # type: ignore[misc]


@pytest.mark.parametrize("valor", ["2644123456", "+54 264 412-3456"])
def test_celular_valido(valor: str) -> None:
    assert Celular(valor).value.isdigit()


@pytest.mark.parametrize("valor", ["123", "abcd"])
def test_celular_invalido(valor: str) -> None:
    with pytest.raises(ValidationError):
        Celular(valor)


def test_email_normaliza_y_valida() -> None:
    assert Email("Ana@Example.COM").value == "ana@example.com"
    with pytest.raises(ValidationError):
        Email("no-es-email")
