"""Caso de uso: refrescar la sesión (rotación + detección de reuso)."""

from __future__ import annotations

from tarjeta.modules.identidad.domain.errors import ReusoDeRefreshToken
from tarjeta.shared.domain.errors import AuthenticationError

from .deps import Puertos
from .dto import Tokens
from .iniciar_sesion import _perfil_default, _perfil_por_clave
from .permisos import permisos_de


class RefrescarSesion:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, refresh_token: str, huella: str | None = None) -> Tokens:
        p = self.p
        try:
            rot = await p.refresh.rotar(refresh_token)
        except ReusoDeRefreshToken:
            # Persistir la revocación de la familia antes de propagar el error.
            await p.uow.commit()
            raise

        persona = await p.personas.obtener_por_id(rot.id_persona)
        if persona is None:
            raise AuthenticationError("Sesión inválida.")

        perfil = _perfil_por_clave(persona, rot.perfil) or _perfil_default(persona)
        access = p.tokens.crear(
            id_persona=str(persona.id),
            perfil=perfil.clave(),
            permisos=permisos_de(perfil),
            huella=huella,
        )
        await p.uow.commit()
        return Tokens(access_token=access, refresh_token=rot.nuevo_token)
