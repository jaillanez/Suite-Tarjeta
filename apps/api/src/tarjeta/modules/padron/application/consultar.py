"""Casos de uso de padron: consultar el veredicto y actualizar el estado (con degradación)."""

from __future__ import annotations

from datetime import UTC, datetime

from tarjeta.modules.padron.domain.errors import PadronNoDisponible
from tarjeta.modules.padron.domain.estado_padron import EstadoPadron
from tarjeta.modules.padron.domain.events import EstadoPadronActualizado
from tarjeta.modules.padron.domain.ports import ClientePadron, EstadoPadronRepository, Outbox
from tarjeta.shared.domain.types import EntityId

# Orígenes de consulta (§7.5).
BATCH = "BATCH"
BOTON_USUARIO = "BOTON_USUARIO"
ALTA_PRESENCIAL = "ALTA_PRESENCIAL"
REGISTRO = "REGISTRO"


async def consultar_y_actualizar(
    *,
    repo: EstadoPadronRepository,
    cliente: ClientePadron,
    outbox: Outbox,
    id_persona: EntityId,
    dni: str,
    origen: str,
) -> None:
    """Consulta el padrón y actualiza el estado. Degrada sin bajar de nivel si el endpoint cae."""
    anterior = await repo.obtener(id_persona)
    try:
        al_dia = await cliente.al_dia(dni)
    except PadronNoDisponible:
        # §7.3: nadie cambia de estado por falta de dato fresco. Se conserva lo conocido.
        return

    estado = EstadoPadron(
        id_persona=id_persona,
        dni=dni,
        al_dia=al_dia,
        es_comerciante=anterior.es_comerciante if anterior else False,
        fecha_ultima_consulta=datetime.now(UTC),
    )
    await repo.guardar(estado, anterior=anterior, origen=origen)
    await outbox.escribir([EstadoPadronActualizado(id_persona=str(id_persona), al_dia=al_dia)])


async def reconsultar(
    *,
    repo: EstadoPadronRepository,
    cliente: ClientePadron,
    outbox: Outbox,
    id_persona: EntityId,
    origen: str = BOTON_USUARIO,
) -> None:
    """Reconsulta usando el DNI ya conocido (botón 'Actualizar mi estado')."""
    estado = await repo.obtener(id_persona)
    if estado is None:
        return
    await consultar_y_actualizar(
        repo=repo,
        cliente=cliente,
        outbox=outbox,
        id_persona=id_persona,
        dni=estado.dni,
        origen=origen,
    )
