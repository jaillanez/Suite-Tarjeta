"""Cajero y turnos (§06.5): PIN atado a dispositivo, apertura y cierre de turno."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from tarjeta.modules.comercios.domain.errors import PinInvalido, TurnoAbiertoExistente
from tarjeta.modules.comercios.domain.turno import Turno
from tarjeta.modules.comercios.domain.usuario import UsuarioComercio
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

from .deps import ComerciosPuertos


@dataclass(slots=True)
class CajeroAutenticado:
    id_usuario: str
    id_persona: str
    id_comercio: str


@dataclass(slots=True)
class ResumenTurno:
    id: str
    resumen: dict[str, Any]


class GestionCajero:
    def __init__(
        self, puertos: ComerciosPuertos, *, max_intentos: int = 5, bloqueo_seg: int = 300
    ) -> None:
        self.p = puertos
        self.max_intentos = max_intentos
        self.bloqueo_seg = bloqueo_seg

    async def _cargar(self, id_usuario: str) -> UsuarioComercio:
        usuario = await self.p.usuarios.obtener(EntityId.from_str(id_usuario))
        if usuario is None:
            raise NotFoundError("Usuario de comercio inexistente.")
        return usuario

    async def establecer_pin(self, *, id_usuario: str, pin: str, huella: str) -> None:
        usuario = await self._cargar(id_usuario)
        usuario.establecer_pin(self.p.hasher_pin.hash(pin), huella)
        await self.p.usuarios.guardar(usuario)
        await self.p.uow.commit()

    async def login_pin(
        self, *, id_usuario: str, pin: str, huella: str | None
    ) -> CajeroAutenticado:
        usuario = await self._cargar(id_usuario)
        # El PIN solo funciona en el dispositivo registrado (§06.5); reusa la huella (PASO 04).
        usuario.exigir_dispositivo(huella)
        ahora = datetime.now(UTC)
        usuario.exigir_no_bloqueado(ahora)
        if not usuario.activo:
            raise PinInvalido("Usuario dado de baja.")
        ok = usuario.pin_hash is not None and self.p.hasher_pin.verificar(usuario.pin_hash, pin)
        if not ok:
            usuario.registrar_pin_fallido(
                ahora, max_intentos=self.max_intentos, bloqueo_seg=self.bloqueo_seg
            )
            await self.p.usuarios.guardar(usuario)
            await self.p.uow.commit()
            raise PinInvalido("PIN incorrecto.")
        usuario.registrar_pin_ok()
        await self.p.usuarios.guardar(usuario)
        await self.p.uow.commit()
        return CajeroAutenticado(
            id_usuario=str(usuario.id),
            id_persona=str(usuario.id_persona),
            id_comercio=str(usuario.id_comercio),
        )

    async def abrir_turno(self, *, id_usuario: str, id_sucursal: str) -> str:
        usuario = await self._cargar(id_usuario)
        if await self.p.turnos.turno_abierto_de(usuario.id) is not None:
            raise TurnoAbiertoExistente("Ya hay un turno abierto para este cajero.")
        turno = Turno.abrir(id_sucursal=EntityId.from_str(id_sucursal), id_cajero=usuario.id)
        await self.p.turnos.agregar(turno)
        await self.p.uow.commit()
        return str(turno.id)

    async def cerrar_turno(self, *, id_usuario: str) -> ResumenTurno:
        usuario = await self._cargar(id_usuario)
        turno = await self.p.turnos.turno_abierto_de(usuario.id)
        if turno is None:
            raise NotFoundError("No hay un turno abierto para este cajero.")
        turno.cerrar()
        await self.p.turnos.guardar(turno)
        await self.p.uow.commit()
        return ResumenTurno(id=str(turno.id), resumen=turno.resumen)
