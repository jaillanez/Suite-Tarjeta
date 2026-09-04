"""El libro contable: `MovimientoBilletera` es append-only (§09.2).

No tiene métodos de actualización ni de borrado, y el rol `tarjeta_app` no debe tener UPDATE ni
DELETE sobre la tabla (se revoca en la migración, igual que la auditoría del PASO 05). Corregir
un error se hace con un **movimiento compensatorio**, nunca editando el original: eso es lo que
permite responderle a un vecino qué pasó exactamente con sus puntos.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum

from tarjeta.shared.domain.types import EntityId

from .moneda import OrigenPuntos


class TipoMovimiento(StrEnum):
    ACREDITACION = "ACREDITACION"  # +: puntos ganados (canje, PM por conducta)
    CONSUMO = "CONSUMO"  # -: puntos gastados (pagar con puntos, inventario municipal)
    VENCIMIENTO = "VENCIMIENTO"  # -: lote vencido
    REVERSA_ACREDITACION = "REVERSA_ACREDITACION"  # -: compensa una acreditación (anulación)
    REVERSA_CONSUMO = "REVERSA_CONSUMO"  # +: compensa un consumo (anulación)


# Movimientos que suman al saldo (el resto resta). El signo del monto ya lo refleja; esto es
# para validar la coherencia signo/tipo al construir el movimiento.
_SUMAN = frozenset({TipoMovimiento.ACREDITACION, TipoMovimiento.REVERSA_CONSUMO})


@dataclass(slots=True)
class MovimientoBilletera:
    """Asiento inmutable del libro. Se crea una vez y no se modifica jamás."""

    id: EntityId
    id_billetera: EntityId
    tipo: TipoMovimiento
    monto: int  # con signo: + acredita, - consume/vence
    origen_puntos: OrigenPuntos
    creado_en: datetime
    id_lote: EntityId | None = None
    id_transaccion_canje: str | None = None
    id_movimiento_original: EntityId | None = None
    # Clave de idempotencia a nivel base: dos intentos con la misma clave no duplican el asiento.
    clave_dedup: str | None = None
    concepto: str = ""

    def __post_init__(self) -> None:
        suma = self.tipo in _SUMAN
        if suma and self.monto < 0:
            raise ValueError("Un movimiento que acredita no puede tener monto negativo.")
        if not suma and self.monto > 0:
            raise ValueError("Un movimiento que debita no puede tener monto positivo.")
