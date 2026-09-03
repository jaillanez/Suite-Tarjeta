"""Repositorio del módulo padron."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.padron.domain.estado_padron import EstadoPadron
from tarjeta.shared.domain.types import EntityId
from tarjeta.shared.infrastructure.crypto import FieldCipher

from .models import EstadoPadronModel, HistorialEstadoPadronModel


class SqlAlchemyEstadoPadronRepository:
    def __init__(self, session: AsyncSession, *, cipher: FieldCipher) -> None:
        self._session = session
        self._cipher = cipher

    async def obtener(self, id_persona: EntityId) -> EstadoPadron | None:
        model = await self._session.get(EstadoPadronModel, id_persona.value)
        if model is None:
            return None
        return EstadoPadron(
            id_persona=EntityId(model.id_persona),
            dni=self._cipher.decrypt(model.dni_cifrado),
            al_dia=model.al_dia,
            es_comerciante=model.es_comerciante,
            fecha_ultima_consulta=model.fecha_ultima_consulta,
        )

    async def guardar(
        self,
        estado: EstadoPadron,
        *,
        anterior: EstadoPadron | None,
        origen: str,
    ) -> None:
        model = await self._session.get(EstadoPadronModel, estado.id_persona.value)
        if model is None:
            self._session.add(
                EstadoPadronModel(
                    id_persona=estado.id_persona.value,
                    dni_cifrado=self._cipher.encrypt(estado.dni),
                    al_dia=estado.al_dia,
                    es_comerciante=estado.es_comerciante,
                    fecha_ultima_consulta=estado.fecha_ultima_consulta,
                )
            )
        else:
            model.al_dia = estado.al_dia
            model.es_comerciante = estado.es_comerciante
            model.fecha_ultima_consulta = estado.fecha_ultima_consulta

        # Histórico append-only de los cambios de valor (habilita la métrica de recaudación).
        if anterior is None or anterior.al_dia != estado.al_dia:
            self._session.add(
                HistorialEstadoPadronModel(
                    id=uuid.uuid4(),
                    id_persona=estado.id_persona.value,
                    campo="al_dia",
                    valor_anterior=str(anterior.al_dia) if anterior else "",
                    valor_nuevo=str(estado.al_dia),
                    timestamp=datetime.now(UTC),
                    origen_consulta=origen,
                )
            )
