"""Adhesión de comercios (§06.2): solicitud con verificación por CUIT y transiciones."""

from __future__ import annotations

from datetime import UTC, datetime

from tarjeta.modules.comercios.domain.comercio import (
    Comercio,
    EstadoComercio,
    EvidenciaConvenio,
)
from tarjeta.modules.comercios.domain.errors import ComercioDuplicado, NoEsComerciante
from tarjeta.modules.comercios.domain.ports import VerificadorComerciante
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

from .deps import ComerciosPuertos


class SolicitarAdhesion:
    def __init__(self, puertos: ComerciosPuertos, verificador: VerificadorComerciante) -> None:
        self.p = puertos
        self.verificador = verificador

    async def ejecutar(
        self,
        *,
        cuit: str,
        razon_social: str,
        nombre_fantasia: str,
        rubro: str,
        logo_url: str,
        id_responsable: str,
        convenio_version: str,
        ip: str,
    ) -> str:
        # §06.2.1: verificación por CUIT contra el endpoint. Si no es comerciante, no adhiere.
        if not await self.verificador.es_comerciante(cuit):
            raise NoEsComerciante("El CUIT no figura como comerciante en el padrón.")
        if await self.p.comercios.obtener_por_cuit(cuit) is not None:
            raise ComercioDuplicado("Ya existe una solicitud o comercio con ese CUIT.")
        comercio = Comercio.solicitar(
            cuit=cuit,
            razon_social=razon_social,
            nombre_fantasia=nombre_fantasia,
            rubro=rubro,
            logo_url=logo_url,
            id_responsable=EntityId.from_str(id_responsable),
            convenio=EvidenciaConvenio(version=convenio_version, fecha=datetime.now(UTC), ip=ip),
        )
        await self.p.comercios.agregar(comercio)
        await self.p.outbox.escribir(comercio.pull_events())
        await self.p.uow.commit()
        return str(comercio.id)


class RevisarComercio:
    """Acciones de la bandeja municipal (§06.6). La baja definitiva va por doble conformidad."""

    def __init__(self, puertos: ComerciosPuertos) -> None:
        self.p = puertos

    async def _cargar(self, id_comercio: str) -> Comercio:
        comercio = await self.p.comercios.obtener(EntityId.from_str(id_comercio))
        if comercio is None:
            raise NotFoundError("Comercio inexistente.")
        return comercio

    async def _transicionar(self, id_comercio: str, destino: EstadoComercio, motivo: str) -> None:
        comercio = await self._cargar(id_comercio)
        comercio.transicionar(destino, motivo=motivo)
        await self.p.comercios.guardar(comercio)
        await self.p.outbox.escribir(comercio.pull_events())
        await self.p.uow.commit()

    async def tomar(self, id_comercio: str) -> None:
        await self._transicionar(id_comercio, EstadoComercio.EN_REVISION, "en revisión")

    async def pedir_documentacion(self, id_comercio: str, motivo: str) -> None:
        await self._transicionar(id_comercio, EstadoComercio.DOCUMENTACION_PENDIENTE, motivo)

    async def rechazar(self, id_comercio: str, motivo: str) -> None:
        await self._transicionar(id_comercio, EstadoComercio.RECHAZADA, motivo)

    async def suspender(self, id_comercio: str, motivo: str) -> None:
        await self._transicionar(id_comercio, EstadoComercio.SUSPENDIDA, motivo)

    async def reactivar(self, id_comercio: str) -> None:
        await self._transicionar(id_comercio, EstadoComercio.ACTIVA, "reactivado")

    async def aprobar(self, id_comercio: str) -> None:
        # Aprobar deja el comercio operativo: EN_REVISION -> APROBADA -> ACTIVA.
        comercio = await self._cargar(id_comercio)
        comercio.transicionar(EstadoComercio.APROBADA, motivo="aprobado")
        comercio.transicionar(EstadoComercio.ACTIVA, motivo="activado")
        await self.p.comercios.guardar(comercio)
        await self.p.outbox.escribir(comercio.pull_events())
        await self.p.uow.commit()

    async def dar_de_baja(self, id_comercio: str, motivo: str) -> None:
        """Baja definitiva. Solo debe invocarse tras la doble conformidad (composition root)."""
        await self._transicionar(id_comercio, EstadoComercio.BAJA, motivo)
