"""Usuarios del comercio (§06.4): invitación, aceptación y baja."""

from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime

from tarjeta.modules.comercios.domain.errors import InvitacionInvalida
from tarjeta.modules.comercios.domain.events import CajeroDadoDeBaja
from tarjeta.modules.comercios.domain.invitacion import Invitacion
from tarjeta.modules.comercios.domain.roles import RolComercio
from tarjeta.modules.comercios.domain.usuario import UsuarioComercio
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

from .deps import ComerciosPuertos


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(slots=True)
class InvitacionCreada:
    id_invitacion: str
    token: str  # plano, solo se devuelve una vez para armar el link


@dataclass(slots=True)
class UsuarioAceptado:
    id_usuario: str
    id_comercio: str
    rol: str


class GestionUsuarios:
    def __init__(self, puertos: ComerciosPuertos) -> None:
        self.p = puertos

    async def invitar(
        self,
        *,
        id_comercio: str,
        rol: str,
        destino: str,
        sucursales: list[str] | None = None,
    ) -> InvitacionCreada:
        token = secrets.token_urlsafe(24)
        invitacion = Invitacion.crear(
            id_comercio=EntityId.from_str(id_comercio),
            rol=RolComercio(rol),
            sucursales=[EntityId.from_str(s) for s in (sucursales or [])],
            destino=destino,
            token_hash=_hash_token(token),
        )
        await self.p.invitaciones.agregar(invitacion)
        await self.p.uow.commit()
        return InvitacionCreada(id_invitacion=str(invitacion.id), token=token)

    async def aceptar(self, *, token: str, id_persona: str) -> UsuarioAceptado:
        invitacion = await self.p.invitaciones.obtener_por_token_hash(_hash_token(token))
        if invitacion is None:
            raise InvitacionInvalida("Invitación inexistente.")
        invitacion.aceptar(datetime.now(UTC))  # puede lanzar InvitacionExpirada
        usuario = UsuarioComercio.crear(
            id_comercio=invitacion.id_comercio,
            id_persona=EntityId.from_str(id_persona),
            rol=invitacion.rol,
            sucursales=list(invitacion.sucursales),
        )
        await self.p.usuarios.agregar(usuario)
        await self.p.invitaciones.guardar(invitacion)
        await self.p.uow.commit()
        return UsuarioAceptado(
            id_usuario=str(usuario.id),
            id_comercio=str(invitacion.id_comercio),
            rol=invitacion.rol.value,
        )

    async def dar_de_baja(self, *, id_usuario: str) -> UsuarioComercio:
        usuario = await self.p.usuarios.obtener(EntityId.from_str(id_usuario))
        if usuario is None:
            raise NotFoundError("Usuario de comercio inexistente.")
        usuario.dar_de_baja()
        if usuario.rol is RolComercio.CAJERO:
            usuario.record_event(
                CajeroDadoDeBaja(
                    id_comercio=str(usuario.id_comercio), id_persona=str(usuario.id_persona)
                )
            )
        await self.p.usuarios.guardar(usuario)
        await self.p.outbox.escribir(usuario.pull_events())
        await self.p.uow.commit()
        return usuario
