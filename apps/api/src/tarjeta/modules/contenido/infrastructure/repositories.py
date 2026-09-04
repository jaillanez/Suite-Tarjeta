"""Repositorios del módulo contenido (piezas y cuota atómica)."""

from __future__ import annotations

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.contenido.domain.pieza import Pieza, Superposicion
from tarjeta.modules.contenido.domain.tipos import EstadoPieza, OrigenPieza
from tarjeta.shared.domain.types import EntityId

from .models import CreditoGeneracionModel, PiezaModel


def _to_domain(m: PiezaModel) -> Pieza:
    return Pieza(
        id=EntityId(m.id),
        id_comercio=m.id_comercio,
        id_promocion=m.id_promocion,
        origen=OrigenPieza(m.origen),
        estado=EstadoPieza(m.estado),
        plantilla=m.plantilla,
        idea_texto=m.idea_texto,
        prompt_usado=m.prompt_usado,
        superposicion=Superposicion(**m.superposicion),
        imagen_fondo_clave=m.imagen_fondo_clave,
        variantes_claves=list(m.variantes_claves),
        formatos=dict(m.formatos),
        generada_por_ia=m.generada_por_ia,
        modelo_ia=m.modelo_ia,
        creado_en=m.creado_en,
    )


class SqlAlchemyPiezaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    def _to_model(self, p: Pieza) -> PiezaModel:
        return PiezaModel(
            id=p.id.value,
            id_comercio=p.id_comercio,
            id_promocion=p.id_promocion,
            origen=p.origen.value,
            estado=p.estado.value,
            plantilla=p.plantilla,
            idea_texto=p.idea_texto,
            prompt_usado=p.prompt_usado,
            superposicion={
                "porcentaje": p.superposicion.porcentaje,
                "vigencia": p.superposicion.vigencia,
                "nombre": p.superposicion.nombre,
            },
            imagen_fondo_clave=p.imagen_fondo_clave,
            variantes_claves=list(p.variantes_claves),
            formatos=dict(p.formatos),
            generada_por_ia=p.generada_por_ia,
            modelo_ia=p.modelo_ia,
            creado_en=p.creado_en,
        )

    async def agregar(self, pieza: Pieza) -> None:
        self._s.add(self._to_model(pieza))
        await self._s.flush()

    async def guardar(self, pieza: Pieza) -> None:
        m = await self._s.get(PiezaModel, pieza.id.value)
        if m is None:
            return
        m.estado = pieza.estado.value
        m.plantilla = pieza.plantilla
        m.superposicion = {
            "porcentaje": pieza.superposicion.porcentaje,
            "vigencia": pieza.superposicion.vigencia,
            "nombre": pieza.superposicion.nombre,
        }
        m.imagen_fondo_clave = pieza.imagen_fondo_clave
        m.formatos = dict(pieza.formatos)

    async def obtener(self, id: EntityId) -> Pieza | None:
        m = await self._s.get(PiezaModel, id.value)
        return _to_domain(m) if m else None

    async def listar_por_comercio(self, id_comercio: str) -> list[Pieza]:
        rows = (
            await self._s.execute(
                select(PiezaModel)
                .where(PiezaModel.id_comercio == id_comercio)
                .order_by(PiezaModel.creado_en.desc())
            )
        ).scalars()
        return [_to_domain(m) for m in rows]

    async def listar_en_moderacion(self) -> list[Pieza]:
        rows = (
            await self._s.execute(
                select(PiezaModel)
                .where(PiezaModel.estado == EstadoPieza.EN_MODERACION.value)
                .order_by(PiezaModel.creado_en.asc())
            )
        ).scalars()
        return [_to_domain(m) for m in rows]

    async def de_promocion(self, id_promocion: str) -> list[Pieza]:
        rows = (
            await self._s.execute(select(PiezaModel).where(PiezaModel.id_promocion == id_promocion))
        ).scalars()
        return [_to_domain(m) for m in rows]


class SqlAlchemyCreditoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def _asegurar(self, id_comercio: str, periodo: str) -> None:
        await self._s.execute(
            text(
                "INSERT INTO credito_generacion (id_comercio, periodo, usados, extra) "
                "VALUES (:c, :p, 0, 0) ON CONFLICT (id_comercio, periodo) DO NOTHING"
            ),
            {"c": id_comercio, "p": periodo},
        )

    async def reservar(self, id_comercio: str, periodo: str, cuota: int) -> int | None:
        # §11.9: verificación del tope + incremento en UNA operación atómica (dos pestañas no
        # pueden gastar el mismo crédito).
        await self._asegurar(id_comercio, periodo)
        row = (
            await self._s.execute(
                text(
                    "UPDATE credito_generacion SET usados = usados + 1 "
                    "WHERE id_comercio = :c AND periodo = :p AND usados < :cuota + extra "
                    "RETURNING usados"
                ),
                {"c": id_comercio, "p": periodo, "cuota": cuota},
            )
        ).scalar_one_or_none()
        return int(row) if row is not None else None

    async def devolver(self, id_comercio: str, periodo: str) -> None:
        await self._s.execute(
            text(
                "UPDATE credito_generacion SET usados = GREATEST(0, usados - 1) "
                "WHERE id_comercio = :c AND periodo = :p"
            ),
            {"c": id_comercio, "p": periodo},
        )

    async def usados(self, id_comercio: str, periodo: str) -> int:
        val = await self._s.scalar(
            select(CreditoGeneracionModel.usados).where(
                CreditoGeneracionModel.id_comercio == id_comercio,
                CreditoGeneracionModel.periodo == periodo,
            )
        )
        return int(val or 0)

    async def extra(self, id_comercio: str, periodo: str) -> int:
        val = await self._s.scalar(
            select(CreditoGeneracionModel.extra).where(
                CreditoGeneracionModel.id_comercio == id_comercio,
                CreditoGeneracionModel.periodo == periodo,
            )
        )
        return int(val or 0)

    async def otorgar_extra(self, id_comercio: str, periodo: str, cantidad: int) -> None:
        await self._asegurar(id_comercio, periodo)
        await self._s.execute(
            text(
                "UPDATE credito_generacion SET extra = extra + :n "
                "WHERE id_comercio = :c AND periodo = :p"
            ),
            {"c": id_comercio, "p": periodo, "n": cantidad},
        )
