"""QR dinámico del ciudadano (§3.4, §08.2). Nunca estático.

Token firmado (HMAC) que rota cada 45 s con validez de 90 s (tolera desfases de reloj). Lleva
id de persona, **nivel congelado**, ventana temporal y un valor único (nonce). El nonce se
consume una sola vez (Redis). La app pregenera los tokens de las próximas dos horas para poder
mostrar la tarjeta sin señal.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass

VENTANA_SEG = 45
TOLERANCIA_SEG = 90


@dataclass(slots=True)
class DatosToken:
    id_persona: str
    nivel: str
    nonce: str


@dataclass(slots=True)
class TokenEmitido:
    token: str
    valido_desde: int  # epoch
    valido_hasta: int  # epoch


class FirmadorTokenCiudadano:
    def __init__(self, secreto: str) -> None:
        self._secreto = secreto.encode()

    def _firma(self, payload: str) -> str:
        return hmac.new(self._secreto, payload.encode(), hashlib.sha256).hexdigest()[:32]

    def _armar(self, id_persona: str, nivel: str, ventana: int, nonce: str) -> str:
        payload = f"{id_persona}|{nivel}|{ventana}|{nonce}"
        cuerpo = base64.urlsafe_b64encode(payload.encode()).decode().rstrip("=")
        return f"{cuerpo}.{self._firma(payload)}"

    def emitir_lote(
        self, *, id_persona: str, nivel: str, ahora_epoch: int, horas: int = 2
    ) -> list[TokenEmitido]:
        ventana_actual = ahora_epoch // VENTANA_SEG
        cantidad = (horas * 3600) // VENTANA_SEG
        lote: list[TokenEmitido] = []
        for i in range(cantidad):
            ventana = ventana_actual + i
            token = self._armar(id_persona, nivel, ventana, secrets.token_urlsafe(9))
            desde = ventana * VENTANA_SEG
            lote.append(
                TokenEmitido(token=token, valido_desde=desde, valido_hasta=desde + TOLERANCIA_SEG)
            )
        return lote

    def verificar(self, token: str, *, ahora_epoch: int) -> DatosToken | None:
        if "." not in token:
            return None
        cuerpo, firma = token.rsplit(".", 1)
        try:
            relleno = "=" * (-len(cuerpo) % 4)
            payload = base64.urlsafe_b64decode(cuerpo + relleno).decode()
        except Exception:  # noqa: BLE001 - token mal formado
            return None
        if not hmac.compare_digest(firma, self._firma(payload)):
            return None
        partes = payload.split("|")
        if len(partes) != 4:
            return None
        id_persona, nivel, ventana_str, nonce = partes
        try:
            ventana = int(ventana_str)
        except ValueError:
            return None
        inicio = ventana * VENTANA_SEG
        if not (inicio <= ahora_epoch < inicio + TOLERANCIA_SEG):
            return None  # vencido o todavía no vigente
        return DatosToken(id_persona=id_persona, nivel=nivel, nonce=nonce)
