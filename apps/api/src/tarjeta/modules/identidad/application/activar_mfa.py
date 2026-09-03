"""Caso de uso: activar MFA (TOTP) con códigos de recuperación (§03.5)."""

from __future__ import annotations

import hashlib
import secrets

from tarjeta.shared.domain.types import EntityId

from .deps import Puertos
from .dto import ActivacionMfa

_CANTIDAD_CODIGOS = 8


def _codigo_recuperacion() -> str:
    return secrets.token_hex(5)  # 10 caracteres hex


class ActivarMfa:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_persona: str, cuenta: str) -> ActivacionMfa:
        p = self.p
        secreto = p.totp.generar_secreto()
        uri = p.totp.uri(secreto, cuenta)
        codigos = [_codigo_recuperacion() for _ in range(_CANTIDAD_CODIGOS)]
        hashes = [hashlib.sha256(c.encode()).hexdigest() for c in codigos]
        await p.mfa.guardar(
            EntityId.from_str(id_persona),
            secreto=secreto,
            activo=True,
            codigos_recuperacion=hashes,
        )
        await p.uow.commit()
        return ActivacionMfa(secreto=secreto, uri=uri, codigos_recuperacion=codigos)
