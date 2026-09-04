"""Recuperación de cuenta por email (§04.0.B).

Flujo en dos pasos, **sin revelar si el email existe** (anti-enumeración):
1. `SolicitarRecuperacion(email)`: si hay cuenta, emite un token de un solo uso y lo manda al email.
2. `ConfirmarRecuperacion(token, password)`: valida el token, cambia la contraseña y **cierra las
   sesiones abiertas** (revoca los refresh vigentes).
"""

from __future__ import annotations

import secrets

from tarjeta.shared.domain.errors import ValidationError
from tarjeta.shared.domain.types import EntityId

from .deps import Puertos
from .password_policy import validar_password


class TokenRecuperacionInvalido(ValidationError):
    """El token de recuperación no existe, venció o ya se usó."""


class SolicitarRecuperacion:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, email: str) -> None:
        clave = email.strip().lower()
        # Rate limit por email: no permitir inundar de correos a un vecino.
        if not await self.p.rate_limiter.permitido(
            f"reset:{clave}", self.p.reset_max_solicitudes_hora, 3600
        ):
            return  # silencioso: no revela nada
        persona = await self.p.personas.obtener_por_email(clave)
        if persona is None:
            return  # anti-enumeración: misma respuesta que si la cuenta existiera
        token = secrets.token_urlsafe(32)
        await self.p.almacen_reset.emitir(token, str(persona.id), self.p.reset_ttl_seg)
        await self.p.emisor_email.enviar(
            clave,
            "Recuperá tu cuenta",
            f"Usá este código para restablecer tu contraseña (vence en 1 h): {token}",
        )


class ConfirmarRecuperacion:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, token: str, password: str) -> None:
        # Validar la política ANTES de consumir el token, para no quemarlo por una contraseña débil.
        validar_password(password, min_length=self.p.password_min_length)
        id_persona = await self.p.almacen_reset.consumir(token)  # un solo uso (GETDEL)
        if id_persona is None:
            raise TokenRecuperacionInvalido("El enlace de recuperación no es válido o venció.")
        cred = await self.p.credenciales.obtener_por_persona(EntityId.from_str(id_persona))
        if cred is None:
            raise TokenRecuperacionInvalido("El enlace de recuperación no es válido o venció.")
        cred.actualizar_hash(self.p.hasher.hash(password))
        await self.p.credenciales.guardar(cred)
        # Seguridad: cambiar la contraseña cierra todas las sesiones abiertas.
        await self.p.refresh.revocar_todo_de(EntityId.from_str(id_persona))
        await self.p.uow.commit()
