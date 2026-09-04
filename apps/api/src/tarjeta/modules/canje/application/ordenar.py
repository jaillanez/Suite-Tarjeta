"""Orden de promociones en la caja por descuento real en pesos (§08.0.B)."""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.canje.domain.descuento import calcular_descuento, requiere_cantidad


@dataclass(slots=True)
class PromoParaCaja:
    id: str
    titulo: str
    mecanica: str
    valor: int


@dataclass(slots=True)
class OpcionCaja:
    id: str
    titulo: str
    mecanica: str
    descuento: int
    total: int
    # Las mecánicas por cantidad (2x1, combo) aparecen pero NO se proponen solas.
    auto_propuesta: bool


def ordenar_por_descuento(promos: list[PromoParaCaja], monto: int) -> list[OpcionCaja]:
    opciones = [
        OpcionCaja(
            id=p.id,
            titulo=p.titulo,
            mecanica=p.mecanica,
            descuento=calcular_descuento(p.mecanica, p.valor, monto),
            total=max(0, monto - calcular_descuento(p.mecanica, p.valor, monto)),
            auto_propuesta=not requiere_cantidad(p.mecanica),
        )
        for p in promos
    ]
    # Se proponen automáticamente por MAYOR descuento real; las manuales van al final.
    opciones.sort(key=lambda o: (o.auto_propuesta, o.descuento), reverse=True)
    return opciones
