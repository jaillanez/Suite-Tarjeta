"""Portal municipal (composition root): endpoints que cruzan varios módulos.

No es un módulo de dominio; por eso puede importar identidad/ciudadania/padron/gobierno
(los módulos entre sí siguen sin importarse). Cubre ficha 360, alta presencial, reclamo de
cuenta (con doble conformidad) y asignación de agentes.
"""

from __future__ import annotations

import secrets
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Request
from pydantic import BaseModel

from tarjeta.modules.ciudadania.infrastructure.repositories import (
    SqlAlchemyPerfilCiudadanoRepository,
)
from tarjeta.modules.gobierno.api.deps import Actor, requiere
from tarjeta.modules.gobierno.application.doble_conformidad import (
    DecidirAprobacion,
    SolicitarAprobacion,
)
from tarjeta.modules.gobierno.domain.auditoria import RegistroAuditoria
from tarjeta.modules.gobierno.domain.roles import Permiso, RolMunicipal
from tarjeta.modules.gobierno.infrastructure.composition import construir_puertos_gobierno
from tarjeta.modules.identidad.application.dto import ConsentimientoInput, RegistroInput
from tarjeta.modules.identidad.application.registrar_persona import RegistrarPersona
from tarjeta.modules.identidad.infrastructure.composition import construir_puertos
from tarjeta.modules.identidad.infrastructure.repositories import (
    SqlAlchemyDispositivoRepository,
)
from tarjeta.modules.padron.infrastructure.composition import construir_puertos_padron
from tarjeta.shared.api.dependencies import RedisDep, SessionDep, SettingsDep
from tarjeta.shared.domain.errors import NotFoundError, PermissionDeniedError
from tarjeta.shared.domain.types import EntityId

router = APIRouter(prefix="/api/v1/portal", tags=["portal-municipal"])


class Mensaje(BaseModel):
    mensaje: str


class DispositivoFicha(BaseModel):
    id: str
    nombre: str
    estado: str


class Ficha360Out(BaseModel):
    id: str
    dni: str
    apellido: str
    nombre: str
    estado_identidad: str
    nivel: str | None
    tarjeta: str | None
    estado_tarjeta: str | None
    padron_al_dia: bool | None
    padron_actualizado: str | None
    dispositivos: list[DispositivoFicha]


class AltaPresencialIn(BaseModel):
    dni: str
    fecha_nacimiento: str


class ReclamoIn(BaseModel):
    dni: str
    motivo: str


class DecisionIn(BaseModel):
    motivo: str = ""


class AsignarAgenteIn(BaseModel):
    id_persona: str
    rol: str


@router.get("/ficha360/{id_persona}", response_model=Ficha360Out)
async def ficha360(
    id_persona: str,
    session: SessionDep,
    settings: SettingsDep,
    redis: RedisDep,
    actor: Annotated[Actor, Depends(requiere(Permiso.CIUDADANO_FICHA))],
    x_reauth: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    # §11.3: reautenticación para abrir la ficha; sin caché local (cada apertura consulta).
    if x_reauth != "ok":
        raise PermissionDeniedError("Se requiere reautenticación para abrir la ficha.")

    pid = EntityId.from_str(id_persona)
    id_puertos = construir_puertos(session, settings, redis)
    persona = await id_puertos.personas.obtener_por_id(pid)
    if persona is None:
        raise NotFoundError("Persona inexistente.")
    perfil = await SqlAlchemyPerfilCiudadanoRepository(session).obtener(pid)
    estado = await construir_puertos_padron(session, settings).repo.obtener(pid)
    dispositivos = await SqlAlchemyDispositivoRepository(session).listar_por_persona(pid)

    # Auditar la apertura.
    gob = construir_puertos_gobierno(session)
    await gob.auditoria.agregar(
        RegistroAuditoria.crear(
            accion="ficha360:abrir",
            entidad="persona",
            id_entidad=id_persona,
            id_persona_actor=actor.id_persona,
            rol_actor=actor.rol.value,
        )
    )
    await session.commit()

    return {
        "id": str(persona.id),
        "dni": str(persona.dni),
        "apellido": persona.apellido,
        "nombre": persona.nombre,
        "estado_identidad": str(persona.estado_identidad),
        "nivel": str(perfil.nivel) if perfil else None,
        "tarjeta": perfil.numero_tarjeta if perfil else None,
        "estado_tarjeta": str(perfil.estado_tarjeta) if perfil else None,
        "padron_al_dia": estado.al_dia if estado else None,
        "padron_actualizado": estado.fecha_ultima_consulta.isoformat() if estado else None,
        "dispositivos": [
            {"id": str(d.id), "nombre": d.nombre_declarado, "estado": str(d.estado)}
            for d in dispositivos
        ],
    }


@router.post("/alta-presencial", response_model=dict[str, str])
async def alta_presencial(
    body: AltaPresencialIn,
    request: Request,
    session: SessionDep,
    settings: SettingsDep,
    redis: RedisDep,
    actor: Annotated[Actor, Depends(requiere(Permiso.CIUDADANO_ALTA))],
) -> dict[str, str]:
    password_temporal = secrets.token_urlsafe(9)
    id_puertos = construir_puertos(session, settings, redis)
    id_persona = await RegistrarPersona(id_puertos).ejecutar(
        RegistroInput(
            dni=body.dni,
            fecha_nacimiento=body.fecha_nacimiento,
            password=password_temporal,
            consentimientos=[ConsentimientoInput("TRATAMIENTO_DATOS", True)],
            ip=request.client.host if request.client else "",
            user_agent="alta-presencial",
        )
    )
    return {"id_persona": id_persona, "password_temporal": password_temporal}


@router.post("/reclamos", response_model=dict[str, str])
async def crear_reclamo(
    body: ReclamoIn,
    session: SessionDep,
    actor: Annotated[Actor, Depends(requiere(Permiso.RECLAMO_CUENTA))],
) -> dict[str, str]:
    # Doble conformidad: crea la solicitud; la aprueba otro agente (§05.7).
    gob = construir_puertos_gobierno(session)
    id_solicitud = await SolicitarAprobacion(gob).ejecutar(
        accion="ciudadano:reclamo",
        payload={"dni": body.dni, "motivo": body.motivo},
        id_solicitante=actor.id_persona,
        rol=actor.rol.value,
    )
    return {"id": id_solicitud}


@router.post("/reclamos/{id_solicitud}/aprobar", response_model=Mensaje)
async def aprobar_reclamo(
    id_solicitud: str,
    body: DecisionIn,
    session: SessionDep,
    settings: SettingsDep,
    redis: RedisDep,
    actor: Annotated[Actor, Depends(requiere(Permiso.RECLAMO_CUENTA))],
) -> Mensaje:
    id_puertos = construir_puertos(session, settings, redis)

    async def ejecutar_reclamo(payload: dict[str, Any]) -> None:
        # Revoca todo de la cuenta anterior y resetea credenciales (§05.7).
        persona = await id_puertos.personas.obtener_por_dni(str(payload["dni"]))
        if persona is None:
            raise NotFoundError("No hay cuenta con ese DNI.")
        await id_puertos.refresh.revocar_todo_de(persona.id)
        for d in await id_puertos.dispositivos.listar_por_persona(persona.id):
            d.revocar()
            await id_puertos.dispositivos.guardar(d)
        credencial = await id_puertos.credenciales.obtener_por_persona(persona.id)
        if credencial is not None:
            credencial.actualizar_hash(id_puertos.hasher.hash(secrets.token_urlsafe(16)))
            await id_puertos.credenciales.guardar(credencial)

    await DecidirAprobacion(construir_puertos_gobierno(session)).aprobar(
        id_solicitud=id_solicitud,
        id_aprobador=actor.id_persona,
        rol_aprobador=actor.rol.value,
        motivo=body.motivo,
        ejecutor=ejecutar_reclamo,
    )
    return Mensaje(mensaje="Reclamo aprobado; la cuenta anterior fue revocada.")


@router.post("/agentes", response_model=Mensaje)
async def asignar_agente(
    body: AsignarAgenteIn,
    session: SessionDep,
    settings: SettingsDep,
    redis: RedisDep,
    actor: Annotated[Actor, Depends(requiere(Permiso.ROLES_GESTIONAR))],
) -> Mensaje:
    pid = EntityId.from_str(body.id_persona)
    rol = RolMunicipal(body.rol)
    # Rol municipal en gobierno + perfil municipal en identidad (dueña del hecho, §06.0.B).
    gob = construir_puertos_gobierno(session)
    await gob.agentes.asignar(pid, rol)
    id_puertos = construir_puertos(session, settings, redis)
    persona = await id_puertos.personas.obtener_por_id(pid)
    if persona is None:
        raise NotFoundError("Persona inexistente.")
    persona.otorgar_perfil_municipal(rol.value)
    await id_puertos.personas.guardar(persona)
    await id_puertos.outbox.escribir(persona.pull_events())
    await gob.auditoria.agregar(
        RegistroAuditoria.crear(
            accion="roles:asignar",
            entidad="agente",
            id_entidad=body.id_persona,
            id_persona_actor=actor.id_persona,
            rol_actor=actor.rol.value,
            valor_nuevo={"rol": rol.value},
        )
    )
    await session.commit()
    return Mensaje(mensaje="Agente asignado.")


@router.post("/agentes/{id_persona}/revocar", response_model=Mensaje)
async def revocar_agente(
    id_persona: str,
    body: DecisionIn,
    session: SessionDep,
    settings: SettingsDep,
    redis: RedisDep,
    actor: Annotated[Actor, Depends(requiere(Permiso.ROLES_GESTIONAR))],
) -> Mensaje:
    # identidad revoca el perfil municipal y emite el evento; gobierno desactiva al agente
    # al consumirlo (§06.0.B). También se revocan las sesiones de la persona.
    pid = EntityId.from_str(id_persona)
    id_puertos = construir_puertos(session, settings, redis)
    persona = await id_puertos.personas.obtener_por_id(pid)
    if persona is None:
        raise NotFoundError("Persona inexistente.")
    persona.revocar_perfil_municipal()
    await id_puertos.personas.guardar(persona)
    await id_puertos.refresh.revocar_todo_de(pid)
    await id_puertos.outbox.escribir(persona.pull_events())
    await construir_puertos_gobierno(session).auditoria.agregar(
        RegistroAuditoria.crear(
            accion="roles:revocar",
            entidad="agente",
            id_entidad=id_persona,
            id_persona_actor=actor.id_persona,
            rol_actor=actor.rol.value,
            motivo=body.motivo,
        )
    )
    await session.commit()
    return Mensaje(mensaje="Perfil municipal revocado.")
