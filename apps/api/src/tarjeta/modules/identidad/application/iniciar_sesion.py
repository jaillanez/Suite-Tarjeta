"""Casos de uso: login (con no-filtrado y tiempo constante) y verificación de MFA."""

from __future__ import annotations

import hashlib
import hmac

from tarjeta.modules.identidad.domain.errors import CredencialesInvalidas
from tarjeta.modules.identidad.domain.events import IntentoDeLoginFallido, SesionIniciada
from tarjeta.modules.identidad.domain.perfil import Perfil, TipoPerfil
from tarjeta.modules.identidad.domain.persona import Persona
from tarjeta.shared.domain.errors import AuthenticationError

from .deps import Puertos
from .dto import LoginResultado, PerfilInfo, Tokens
from .permisos import permisos_de

_MFA_SCOPE = "mfa_challenge"


def _perfil_default(persona: Persona) -> Perfil:
    for p in persona.perfiles:
        if p.tipo is TipoPerfil.CIUDADANO:
            return p
    return persona.perfiles[0]


def _perfil_por_clave(persona: Persona, clave: str) -> Perfil | None:
    for p in persona.perfiles:
        if p.clave() == clave:
            return p
    return None


def _perfiles_info(persona: Persona) -> list[PerfilInfo]:
    return [
        PerfilInfo(
            clave=p.clave(),
            tipo=str(p.tipo),
            id_comercio=str(p.id_comercio) if p.id_comercio else None,
            rol=p.rol,
        )
        for p in persona.perfiles
    ]


async def emitir_tokens(
    p: Puertos, persona: Persona, perfil: Perfil, huella: str | None = None
) -> Tokens:
    access = p.tokens.crear(
        id_persona=str(persona.id),
        perfil=perfil.clave(),
        permisos=permisos_de(perfil),
        huella=huella,
    )
    refresh = await p.refresh.emitir(persona.id, perfil.clave())
    await p.outbox.escribir([SesionIniciada(id_persona=str(persona.id), perfil=perfil.clave())])
    await p.uow.commit()
    return Tokens(access_token=access, refresh_token=refresh)


class IniciarSesion:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(
        self, *, dni: str, password: str, ip: str, huella: str | None = None
    ) -> LoginResultado:
        p = self.p
        if ip and not await p.rate_limiter.permitido(f"login:ip:{ip}", p.rate_limit_login, 60):
            raise AuthenticationError("Demasiados intentos. Probá más tarde.")

        persona = await p.personas.obtener_por_dni(dni)
        credencial = (
            await p.credenciales.obtener_por_persona(persona.id) if persona is not None else None
        )

        if persona is not None and credencial is not None:
            ok = p.hasher.verificar(credencial.hash, password)
        else:
            # Equaliza el tiempo de respuesta cuando el usuario no existe.
            p.hasher.hash(password)
            ok = False

        if not ok or persona is None or credencial is None:
            ident = hashlib.sha256(dni.encode()).hexdigest() if persona is None else str(persona.id)
            await p.outbox.escribir([IntentoDeLoginFallido(identificador_hash=ident)])
            await p.uow.commit()
            raise CredencialesInvalidas("Usuario o contraseña incorrectos.")

        if p.hasher.necesita_rehash(credencial.hash):
            credencial.actualizar_hash(p.hasher.hash(password))
            await p.credenciales.guardar(credencial)
            await p.uow.commit()

        mfa = await p.mfa.obtener(persona.id)
        if mfa is not None and mfa.activo:
            reto = p.tokens.crear(id_persona=str(persona.id), perfil=_MFA_SCOPE, permisos=[])
            return LoginResultado(
                mfa_requerido=True,
                perfiles=_perfiles_info(persona),
                mfa_token=reto,
            )

        perfil = _perfil_default(persona)
        tokens = await emitir_tokens(p, persona, perfil, huella)
        return LoginResultado(
            mfa_requerido=False,
            perfiles=_perfiles_info(persona),
            perfil_activo=perfil.clave(),
            tokens=tokens,
        )


class VerificarMfa:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(
        self, *, mfa_token: str, codigo: str, huella: str | None = None
    ) -> LoginResultado:
        p = self.p
        claims = p.tokens.decodificar(mfa_token)
        if claims.perfil != _MFA_SCOPE:
            raise AuthenticationError("Token de MFA inválido.")

        from tarjeta.shared.domain.types import EntityId

        persona = await p.personas.obtener_por_id(EntityId.from_str(claims.id_persona))
        mfa = await p.mfa.obtener(EntityId.from_str(claims.id_persona)) if persona else None
        if persona is None or mfa is None or not mfa.activo:
            raise AuthenticationError("MFA no configurado.")

        codigo_hash = hashlib.sha256(codigo.encode()).hexdigest()
        recovery_match = any(hmac.compare_digest(codigo_hash, h) for h in mfa.codigos_recuperacion)
        if p.totp.verificar(mfa.secreto, codigo):
            pass
        elif recovery_match:
            restantes = [h for h in mfa.codigos_recuperacion if h != codigo_hash]
            await p.mfa.guardar(
                persona.id, secreto=mfa.secreto, activo=True, codigos_recuperacion=restantes
            )
        else:
            raise AuthenticationError("Código de MFA inválido.")

        perfil = _perfil_default(persona)
        tokens = await emitir_tokens(p, persona, perfil, huella)
        return LoginResultado(
            mfa_requerido=False,
            perfiles=_perfiles_info(persona),
            perfil_activo=perfil.clave(),
            tokens=tokens,
        )
