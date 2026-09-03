"""Almacén de refresh tokens (opacos) con rotación y detección de reuso (§03.4)."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.identidad.domain.errors import ReusoDeRefreshToken
from tarjeta.modules.identidad.domain.ports import Rotacion
from tarjeta.shared.domain.errors import AuthenticationError
from tarjeta.shared.domain.types import EntityId

from .models import RefreshTokenModel


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


class SqlAlchemyAlmacenRefresh:
    def __init__(self, session: AsyncSession, *, ttl_seg: int) -> None:
        self._session = session
        self._ttl = ttl_seg

    async def _crear(self, id_persona: EntityId, perfil: str, family_id: uuid.UUID) -> str:
        token = secrets.token_urlsafe(48)
        ahora = datetime.now(UTC)
        self._session.add(
            RefreshTokenModel(
                id=uuid.uuid4(),
                id_persona=id_persona.value,
                family_id=family_id,
                token_hash=_hash(token),
                perfil=perfil,
                creado=ahora,
                expira=ahora + timedelta(seconds=self._ttl),
                usado=False,
                revocado=False,
            )
        )
        return token

    async def emitir(self, id_persona: EntityId, perfil: str) -> str:
        return await self._crear(id_persona, perfil, uuid.uuid4())

    async def rotar(self, token_plano: str) -> Rotacion:
        row = (
            await self._session.execute(
                select(RefreshTokenModel).where(RefreshTokenModel.token_hash == _hash(token_plano))
            )
        ).scalar_one_or_none()

        if row is None or row.revocado:
            raise AuthenticationError("Refresh token inválido.")

        if row.usado:
            # Reuso: se revoca toda la familia.
            await self._session.execute(
                update(RefreshTokenModel)
                .where(RefreshTokenModel.family_id == row.family_id)
                .values(revocado=True)
            )
            raise ReusoDeRefreshToken("Refresh token ya utilizado; familia revocada.")

        if row.expira < datetime.now(UTC):
            raise AuthenticationError("Refresh token expirado.")

        row.usado = True
        nuevo = await self._crear(EntityId(row.id_persona), row.perfil, row.family_id)
        return Rotacion(id_persona=EntityId(row.id_persona), perfil=row.perfil, nuevo_token=nuevo)

    async def revocar(self, token_plano: str) -> None:
        row = (
            await self._session.execute(
                select(RefreshTokenModel).where(RefreshTokenModel.token_hash == _hash(token_plano))
            )
        ).scalar_one_or_none()
        if row is not None:
            await self._session.execute(
                update(RefreshTokenModel)
                .where(RefreshTokenModel.family_id == row.family_id)
                .values(revocado=True)
            )

    async def revocar_todo_de(self, id_persona: EntityId) -> None:
        await self._session.execute(
            update(RefreshTokenModel)
            .where(RefreshTokenModel.id_persona == id_persona.value)
            .values(revocado=True)
        )
