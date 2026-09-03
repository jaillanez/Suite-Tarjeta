"""Adaptadores que cierran puertos usando otras piezas de infraestructura."""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.identidad.domain.consentimiento import TipoConsentimiento
from tarjeta.modules.identidad.domain.ports import MfaEstado
from tarjeta.shared.domain.types import EntityId
from tarjeta.shared.infrastructure.crypto import FieldCipher

from .repositories import SqlAlchemyMfaRepository, version_consentimiento_vigente


class MfaCifrado:
    """AlmacenMfa: cifra/descifra el secreto TOTP en reposo."""

    def __init__(self, repo: SqlAlchemyMfaRepository, cipher: FieldCipher) -> None:
        self._repo = repo
        self._cipher = cipher

    async def obtener(self, id_persona: EntityId) -> MfaEstado | None:
        m = await self._repo.obtener(id_persona)
        if m is None:
            return None
        return MfaEstado(
            secreto=self._cipher.decrypt(m.secreto_cifrado),
            activo=m.activo,
            codigos_recuperacion=list(m.codigos_recuperacion),
        )

    async def guardar(
        self,
        id_persona: EntityId,
        *,
        secreto: str,
        activo: bool,
        codigos_recuperacion: list[str],
    ) -> None:
        await self._repo.guardar(
            id_persona,
            secreto_cifrado=self._cipher.encrypt(secreto),
            activo=activo,
            codigos_recuperacion=codigos_recuperacion,
        )


class TextosLegalesSql:
    """TextosLegales sobre la tabla texto_legal."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def version_vigente(self, tipo: TipoConsentimiento) -> str | None:
        return await version_consentimiento_vigente(self._session, tipo)
