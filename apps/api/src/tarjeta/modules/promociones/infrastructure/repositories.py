"""Repositorios del módulo promociones (reserva atómica, motor y búsqueda)."""

from __future__ import annotations

import uuid
from datetime import date, datetime

from sqlalchemy import bindparam, delete, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.promociones.domain.confianza import NivelConfianza, PerfilConfianza
from tarjeta.modules.promociones.domain.mecanica import Mecanica, Segmento
from tarjeta.modules.promociones.domain.ports import CriteriosBusqueda
from tarjeta.modules.promociones.domain.promocion import EstadoPromocion, Promocion
from tarjeta.modules.promociones.domain.vigencia import Vigencia
from tarjeta.shared.domain.types import EntityId

from .models import (
    FavoritoModel,
    PerfilConfianzaModel,
    PromocionModel,
    PromocionSucursalModel,
)


def _to_domain(m: PromocionModel, sucursales: list[EntityId]) -> Promocion:
    return Promocion(
        id=EntityId(m.id),
        id_comercio=EntityId(m.id_comercio),
        titulo=m.titulo,
        descripcion=m.descripcion,
        mecanica=Mecanica(m.mecanica),
        segmento=Segmento(m.segmento),
        valor_platino=m.valor_platino,
        valor_black=m.valor_black,
        vigencia=Vigencia(
            fecha_desde=m.fecha_desde,
            fecha_hasta=m.fecha_hasta,
            dias_semana=frozenset(m.dias_semana),
            hora_desde=m.hora_desde,
            hora_hasta=m.hora_hasta,
        ),
        sucursales=sucursales,
        acumulable=m.acumulable,
        destacada_municipal=m.destacada_municipal,
        tope_total=m.tope_total,
        tope_por_usuario=m.tope_por_usuario,
        tope_por_dia=m.tope_por_dia,
        usos_totales=m.usos_totales,
        monto_minimo=m.monto_minimo,
        imagen_url=m.imagen_url,
        estado=EstadoPromocion(m.estado),
        creada_en=m.creada_en,
    )


class SqlAlchemyPromocionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    def _to_model(self, p: Promocion) -> PromocionModel:
        return PromocionModel(
            id=p.id.value,
            id_comercio=p.id_comercio.value,
            titulo=p.titulo,
            descripcion=p.descripcion,
            mecanica=p.mecanica.value,
            segmento=p.segmento.value,
            valor_platino=p.valor_platino,
            valor_black=p.valor_black,
            fecha_desde=p.vigencia.fecha_desde,
            fecha_hasta=p.vigencia.fecha_hasta,
            dias_semana=sorted(p.vigencia.dias_semana),
            hora_desde=p.vigencia.hora_desde,
            hora_hasta=p.vigencia.hora_hasta,
            acumulable=p.acumulable,
            destacada_municipal=p.destacada_municipal,
            tope_total=p.tope_total,
            tope_por_usuario=p.tope_por_usuario,
            tope_por_dia=p.tope_por_dia,
            usos_totales=p.usos_totales,
            monto_minimo=p.monto_minimo,
            imagen_url=p.imagen_url,
            estado=p.estado.value,
            creada_en=p.creada_en,
        )

    async def _sucursales_de(self, id_promocion: uuid.UUID) -> list[EntityId]:
        rows = (
            await self._s.execute(
                select(PromocionSucursalModel.id_sucursal).where(
                    PromocionSucursalModel.id_promocion == id_promocion
                )
            )
        ).scalars()
        return [EntityId(r) for r in rows]

    async def _sync_sucursales(self, p: Promocion) -> None:
        await self._s.execute(
            delete(PromocionSucursalModel).where(PromocionSucursalModel.id_promocion == p.id.value)
        )
        for s in p.sucursales:
            self._s.add(PromocionSucursalModel(id_promocion=p.id.value, id_sucursal=s.value))

    async def agregar(self, promocion: Promocion) -> None:
        self._s.add(self._to_model(promocion))
        await self._s.flush()
        await self._sync_sucursales(promocion)
        await self._s.flush()

    async def guardar(self, promocion: Promocion) -> None:
        m = await self._s.get(PromocionModel, promocion.id.value)
        if m is None:
            return
        m.titulo = promocion.titulo
        m.descripcion = promocion.descripcion
        m.mecanica = promocion.mecanica.value
        m.segmento = promocion.segmento.value
        m.valor_platino = promocion.valor_platino
        m.valor_black = promocion.valor_black
        m.fecha_desde = promocion.vigencia.fecha_desde
        m.fecha_hasta = promocion.vigencia.fecha_hasta
        m.dias_semana = sorted(promocion.vigencia.dias_semana)
        m.hora_desde = promocion.vigencia.hora_desde
        m.hora_hasta = promocion.vigencia.hora_hasta
        m.acumulable = promocion.acumulable
        m.tope_total = promocion.tope_total
        m.monto_minimo = promocion.monto_minimo
        m.imagen_url = promocion.imagen_url
        m.estado = promocion.estado.value
        await self._sync_sucursales(promocion)

    async def obtener(self, id: EntityId) -> Promocion | None:
        m = await self._s.get(PromocionModel, id.value)
        if m is None:
            return None
        return _to_domain(m, await self._sucursales_de(m.id))

    async def listar_por_comercio(self, id_comercio: EntityId) -> list[Promocion]:
        rows = (
            await self._s.execute(
                select(PromocionModel)
                .where(PromocionModel.id_comercio == id_comercio.value)
                .order_by(PromocionModel.creada_en.desc())
            )
        ).scalars()
        return [_to_domain(m, []) for m in rows]

    async def listar_en_revision(self) -> list[Promocion]:
        rows = (
            await self._s.execute(
                select(PromocionModel).where(
                    PromocionModel.estado == EstadoPromocion.EN_REVISION.value
                )
            )
        ).scalars()
        return [_to_domain(m, []) for m in rows]

    async def reservar_uso_total(self, id: EntityId) -> int | None:
        # §07.3: verificación del tope + incremento en UNA operación atómica.
        row = (
            await self._s.execute(
                text(
                    "UPDATE promocion SET usos_totales = usos_totales + 1 "
                    "WHERE id = :id AND (tope_total IS NULL OR usos_totales < tope_total) "
                    "RETURNING usos_totales"
                ),
                {"id": id.value},
            )
        ).scalar_one_or_none()
        return int(row) if row is not None else None

    async def marcar_agotada(self, id: EntityId) -> None:
        await self._s.execute(
            text("UPDATE promocion SET estado = 'AGOTADA' WHERE id = :id AND estado = 'ACTIVA'"),
            {"id": id.value},
        )

    async def candidatas(
        self, *, id_sucursal: EntityId, nivel: str, momento_local: datetime, monto: int
    ) -> list[Promocion]:
        hoy = momento_local.date()
        stmt = (
            select(PromocionModel)
            .join(
                PromocionSucursalModel,
                PromocionSucursalModel.id_promocion == PromocionModel.id,
            )
            .where(
                PromocionModel.estado == EstadoPromocion.ACTIVA.value,
                PromocionSucursalModel.id_sucursal == id_sucursal.value,
                PromocionModel.fecha_desde <= hoy,
                PromocionModel.fecha_hasta >= hoy,
                PromocionModel.monto_minimo <= monto,
            )
        )
        if nivel != "BLACK":
            stmt = stmt.where(PromocionModel.segmento == Segmento.AMBOS.value)
        rows = (await self._s.execute(stmt)).scalars()
        return [_to_domain(m, []) for m in rows]

    async def buscar(self, criterios: CriteriosBusqueda) -> list[Promocion]:
        sql = (
            "SELECT p.* FROM promocion p WHERE p.estado = 'ACTIVA' "
            "AND (:pct = 0 OR p.valor_black >= :pct) "
        )
        if criterios.solo_black:
            sql += "AND p.segmento = 'SOLO_BLACK' "
        if criterios.texto:
            # pg_trgm + unaccent (§07.6): en español la búsqueda sin tildes no es opcional.
            sql += (
                "AND f_unaccent(p.titulo || ' ' || p.descripcion) "
                "ILIKE '%' || f_unaccent(:texto) || '%' "
            )
        if criterios.ids_sucursal is not None:
            sql += (
                "AND EXISTS (SELECT 1 FROM promocion_sucursal ps "
                "WHERE ps.id_promocion = p.id AND ps.id_sucursal = ANY(:ids)) "
            )
        # Ranking publicado (§3.5): destaques primero, luego mayor beneficio, luego recencia.
        sql += (
            "ORDER BY p.destacada_municipal DESC, p.valor_black DESC, p.creada_en DESC LIMIT :lim"
        )
        crudo = text(sql).bindparams(
            bindparam("pct", criterios.porcentaje_min),
            bindparam("texto", criterios.texto),
            bindparam("lim", criterios.limite),
        )
        if criterios.ids_sucursal is not None:
            crudo = crudo.bindparams(
                bindparam("ids", [uuid.UUID(s) for s in criterios.ids_sucursal])
            )
        rows = (await self._s.execute(select(PromocionModel).from_statement(crudo))).scalars()
        return [_to_domain(m, []) for m in rows]

    async def nuevas_desde(self, desde: datetime, limite: int) -> list[Promocion]:
        rows = (
            await self._s.execute(
                select(PromocionModel)
                .where(
                    PromocionModel.estado == EstadoPromocion.ACTIVA.value,
                    PromocionModel.creada_en >= desde,
                )
                .order_by(PromocionModel.creada_en.desc())
                .limit(limite)
            )
        ).scalars()
        return [_to_domain(m, []) for m in rows]

    async def vencen_antes_de(self, hasta_fecha: date, limite: int) -> list[Promocion]:
        rows = (
            await self._s.execute(
                select(PromocionModel)
                .where(
                    PromocionModel.estado == EstadoPromocion.ACTIVA.value,
                    PromocionModel.fecha_hasta <= hasta_fecha,
                )
                .order_by(PromocionModel.fecha_hasta.asc())
                .limit(limite)
            )
        ).scalars()
        return [_to_domain(m, []) for m in rows]

    async def exclusivas_black(self, limite: int) -> list[Promocion]:
        rows = (
            await self._s.execute(
                select(PromocionModel)
                .where(
                    PromocionModel.estado == EstadoPromocion.ACTIVA.value,
                    PromocionModel.segmento == Segmento.SOLO_BLACK.value,
                )
                .order_by(PromocionModel.creada_en.desc())
                .limit(limite)
            )
        ).scalars()
        return [_to_domain(m, []) for m in rows]


class SqlAlchemyPerfilConfianzaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def obtener(self, id_comercio: EntityId) -> PerfilConfianza | None:
        m = await self._s.get(PerfilConfianzaModel, id_comercio.value)
        if m is None:
            return None
        return PerfilConfianza(
            id=EntityId(m.id_comercio),
            nivel=NivelConfianza(m.nivel),
            promos_aprobadas=m.promos_aprobadas,
        )

    async def guardar(self, perfil: PerfilConfianza) -> None:
        m = await self._s.get(PerfilConfianzaModel, perfil.id_comercio.value)
        if m is None:
            self._s.add(
                PerfilConfianzaModel(
                    id_comercio=perfil.id_comercio.value,
                    nivel=perfil.nivel.value,
                    promos_aprobadas=perfil.promos_aprobadas,
                )
            )
        else:
            m.nivel = perfil.nivel.value
            m.promos_aprobadas = perfil.promos_aprobadas


class SqlAlchemyFavoritoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._s = session

    async def _agregar(self, id_persona: EntityId, tipo: str, valor: str) -> None:
        existe = await self._s.scalar(
            select(FavoritoModel.id).where(
                FavoritoModel.id_persona == id_persona.value,
                FavoritoModel.tipo == tipo,
                FavoritoModel.valor == valor,
            )
        )
        if existe is None:
            self._s.add(
                FavoritoModel(id=uuid.uuid4(), id_persona=id_persona.value, tipo=tipo, valor=valor)
            )

    async def agregar(self, id_persona: EntityId, *, comercio: str = "", rubro: str = "") -> None:
        if comercio:
            await self._agregar(id_persona, "comercio", comercio)
        if rubro:
            await self._agregar(id_persona, "rubro", rubro)

    async def quitar(self, id_persona: EntityId, *, comercio: str = "", rubro: str = "") -> None:
        if comercio:
            await self._s.execute(
                delete(FavoritoModel).where(
                    FavoritoModel.id_persona == id_persona.value,
                    FavoritoModel.tipo == "comercio",
                    FavoritoModel.valor == comercio,
                )
            )
        if rubro:
            await self._s.execute(
                delete(FavoritoModel).where(
                    FavoritoModel.id_persona == id_persona.value,
                    FavoritoModel.tipo == "rubro",
                    FavoritoModel.valor == rubro,
                )
            )

    async def _listar(self, id_persona: EntityId, tipo: str) -> list[str]:
        rows = (
            await self._s.execute(
                select(FavoritoModel.valor).where(
                    FavoritoModel.id_persona == id_persona.value, FavoritoModel.tipo == tipo
                )
            )
        ).scalars()
        return list(rows)

    async def comercios_de(self, id_persona: EntityId) -> list[str]:
        return await self._listar(id_persona, "comercio")

    async def rubros_de(self, id_persona: EntityId) -> list[str]:
        return await self._listar(id_persona, "rubro")
