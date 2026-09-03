"""Dispositivo (§03.4)."""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from tarjeta.shared.domain.entity import Entity
from tarjeta.shared.domain.types import EntityId


class EstadoDispositivo(StrEnum):
    ACTIVO = "ACTIVO"
    REVOCADO = "REVOCADO"


class Dispositivo(Entity):
    def __init__(
        self,
        *,
        id: EntityId,
        id_persona: EntityId,
        nombre_declarado: str,
        plataforma: str,
        huella: str,
        fecha_alta: datetime,
        fecha_ultimo_uso: datetime,
        estado: EstadoDispositivo,
        autorizado_para_perfil_municipal: bool,
    ) -> None:
        super().__init__(id)
        self.id_persona = id_persona
        self.nombre_declarado = nombre_declarado
        self.plataforma = plataforma
        self.huella = huella
        self.fecha_alta = fecha_alta
        self.fecha_ultimo_uso = fecha_ultimo_uso
        self.estado = estado
        self.autorizado_para_perfil_municipal = autorizado_para_perfil_municipal

    @classmethod
    def registrar(
        cls,
        *,
        id_persona: EntityId,
        nombre_declarado: str,
        plataforma: str,
        huella: str,
    ) -> Dispositivo:
        ahora = datetime.now(UTC)
        return cls(
            id=EntityId.new(),
            id_persona=id_persona,
            nombre_declarado=nombre_declarado,
            plataforma=plataforma,
            huella=huella,
            fecha_alta=ahora,
            fecha_ultimo_uso=ahora,
            estado=EstadoDispositivo.ACTIVO,
            autorizado_para_perfil_municipal=False,
        )

    @property
    def activo(self) -> bool:
        return self.estado is EstadoDispositivo.ACTIVO

    def revocar(self) -> None:
        self.estado = EstadoDispositivo.REVOCADO

    def autorizar_para_municipal(self) -> None:
        self.autorizado_para_perfil_municipal = True
