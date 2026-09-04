"""Billetera: titular persona o grupo, una por moneda y comercio (§09.1, §09.3).

El saldo NO se guarda como campo editable a criterio de la aplicación: se mantiene con la misma
disciplina atómica de los topes del PASO 07 (se ajusta en la base dentro de la transacción que
crea el movimiento) y existe un proceso de verificación que lo compara contra la suma del libro.
Se permite saldo negativo: una anulación cuyos puntos ya se gastaron deja el saldo en negativo y
se compensa con las siguientes acumulaciones (§09.4).
"""

from __future__ import annotations

from datetime import datetime

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId

from .moneda import COMERCIO_MUNICIPAL, TipoMoneda, TipoTitular


class Billetera(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        tipo_titular: TipoTitular,
        id_titular: str,
        tipo_moneda: TipoMoneda,
        id_comercio: str,
        saldo: int,
        creada_en: datetime,
    ) -> None:
        super().__init__(id)
        self.tipo_titular = tipo_titular
        self.id_titular = id_titular
        self.tipo_moneda = tipo_moneda
        # PC: comercio emisor; PM: centinela municipal ("").
        self.id_comercio = id_comercio
        self.saldo = saldo
        self.creada_en = creada_en

    @classmethod
    def crear(
        cls,
        *,
        tipo_titular: TipoTitular,
        id_titular: str,
        tipo_moneda: TipoMoneda,
        id_comercio: str | None,
    ) -> Billetera:
        comercio = COMERCIO_MUNICIPAL if tipo_moneda is TipoMoneda.PM else (id_comercio or "")
        if tipo_moneda is TipoMoneda.PC and not comercio:
            raise ValueError("La billetera de PC necesita el comercio emisor.")
        return cls(
            id=EntityId.new(),
            tipo_titular=tipo_titular,
            id_titular=id_titular,
            tipo_moneda=tipo_moneda,
            id_comercio=comercio,
            saldo=0,
            creada_en=datetime.now().astimezone(),
        )
