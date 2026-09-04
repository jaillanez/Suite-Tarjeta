"""Portal de contenido (composition root, §11).

Cruza `contenido` con `comercios` (nombre de fantasía, rubro), `promociones` (mecánica, valor,
vigencia y nivel de confianza para la moderación) y sirve las imágenes del almacén de objetos. Los
módulos no se importan entre sí: acá se cablean. El porcentaje/vigencia/nombre se toman de la
promoción y se superponen; la IA nunca los escribe (§11.5).
"""

from __future__ import annotations

import base64
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel

from tarjeta.modules.comercios.api.deps import ActorComercio, requiere_comercio
from tarjeta.modules.comercios.domain.roles import Permiso as PermisoComercio
from tarjeta.modules.comercios.infrastructure.repositories import SqlAlchemyComercioRepository
from tarjeta.modules.contenido.application.cuota import Creditos
from tarjeta.modules.contenido.application.generacion import (
    CrearPiezaDesdeFoto,
    EditarPieza,
    GenerarPieza,
    RegenerarSuperposicion,
)
from tarjeta.modules.contenido.application.moderacion import ModeracionPiezas
from tarjeta.modules.contenido.domain.pieza import Pieza, Superposicion
from tarjeta.modules.contenido.domain.plantillas import PLANTILLA_POR_DEFECTO, PLANTILLAS
from tarjeta.modules.contenido.infrastructure.almacen import AlmacenLocal
from tarjeta.modules.contenido.infrastructure.composition import construir_puertos_contenido
from tarjeta.modules.gobierno.api.deps import Actor, requiere
from tarjeta.modules.gobierno.domain.roles import Permiso
from tarjeta.modules.promociones.domain.confianza import NivelConfianza
from tarjeta.modules.promociones.domain.promocion import Promocion
from tarjeta.modules.promociones.infrastructure.repositories import (
    SqlAlchemyPerfilConfianzaRepository,
    SqlAlchemyPromocionRepository,
)
from tarjeta.shared.api.dependencies import SessionDep, SettingsDep
from tarjeta.shared.domain.errors import NotFoundError, ValidationError
from tarjeta.shared.domain.types import EntityId

router = APIRouter(prefix="/api/v1/contenido", tags=["contenido"])


def _puertos(session: SessionDep, settings: SettingsDep):  # type: ignore[no-untyped-def]
    return construir_puertos_contenido(session, settings)


def _periodo() -> str:
    return datetime.now(UTC).strftime("%Y-%m")


def _texto_beneficio(promo: Promocion) -> str:
    valor = promo.valor_para("BLACK")
    m = promo.mecanica.value
    if m in ("PORCENTAJE", "CUPON_UNICO"):
        return f"{valor}%"
    if m == "MONTO_FIJO":
        return f"${valor} OFF"
    if m == "DOS_POR_UNO":
        return "2x1"
    if m in ("PRECIO_ESPECIAL", "COMBO"):
        return f"${valor}"
    if m == "MULTIPLICADOR_PUNTOS":
        return f"{valor} pts x $100"
    return promo.titulo


async def _contexto_promo(
    session: SessionDep, id_comercio: str, id_promocion: str
) -> tuple[Promocion, Superposicion, str, bool]:
    """Devuelve (promo, superposición desde la promo, nombre_fantasia+rubro, auto_aprueba)."""
    promo = await SqlAlchemyPromocionRepository(session).obtener(EntityId.from_str(id_promocion))
    if promo is None:
        raise NotFoundError("Promoción inexistente.")
    comercio = await SqlAlchemyComercioRepository(session).obtener(EntityId.from_str(id_comercio))
    nombre = comercio.nombre_fantasia if comercio else "Comercio"
    rubro = comercio.rubro if comercio else ""
    superposicion = Superposicion(
        porcentaje=_texto_beneficio(promo),
        vigencia=f"Hasta {promo.vigencia.fecha_hasta.isoformat()}",
        nombre=nombre,
    )
    perfil = await SqlAlchemyPerfilConfianzaRepository(session).obtener(
        EntityId.from_str(id_comercio)
    )
    # §11.6: VERIFICADO publica sin cola; el resto entra a moderación.
    auto_aprueba = perfil is not None and perfil.nivel is NivelConfianza.VERIFICADO
    return promo, superposicion, f"{rubro}|{nombre}", auto_aprueba


# ------------------------------------------------------------------ schemas


class Mensaje(BaseModel):
    mensaje: str


class PlantillaOut(BaseModel):
    id: str
    nombre: str


class CuotaOut(BaseModel):
    usados: int
    cuota: int
    disponibles: int


class GenerarIn(BaseModel):
    id_promocion: str
    idea: str
    plantilla: str = PLANTILLA_POR_DEFECTO


class FotoIn(BaseModel):
    id_promocion: str
    foto_base64: str
    plantilla: str = PLANTILLA_POR_DEFECTO


class PlantillaIn(BaseModel):
    plantilla: str


class VarianteIn(BaseModel):
    indice: int


class ModeracionPiezaIn(BaseModel):
    motivo: str = ""


class PiezaOut(BaseModel):
    id: str
    id_promocion: str
    origen: str
    estado: str
    plantilla: str
    superposicion: dict[str, str]
    generada_por_ia: bool
    modelo_ia: str | None
    formatos: dict[str, str]
    variantes: list[str]


def _pieza_out(pieza: Pieza, almacen) -> PiezaOut:  # type: ignore[no-untyped-def]
    return PiezaOut(
        id=str(pieza.id),
        id_promocion=pieza.id_promocion,
        origen=pieza.origen.value,
        estado=pieza.estado.value,
        plantilla=pieza.plantilla,
        superposicion={
            "porcentaje": pieza.superposicion.porcentaje,
            "vigencia": pieza.superposicion.vigencia,
            "nombre": pieza.superposicion.nombre,
        },
        generada_por_ia=pieza.generada_por_ia,
        modelo_ia=pieza.modelo_ia,
        formatos={k: almacen.url_publica(v) for k, v in pieza.formatos.items()},
        variantes=[almacen.url_publica(v) for v in pieza.variantes_claves],
    )


# ------------------------------------------------------------------ comercio


@router.get("/plantillas", response_model=list[PlantillaOut])
async def plantillas() -> list[PlantillaOut]:
    return [PlantillaOut(id=p.id, nombre=p.nombre) for p in PLANTILLAS]


@router.get("/creditos", response_model=CuotaOut)
async def creditos(
    session: SessionDep,
    settings: SettingsDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> CuotaOut:
    est = await Creditos(_puertos(session, settings)).estado(
        id_comercio=str(actor.id_comercio), periodo=_periodo()
    )
    return CuotaOut(usados=est.usados, cuota=est.cuota, disponibles=est.disponibles)


@router.post("/piezas/generar", response_model=PiezaOut)
async def generar(
    body: GenerarIn,
    session: SessionDep,
    settings: SettingsDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> PiezaOut:
    id_comercio = str(actor.id_comercio)
    promo, superposicion, contexto, auto = await _contexto_promo(
        session, id_comercio, body.id_promocion
    )
    rubro, nombre = contexto.split("|", 1)
    puertos = _puertos(session, settings)
    pieza = await GenerarPieza(puertos).ejecutar(
        id_comercio=id_comercio,
        id_promocion=body.id_promocion,
        idea=body.idea,
        rubro=rubro,
        nombre_fantasia=nombre,
        mecanica=promo.mecanica.value,
        estilo_plantilla=body.plantilla,
        superposicion=superposicion,
        plantilla=body.plantilla,
        auto_aprueba=auto,
        periodo=_periodo(),
    )
    return _pieza_out(pieza, puertos.almacen)


@router.post("/piezas/foto", response_model=PiezaOut)
async def desde_foto(
    body: FotoIn,
    session: SessionDep,
    settings: SettingsDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> PiezaOut:
    id_comercio = str(actor.id_comercio)
    _promo, superposicion, _contexto, auto = await _contexto_promo(
        session, id_comercio, body.id_promocion
    )
    try:
        foto = base64.b64decode(body.foto_base64)
    except (ValueError, TypeError) as exc:
        raise ValidationError("La foto no es un base64 válido.") from exc
    puertos = _puertos(session, settings)
    pieza = await CrearPiezaDesdeFoto(puertos).ejecutar(
        id_comercio=id_comercio,
        id_promocion=body.id_promocion,
        foto=foto,
        superposicion=superposicion,
        plantilla=body.plantilla,
        auto_aprueba=auto,
    )
    return _pieza_out(pieza, puertos.almacen)


@router.get("/piezas", response_model=list[PiezaOut])
async def listar_piezas(
    session: SessionDep,
    settings: SettingsDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> list[PiezaOut]:
    puertos = _puertos(session, settings)
    piezas = await puertos.piezas.listar_por_comercio(str(actor.id_comercio))
    return [_pieza_out(p, puertos.almacen) for p in piezas]


async def _pieza_propia(session: SessionDep, settings: SettingsDep, id_pieza: str, actor):  # type: ignore[no-untyped-def]
    puertos = _puertos(session, settings)
    pieza = await puertos.piezas.obtener(EntityId.from_str(id_pieza))
    if pieza is None or pieza.id_comercio != str(actor.id_comercio):
        raise NotFoundError("Pieza inexistente.")
    return puertos


@router.post("/piezas/{id_pieza}/plantilla", response_model=PiezaOut)
async def cambiar_plantilla(
    id_pieza: str,
    body: PlantillaIn,
    session: SessionDep,
    settings: SettingsDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> PiezaOut:
    puertos = await _pieza_propia(session, settings, id_pieza, actor)
    pieza = await EditarPieza(puertos).cambiar_plantilla(
        id_pieza=id_pieza, plantilla=body.plantilla
    )
    return _pieza_out(pieza, puertos.almacen)


@router.post("/piezas/{id_pieza}/variante", response_model=PiezaOut)
async def elegir_variante(
    id_pieza: str,
    body: VarianteIn,
    session: SessionDep,
    settings: SettingsDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> PiezaOut:
    puertos = await _pieza_propia(session, settings, id_pieza, actor)
    pieza = await EditarPieza(puertos).elegir_variante(id_pieza=id_pieza, indice=body.indice)
    return _pieza_out(pieza, puertos.almacen)


@router.post("/piezas/{id_pieza}/sincronizar-datos", response_model=PiezaOut)
async def sincronizar_datos(
    id_pieza: str,
    session: SessionDep,
    settings: SettingsDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio(PermisoComercio.PROMOCION_GESTIONAR))
    ],
) -> PiezaOut:
    # §11.5: recompone el texto con el % vigente de la promoción, sin gastar crédito.
    puertos = await _pieza_propia(session, settings, id_pieza, actor)
    pieza = await puertos.piezas.obtener(EntityId.from_str(id_pieza))
    assert pieza is not None
    _promo, superposicion, _c, _a = await _contexto_promo(
        session, str(actor.id_comercio), pieza.id_promocion
    )
    pieza = await RegenerarSuperposicion(puertos).ejecutar(
        id_pieza=id_pieza, superposicion=superposicion
    )
    return _pieza_out(pieza, puertos.almacen)


# ------------------------------------------------------------------ moderación municipal


@router.get("/moderacion", response_model=list[PiezaOut])
async def cola_moderacion(
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[Actor, Depends(requiere(Permiso.PROMOCION_MODERAR))],
) -> list[PiezaOut]:
    puertos = _puertos(session, settings)
    return [_pieza_out(p, puertos.almacen) for p in await ModeracionPiezas(puertos).cola()]


@router.post("/moderacion/{id_pieza}/aprobar", response_model=Mensaje)
async def aprobar_pieza(
    id_pieza: str,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[Actor, Depends(requiere(Permiso.PROMOCION_MODERAR))],
) -> Mensaje:
    await ModeracionPiezas(_puertos(session, settings)).aprobar(id_pieza=id_pieza)
    return Mensaje(mensaje="Pieza aprobada.")


@router.post("/moderacion/{id_pieza}/rechazar", response_model=Mensaje)
async def rechazar_pieza(
    id_pieza: str,
    body: ModeracionPiezaIn,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[Actor, Depends(requiere(Permiso.PROMOCION_MODERAR))],
) -> Mensaje:
    await ModeracionPiezas(_puertos(session, settings)).rechazar(
        id_pieza=id_pieza, motivo=body.motivo
    )
    return Mensaje(mensaje="Pieza rechazada.")


# ------------------------------------------------------------------ servir objetos


@router.get("/objeto/{clave:path}")
async def servir_objeto(clave: str, settings: SettingsDep) -> Response:
    # Claves con UUID no adivinables: se sirve como estático (para que funcione en <img src>).
    if ".." in clave:
        raise NotFoundError("Objeto inexistente.")
    datos = await AlmacenLocal(settings.contenido_almacen_dir).leer(clave)
    if datos is None:
        raise NotFoundError("Objeto inexistente.")
    return Response(
        content=datos,
        media_type="image/png",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )
