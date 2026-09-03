"""Casos de uso: registrar, listar, autorizar y revocar dispositivos (§03.4)."""

from __future__ import annotations

from tarjeta.modules.identidad.domain.dispositivo import Dispositivo
from tarjeta.modules.identidad.domain.events import DispositivoRevocado
from tarjeta.shared.domain.errors import NotFoundError, PermissionDeniedError
from tarjeta.shared.domain.types import EntityId

from .deps import Puertos
from .dto import DispositivoInfo


def _info(d: Dispositivo) -> DispositivoInfo:
    return DispositivoInfo(
        id=str(d.id),
        nombre_declarado=d.nombre_declarado,
        plataforma=d.plataforma,
        estado=str(d.estado),
        autorizado_para_perfil_municipal=d.autorizado_para_perfil_municipal,
    )


class RegistrarDispositivo:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(
        self, *, id_persona: str, nombre: str, plataforma: str, huella: str
    ) -> DispositivoInfo:
        dispositivo = Dispositivo.registrar(
            id_persona=EntityId.from_str(id_persona),
            nombre_declarado=nombre,
            plataforma=plataforma,
            huella=huella,
        )
        await self.p.dispositivos.agregar(dispositivo)
        await self.p.uow.commit()
        return _info(dispositivo)


class ListarDispositivos:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_persona: str) -> list[DispositivoInfo]:
        ds = await self.p.dispositivos.listar_por_persona(EntityId.from_str(id_persona))
        return [_info(d) for d in ds]


class AutorizarDispositivoMunicipal:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_persona: str, id_dispositivo: str) -> None:
        p = self.p
        dispositivo = await p.dispositivos.obtener(EntityId.from_str(id_dispositivo))
        if dispositivo is None or str(dispositivo.id_persona) != id_persona:
            raise NotFoundError("Dispositivo inexistente.")
        dispositivo.autorizar_para_municipal()
        await p.dispositivos.guardar(dispositivo)
        await p.uow.commit()


class RevocarDispositivo:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_persona: str, id_dispositivo: str) -> None:
        p = self.p
        dispositivo = await p.dispositivos.obtener(EntityId.from_str(id_dispositivo))
        if dispositivo is None:
            raise NotFoundError("Dispositivo inexistente.")
        if str(dispositivo.id_persona) != id_persona:
            # No se revela que existe: mismo error que "no encontrado".
            raise PermissionDeniedError("No autorizado.")
        dispositivo.revocar()
        await p.dispositivos.guardar(dispositivo)
        await p.outbox.escribir(
            [DispositivoRevocado(id_persona=id_persona, id_dispositivo=id_dispositivo)]
        )
        await p.uow.commit()
