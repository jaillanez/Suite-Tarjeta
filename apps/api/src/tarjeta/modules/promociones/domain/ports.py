"""Puertos del módulo promociones."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol

from tarjeta.shared.domain.events import DomainEvent
from tarjeta.shared.domain.types import EntityId

from .confianza import PerfilConfianza
from .promocion import Promocion


@dataclass(frozen=True, slots=True)
class CriteriosBusqueda:
    texto: str = ""
    porcentaje_min: int = 0
    solo_black: bool = False
    nivel: str = "PLATINO"
    # Si viene, restringe a promociones de estas sucursales (las calcula el composition root
    # con los filtros geográficos/rubro de comercios).
    ids_sucursal: list[str] | None = None
    limite: int = 50


class PromocionRepository(Protocol):
    async def agregar(self, promocion: Promocion) -> None: ...
    async def guardar(self, promocion: Promocion) -> None: ...
    async def obtener(self, id: EntityId) -> Promocion | None: ...
    async def listar_por_comercio(self, id_comercio: EntityId) -> list[Promocion]: ...
    async def listar_en_revision(self) -> list[Promocion]: ...

    # §07.3: incremento atómico del contador con verificación del tope en una sola operación.
    # Devuelve el nuevo total de usos si otorgó; None si el tope total está agotado.
    async def reservar_uso_total(self, id: EntityId) -> int | None: ...
    async def marcar_agotada(self, id: EntityId) -> None: ...

    # §08.0.A: reserva verificando los TRES topes (total, por usuario, por día) en una sola
    # operación (fila de promocion bloqueada con FOR UPDATE). Lanza TopeAgotado si no hay cupo.
    async def reservar_uso(self, id: EntityId, id_persona: EntityId, fecha: date) -> None: ...
    async def liberar_uso(self, id: EntityId, id_persona: EntityId, fecha: date) -> None: ...

    # §07.4: motor de resolución (candidatas por SQL; el filtro fino y el orden van en la app).
    async def candidatas(
        self, *, id_sucursal: EntityId, nivel: str, momento_local: datetime, monto: int
    ) -> list[Promocion]: ...

    # §07.6: descubrimiento.
    async def buscar(self, criterios: CriteriosBusqueda) -> list[Promocion]: ...
    async def nuevas_desde(self, desde: datetime, limite: int) -> list[Promocion]: ...
    async def vencen_antes_de(self, hasta_fecha: date, limite: int) -> list[Promocion]: ...
    async def exclusivas_black(self, limite: int) -> list[Promocion]: ...


class PerfilConfianzaRepository(Protocol):
    async def obtener(self, id_comercio: EntityId) -> PerfilConfianza | None: ...
    async def guardar(self, perfil: PerfilConfianza) -> None: ...


class FavoritoRepository(Protocol):
    async def agregar(
        self, id_persona: EntityId, *, comercio: str = "", rubro: str = ""
    ) -> None: ...
    async def quitar(
        self, id_persona: EntityId, *, comercio: str = "", rubro: str = ""
    ) -> None: ...
    async def comercios_de(self, id_persona: EntityId) -> list[str]: ...
    async def rubros_de(self, id_persona: EntityId) -> list[str]: ...


class Outbox(Protocol):
    async def escribir(self, eventos: list[DomainEvent]) -> None: ...
