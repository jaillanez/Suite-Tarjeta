"""Routers FastAPI del módulo identidad (bajo /api/v1)."""

from __future__ import annotations

import dataclasses
from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response, status

from tarjeta.modules.identidad.application.activar_mfa import ActivarMfa
from tarjeta.modules.identidad.application.cambiar_perfil import CambiarPerfil, ListarPerfiles
from tarjeta.modules.identidad.application.dto import ConsentimientoInput, RegistroInput
from tarjeta.modules.identidad.application.gestionar_dispositivos import (
    ListarDispositivos,
    RegistrarDispositivo,
    RevocarDispositivo,
)
from tarjeta.modules.identidad.application.iniciar_sesion import IniciarSesion, VerificarMfa
from tarjeta.modules.identidad.application.recuperar_password import (
    ConfirmarRecuperacion,
    SolicitarRecuperacion,
)
from tarjeta.modules.identidad.application.refrescar_sesion import RefrescarSesion
from tarjeta.modules.identidad.application.registrar_consentimiento import (
    ListarConsentimientos,
    RegistrarConsentimiento,
)
from tarjeta.modules.identidad.application.registrar_persona import RegistrarPersona
from tarjeta.modules.identidad.application.verificar_celular import SolicitarOtp, VerificarCelular
from tarjeta.shared.api.dependencies import SettingsDep
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

from .cookies import clear_refresh_cookie, leer_refresh, modo_cookie, set_refresh_cookie
from .deps import ClaimsDep, HuellaDep, PuertosDep, get_ip, get_user_agent, require_verificada
from .schemas import (
    DispositivoCrearRequest,
    DispositivoResponse,
    LoginRequest,
    LoginResponse,
    MensajeResponse,
    MfaActivarResponse,
    MfaVerificarRequest,
    PerfilOut,
    PersonaMeResponse,
    PersonaPatchRequest,
    RecuperarConfirmarRequest,
    RecuperarRequest,
    ReenviarOtpRequest,
    RefreshRequest,
    RegistroRequest,
    TokensResponse,
    VerificarCelularRequest,
)

router = APIRouter(prefix="/api/v1", tags=["identidad"])


# --- auth --------------------------------------------------------------------
@router.post("/auth/registro", status_code=status.HTTP_201_CREATED, response_model=MensajeResponse)
async def registro(body: RegistroRequest, request: Request, puertos: PuertosDep) -> MensajeResponse:
    entrada = RegistroInput(
        dni=body.dni,
        fecha_nacimiento=body.fecha_nacimiento,
        password=body.password,
        consentimientos=[ConsentimientoInput(c.tipo, c.otorgado) for c in body.consentimientos],
        celular=body.celular,
        email=body.email,
        ip=get_ip(request),
        user_agent=get_user_agent(request),
    )
    await RegistrarPersona(puertos).ejecutar(entrada)
    return MensajeResponse(mensaje="Registro exitoso.")


@router.post("/auth/verificar-celular", response_model=MensajeResponse)
async def verificar_celular(body: VerificarCelularRequest, puertos: PuertosDep) -> MensajeResponse:
    await VerificarCelular(puertos).ejecutar(celular=body.celular, codigo=body.codigo)
    return MensajeResponse(mensaje="Celular verificado.")


@router.post("/auth/reenviar-otp", response_model=MensajeResponse)
async def reenviar_otp(
    body: ReenviarOtpRequest, request: Request, puertos: PuertosDep
) -> MensajeResponse:
    await SolicitarOtp(puertos).ejecutar(celular=body.celular, ip=get_ip(request))
    return MensajeResponse(mensaje="Código enviado.")


@router.post("/auth/login", response_model=LoginResponse)
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    puertos: PuertosDep,
    huella: HuellaDep,
    settings: SettingsDep,
) -> LoginResponse:
    r = await IniciarSesion(puertos).ejecutar(
        dni=body.dni, password=body.password, ip=get_ip(request), huella=huella
    )
    return _login_response(r, request, response, settings)


@router.post("/auth/mfa/verificar", response_model=LoginResponse)
async def mfa_verificar(
    body: MfaVerificarRequest,
    request: Request,
    response: Response,
    puertos: PuertosDep,
    huella: HuellaDep,
    settings: SettingsDep,
) -> LoginResponse:
    r = await VerificarMfa(puertos).ejecutar(
        mfa_token=body.mfa_token, codigo=body.codigo, huella=huella
    )
    return _login_response(r, request, response, settings)


@router.post("/auth/refresh", response_model=TokensResponse)
async def refresh(
    body: RefreshRequest,
    request: Request,
    response: Response,
    puertos: PuertosDep,
    huella: HuellaDep,
    settings: SettingsDep,
) -> TokensResponse:
    t = await RefrescarSesion(puertos).ejecutar(
        refresh_token=leer_refresh(request, body.refresh_token), huella=huella
    )
    return _tokens_response(t.access_token, t.refresh_token, request, response, settings)


@router.post("/auth/logout", response_model=MensajeResponse)
async def logout(
    body: RefreshRequest, request: Request, response: Response, puertos: PuertosDep
) -> MensajeResponse:
    await puertos.refresh.revocar(leer_refresh(request, body.refresh_token))
    await puertos.uow.commit()
    if modo_cookie(request):
        clear_refresh_cookie(response)
    return MensajeResponse(mensaje="Sesión cerrada.")


@router.post(
    "/auth/recuperar", status_code=status.HTTP_202_ACCEPTED, response_model=MensajeResponse
)
async def recuperar(body: RecuperarRequest, puertos: PuertosDep) -> MensajeResponse:
    # §04.0.B: recuperación por email. Nunca revela si el email existe (anti-enumeración).
    # El envío real depende del proveedor (EMAIL_PROVEEDOR); en dev se escribe al log.
    await SolicitarRecuperacion(puertos).ejecutar(email=body.email)
    return MensajeResponse(mensaje="Si la cuenta existe, enviamos instrucciones por email.")


@router.post("/auth/recuperar/confirmar", response_model=MensajeResponse)
async def recuperar_confirmar(
    body: RecuperarConfirmarRequest, puertos: PuertosDep
) -> MensajeResponse:
    # Cambia la contraseña con un token de un solo uso y cierra todas las sesiones abiertas.
    await ConfirmarRecuperacion(puertos).ejecutar(token=body.token, password=body.password)
    return MensajeResponse(mensaje="Contraseña actualizada. Iniciá sesión con la nueva.")


@router.get("/canje/puerta", response_model=MensajeResponse)
async def puerta_canje(
    id_persona: Annotated[str, Depends(require_verificada)],
) -> MensajeResponse:
    # Endpoint testigo de la puerta de canje (§05.0.B). El canje real llega en su módulo.
    return MensajeResponse(mensaje="Habilitado para canjear.")


@router.get("/auth/perfiles", response_model=list[PerfilOut])
async def perfiles(claims: ClaimsDep, puertos: PuertosDep) -> list[PerfilOut]:
    ps = await ListarPerfiles(puertos).ejecutar(id_persona=claims.id_persona)
    return [PerfilOut(**dataclasses.asdict(p)) for p in ps]


@router.post("/auth/perfiles/{clave}/activar", response_model=TokensResponse)
async def activar_perfil(
    clave: str,
    request: Request,
    response: Response,
    claims: ClaimsDep,
    puertos: PuertosDep,
    huella: HuellaDep,
    settings: SettingsDep,
) -> TokensResponse:
    t = await CambiarPerfil(puertos).ejecutar(
        id_persona=claims.id_persona, clave_destino=clave, huella=huella
    )
    return _tokens_response(t.access_token, t.refresh_token, request, response, settings)


# --- personas/me -------------------------------------------------------------
@router.get("/personas/me", response_model=PersonaMeResponse)
async def personas_me(claims: ClaimsDep, puertos: PuertosDep) -> PersonaMeResponse:
    persona = await puertos.personas.obtener_por_id(EntityId.from_str(claims.id_persona))
    if persona is None:
        raise NotFoundError("Persona inexistente.")
    return PersonaMeResponse(
        id=str(persona.id),
        dni=str(persona.dni),
        cuil=str(persona.cuil) if persona.cuil else None,
        apellido=persona.apellido,
        nombre=persona.nombre,
        celular=str(persona.celular) if persona.celular else None,
        email=str(persona.email) if persona.email else None,
        estado_identidad=str(persona.estado_identidad),
        celular_verificado=persona.celular_verificado,
        perfiles=[
            PerfilOut(
                clave=p.clave(),
                tipo=str(p.tipo),
                id_comercio=str(p.id_comercio) if p.id_comercio else None,
                rol=p.rol,
            )
            for p in persona.perfiles
        ],
    )


@router.patch("/personas/me", response_model=MensajeResponse)
async def personas_me_patch(
    body: PersonaPatchRequest, claims: ClaimsDep, puertos: PuertosDep
) -> MensajeResponse:
    from tarjeta.modules.identidad.domain.value_objects import Email

    persona = await puertos.personas.obtener_por_id(EntityId.from_str(claims.id_persona))
    if persona is None:
        raise NotFoundError("Persona inexistente.")
    if body.email is not None:
        persona.email = Email(body.email)
        persona.email_verificado = False
    await puertos.personas.guardar(persona)
    await puertos.uow.commit()
    return MensajeResponse(mensaje="Datos actualizados.")


@router.get("/personas/me/consentimientos", response_model=dict[str, bool])
async def consentimientos_get(claims: ClaimsDep, puertos: PuertosDep) -> dict[str, bool]:
    return await ListarConsentimientos(puertos).ejecutar(id_persona=claims.id_persona)


@router.post("/personas/me/consentimientos", response_model=MensajeResponse)
async def consentimientos_post(
    body: ConsentimientoInput,
    request: Request,
    claims: ClaimsDep,
    puertos: PuertosDep,
) -> MensajeResponse:
    await RegistrarConsentimiento(puertos).ejecutar(
        id_persona=claims.id_persona,
        entrada=body,
        ip=get_ip(request),
        ua=get_user_agent(request),
    )
    return MensajeResponse(mensaje="Consentimiento registrado.")


@router.post("/personas/me/dispositivos", response_model=DispositivoResponse)
async def dispositivos_post(
    body: DispositivoCrearRequest, claims: ClaimsDep, puertos: PuertosDep
) -> DispositivoResponse:
    d = await RegistrarDispositivo(puertos).ejecutar(
        id_persona=claims.id_persona,
        nombre=body.nombre_declarado,
        plataforma=body.plataforma,
        huella=body.huella,
    )
    return DispositivoResponse(**dataclasses.asdict(d))


@router.get("/personas/me/dispositivos", response_model=list[DispositivoResponse])
async def dispositivos_get(claims: ClaimsDep, puertos: PuertosDep) -> list[DispositivoResponse]:
    ds = await ListarDispositivos(puertos).ejecutar(id_persona=claims.id_persona)
    return [DispositivoResponse(**dataclasses.asdict(d)) for d in ds]


@router.delete("/personas/me/dispositivos/{id_dispositivo}", response_model=MensajeResponse)
async def dispositivos_delete(
    id_dispositivo: str, claims: ClaimsDep, puertos: PuertosDep
) -> MensajeResponse:
    await RevocarDispositivo(puertos).ejecutar(
        id_persona=claims.id_persona, id_dispositivo=id_dispositivo
    )
    return MensajeResponse(mensaje="Dispositivo revocado.")


@router.post("/personas/me/mfa/activar", response_model=MfaActivarResponse)
async def mfa_activar(claims: ClaimsDep, puertos: PuertosDep) -> MfaActivarResponse:
    persona = await puertos.personas.obtener_por_id(EntityId.from_str(claims.id_persona))
    if persona is None:
        raise NotFoundError("Persona inexistente.")
    cuenta = str(persona.dni)
    a = await ActivarMfa(puertos).ejecutar(id_persona=claims.id_persona, cuenta=cuenta)
    return MfaActivarResponse(
        secreto=a.secreto, uri=a.uri, codigos_recuperacion=a.codigos_recuperacion
    )


def _tokens_response(
    access: str, refresh: str, request: Request, response: Response, settings: SettingsDep
) -> TokensResponse:
    """En modo cookie, el refresh va a la cookie HttpOnly y NO al cuerpo; si no, va al cuerpo."""
    if modo_cookie(request):
        set_refresh_cookie(response, refresh, settings)
        return TokensResponse(access_token=access, refresh_token="")
    return TokensResponse(access_token=access, refresh_token=refresh)


def _login_response(
    r: object, request: Request, response: Response, settings: SettingsDep
) -> LoginResponse:
    from tarjeta.modules.identidad.application.dto import LoginResultado

    assert isinstance(r, LoginResultado)
    tokens = (
        _tokens_response(r.tokens.access_token, r.tokens.refresh_token, request, response, settings)
        if r.tokens
        else None
    )
    return LoginResponse(
        mfa_requerido=r.mfa_requerido,
        perfiles=[PerfilOut(**dataclasses.asdict(p)) for p in r.perfiles],
        perfil_activo=r.perfil_activo,
        tokens=tokens,
        mfa_token=r.mfa_token,
    )
