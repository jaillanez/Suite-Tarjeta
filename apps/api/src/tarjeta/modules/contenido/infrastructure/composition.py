"""Composición del módulo contenido."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.config import Settings
from tarjeta.modules.contenido.application.deps import ContenidoConfig, ContenidoPuertos
from tarjeta.modules.contenido.domain.ports import GeneradorImagen
from tarjeta.shared.infrastructure.database import SqlAlchemyUnitOfWork
from tarjeta.shared.infrastructure.outbox import SqlAlchemyOutbox

from .almacen import AlmacenLocal
from .compositor import CompositorPIL
from .generador import GeneradorReal, GeneradorSimulacion
from .repositories import SqlAlchemyCreditoRepository, SqlAlchemyPiezaRepository


def construir_generador(settings: Settings) -> GeneradorImagen:
    if settings.contenido_proveedor == "real":
        return GeneradorReal(
            api_key=settings.contenido_ia_api_key.get_secret_value(),
            modelo=settings.contenido_ia_modelo,
            base_url=settings.contenido_ia_base_url,
        )
    return GeneradorSimulacion()


def construir_config(settings: Settings) -> ContenidoConfig:
    return ContenidoConfig(
        cuota_mensual=settings.cuota_ia_mensual_por_comercio,
        variantes_por_credito=settings.contenido_variantes_por_credito,
        tamano=settings.contenido_ia_tamano,
        modelo=settings.contenido_ia_modelo,
        precio_unitario_centavos=settings.contenido_ia_precio_unitario_centavos,
    )


def construir_puertos_contenido(
    session: AsyncSession,
    settings: Settings,
    *,
    generador: GeneradorImagen | None = None,
) -> ContenidoPuertos:
    return ContenidoPuertos(
        uow=SqlAlchemyUnitOfWork(session),
        piezas=SqlAlchemyPiezaRepository(session),
        creditos=SqlAlchemyCreditoRepository(session),
        generador=generador or construir_generador(settings),
        compositor=CompositorPIL(),
        almacen=AlmacenLocal(
            settings.contenido_almacen_dir, url_prefijo="/api/v1/contenido/objeto"
        ),
        outbox=SqlAlchemyOutbox(session),
        config=construir_config(settings),
    )
