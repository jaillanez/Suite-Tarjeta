"""Portal de promociones (composition root): cruza comercios, ciudadania, gobierno y promociones.

No es un módulo de dominio; por eso puede importar varios (los módulos entre sí no se importan).
Cubre la carga por el comercio, la cola de moderación municipal (con umbrales de parametría),
el descubrimiento del ciudadano (buscador/feed/resolución, con su nivel y la geo de comercios)
y la ficha pública para Open Graph.
"""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel

from tarjeta.modules.ciudadania.infrastructure.repositories import (
    SqlAlchemyPerfilCiudadanoRepository,
)
from tarjeta.modules.comercios.api.deps import ActorComercio, requiere_comercio
from tarjeta.modules.comercios.domain.roles import Permiso as PermisoComercio
from tarjeta.modules.comercios.infrastructure.repositories import SqlAlchemySucursalRepository
from tarjeta.modules.gobierno.api.deps import Actor, requiere
from tarjeta.modules.gobierno.application.parametria import ParametriaService
from tarjeta.modules.gobierno.domain.roles import Permiso as PermisoMunicipal
from tarjeta.modules.gobierno.infrastructure.composition import construir_puertos_gobierno
from tarjeta.modules.promociones.application.descubrimiento import Descubrimiento
from tarjeta.modules.promociones.application.gestion import GestionPromociones
from tarjeta.modules.promociones.application.publicacion import ModerarPromocion, PublicarPromocion
from tarjeta.modules.promociones.application.resolucion import MotorResolucion
from tarjeta.modules.promociones.domain.mecanica import Mecanica, Segmento
from tarjeta.modules.promociones.domain.ports import CriteriosBusqueda
from tarjeta.modules.promociones.domain.promocion import Promocion
from tarjeta.modules.promociones.domain.vigencia import Vigencia
from tarjeta.modules.promociones.infrastructure.composition import (
    construir_puertos_promociones,
)
from tarjeta.shared.api.auth import SesionDep
from tarjeta.shared.api.dependencies import SessionDep, SettingsDep
from tarjeta.shared.domain.errors import NotFoundError, ValidationError
from tarjeta.shared.domain.types import EntityId

router = APIRouter(prefix="/api/v1", tags=["promociones"])

# Criterio de ordenamiento publicado y auditable (§3.5, §07.6). No es una caja negra.
RANKING_CRITERIO = (
    "1) Destaques municipales primero (marcados como tales). "
    "2) Mayor beneficio para el ciudadano. "
    "3) Más recientes primero. El criterio es público y no se vende."
)


# ------------------------------------------------------------------ schemas


class Mensaje(BaseModel):
    mensaje: str


class VigenciaIn(BaseModel):
    fecha_desde: str
    fecha_hasta: str
    dias_semana: list[int] = []
    hora_desde: str | None = None
    hora_hasta: str | None = None


class PromocionIn(BaseModel):
    titulo: str
    descripcion: str = ""
    mecanica: str
    segmento: str = "AMBOS"
    valor_platino: int | None = None
    valor_black: int
    vigencia: VigenciaIn
    sucursales: list[str]
    acumulable: bool = False
    tope_total: int | None = None
    tope_por_usuario: int | None = None
    tope_por_dia: int | None = None
    monto_minimo: int = 0
    imagen_url: str = ""


class CondicionesIn(BaseModel):
    mecanica: str
    valor_platino: int | None = None
    valor_black: int
    tope_total: int | None = None


class ModeracionIn(BaseModel):
    motivo: str = ""
    titulo: str | None = None
    descripcion: str | None = None
    imagen_url: str | None = None


class FavoritoIn(BaseModel):
    comercio: str = ""
    rubro: str = ""


class PromocionOut(BaseModel):
    id: str
    id_comercio: str
    titulo: str
    descripcion: str
    mecanica: str
    segmento: str
    valor_platino: int | None
    valor_black: int
    estado: str
    imagen_url: str
    destacada_municipal: bool
    usos_totales: int
    tope_total: int | None


class PromocionFeedOut(PromocionOut):
    # Para la sección "Exclusivos Black": si el vecino es Platino, llega bloqueada (§3.5).
    bloqueada: bool = False


class FichaPublicaOut(BaseModel):
    id: str
    titulo: str
    descripcion: str
    imagen_url: str
    estado: str
    disponible: bool
    valor_platino: int | None
    valor_black: int
    mecanica: str


class FeedOut(BaseModel):
    nuevos_esta_semana: list[PromocionOut]
    exclusivos_black: list[PromocionFeedOut]
    vencen_pronto: list[PromocionOut]


# ------------------------------------------------------------------ helpers


def _promo_out(p: Promocion) -> PromocionOut:
    return PromocionOut(
        id=str(p.id),
        id_comercio=str(p.id_comercio),
        titulo=p.titulo,
        descripcion=p.descripcion,
        mecanica=p.mecanica.value,
        segmento=p.segmento.value,
        valor_platino=p.valor_platino,
        valor_black=p.valor_black,
        estado=p.estado.value,
        imagen_url=p.imagen_url,
        destacada_municipal=p.destacada_municipal,
        usos_totales=p.usos_totales,
        tope_total=p.tope_total,
    )


def _fecha(valor: str) -> date:
    return datetime.strptime(valor, "%Y-%m-%d").date()


def _vigencia(v: VigenciaIn) -> Vigencia:
    return Vigencia(
        fecha_desde=_fecha(v.fecha_desde),
        fecha_hasta=_fecha(v.fecha_hasta),
        dias_semana=frozenset(v.dias_semana),
        hora_desde=time.fromisoformat(v.hora_desde) if v.hora_desde else None,
        hora_hasta=time.fromisoformat(v.hora_hasta) if v.hora_hasta else None,
    )


async def _umbrales(session: SessionDep) -> tuple[int, int]:
    svc = ParametriaService(construir_puertos_gobierno(session))
    return (
        await svc.obtener("promos_para_establecido"),
        await svc.obtener("promos_para_verificado"),
    )


async def _nivel(session: SessionDep, id_persona: str) -> str:
    perfil = await SqlAlchemyPerfilCiudadanoRepository(session).obtener(
        EntityId.from_str(id_persona)
    )
    return str(perfil.nivel) if perfil else "PLATINO"


# ------------------------------------------------------------------ comercio (§07.8)


@router.post("/portal-comercio/promociones", response_model=Mensaje)
async def crear_promocion(
    body: PromocionIn,
    session: SessionDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> Mensaje:
    # §07.2: el alcance por sucursal solo admite sucursales del propio comercio y activas.
    validas = {
        str(s.id)
        for s in await SqlAlchemySucursalRepository(session).listar_por_comercio(actor.id_comercio)
        if s.estado.value == "ACTIVA"
    }
    ajenas = [s for s in body.sucursales if s not in validas]
    if ajenas:
        raise ValidationError("Solo se pueden incluir sucursales activas del propio comercio.")
    id_promo = await GestionPromociones(construir_puertos_promociones(session)).crear(
        id_comercio=str(actor.id_comercio),
        titulo=body.titulo,
        descripcion=body.descripcion,
        mecanica=Mecanica(body.mecanica),
        segmento=Segmento(body.segmento),
        valor_platino=body.valor_platino,
        valor_black=body.valor_black,
        vigencia=_vigencia(body.vigencia),
        sucursales=body.sucursales,
        acumulable=body.acumulable,
        tope_total=body.tope_total,
        tope_por_usuario=body.tope_por_usuario,
        tope_por_dia=body.tope_por_dia,
        monto_minimo=body.monto_minimo,
        imagen_url=body.imagen_url,
    )
    return Mensaje(mensaje=id_promo)


@router.get("/portal-comercio/promociones", response_model=list[PromocionOut])
async def listar_promociones(
    session: SessionDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> list[PromocionOut]:
    promos = await construir_puertos_promociones(session).promociones.listar_por_comercio(
        actor.id_comercio
    )
    return [_promo_out(p) for p in promos]


@router.put("/portal-comercio/promociones/{id_promocion}/condiciones", response_model=Mensaje)
async def editar_condiciones(
    id_promocion: str,
    body: CondicionesIn,
    session: SessionDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> Mensaje:
    await GestionPromociones(construir_puertos_promociones(session)).editar_condiciones(
        id_promocion=id_promocion,
        id_comercio=str(actor.id_comercio),
        mecanica=Mecanica(body.mecanica),
        valor_platino=body.valor_platino,
        valor_black=body.valor_black,
        tope_total=body.tope_total,
    )
    return Mensaje(mensaje="Condiciones actualizadas.")


@router.post("/portal-comercio/promociones/{id_promocion}/publicar", response_model=Mensaje)
async def publicar_promocion(
    id_promocion: str,
    session: SessionDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> Mensaje:
    est, ver = await _umbrales(session)
    estado = await PublicarPromocion(construir_puertos_promociones(session)).ejecutar(
        id_promocion=id_promocion,
        id_comercio=str(actor.id_comercio),
        umbral_establecido=est,
        umbral_verificado=ver,
    )
    return Mensaje(mensaje=estado)


@router.post("/portal-comercio/promociones/{id_promocion}/pausar", response_model=Mensaje)
async def pausar_promocion(
    id_promocion: str,
    session: SessionDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> Mensaje:
    await GestionPromociones(construir_puertos_promociones(session)).pausar(
        id_promocion=id_promocion, id_comercio=str(actor.id_comercio)
    )
    return Mensaje(mensaje="Promoción pausada.")


@router.post("/portal-comercio/promociones/{id_promocion}/reanudar", response_model=Mensaje)
async def reanudar_promocion(
    id_promocion: str,
    session: SessionDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> Mensaje:
    await GestionPromociones(construir_puertos_promociones(session)).reanudar(
        id_promocion=id_promocion, id_comercio=str(actor.id_comercio)
    )
    return Mensaje(mensaje="Promoción reanudada.")


@router.post("/portal-comercio/promociones/{id_promocion}/duplicar", response_model=Mensaje)
async def duplicar_promocion(
    id_promocion: str,
    session: SessionDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> Mensaje:
    nuevo = await GestionPromociones(construir_puertos_promociones(session)).duplicar(
        id_promocion=id_promocion, id_comercio=str(actor.id_comercio)
    )
    return Mensaje(mensaje=nuevo)


# ------------------------------------------------------------------ moderación municipal (§07.5)


@router.get("/portal-comercio/moderacion/promociones", response_model=list[PromocionOut])
async def cola_moderacion(
    session: SessionDep,
    _: Annotated[Actor, Depends(requiere(PermisoMunicipal.PROMOCION_MODERAR))],
) -> list[PromocionOut]:
    promos = await construir_puertos_promociones(session).promociones.listar_en_revision()
    return [_promo_out(p) for p in promos]


@router.post(
    "/portal-comercio/moderacion/promociones/{id_promocion}/aprobar", response_model=Mensaje
)
async def moderar_aprobar(
    id_promocion: str,
    body: ModeracionIn,
    session: SessionDep,
    _: Annotated[Actor, Depends(requiere(PermisoMunicipal.PROMOCION_MODERAR))],
) -> Mensaje:
    est, ver = await _umbrales(session)
    servicio = ModerarPromocion(construir_puertos_promociones(session))
    if body.titulo is not None or body.descripcion is not None or body.imagen_url is not None:
        await servicio.aprobar_con_edicion(
            id_promocion=id_promocion,
            titulo=body.titulo or "",
            descripcion=body.descripcion or "",
            imagen_url=body.imagen_url or "",
            umbral_establecido=est,
            umbral_verificado=ver,
        )
    else:
        await servicio.aprobar(
            id_promocion=id_promocion, umbral_establecido=est, umbral_verificado=ver
        )
    return Mensaje(mensaje="Promoción aprobada y activa.")


@router.post(
    "/portal-comercio/moderacion/promociones/{id_promocion}/rechazar", response_model=Mensaje
)
async def moderar_rechazar(
    id_promocion: str,
    body: ModeracionIn,
    session: SessionDep,
    _: Annotated[Actor, Depends(requiere(PermisoMunicipal.PROMOCION_MODERAR))],
) -> Mensaje:
    await ModerarPromocion(construir_puertos_promociones(session)).rechazar(
        id_promocion=id_promocion, motivo=body.motivo
    )
    return Mensaje(mensaje="Promoción rechazada.")


# ------------------------------------------------------------------ descubrimiento (§07.6)


@router.get("/promociones/ranking-criterio", response_model=Mensaje)
async def ranking_criterio() -> Mensaje:
    return Mensaje(mensaje=RANKING_CRITERIO)


async def _ids_sucursal_cercanas(
    session: SessionDep, lat: float | None, lon: float | None, radio_m: float
) -> list[str] | None:
    if lat is None or lon is None:
        return None
    cercanas = await SqlAlchemySucursalRepository(session).cercanas(
        lat=lat, lon=lon, radio_m=radio_m, limite=200
    )
    return [c.id for c in cercanas]


@router.get("/promociones/buscar", response_model=list[PromocionOut])
async def buscar(
    sesion: SesionDep,
    session: SessionDep,
    texto: str = "",
    porcentaje_min: int = 0,
    solo_black: bool = False,
    lat: float | None = None,
    lon: float | None = None,
    radio_m: float = Query(5000, gt=0, le=50000),
) -> list[PromocionOut]:
    nivel = await _nivel(session, sesion.id_persona)
    ids = await _ids_sucursal_cercanas(session, lat, lon, radio_m)
    promos = await Descubrimiento(construir_puertos_promociones(session)).buscar(
        CriteriosBusqueda(
            texto=texto,
            porcentaje_min=porcentaje_min,
            solo_black=solo_black,
            nivel=nivel,
            ids_sucursal=ids,
        )
    )
    return [_promo_out(p) for p in promos]


@router.get("/promociones/feed", response_model=FeedOut)
async def feed(sesion: SesionDep, session: SessionDep) -> FeedOut:
    nivel = await _nivel(session, sesion.id_persona)
    desc = Descubrimiento(construir_puertos_promociones(session))
    nuevos = await desc.nuevas_esta_semana()
    exclusivos = await desc.exclusivas_black()
    vencen = await desc.vencen_pronto()
    # §3.5: si el vecino es Platino, las exclusivas Black llegan BLOQUEADAS con el % visible.
    es_platino = nivel != "BLACK"
    return FeedOut(
        nuevos_esta_semana=[_promo_out(p) for p in nuevos],
        exclusivos_black=[
            PromocionFeedOut(**_promo_out(p).model_dump(), bloqueada=es_platino) for p in exclusivos
        ],
        vencen_pronto=[_promo_out(p) for p in vencen],
    )


@router.get("/promociones/resolver", response_model=list[PromocionOut])
async def resolver(
    sesion: SesionDep,
    session: SessionDep,
    settings: SettingsDep,
    id_sucursal: str,
    monto: int = 0,
) -> list[PromocionOut]:
    nivel = await _nivel(session, sesion.id_persona)
    ahora = datetime.now(ZoneInfo(settings.municipio_timezone))
    promos = await MotorResolucion(construir_puertos_promociones(session)).resolver(
        nivel=nivel, id_sucursal=id_sucursal, momento_local=ahora, monto=monto
    )
    return [_promo_out(p) for p in promos]


@router.get("/promociones/favoritos", response_model=dict[str, list[str]])
async def favoritos(sesion: SesionDep, session: SessionDep) -> dict[str, list[str]]:
    return await Descubrimiento(construir_puertos_promociones(session)).favoritos_de(
        id_persona=sesion.id_persona
    )


@router.post("/promociones/favoritos", response_model=Mensaje)
async def marcar_favorito(body: FavoritoIn, sesion: SesionDep, session: SessionDep) -> Mensaje:
    await Descubrimiento(construir_puertos_promociones(session)).marcar_favorito(
        id_persona=sesion.id_persona, comercio=body.comercio, rubro=body.rubro
    )
    return Mensaje(mensaje="Favorito agregado.")


# ------------------------------------------------------------------ ficha pública OG (§07.7)


@router.get("/promociones/{id_promocion}", response_model=FichaPublicaOut)
async def ficha_publica(id_promocion: str, session: SessionDep) -> FichaPublicaOut:
    promo = await construir_puertos_promociones(session).promociones.obtener(
        EntityId.from_str(id_promocion)
    )
    if promo is None:
        raise NotFoundError("Promoción inexistente.")
    return FichaPublicaOut(
        id=str(promo.id),
        titulo=promo.titulo,
        descripcion=promo.descripcion,
        imagen_url=promo.imagen_url,
        estado=promo.estado.value,
        disponible=promo.estado.value == "ACTIVA",
        valor_platino=promo.valor_platino,
        valor_black=promo.valor_black,
        mecanica=promo.mecanica.value,
    )
