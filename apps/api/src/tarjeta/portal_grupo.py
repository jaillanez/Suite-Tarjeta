"""Portal del grupo familiar (composition root, §10).

Cruza `grupo` con `ciudadania`/`padron` (quién puede crear, sucesión por Black propio) y `puntos`
(pozo común). La herencia de nivel NO se toca acá: los casos emiten eventos y el dispatcher la
recalcula (ver `orquestacion` + `herencia`). El pozo, en cambio, se traspasa atómicamente al
cambiar de modo.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Request
from pydantic import BaseModel

from tarjeta.herencia import es_black_propio_al_dia
from tarjeta.modules.canje.infrastructure.repositories import SqlAlchemyTransaccionRepository
from tarjeta.modules.ciudadania.domain.nivel import Nivel, NivelOrigen
from tarjeta.modules.ciudadania.infrastructure.repositories import (
    SqlAlchemyPerfilCiudadanoRepository,
)
from tarjeta.modules.grupo.application.casos import (
    AceptarInvitacion,
    CrearGrupo,
    DisolverGrupo,
    GestionMiembro,
    InvitarMiembro,
    SalirDelGrupo,
    SucederTitular,
)
from tarjeta.modules.grupo.domain.tipos import ModoBilletera, RolGrupo
from tarjeta.modules.grupo.infrastructure.composition import construir_puertos_grupo
from tarjeta.modules.grupo.infrastructure.repositories import SqlAlchemyGrupoRepository
from tarjeta.modules.puntos.application.pozo import TraspasarPozo
from tarjeta.modules.puntos.infrastructure.composition import construir_puertos_puntos
from tarjeta.shared.api.auth import SesionDep
from tarjeta.shared.api.dependencies import SessionDep, SettingsDep
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

router = APIRouter(prefix="/api/v1/grupo", tags=["grupo"])


def _puertos(session: SessionDep):  # type: ignore[no-untyped-def]
    return construir_puertos_grupo(session)


# ------------------------------------------------------------------ schemas


class Mensaje(BaseModel):
    mensaje: str


class CrearIn(BaseModel):
    modo_billetera: str = "COMUN"


class GrupoInvitacionOut(BaseModel):
    token: str
    texto_declaracion: str
    vence_en: str


class InvitacionDetalleOut(BaseModel):
    id_grupo: str
    texto_declaracion: str
    vence_en: str
    vigente: bool


class ModoIn(BaseModel):
    modo_billetera: str


class TopeIn(BaseModel):
    tope_mensual: int | None = None


class ConsumoMes(BaseModel):
    operaciones: int
    monto: int
    puntos_acreditados: int
    puntos_usados: int


class MiembroOut(BaseModel):
    id_persona: str
    rol: str
    estado: str
    tope_mensual: int | None
    consumo_mes: ConsumoMes


class MiGrupoOut(BaseModel):
    sin_grupo: bool
    es_titular: bool
    id_grupo: str | None = None
    modo_billetera: str | None = None
    miembros: list[MiembroOut] = []
    alertas: list[dict[str, str]] = []


def _ip(request: Request) -> str:
    return request.client.host if request.client else "desconocida"


# ------------------------------------------------------------------ crear / invitar / aceptar


@router.post("/crear", response_model=dict)
async def crear_grupo(
    body: CrearIn, sesion: SesionDep, session: SessionDep, settings: SettingsDep
) -> dict[str, str]:
    puede = await es_black_propio_al_dia(session, settings, sesion.id_persona)
    grupo = await CrearGrupo(_puertos(session)).ejecutar(
        id_titular=sesion.id_persona,
        modo=ModoBilletera(body.modo_billetera),
        es_black_propio_al_dia=puede,
    )
    return {"id_grupo": str(grupo.id)}


@router.post("/invitar", response_model=GrupoInvitacionOut)
async def invitar(request: Request, sesion: SesionDep, session: SessionDep) -> GrupoInvitacionOut:
    grupo = await SqlAlchemyGrupoRepository(session).por_titular(sesion.id_persona)
    if grupo is None:
        raise NotFoundError("No tenés un grupo del que seas titular.")
    inv = await InvitarMiembro(_puertos(session)).ejecutar(
        id_grupo=str(grupo.id), id_actor=sesion.id_persona, ip=_ip(request)
    )
    return GrupoInvitacionOut(
        token=inv.token,
        texto_declaracion=inv.texto_declaracion,
        vence_en=inv.vence_en.isoformat(),
    )


@router.get("/invitacion/{token}", response_model=InvitacionDetalleOut)
async def ver_invitacion(
    token: str, sesion: SesionDep, session: SessionDep
) -> InvitacionDetalleOut:
    inv = await _puertos(session).invitaciones.por_token(token)
    if inv is None:
        raise NotFoundError("Invitación inexistente.")
    return InvitacionDetalleOut(
        id_grupo=str(inv.id_grupo),
        texto_declaracion=inv.texto_declaracion,
        vence_en=inv.vence_en.isoformat(),
        vigente=inv.vigente(datetime.now(UTC)),
    )


@router.post("/invitacion/{token}/aceptar", response_model=dict)
async def aceptar_invitacion(token: str, sesion: SesionDep, session: SessionDep) -> dict[str, str]:
    grupo = await AceptarInvitacion(_puertos(session)).ejecutar(
        token=token, id_invitado=sesion.id_persona
    )
    return {"id_grupo": str(grupo.id)}


# ------------------------------------------------------------------ salir / disolver / sucesión


@router.post("/salir", response_model=Mensaje)
async def salir(sesion: SesionDep, session: SessionDep) -> Mensaje:
    grupos = SqlAlchemyGrupoRepository(session)
    grupo = await grupos.por_titular(sesion.id_persona)
    if grupo is None:
        # Miembro común: salida inmediata.
        miembro = await grupos.miembro_de(sesion.id_persona)
        if miembro is None:
            raise NotFoundError("No pertenecés a ningún grupo.")
        await SalirDelGrupo(_puertos(session)).ejecutar(
            id_grupo=str(miembro.id_grupo), id_persona=sesion.id_persona
        )
        return Mensaje(mensaje="Saliste del grupo.")
    # Titular: sucesión al miembro más antiguo que sea Black por mérito propio; si no, disolución.
    perfiles = SqlAlchemyPerfilCiudadanoRepository(session)
    sucesor: str | None = None
    for m in await grupos.miembros_activos(grupo.id):
        if m.rol is RolGrupo.TITULAR:
            continue
        perfil = await perfiles.obtener(EntityId.from_str(m.id_persona))
        if perfil and perfil.nivel is Nivel.BLACK and perfil.nivel_origen is NivelOrigen.PROPIO:
            sucesor = m.id_persona
            break
    if sucesor is not None:
        await SucederTitular(_puertos(session)).ejecutar(
            id_grupo=str(grupo.id),
            id_titular_actual=sesion.id_persona,
            id_nuevo_titular=sucesor,
        )
        return Mensaje(mensaje="Cediste la titularidad y saliste del grupo.")
    await DisolverGrupo(_puertos(session)).ejecutar(
        id_grupo=str(grupo.id), id_actor=sesion.id_persona
    )
    return Mensaje(mensaje="No había sucesor Black propio: el grupo se disolvió.")


@router.post("/disolver", response_model=Mensaje)
async def disolver(sesion: SesionDep, session: SessionDep) -> Mensaje:
    grupo = await SqlAlchemyGrupoRepository(session).por_titular(sesion.id_persona)
    if grupo is None:
        raise NotFoundError("No sos titular de ningún grupo.")
    await DisolverGrupo(_puertos(session)).ejecutar(
        id_grupo=str(grupo.id), id_actor=sesion.id_persona
    )
    return Mensaje(mensaje="Grupo disuelto.")


# ------------------------------------------------------------------ modo de billetera (con pozo)


@router.post("/modo", response_model=Mensaje)
async def cambiar_modo(body: ModoIn, sesion: SesionDep, session: SessionDep) -> Mensaje:
    grupos = SqlAlchemyGrupoRepository(session)
    grupo = await grupos.por_titular(sesion.id_persona)
    if grupo is None:
        raise NotFoundError("No sos titular de ningún grupo.")
    nuevo = ModoBilletera(body.modo_billetera)
    # §10.5: al pasar de COMÚN a INDIVIDUAL el pozo queda en el titular (traspaso atómico).
    if grupo.modo_billetera is ModoBilletera.COMUN and nuevo is ModoBilletera.INDIVIDUAL:
        await TraspasarPozo(construir_puertos_puntos(session)).al_titular(
            id_grupo=str(grupo.id), id_titular=grupo.id_titular
        )
    grupo.cambiar_modo(nuevo)
    await grupos.guardar(grupo)
    await _puertos(session).outbox.escribir(grupo.pull_events())
    await _puertos(session).uow.commit()
    return Mensaje(mensaje=f"Modo de billetera: {nuevo.value}.")


# ------------------------------------------------------------------ panel del titular


@router.get("/mi-grupo", response_model=MiGrupoOut)
async def mi_grupo(sesion: SesionDep, session: SessionDep) -> MiGrupoOut:
    grupos = SqlAlchemyGrupoRepository(session)
    grupo = await grupos.por_titular(sesion.id_persona)
    if grupo is None:
        miembro = await grupos.miembro_de(sesion.id_persona)
        if miembro is None:
            return MiGrupoOut(sin_grupo=True, es_titular=False)
        g = await grupos.obtener(miembro.id_grupo)
        return MiGrupoOut(
            sin_grupo=False,
            es_titular=False,
            id_grupo=str(miembro.id_grupo),
            modo_billetera=g.modo_billetera.value if g else None,
        )
    # Titular: ve montos y puntos por miembro, nunca el detalle de compras (§10.6).
    transacciones = SqlAlchemyTransaccionRepository(session)
    ahora = datetime.now(UTC)
    inicio_mes = ahora.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    miembros: list[MiembroOut] = []
    for m in await grupos.miembros_activos(grupo.id):
        ops, monto, _desc, pac, pus = await transacciones.resumen_persona_desde(
            m.id_persona, inicio_mes
        )
        miembros.append(
            MiembroOut(
                id_persona=m.id_persona,
                rol=m.rol.value,
                estado=m.estado.value,
                tope_mensual=m.tope_mensual,
                consumo_mes=ConsumoMes(
                    operaciones=ops, monto=monto, puntos_acreditados=pac, puntos_usados=pus
                ),
            )
        )
    alertas = [
        {"tipo": t, "detalle": d, "fecha": f}
        for t, d, f in await _puertos(session).alertas.de_grupo(str(grupo.id))
    ]
    return MiGrupoOut(
        sin_grupo=False,
        es_titular=True,
        id_grupo=str(grupo.id),
        modo_billetera=grupo.modo_billetera.value,
        miembros=miembros,
        alertas=alertas,
    )


# ------------------------------------------------------------------ gestión de miembros


@router.post("/miembros/{id_persona}/suspender", response_model=Mensaje)
async def suspender_miembro(id_persona: str, sesion: SesionDep, session: SessionDep) -> Mensaje:
    grupo = await _grupo_titular(session, sesion.id_persona)
    await GestionMiembro(_puertos(session)).suspender(
        id_grupo=str(grupo.id), id_actor=sesion.id_persona, id_persona=id_persona
    )
    return Mensaje(mensaje="Miembro suspendido.")


@router.post("/miembros/{id_persona}/reactivar", response_model=Mensaje)
async def reactivar_miembro(id_persona: str, sesion: SesionDep, session: SessionDep) -> Mensaje:
    grupo = await _grupo_titular(session, sesion.id_persona)
    await GestionMiembro(_puertos(session)).reactivar(
        id_grupo=str(grupo.id), id_actor=sesion.id_persona, id_persona=id_persona
    )
    return Mensaje(mensaje="Miembro reactivado.")


@router.post("/miembros/{id_persona}/tope", response_model=Mensaje)
async def fijar_tope(
    id_persona: str, body: TopeIn, sesion: SesionDep, session: SessionDep
) -> Mensaje:
    grupo = await _grupo_titular(session, sesion.id_persona)
    await GestionMiembro(_puertos(session)).fijar_tope(
        id_grupo=str(grupo.id),
        id_actor=sesion.id_persona,
        id_persona=id_persona,
        tope_mensual=body.tope_mensual,
    )
    return Mensaje(mensaje="Tope actualizado.")


async def _grupo_titular(session: SessionDep, id_persona: str) -> Any:
    grupo = await SqlAlchemyGrupoRepository(session).por_titular(id_persona)
    if grupo is None:
        raise NotFoundError("No sos titular de ningún grupo.")
    return grupo
