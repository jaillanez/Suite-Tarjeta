"""Consumidor de eventos que persiste la auditoría inmutable (§05.4).

Suscripto a todos los eventos. Idempotente por `id_evento_origen`. Redacta DNI/CUIL/
domicilio antes de guardar (mismo filtro del PASO 03).
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from tarjeta.modules.gobierno.domain.auditoria import RegistroAuditoria
from tarjeta.modules.gobierno.infrastructure.repositories import SqlAlchemyAuditoriaRepository
from tarjeta.shared.infrastructure.logging import redact


def _redactar(valor: Any) -> Any:
    if isinstance(valor, str):
        return redact(valor)
    if isinstance(valor, dict):
        return {k: _redactar(v) for k, v in valor.items()}
    if isinstance(valor, list):
        return [_redactar(v) for v in valor]
    return valor


async def consumir_evento(payload: dict[str, Any], session: AsyncSession) -> None:
    repo = SqlAlchemyAuditoriaRepository(session)
    evento_id = str(payload.get("event_id", ""))
    if evento_id and await repo.existe_evento(evento_id):
        return  # idempotencia: el evento ya fue auditado
    seguro = _redactar(payload)
    await repo.agregar(
        RegistroAuditoria.crear(
            accion=str(payload.get("__tipo__", "evento")),
            entidad="evento",
            id_entidad=str(payload.get("id_persona", "-")),
            valor_nuevo=seguro if isinstance(seguro, dict) else {"valor": seguro},
            id_evento_origen=evento_id or None,
        )
    )
