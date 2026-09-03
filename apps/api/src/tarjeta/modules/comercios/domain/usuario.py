"""UsuarioComercio (§2.1, §06.4-06.5): membresía de una persona en un comercio con rol."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId

from .errors import CajeroBloqueado, DispositivoNoRegistrado
from .roles import RolComercio


class EstadoUsuario(StrEnum):
    ACTIVO = "ACTIVO"
    BAJA = "BAJA"


class UsuarioComercio(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        id_comercio: EntityId,
        id_persona: EntityId,
        rol: RolComercio,
        sucursales: list[EntityId] | None = None,
        estado: EstadoUsuario = EstadoUsuario.ACTIVO,
        pin_hash: str | None = None,
        huella_dispositivo: str | None = None,
        pin_intentos: int = 0,
        pin_bloqueado_hasta: datetime | None = None,
    ) -> None:
        super().__init__(id)
        self.id_comercio = id_comercio
        self.id_persona = id_persona
        self.rol = rol
        self.sucursales = sucursales or []
        self._estado = estado
        self.pin_hash = pin_hash
        self.huella_dispositivo = huella_dispositivo
        self.pin_intentos = pin_intentos
        self.pin_bloqueado_hasta = pin_bloqueado_hasta

    @classmethod
    def crear(
        cls,
        *,
        id_comercio: EntityId,
        id_persona: EntityId,
        rol: RolComercio,
        sucursales: list[EntityId] | None = None,
    ) -> UsuarioComercio:
        return cls(
            id=EntityId.new(),
            id_comercio=id_comercio,
            id_persona=id_persona,
            rol=rol,
            sucursales=sucursales,
        )

    @property
    def estado(self) -> EstadoUsuario:
        return self._estado

    @property
    def activo(self) -> bool:
        return self._estado is EstadoUsuario.ACTIVO

    def opera_sucursal(self, id_sucursal: EntityId) -> bool:
        # ADMIN_COMERCIO no tiene alcance limitado; los demás, solo sus sucursales.
        from .roles import alcance_limitado

        if not alcance_limitado(self.rol):
            return True
        return id_sucursal in self.sucursales

    def dar_de_baja(self) -> None:
        self._estado = EstadoUsuario.BAJA

    # --- PIN de cajero (§06.5) ------------------------------------------------
    def establecer_pin(self, pin_hash: str, huella_dispositivo: str) -> None:
        """El PIN se ata a un dispositivo registrado; fuera de él no hay acceso."""
        self.pin_hash = pin_hash
        self.huella_dispositivo = huella_dispositivo
        self.pin_intentos = 0
        self.pin_bloqueado_hasta = None

    def exigir_dispositivo(self, huella: str | None) -> None:
        if self.huella_dispositivo is None or huella != self.huella_dispositivo:
            raise DispositivoNoRegistrado("El PIN solo funciona en el dispositivo registrado.")

    def exigir_no_bloqueado(self, ahora: datetime) -> None:
        if self.pin_bloqueado_hasta is not None and ahora < self.pin_bloqueado_hasta:
            raise CajeroBloqueado("Cajero bloqueado por intentos fallidos. Probá más tarde.")

    def registrar_pin_ok(self) -> None:
        self.pin_intentos = 0
        self.pin_bloqueado_hasta = None

    def registrar_pin_fallido(
        self, ahora: datetime, *, max_intentos: int, bloqueo_seg: int
    ) -> None:
        from datetime import timedelta

        self.pin_intentos += 1
        if self.pin_intentos >= max_intentos:
            self.pin_bloqueado_hasta = ahora + timedelta(seconds=bloqueo_seg)
            self.pin_intentos = 0
