"""Sucursales (§06.3): alta con QR, cierres, cercanía y apertura."""

from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from tarjeta.modules.comercios.domain.sucursal import (
    Horario,
    Sucursal,
    SucursalCercana,
)
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

from .deps import ComerciosPuertos


class GestionSucursales:
    def __init__(self, puertos: ComerciosPuertos) -> None:
        self.p = puertos

    async def crear(
        self,
        *,
        id_comercio: str,
        nombre: str,
        direccion: str,
        lat: float | None,
        lon: float | None,
        telefono: str = "",
        es_casa_central: bool = False,
        horarios: list[Horario] | None = None,
        fotos: list[str] | None = None,
    ) -> str:
        sucursal = Sucursal.crear(
            id_comercio=EntityId.from_str(id_comercio),
            nombre=nombre,
            direccion=direccion,
            lat=lat,
            lon=lon,
            telefono=telefono,
            es_casa_central=es_casa_central,
            horarios=horarios,
            fotos=fotos,
        )
        # QR fijo permanente del establecimiento (§3.4): token firmado por sucursal.
        sucursal.qr_token = self.p.firmador.token(str(sucursal.id))
        await self.p.sucursales.agregar(sucursal)
        await self.p.outbox.escribir(sucursal.pull_events())
        await self.p.uow.commit()
        return str(sucursal.id)

    async def _cargar(self, id_sucursal: str) -> Sucursal:
        sucursal = await self.p.sucursales.obtener(EntityId.from_str(id_sucursal))
        if sucursal is None:
            raise NotFoundError("Sucursal inexistente.")
        return sucursal

    async def cerrar_temporal(
        self, id_sucursal: str, motivo: str, reapertura_estimada: str | None
    ) -> None:
        sucursal = await self._cargar(id_sucursal)
        sucursal.cerrar_temporal(motivo, reapertura_estimada)
        await self.p.sucursales.guardar(sucursal)
        await self.p.uow.commit()

    async def reabrir(self, id_sucursal: str) -> None:
        sucursal = await self._cargar(id_sucursal)
        sucursal.reabrir()
        await self.p.sucursales.guardar(sucursal)
        await self.p.uow.commit()

    async def cercanas(
        self, *, lat: float, lon: float, radio_m: float, limite: int
    ) -> list[SucursalCercana]:
        return await self.p.sucursales.cercanas(lat=lat, lon=lon, radio_m=radio_m, limite=limite)

    async def abierto_ahora(self, id_sucursal: str, *, zona: str) -> bool:
        sucursal = await self._cargar(id_sucursal)
        ahora_local = datetime.now(ZoneInfo(zona))
        return sucursal.abierto_ahora(ahora_local)
