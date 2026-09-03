"""Casos de uso: listar perfiles y cambiar de perfil activo (§11.2/§11.3)."""

from __future__ import annotations

from tarjeta.modules.identidad.domain.errors import (
    DispositivoNoRegistrado,
    MfaNoEnrolado,
    PerfilNoAsignado,
)
from tarjeta.modules.identidad.domain.events import PerfilCambiado
from tarjeta.modules.identidad.domain.perfil import TipoPerfil
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

from .deps import Puertos
from .dto import PerfilInfo, Tokens
from .iniciar_sesion import _perfil_por_clave, _perfiles_info
from .permisos import permisos_de


class ListarPerfiles:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_persona: str) -> list[PerfilInfo]:
        persona = await self.p.personas.obtener_por_id(EntityId.from_str(id_persona))
        if persona is None:
            raise NotFoundError("Persona inexistente.")
        return _perfiles_info(persona)


class CambiarPerfil:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(
        self, *, id_persona: str, clave_destino: str, huella: str | None = None
    ) -> Tokens:
        p = self.p
        persona = await p.personas.obtener_por_id(EntityId.from_str(id_persona))
        if persona is None:
            raise NotFoundError("Persona inexistente.")

        perfil = _perfil_por_clave(persona, clave_destino)
        if perfil is None:
            # §11.3: no se puede "pedir" un perfil no asignado. 403 sin filtrar info.
            raise PerfilNoAsignado("Perfil no disponible.")

        if perfil.tipo is TipoPerfil.MUNICIPAL:
            # §11.3: la petición debe venir DESDE un dispositivo autorizado, no basta con
            # que la persona tenga alguno. Se exige que la huella de la petición coincida.
            dispositivos = await p.dispositivos.listar_por_persona(persona.id)
            autorizado = any(
                d.activo
                and d.autorizado_para_perfil_municipal
                and huella is not None
                and d.huella == huella
                for d in dispositivos
            )
            if not autorizado:
                raise DispositivoNoRegistrado(
                    "El perfil municipal exige activarse desde un dispositivo autorizado."
                )
            # §05.3: MFA obligatorio enrolado para operar como municipal.
            mfa = await p.mfa.obtener(persona.id)
            if mfa is None or not mfa.activo:
                raise MfaNoEnrolado("El perfil municipal exige MFA enrolado.")

        access = p.tokens.crear(
            id_persona=str(persona.id),
            perfil=perfil.clave(),
            permisos=permisos_de(perfil),
            huella=huella,
        )
        nuevo_refresh = await p.refresh.emitir(persona.id, perfil.clave())
        await p.outbox.escribir([PerfilCambiado(id_persona=str(persona.id), perfil=perfil.clave())])
        await p.uow.commit()
        return Tokens(access_token=access, refresh_token=nuevo_refresh)
