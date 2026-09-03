"""Agregado Sucursal (§1.5, §06.3): ubicación, horarios de doble turno y estados."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time
from enum import StrEnum

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId

from .errors import TransicionSucursalInvalida, UbicacionRequerida
from .events import SucursalCreada


class EstadoSucursal(StrEnum):
    ACTIVA = "ACTIVA"
    SUSPENDIDA = "SUSPENDIDA"
    CERRADA_TEMPORAL = "CERRADA_TEMPORAL"
    CERRADA_DEFINITIVA = "CERRADA_DEFINITIVA"


@dataclass(frozen=True, slots=True)
class Franja:
    """Un tramo de atención (apertura, cierre) dentro de un día."""

    desde: time
    hasta: time

    def contiene(self, t: time) -> bool:
        return self.desde <= t < self.hasta


@dataclass(frozen=True, slots=True)
class Horario:
    """Horario de un día (0=lunes .. 6=domingo) con hasta dos turnos (§06.3)."""

    dia: int
    franjas: tuple[Franja, ...] = ()

    def abierto_a(self, t: time) -> bool:
        return any(f.contiene(t) for f in self.franjas)


class Sucursal(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        id_comercio: EntityId,
        nombre: str,
        direccion: str,
        lat: float,
        lon: float,
        telefono: str = "",
        estado: EstadoSucursal = EstadoSucursal.ACTIVA,
        es_casa_central: bool = False,
        horarios: list[Horario] | None = None,
        fotos: list[str] | None = None,
        qr_token: str = "",
        motivo_cierre: str = "",
        reapertura_estimada: str | None = None,
    ) -> None:
        super().__init__(id)
        self.id_comercio = id_comercio
        self.nombre = nombre
        self.direccion = direccion
        self.lat = lat
        self.lon = lon
        self.telefono = telefono
        self._estado = estado
        self.es_casa_central = es_casa_central
        self.horarios = horarios or []
        self.fotos = fotos or []
        self.qr_token = qr_token
        self.motivo_cierre = motivo_cierre
        self.reapertura_estimada = reapertura_estimada

    @classmethod
    def crear(
        cls,
        *,
        id_comercio: EntityId,
        nombre: str,
        direccion: str,
        lat: float | None,
        lon: float | None,
        telefono: str = "",
        es_casa_central: bool = False,
        horarios: list[Horario] | None = None,
        fotos: list[str] | None = None,
    ) -> Sucursal:
        # El pin en el mapa es obligatorio (§06.3): la dirección textual no alcanza.
        if lat is None or lon is None:
            raise UbicacionRequerida("La sucursal necesita una ubicación en el mapa.")
        if not (-90 <= lat <= 90) or not (-180 <= lon <= 180):
            raise UbicacionRequerida("Coordenadas fuera de rango.")
        sucursal = cls(
            id=EntityId.new(),
            id_comercio=id_comercio,
            nombre=nombre,
            direccion=direccion,
            lat=lat,
            lon=lon,
            telefono=telefono,
            es_casa_central=es_casa_central,
            horarios=horarios,
            fotos=fotos,
        )
        sucursal.record_event(
            SucursalCreada(id_comercio=str(id_comercio), id_sucursal=str(sucursal.id))
        )
        return sucursal

    @property
    def estado(self) -> EstadoSucursal:
        return self._estado

    def cerrar_temporal(self, motivo: str, reapertura_estimada: str | None) -> None:
        self._exigir_operable()
        self._estado = EstadoSucursal.CERRADA_TEMPORAL
        self.motivo_cierre = motivo
        self.reapertura_estimada = reapertura_estimada

    def reabrir(self) -> None:
        if self._estado not in {EstadoSucursal.CERRADA_TEMPORAL, EstadoSucursal.SUSPENDIDA}:
            raise TransicionSucursalInvalida("La sucursal no está cerrada temporal ni suspendida.")
        self._estado = EstadoSucursal.ACTIVA
        self.motivo_cierre = ""
        self.reapertura_estimada = None

    def cerrar_definitiva(self, motivo: str) -> None:
        self._estado = EstadoSucursal.CERRADA_DEFINITIVA
        self.motivo_cierre = motivo

    def _exigir_operable(self) -> None:
        if self._estado is EstadoSucursal.CERRADA_DEFINITIVA:
            raise TransicionSucursalInvalida("La sucursal ya está cerrada definitivamente.")

    def abierto_ahora(self, ahora_local: datetime) -> bool:
        """¿Está abierta en este instante? Respeta la zona horaria del `datetime` recibido."""
        if self._estado is not EstadoSucursal.ACTIVA:
            return False
        dia = ahora_local.weekday()  # 0 = lunes
        t = ahora_local.time()
        return any(h.abierto_a(t) for h in self.horarios if h.dia == dia)


@dataclass(slots=True)
class SucursalCercana:
    """Resultado de la consulta de cercanía (§06.3)."""

    id: str
    nombre: str
    lat: float
    lon: float
    distancia_m: float
    campos: dict[str, str] = field(default_factory=dict)
