"""Repositorios SQLAlchemy del módulo identidad."""

from __future__ import annotations

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.identidad.domain.consentimiento import Consentimiento, TipoConsentimiento
from tarjeta.modules.identidad.domain.credencial import Credencial
from tarjeta.modules.identidad.domain.dispositivo import Dispositivo
from tarjeta.modules.identidad.domain.persona import Persona
from tarjeta.shared.domain.types import EntityId
from tarjeta.shared.infrastructure.crypto import FieldCipher, search_hash

from .mappers import (
    actualizar_model,
    consentimiento_to_model,
    dispositivo_to_model,
    model_to_consentimiento,
    model_to_dispositivo,
    model_to_persona,
    persona_to_model,
)
from .models import (
    ConsentimientoModel,
    CredencialModel,
    DispositivoModel,
    MfaModel,
    PersonaModel,
    TextoLegalModel,
)


class SqlAlchemyPersonaRepository:
    def __init__(self, session: AsyncSession, *, cipher: FieldCipher, pepper: str) -> None:
        self._session = session
        self._cipher = cipher
        self._pepper = pepper

    async def agregar(self, persona: Persona) -> None:
        self._session.add(persona_to_model(persona, self._cipher, self._pepper))
        # Flush inmediato: sin relationship() la UoW no ordena inserts por FK, así que
        # garantizamos que la fila persona exista antes de insertar sus hijos.
        await self._session.flush()

    async def guardar(self, persona: Persona) -> None:
        model = await self._session.get(PersonaModel, persona.id.value)
        if model is None:
            raise LookupError("Persona inexistente")
        actualizar_model(model, persona)

    async def obtener_por_id(self, id: EntityId) -> Persona | None:
        model = await self._session.get(PersonaModel, id.value)
        return model_to_persona(model, self._cipher) if model else None

    async def obtener_por_dni(self, dni: str) -> Persona | None:
        model = (
            await self._session.execute(
                select(PersonaModel).where(PersonaModel.dni_hash == search_hash(dni, self._pepper))
            )
        ).scalar_one_or_none()
        return model_to_persona(model, self._cipher) if model else None

    async def obtener_por_celular(self, celular: str) -> Persona | None:
        digits = "".join(ch for ch in celular if ch.isdigit())
        model = (
            await self._session.execute(select(PersonaModel).where(PersonaModel.celular == digits))
        ).scalar_one_or_none()
        return model_to_persona(model, self._cipher) if model else None

    async def existe_dni(self, dni: str) -> bool:
        return bool(
            await self._session.scalar(
                select(exists().where(PersonaModel.dni_hash == search_hash(dni, self._pepper)))
            )
        )

    async def existe_cuil(self, cuil: str) -> bool:
        return bool(
            await self._session.scalar(
                select(exists().where(PersonaModel.cuil_hash == search_hash(cuil, self._pepper)))
            )
        )


class SqlAlchemyCredencialRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def agregar(self, credencial: Credencial) -> None:
        self._session.add(
            CredencialModel(
                id=credencial.id.value,
                id_persona=credencial.id_persona.value,
                hash=credencial.hash,
            )
        )

    async def guardar(self, credencial: Credencial) -> None:
        model = await self._session.get(CredencialModel, credencial.id.value)
        if model is not None:
            model.hash = credencial.hash

    async def obtener_por_persona(self, id_persona: EntityId) -> Credencial | None:
        model = (
            await self._session.execute(
                select(CredencialModel).where(CredencialModel.id_persona == id_persona.value)
            )
        ).scalar_one_or_none()
        if model is None:
            return None
        return Credencial(
            id=EntityId(model.id), id_persona=EntityId(model.id_persona), hash=model.hash
        )


class SqlAlchemyDispositivoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def agregar(self, dispositivo: Dispositivo) -> None:
        self._session.add(dispositivo_to_model(dispositivo))

    async def guardar(self, dispositivo: Dispositivo) -> None:
        model = await self._session.get(DispositivoModel, dispositivo.id.value)
        if model is not None:
            model.estado = dispositivo.estado.value
            model.fecha_ultimo_uso = dispositivo.fecha_ultimo_uso
            model.autorizado_para_perfil_municipal = dispositivo.autorizado_para_perfil_municipal

    async def obtener(self, id: EntityId) -> Dispositivo | None:
        model = await self._session.get(DispositivoModel, id.value)
        return model_to_dispositivo(model) if model else None

    async def listar_por_persona(self, id_persona: EntityId) -> list[Dispositivo]:
        rows = (
            await self._session.execute(
                select(DispositivoModel).where(DispositivoModel.id_persona == id_persona.value)
            )
        ).scalars()
        return [model_to_dispositivo(m) for m in rows]


class SqlAlchemyConsentimientoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def agregar(self, consentimiento: Consentimiento) -> None:
        self._session.add(consentimiento_to_model(consentimiento))

    async def listar_por_persona(self, id_persona: EntityId) -> list[Consentimiento]:
        rows = (
            await self._session.execute(
                select(ConsentimientoModel)
                .where(ConsentimientoModel.id_persona == id_persona.value)
                .order_by(ConsentimientoModel.fecha.desc())
            )
        ).scalars()
        return [model_to_consentimiento(m) for m in rows]

    async def ultimo_por_tipo(
        self, id_persona: EntityId, tipo: TipoConsentimiento
    ) -> Consentimiento | None:
        model = (
            await self._session.execute(
                select(ConsentimientoModel)
                .where(
                    ConsentimientoModel.id_persona == id_persona.value,
                    ConsentimientoModel.tipo == tipo.value,
                )
                .order_by(ConsentimientoModel.fecha.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        return model_to_consentimiento(model) if model else None


class SqlAlchemyMfaRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def obtener(self, id_persona: EntityId) -> MfaModel | None:
        return await self._session.get(MfaModel, id_persona.value)

    async def guardar(
        self,
        id_persona: EntityId,
        *,
        secreto_cifrado: str,
        activo: bool,
        codigos_recuperacion: list[str],
    ) -> None:
        model = await self._session.get(MfaModel, id_persona.value)
        if model is None:
            self._session.add(
                MfaModel(
                    id_persona=id_persona.value,
                    secreto_cifrado=secreto_cifrado,
                    activo=activo,
                    codigos_recuperacion=codigos_recuperacion,
                )
            )
        else:
            model.secreto_cifrado = secreto_cifrado
            model.activo = activo
            model.codigos_recuperacion = codigos_recuperacion


async def version_consentimiento_vigente(
    session: AsyncSession, tipo: TipoConsentimiento
) -> str | None:
    version: str | None = await session.scalar(
        select(TextoLegalModel.version)
        .where(TextoLegalModel.tipo == tipo.value, TextoLegalModel.vigente.is_(True))
        .limit(1)
    )
    return version
