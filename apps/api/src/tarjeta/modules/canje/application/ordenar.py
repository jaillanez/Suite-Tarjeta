"""Orden de promociones en la caja por beneficio real (§08.0.B, deuda §09.0.B).

El orden mezcla pesos y puntos: el descuento en pesos según el monto MÁS el valor en pesos de los
puntos que otorga la promoción. Así `MULTIPLICADOR_PUNTOS` deja de quedar siempre último (antes
descontaba cero pesos y no se proponía nunca). Las mecánicas por cantidad (2x1, combo) aparecen
pero NO se proponen solas: el cajero las elige a mano.
"""

from __future__ import annotations

from dataclasses import dataclass

from tarjeta.modules.canje.domain.descuento import calcular_descuento, requiere_cantidad


@dataclass(slots=True)
class PromoParaCaja:
    id: str
    titulo: str
    mecanica: str
    valor: int
    # PC que otorgaría este canje; lo calcula el composition root con el módulo puntos.
    puntos: int = 0


@dataclass(slots=True)
class OpcionCaja:
    id: str
    titulo: str
    mecanica: str
    descuento: int
    total: int
    puntos: int
    # Beneficio comparable: pesos ahorrados ahora + valor en pesos de los puntos ganados.
    beneficio: int
    auto_propuesta: bool


def ordenar_por_descuento(
    promos: list[PromoParaCaja], monto: int, *, valor_punto: int = 0
) -> list[OpcionCaja]:
    opciones = []
    for p in promos:
        descuento = calcular_descuento(p.mecanica, p.valor, monto)
        opciones.append(
            OpcionCaja(
                id=p.id,
                titulo=p.titulo,
                mecanica=p.mecanica,
                descuento=descuento,
                total=max(0, monto - descuento),
                puntos=p.puntos,
                beneficio=descuento + p.puntos * valor_punto,
                auto_propuesta=not requiere_cantidad(p.mecanica),
            )
        )
    # Se proponen automáticamente por MAYOR beneficio (pesos + puntos); las manuales van al final.
    opciones.sort(key=lambda o: (o.auto_propuesta, o.beneficio), reverse=True)
    return opciones
