"""Doble conformidad: solicitar, aprobar, rechazar, expirar (§05.5)."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

from tarjeta.modules.gobierno.domain.aprobacion import SolicitudAprobacion
from tarjeta.modules.gobierno.domain.auditoria import RegistroAuditoria
from tarjeta.modules.gobierno.domain.errors import SolicitudNoAprobable
from tarjeta.modules.gobierno.domain.roles import RolMunicipal
from tarjeta.shared.domain.types import EntityId

from .deps import GobiernoPuertos

# Un ejecutor aplica la acción aprobada; recibe el payload. Lo registra el composition root
# para acciones cross-módulo (p. ej. reclamo de cuenta).
Ejecutor = Callable[[dict[str, object]], Awaitable[None]]


class SolicitarAprobacion:
    def __init__(self, puertos: GobiernoPuertos) -> None:
        self.p = puertos

    async def ejecutar(
        self, *, accion: str, payload: dict[str, object], id_solicitante: str, rol: str
    ) -> str:
        solicitud = SolicitudAprobacion.crear(
            accion=accion,
            payload=payload,
            id_solicitante=id_solicitante,
            rol=RolMunicipal(rol),
        )
        await self.p.aprobaciones.agregar(solicitud)
        await self.p.uow.commit()
        return str(solicitud.id)


class DecidirAprobacion:
    def __init__(self, puertos: GobiernoPuertos) -> None:
        self.p = puertos

    async def aprobar(
        self,
        *,
        id_solicitud: str,
        id_aprobador: str,
        rol_aprobador: str,
        motivo: str,
        ejecutor: Ejecutor | None = None,
    ) -> None:
        solicitud = await self.p.aprobaciones.obtener(EntityId.from_str(id_solicitud))
        if solicitud is None:
            raise SolicitudNoAprobable("Solicitud inexistente.")
        # Puede lanzar AutoaprobacionProhibida / RangoInsuficiente / SolicitudNoAprobable.
        solicitud.aprobar(
            id_aprobador=id_aprobador, rol_aprobador=RolMunicipal(rol_aprobador), motivo=motivo
        )
        if ejecutor is not None:
            try:
                await ejecutor(solicitud.payload)
            except Exception as exc:  # noqa: BLE001 - la solicitud queda en ERROR, no se pierde
                solicitud.marcar_error(str(exc))
        await self.p.aprobaciones.guardar(solicitud)
        await self.p.auditoria.agregar(
            RegistroAuditoria.crear(
                accion=f"doble_conformidad:{solicitud.estado.value.lower()}",
                entidad="solicitud_aprobacion",
                id_entidad=id_solicitud,
                id_persona_actor=id_aprobador,
                rol_actor=rol_aprobador,
                motivo=motivo,
            )
        )
        await self.p.uow.commit()

    async def rechazar(self, *, id_solicitud: str, id_aprobador: str, motivo: str) -> None:
        solicitud = await self.p.aprobaciones.obtener(EntityId.from_str(id_solicitud))
        if solicitud is None:
            raise SolicitudNoAprobable("Solicitud inexistente.")
        solicitud.rechazar(id_aprobador=id_aprobador, motivo=motivo)
        await self.p.aprobaciones.guardar(solicitud)
        await self.p.uow.commit()


class ExpirarPendientes:
    def __init__(self, puertos: GobiernoPuertos) -> None:
        self.p = puertos

    async def ejecutar(self) -> int:
        n = await self.p.aprobaciones.expirar_vencidas(datetime.now(UTC))
        await self.p.uow.commit()
        return n
