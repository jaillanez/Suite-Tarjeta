"""Caso de uso: registrar una persona (§3.1)."""

from __future__ import annotations

from tarjeta.modules.identidad.domain.consentimiento import (
    OBLIGATORIOS,
    Consentimiento,
    TipoConsentimiento,
)
from tarjeta.modules.identidad.domain.credencial import Credencial
from tarjeta.modules.identidad.domain.errors import (
    ConsentimientoObligatorioFaltante,
    PersonaYaRegistrada,
)
from tarjeta.modules.identidad.domain.events import ConsentimientoOtorgado
from tarjeta.modules.identidad.domain.persona import Persona
from tarjeta.modules.identidad.domain.value_objects import Celular, Email
from tarjeta.shared.domain.events import DomainEvent
from tarjeta.shared.domain.types import Cuil, Dni

from .deps import Puertos
from .dto import RegistroInput
from .password_policy import validar_password
from .verificar_celular import SolicitarOtp


class RegistrarPersona:
    def __init__(self, puertos: Puertos) -> None:
        self.p = puertos

    async def ejecutar(self, entrada: RegistroInput) -> str:
        p = self.p
        validar_password(entrada.password, min_length=p.password_min_length)

        dni = Dni(entrada.dni)
        cuil = Cuil(entrada.cuil)
        celular = Celular(entrada.celular)
        email = Email(entrada.email) if entrada.email else None

        otorgados = {c.tipo: c.otorgado for c in entrada.consentimientos}
        for obligatorio in OBLIGATORIOS:
            if not otorgados.get(obligatorio.value, False):
                raise ConsentimientoObligatorioFaltante(
                    "Falta el consentimiento obligatorio de tratamiento de datos."
                )

        # §3.1: un DNI/CUIL ya registrado no puede registrarse de nuevo.
        if await p.personas.existe_dni(str(dni)) or await p.personas.existe_cuil(str(cuil)):
            raise PersonaYaRegistrada("Ya existe una cuenta asociada. Recuperá tu cuenta.")

        persona = Persona.registrar(
            dni=dni,
            cuil=cuil,
            apellido=entrada.apellido,
            nombre=entrada.nombre,
            celular=celular,
            email=email,
        )
        await p.personas.agregar(persona)
        await p.credenciales.agregar(
            Credencial.crear(id_persona=persona.id, hash=p.hasher.hash(entrada.password))
        )

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

        # Envío del OTP de verificación de celular (fuera de la transacción anterior).
        await SolicitarOtp(p).ejecutar(celular=str(celular), ip=entrada.ip)
        return str(persona.id)
