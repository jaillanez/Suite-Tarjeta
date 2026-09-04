"""Portal de puntos (composition root): billeteras del ciudadano, pasivo del comercio e
inventario municipal (§09.7).

Cruza `puntos` con `comercios` (pasivo del comercio) y `gobierno` (administración del catálogo).
Las dos monedas (PC y PM) se muestran siempre separadas y no se convierten entre sí. El canje
contra tasas NO se expone: su feature flag está apagado y no hay ningún endpoint que lo permita.
"""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tarjeta.modules.comercios.api.deps import ActorComercio, requiere_comercio
from tarjeta.modules.comercios.domain.roles import Permiso as PermisoComercio
from tarjeta.modules.gobierno.api.deps import Actor, requiere
from tarjeta.modules.gobierno.domain.roles import Permiso
from tarjeta.modules.grupo.domain.tipos import EstadoMiembro, ModoBilletera
from tarjeta.modules.grupo.infrastructure.repositories import SqlAlchemyGrupoRepository
from tarjeta.modules.puntos.application.consulta import ConsultaBilleteras
from tarjeta.modules.puntos.application.inventario import CanjearInventario, GestionInventario
from tarjeta.modules.puntos.application.municipales import AcreditarPuntosMunicipales
from tarjeta.modules.puntos.domain.moneda import TipoTitular
from tarjeta.modules.puntos.infrastructure.composition import construir_puertos_puntos
from tarjeta.shared.api.auth import SesionDep
from tarjeta.shared.api.dependencies import SessionDep

router = APIRouter(prefix="/api/v1/puntos", tags=["puntos"])


def _puertos(session: SessionDep):  # type: ignore[no-untyped-def]
    return construir_puertos_puntos(session)


async def _owner(session: SessionDep, id_persona: str) -> tuple[TipoTitular, str]:
    """En modo COMÚN la billetera visible es el pozo del grupo; si no, la personal (§10.5)."""
    grupos = SqlAlchemyGrupoRepository(session)
    miembro = await grupos.miembro_de(id_persona)
    if miembro is None or miembro.estado is not EstadoMiembro.ACTIVO:
        return (TipoTitular.PERSONA, id_persona)
    grupo = await grupos.obtener(miembro.id_grupo)
    if grupo is None or not grupo.activo or grupo.modo_billetera is not ModoBilletera.COMUN:
        return (TipoTitular.PERSONA, id_persona)
    return (TipoTitular.GRUPO, str(grupo.id))


# ------------------------------------------------------------------ schemas


class BilleteraPCOut(BaseModel):
    id_comercio: str
    saldo: int


class BilleterasOut(BaseModel):
    pc: list[BilleteraPCOut]
    pm: int


class MovimientoOut(BaseModel):
    id: str
    tipo: str
    monto: int
    concepto: str
    creado_en: str


class LotePorVencerOut(BaseModel):
    tipo_moneda: str
    id_comercio: str
    saldo_restante: int
    vence_en: str
    dias_restantes: int


class ItemOut(BaseModel):
    id: str
    titulo: str
    descripcion: str
    costo_pm: int
    stock: int
    fecha_desde: str
    fecha_hasta: str
    estado: str


class ComprobanteOut(BaseModel):
    id: str
    codigo: str
    titulo_item: str
    costo_pm: int
    creado_en: str


class ItemIn(BaseModel):
    titulo: str
    descripcion: str = ""
    costo_pm: int
    stock: int
    fecha_desde: date
    fecha_hasta: date


class PasivoComercioOut(BaseModel):
    emitidos: int
    canjeados: int


class PmCirculanteOut(BaseModel):
    total: int


class AcreditarPmIn(BaseModel):
    id_persona: str
    puntos: int
    concepto: str
    clave_dedup: str


class Mensaje(BaseModel):
    mensaje: str


# ------------------------------------------------------------------ ciudadano


@router.get("/billeteras", response_model=BilleterasOut)
async def mis_billeteras(sesion: SesionDep, session: SessionDep) -> BilleterasOut:
    tipo_titular, id_titular = await _owner(session, sesion.id_persona)
    r = await ConsultaBilleteras(_puertos(session)).resumen(id_titular, tipo_titular=tipo_titular)
    return BilleterasOut(
        pc=[BilleteraPCOut(id_comercio=s.id_comercio, saldo=s.saldo) for s in r.pc], pm=r.pm
    )


@router.get("/movimientos", response_model=list[MovimientoOut])
async def mis_movimientos(
    sesion: SesionDep,
    session: SessionDep,
    tipo_moneda: str = "PM",
    id_comercio: str | None = None,
) -> list[MovimientoOut]:
    tipo_titular, id_titular = await _owner(session, sesion.id_persona)
    movs = await ConsultaBilleteras(_puertos(session)).movimientos(
        id_titular, tipo_moneda=tipo_moneda, id_comercio=id_comercio, tipo_titular=tipo_titular
    )
    return [
        MovimientoOut(
            id=str(m.id),
            tipo=m.tipo.value,
            monto=m.monto,
            concepto=m.concepto,
            creado_en=m.creado_en.isoformat(),
        )
        for m in movs
    ]


@router.get("/por-vencer", response_model=list[LotePorVencerOut])
async def mis_lotes_por_vencer(
    sesion: SesionDep, session: SessionDep, dias: int = 30
) -> list[LotePorVencerOut]:
    tipo_titular, id_titular = await _owner(session, sesion.id_persona)
    lotes = await ConsultaBilleteras(_puertos(session)).por_vencer(
        id_titular, dias=dias, tipo_titular=tipo_titular
    )
    return [
        LotePorVencerOut(
            tipo_moneda=x.tipo_moneda,
            id_comercio=x.id_comercio,
            saldo_restante=x.saldo_restante,
            vence_en=x.vence_en,
            dias_restantes=x.dias_restantes,
        )
        for x in lotes
    ]


@router.get("/catalogo", response_model=list[ItemOut])
async def catalogo(sesion: SesionDep, session: SessionDep) -> list[ItemOut]:
    items = await GestionInventario(_puertos(session)).listar_activos()
    return [_item_out(i) for i in items]


@router.post("/catalogo/{id_item}/canjear", response_model=ComprobanteOut)
async def canjear_inventario(
    id_item: str, sesion: SesionDep, session: SessionDep
) -> ComprobanteOut:
    tipo_titular, id_titular = await _owner(session, sesion.id_persona)
    c = await CanjearInventario(_puertos(session)).ejecutar(
        id_persona=sesion.id_persona,
        id_item=id_item,
        tipo_titular=tipo_titular,
        id_titular=id_titular,
    )
    return ComprobanteOut(
        id=str(c.id),
        codigo=c.codigo,
        titulo_item=c.titulo_item,
        costo_pm=c.costo_pm,
        creado_en=c.creado_en.isoformat(),
    )


@router.get("/mis-comprobantes", response_model=list[ComprobanteOut])
async def mis_comprobantes(sesion: SesionDep, session: SessionDep) -> list[ComprobanteOut]:
    comps = await CanjearInventario(_puertos(session)).comprobantes_de(sesion.id_persona)
    return [
        ComprobanteOut(
            id=str(c.id),
            codigo=c.codigo,
            titulo_item=c.titulo_item,
            costo_pm=c.costo_pm,
            creado_en=c.creado_en.isoformat(),
        )
        for c in comps
    ]


# ------------------------------------------------------------------ comercio


@router.get("/comercio/pasivo", response_model=PasivoComercioOut)
async def pasivo_comercio(
    session: SessionDep,
    actor: Annotated[ActorComercio, Depends(requiere_comercio(PermisoComercio.REPORTES_VER))],
) -> PasivoComercioOut:
    emitidos, canjeados = await _puertos(session).movimientos.resumen_comercio(
        str(actor.id_comercio)
    )
    return PasivoComercioOut(emitidos=emitidos, canjeados=canjeados)


# ------------------------------------------------------------------ municipal


@router.post("/municipal/catalogo", response_model=dict)
async def publicar_item(
    body: ItemIn,
    session: SessionDep,
    _: Annotated[Actor, Depends(requiere(Permiso.AJUSTE_PUNTOS))],
) -> dict[str, str]:
    id_item = await GestionInventario(_puertos(session)).publicar(
        titulo=body.titulo,
        descripcion=body.descripcion,
        costo_pm=body.costo_pm,
        stock=body.stock,
        fecha_desde=body.fecha_desde,
        fecha_hasta=body.fecha_hasta,
    )
    return {"id": id_item}


@router.get("/municipal/catalogo", response_model=list[ItemOut])
async def catalogo_municipal(
    session: SessionDep,
    _: Annotated[Actor, Depends(requiere(Permiso.AJUSTE_PUNTOS))],
) -> list[ItemOut]:
    items = await GestionInventario(_puertos(session)).listar_todos()
    return [_item_out(i) for i in items]


@router.get("/municipal/pm-circulante", response_model=PmCirculanteOut)
async def pm_circulante(
    session: SessionDep,
    _: Annotated[Actor, Depends(requiere(Permiso.AJUSTE_PUNTOS))],
) -> PmCirculanteOut:
    total = await _puertos(session).movimientos.pm_en_circulacion()
    return PmCirculanteOut(total=total)


@router.post("/municipal/acreditar", response_model=Mensaje)
async def acreditar_pm(
    body: AcreditarPmIn,
    session: SessionDep,
    _: Annotated[Actor, Depends(requiere(Permiso.AJUSTE_PUNTOS))],
) -> Mensaje:
    # Mecanismo genérico (campañas, referidos): reglas por parametría (§09.5).
    otorgados = await AcreditarPuntosMunicipales(_puertos(session)).por_concepto(
        id_persona=body.id_persona,
        puntos=body.puntos,
        concepto=body.concepto,
        clave_dedup=body.clave_dedup,
    )
    return Mensaje(mensaje=f"Se acreditaron {otorgados} PM.")


def _item_out(i) -> ItemOut:  # type: ignore[no-untyped-def]
    return ItemOut(
        id=str(i.id),
        titulo=i.titulo,
        descripcion=i.descripcion,
        costo_pm=i.costo_pm,
        stock=i.stock,
        fecha_desde=i.fecha_desde.isoformat(),
        fecha_hasta=i.fecha_hasta.isoformat(),
        estado=i.estado.value,
    )
