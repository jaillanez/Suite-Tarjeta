"""Puertos del módulo contenido."""

from __future__ import annotations

from typing import Protocol

from tarjeta.shared.domain.events import DomainEvent
from tarjeta.shared.domain.types import EntityId

from .pieza import Pieza, Superposicion
from .plantillas import Plantilla
from .tipos import FormatoPieza


class GeneradorImagen(Protocol):
    """§11.2: mismo patrón que el OTP. Simulación para dev/tests; real por configuración."""

    nombre: str

    async def generar(self, prompt: str, *, cantidad: int, tamano: str) -> list[bytes]:
        """Devuelve `cantidad` imágenes (bytes PNG). Lanza si el proveedor falla."""
        ...


class Compositor(Protocol):
    """Compone el texto de la promoción y la marca de agua sobre el fondo (§11.5)."""

    def componer(
        self,
        *,
        fondo: bytes,
        superposicion: Superposicion,
        plantilla: Plantilla,
        formato: FormatoPieza,
        con_marca_agua: bool,
    ) -> bytes: ...


class AlmacenObjetos(Protocol):
    """§11.10: las imágenes no van en la base; van a un almacén de objetos detrás de un puerto."""

    async def guardar(self, clave: str, datos: bytes, content_type: str) -> None: ...
    async def leer(self, clave: str) -> bytes | None: ...
    async def borrar(self, clave: str) -> None: ...
    def url_publica(self, clave: str) -> str: ...


class PiezaRepository(Protocol):
    async def agregar(self, pieza: Pieza) -> None: ...
    async def guardar(self, pieza: Pieza) -> None: ...
    async def obtener(self, id: EntityId) -> Pieza | None: ...
    async def listar_por_comercio(self, id_comercio: str) -> list[Pieza]: ...
    async def listar_en_moderacion(self) -> list[Pieza]: ...
    async def de_promocion(self, id_promocion: str) -> list[Pieza]: ...


class CreditoRepository(Protocol):
    """Cuota mensual con reserva atómica (§11.9), misma disciplina que los topes del PASO 07."""

    async def reservar(self, id_comercio: str, periodo: str, cuota: int) -> int | None:
        """Reserva un crédito atómicamente. Devuelve los créditos usados tras reservar, o None si
        no quedan (dos pestañas no pueden gastar el mismo crédito)."""
        ...

    async def devolver(self, id_comercio: str, periodo: str) -> None: ...
    async def usados(self, id_comercio: str, periodo: str) -> int: ...
    async def extra(self, id_comercio: str, periodo: str) -> int: ...
    async def otorgar_extra(self, id_comercio: str, periodo: str, cantidad: int) -> None: ...


class Outbox(Protocol):
    async def escribir(self, eventos: list[DomainEvent]) -> None: ...
