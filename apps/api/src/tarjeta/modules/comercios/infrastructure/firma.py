"""Firma del QR de establecimiento (§3.4): token permanente por sucursal, HMAC-SHA256."""

from __future__ import annotations

import hashlib
import hmac


class FirmadorEstablecimientoHmac:
    """Token fijo `<id_sucursal>.<firma>`. No lleva monto ni promoción: identifica la sucursal."""

    def __init__(self, secreto: str) -> None:
        self._secreto = secreto.encode()

    def _firma(self, id_sucursal: str) -> str:
        return hmac.new(self._secreto, id_sucursal.encode(), hashlib.sha256).hexdigest()[:32]

    def token(self, id_sucursal: str) -> str:
        return f"{id_sucursal}.{self._firma(id_sucursal)}"

    def verificar(self, token: str) -> str | None:
        if "." not in token:
            return None
        id_sucursal, firma = token.rsplit(".", 1)
        esperado = self._firma(id_sucursal)
        return id_sucursal if hmac.compare_digest(firma, esperado) else None
