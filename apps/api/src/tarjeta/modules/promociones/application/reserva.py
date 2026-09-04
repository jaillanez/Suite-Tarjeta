"""Reserva de uso de una promoción con tope (§07.3).

El incremento es atómico a nivel de base (no leído-y-sumado en Python). Al alcanzar el tope,
la promoción pasa a AGOTADA de forma consistente. Lo usará el canje del paso siguiente.
"""

from __future__ import annotations

from tarjeta.modules.promociones.domain.errors import TopeAgotado
from tarjeta.shared.domain.types import EntityId

from .deps import PromocionesPuertos


class ReservarUso:
    def __init__(self, puertos: PromocionesPuertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_promocion: str) -> int:
        """Reserva un uso. Devuelve el nuevo total; lanza TopeAgotado si no hay cupo."""
        pid = EntityId.from_str(id_promocion)
        nuevo = await self.p.promociones.reservar_uso_total(pid)
        if nuevo is None:
            await self.p.uow.commit()
            raise TopeAgotado("La promoción alcanzó su tope de usos.")
        # Si con esta reserva se alcanzó el tope, se marca AGOTADA en la misma transacción.
        promo = await self.p.promociones.obtener(pid)
        if promo is not None and promo.tope_total is not None and nuevo >= promo.tope_total:
            await self.p.promociones.marcar_agotada(pid)
        await self.p.uow.commit()
        return nuevo
