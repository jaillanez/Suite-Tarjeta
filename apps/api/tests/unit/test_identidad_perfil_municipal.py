"""Unit: cambio a perfil municipal exige dispositivo registrado; timeouts por perfil."""

from __future__ import annotations

from datetime import date
from typing import Any

import pytest

from tarjeta.config import Settings
from tarjeta.modules.identidad.application.cambiar_perfil import CambiarPerfil
from tarjeta.modules.identidad.application.deps import Puertos
from tarjeta.modules.identidad.domain.dispositivo import Dispositivo
from tarjeta.modules.identidad.domain.errors import (
    DispositivoNoRegistrado,
    MfaNoEnrolado,
    PerfilNoAsignado,
)
from tarjeta.modules.identidad.domain.perfil import Perfil, TipoPerfil
from tarjeta.modules.identidad.domain.persona import MetodoVerificacion, Persona
from tarjeta.modules.identidad.domain.ports import MfaEstado
from tarjeta.modules.identidad.domain.value_objects import Celular
from tarjeta.shared.domain.types import Dni, EntityId


def _persona_municipal() -> Persona:
    p = Persona.registrar(
        dni=Dni("12345678"),
        fecha_nacimiento=date(1990, 1, 1),
        celular=Celular("2644123456"),
    )
    p.verificar_identidad(MetodoVerificacion.PRESENCIAL)
    p.agregar_perfil(Perfil(tipo=TipoPerfil.MUNICIPAL))
    return p


class _FakePersonas:
    def __init__(self, persona: Persona) -> None:
        self._persona = persona

    async def obtener_por_id(self, id: EntityId) -> Persona:
        return self._persona


class _FakeDispositivos:
    def __init__(self, dispositivos: list[Dispositivo]) -> None:
        self._ds = dispositivos

    async def listar_por_persona(self, id_persona: EntityId) -> list[Dispositivo]:
        return self._ds


class _FakeTokens:
    def crear(
        self, *, id_persona: str, perfil: str, permisos: list[str], huella: str | None = None
    ) -> str:
        return "access"


class _FakeRefresh:
    async def emitir(self, id_persona: EntityId, perfil: str) -> str:
        return "refresh"


class _FakeOutbox:
    async def escribir(self, eventos: list[Any]) -> None:
        return None


class _FakeUow:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class _FakeMfa:
    def __init__(self, estado: MfaEstado | None) -> None:
        self._estado = estado

    async def obtener(self, id_persona: EntityId) -> MfaEstado | None:
        return self._estado


_MFA_ACTIVO = MfaEstado(secreto="s", activo=True, codigos_recuperacion=[])


def _puertos(
    persona: Persona,
    dispositivos: list[Dispositivo],
    *,
    mfa: MfaEstado | None = _MFA_ACTIVO,
) -> Puertos:
    return Puertos(
        uow=_FakeUow(),  # type: ignore[arg-type]
        personas=_FakePersonas(persona),  # type: ignore[arg-type]
        credenciales=None,  # type: ignore[arg-type]
        dispositivos=_FakeDispositivos(dispositivos),  # type: ignore[arg-type]
        consentimientos=None,  # type: ignore[arg-type]
        mfa=_FakeMfa(mfa),  # type: ignore[arg-type]
        textos=None,  # type: ignore[arg-type]
        outbox=_FakeOutbox(),  # type: ignore[arg-type]
        hasher=None,  # type: ignore[arg-type]
        totp=None,  # type: ignore[arg-type]
        tokens=_FakeTokens(),  # type: ignore[arg-type]
        refresh=_FakeRefresh(),  # type: ignore[arg-type]
        envio_otp=None,  # type: ignore[arg-type]
        almacen_otp=None,  # type: ignore[arg-type]
        rate_limiter=None,  # type: ignore[arg-type]
    )


async def test_municipal_sin_dispositivo_falla() -> None:
    persona = _persona_municipal()
    puertos = _puertos(persona, [])
    with pytest.raises(DispositivoNoRegistrado):
        await CambiarPerfil(puertos).ejecutar(id_persona=str(persona.id), clave_destino="MUNICIPAL")


async def test_municipal_con_dispositivo_autorizado_ok() -> None:
    persona = _persona_municipal()
    disp = Dispositivo.registrar(
        id_persona=persona.id, nombre_declarado="tel", plataforma="android", huella="h"
    )
    disp.autorizar_para_municipal()
    puertos = _puertos(persona, [disp])
    tokens = await CambiarPerfil(puertos).ejecutar(
        id_persona=str(persona.id), clave_destino="MUNICIPAL", huella="h"
    )
    assert tokens.access_token == "access"


async def test_municipal_sin_mfa_enrolado_falla() -> None:
    # §05.3: con dispositivo autorizado pero sin MFA enrolado, no puede operar como municipal.
    persona = _persona_municipal()
    disp = Dispositivo.registrar(
        id_persona=persona.id, nombre_declarado="tel", plataforma="android", huella="h"
    )
    disp.autorizar_para_municipal()
    puertos = _puertos(persona, [disp], mfa=None)
    with pytest.raises(MfaNoEnrolado):
        await CambiarPerfil(puertos).ejecutar(
            id_persona=str(persona.id), clave_destino="MUNICIPAL", huella="h"
        )


async def test_municipal_con_dispositivo_pero_otra_huella_falla() -> None:
    # §11.3: no basta con tener un dispositivo autorizado; la petición debe venir de él.
    persona = _persona_municipal()
    disp = Dispositivo.registrar(
        id_persona=persona.id, nombre_declarado="tel", plataforma="android", huella="h"
    )
    disp.autorizar_para_municipal()
    puertos = _puertos(persona, [disp])
    with pytest.raises(DispositivoNoRegistrado):
        await CambiarPerfil(puertos).ejecutar(
            id_persona=str(persona.id), clave_destino="MUNICIPAL", huella="OTRA"
        )


async def test_perfil_no_asignado_lanza_403() -> None:
    persona = Persona.registrar(
        dni=Dni("12345678"),
        fecha_nacimiento=date(1990, 1, 1),
        celular=Celular("2644123456"),
    )
    puertos = _puertos(persona, [])
    with pytest.raises(PerfilNoAsignado):
        await CambiarPerfil(puertos).ejecutar(
            id_persona=str(persona.id), clave_destino="COMERCIO:xyz"
        )


def test_timeouts_por_perfil() -> None:
    s = Settings(
        database_url="postgresql+psycopg://u@localhost/db",  # type: ignore[arg-type]
        database_migrator_url="postgresql+psycopg://u@localhost/db",  # type: ignore[arg-type]
        redis_url="redis://localhost:6379/0",  # type: ignore[arg-type]
        padron_base_url="http://x",
        padron_api_key="k",  # type: ignore[arg-type]
        jwt_secret="s",  # type: ignore[arg-type]
        field_pepper="p",  # type: ignore[arg-type]
        field_encryption_key="k",  # type: ignore[arg-type]
    )
    assert s.sesion_municipal_timeout_minutos == 10
    assert s.sesion_comercio_timeout_minutos == 30
