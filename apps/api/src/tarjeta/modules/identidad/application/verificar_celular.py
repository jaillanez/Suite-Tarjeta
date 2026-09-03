"""Casos de uso: solicitar OTP y verificar el celular (§3.6)."""

from __future__ import annotations

import secrets

from tarjeta.modules.identidad.domain.errors import OtpInvalido
from tarjeta.shared.domain.errors import NotFoundError

from .deps import Puertos


def _generar_codigo(longitud: int) -> str:
    return "".join(secrets.choice("0123456789") for _ in range(longitud))


class SolicitarOtp:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, celular: str, ip: str) -> None:
        p = self.p
        # Rate limit por celular y por IP.
        if not await p.rate_limiter.permitido(
            f"otp:cel:{celular}", p.otp_max_solicitudes_hora, 3600
        ):
            raise OtpInvalido("Demasiadas solicitudes. Probá más tarde.")
        if ip and not await p.rate_limiter.permitido(
            f"otp:ip:{ip}", p.otp_max_solicitudes_hora * 3, 3600
        ):
            raise OtpInvalido("Demasiadas solicitudes. Probá más tarde.")

        codigo = _generar_codigo(p.otp_length)
        await p.almacen_otp.emitir(f"celular:{celular}", codigo, p.otp_ttl_seg)
        await p.envio_otp.enviar(celular, codigo)


class VerificarCelular:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, celular: str, codigo: str) -> None:
        p = self.p
        ok = await p.almacen_otp.verificar_y_consumir(
            f"celular:{celular}", codigo, p.otp_max_intentos
        )
        if not ok:
            raise OtpInvalido("Código inválido o expirado.")

        persona = await p.personas.obtener_por_celular(celular)
        if persona is None:
            raise NotFoundError("No hay una persona con ese celular.")
        persona.verificar_celular()
        await p.personas.guardar(persona)
        await p.outbox.escribir(persona.pull_events())
        await p.uow.commit()
