"""Las dos monedas y las conversiones de mecánica a puntos (§09.1, §09.4).

PC y PM son monedas distintas en financiamiento y destino y **no se convierten entre sí**
por ningún camino. El circuito de PC es cerrado por comercio: el saldo no es uno por persona,
es uno por persona y comercio (por eso la billetera lleva `id_comercio`).
"""

from __future__ import annotations

from enum import StrEnum


class TipoMoneda(StrEnum):
    PC = "PC"  # Puntos Comercio: los financia el comercio; se canjean solo en ese comercio.
    PM = "PM"  # Puntos Municipales: los financia el municipio; se canjean contra inventario.


class TipoTitular(StrEnum):
    """El titular de la billetera puede ser una persona o un grupo familiar (§09.3).

    En este paso solo se crean billeteras de persona; el caso de grupo queda soportado y sin
    usar para no tener que migrar datos contables cuando llegue el grupo familiar.
    """

    PERSONA = "PERSONA"
    GRUPO = "GRUPO"


class OrigenPuntos(StrEnum):
    """De dónde salieron los puntos de un movimiento (§1.7)."""

    INDIVIDUAL = "INDIVIDUAL"
    GRUPO_COMUN = "GRUPO_COMUN"


# Marcador municipal: la billetera de PM no pertenece a ningún comercio. Se usa como valor
# centinela de `id_comercio` para que la unicidad (titular, moneda, comercio) siga funcionando
# (Postgres trata cada NULL como distinto en un índice único).
COMERCIO_MUNICIPAL = ""

# Mecánica cuyo "valor" es el reparto en puntos que el comercio define en la promoción; las demás
# dan descuento en pesos (§09.4). El valor se interpreta como puntos por cada 100 pesos de compra.
MULTIPLICADOR_PUNTOS = "MULTIPLICADOR_PUNTOS"


def puntos_comercio_por_canje(
    mecanica: str, valor: int, monto: int, *, base_por_cien: int = 0
) -> int:
    """PC que acredita un canje (§10.0.A).

    Los PC salen **únicamente del reparto configurado en la promoción**: la mecánica
    `MULTIPLICADOR_PUNTOS` lleva `valor` = puntos por cada 100 pesos de compra. `base_por_cien` es
    una acreditación automática opcional (por defecto 0: el comercio no paga puntos que no eligió).
    Enteros (trunca).
    """
    if monto <= 0:
        return 0
    base = (monto * base_por_cien) // 100
    reparto = (monto * valor) // 100 if (mecanica == MULTIPLICADOR_PUNTOS and valor > 0) else 0
    return base + reparto
