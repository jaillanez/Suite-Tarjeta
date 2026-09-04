"""Caso de uso: registrar una persona (§3.1 + §04.0.B: registro mínimo sin OTP)."""

from __future__ import annotations

from datetime import date

from tarjeta.modules.identidad.domain.consentimiento import (
    OBLIGATORIOS,
    Consentimiento,
    TipoConsentimiento,
)
from tarjeta.modules.identidad.domain.credencial import Credencial
from tarjeta.modules.identidad.domain.errors import (
    ConsentimientoObligatorioFaltante,
    OtpInvalido,
    PersonaYaRegistrada,
)
from tarjeta.modules.identidad.domain.events import ConsentimientoOtorgado
from tarjeta.modules.identidad.domain.persona import MetodoVerificacion, Persona
from tarjeta.modules.identidad.domain.value_objects import Celular, Email
from tarjeta.shared.domain.errors import ValidationError
from tarjeta.shared.domain.events import DomainEvent
from tarjeta.shared.domain.types import Dni

from .deps import Puertos
from .dto import RegistroInput
from .password_policy import validar_password


class RegistrarPersona:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, entrada: RegistroInput) -> str:
        p = self.p
        # Rate limiting reforzado: sin OTP es la única contención contra el alta masiva.
        if entrada.ip and not await p.rate_limiter.permitido(
            f"registro:ip:{entrada.ip}", p.rate_limit_registro, 3600
        ):
            raise OtpInvalido("Demasiados registros desde esta conexión. Probá más tarde.")

        validar_password(entrada.password, min_length=p.password_min_length)

        dni = Dni(entrada.dni)
        try:
            fecha_nacimiento = date.fromisoformat(entrada.fecha_nacimiento)
        except ValueError as exc:
            raise ValidationError("Fecha de nacimiento inválida (formato YYYY-MM-DD).") from exc
        celular = Celular(entrada.celular) if entrada.celular else None
        email = Email(entrada.email) if entrada.email else None

        otorgados = {c.tipo: c.otorgado for c in entrada.consentimientos}
        for obligatorio in OBLIGATORIOS:
            if not otorgados.get(obligatorio.value, False):
                raise ConsentimientoObligatorioFaltante(
                    "Falta el consentimiento obligatorio de tratamiento de datos."
                )

        # §3.1: un DNI ya registrado no puede registrarse de nuevo (ofrece recuperar cuenta).
        if await p.personas.existe_dni(str(dni)):
            raise PersonaYaRegistrada("Ya existe una cuenta con ese DNI. Recuperá tu cuenta.")

        persona = Persona.registrar(
            dni=dni, fecha_nacimiento=fecha_nacimiento, celular=celular, email=email
        )
        await p.personas.agregar(persona)
        await p.credenciales.agregar(
            Credencial.crear(id_persona=persona.id, hash=p.hasher.hash(entrada.password))
        )

        # §3.1 (v2.3): registro ciudadano ABIERTO. La identidad es AUTODECLARADA — no se consulta
        # RENAPER (fuera de alcance) ni se etiqueta como tal. La validación reforzada (PRESENCIAL /
        # DOCUMENTAL) sube el estado más adelante; el reclamo por alta presencial es el remedio
        # ante suplantación (PASO 05). El padrón solo asigna el nivel y nunca bloquea.
        persona.verificar_identidad(MetodoVerificacion.AUTODECLARADA)
        await p.personas.guardar(persona)  # persistir el cambio de estado

        eventos: list[DomainEvent] = list(persona.pull_events())
        for c in entrada.consentimientos:
            tipo = TipoConsentimiento(c.tipo)
            version = await p.textos.version_vigente(tipo) or "v1"
            await p.consentimientos.agregar(
                Consentimiento.registrar(
                    id_persona=persona.id,
                    tipo=tipo,
                    version_texto=version,
                    otorgado=c.otorgado,
                    ip=entrada.ip,
                    user_agent=entrada.user_agent,
                )
            )
            if c.otorgado:
                eventos.append(
                    ConsentimientoOtorgado(
                        id_persona=str(persona.id), tipo=tipo.value, version=version
                    )
                )

        await p.outbox.escribir(eventos)
        await p.uow.commit()
        return str(persona.id)
