"""Agregado Persona (§1.1) con la máquina de estados de identidad (§03.1)."""

from __future__ import annotations

from datetime import UTC, date, datetime
from enum import StrEnum

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import Cuil, Dni, EntityId

from .errors import PerfilDuplicado, PerfilNoAsignado, TransicionIdentidadInvalida
from .events import (
    CelularVerificado,
    IdentidadRechazada,
    IdentidadVerificada,
    PerfilMunicipalOtorgado,
    PerfilMunicipalRevocado,
    PersonaRegistrada,
    PersonaSuspendida,
)
from .perfil import Perfil, TipoPerfil
from .value_objects import Celular, Email


class EstadoIdentidad(StrEnum):
    PENDIENTE = "PENDIENTE"
    VERIFICADA = "VERIFICADA"
    RECHAZADA = "RECHAZADA"
    SUSPENDIDA = "SUSPENDIDA"


class MetodoVerificacion(StrEnum):
    # §3.1 (v2.3): el alta por la app es autodeclarada; RENAPER quedó fuera de alcance. Los otros
    # dos reflejan validaciones reforzadas reales (mostrador / proceso documental).
    AUTODECLARADA = "AUTODECLARADA"
    DOCUMENTAL = "DOCUMENTAL"
    PRESENCIAL = "PRESENCIAL"


class Persona(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        dni: Dni,
        fecha_nacimiento: date,
        estado_identidad: EstadoIdentidad,
        metodo_verificacion: MetodoVerificacion | None,
        celular_verificado: bool,
        email_verificado: bool,
        fecha_alta: datetime,
        perfiles: list[Perfil],
        cuil: Cuil | None = None,
        apellido: str = "",
        nombre: str = "",
        celular: Celular | None = None,
        email: Email | None = None,
    ) -> None:
        super().__init__(id)
        self.dni = dni
        self.fecha_nacimiento = fecha_nacimiento
        self.cuil = cuil
        self.apellido = apellido
        self.nombre = nombre
        self.celular = celular
        self.email = email
        self._estado_identidad = estado_identidad
        self.metodo_verificacion = metodo_verificacion
        self.celular_verificado = celular_verificado
        self.email_verificado = email_verificado
        self.fecha_alta = fecha_alta
        self._perfiles = perfiles

    # --- construcción --------------------------------------------------------
    @classmethod
    def registrar(
        cls,
        *,
        dni: Dni,
        fecha_nacimiento: date,
        celular: Celular | None = None,
        email: Email | None = None,
        cuil: Cuil | None = None,
        apellido: str = "",
        nombre: str = "",
    ) -> Persona:
        # §04.0.B: registro mínimo (DNI + fecha de nacimiento). Nombre/CUIL se completan
        # más adelante (RENAPER o alta presencial); el celular se pide pero no se verifica.
        persona = cls(
            id=EntityId.new(),
            dni=dni,
            fecha_nacimiento=fecha_nacimiento,
            cuil=cuil,
            apellido=apellido,
            nombre=nombre,
            celular=celular,
            email=email,
            estado_identidad=EstadoIdentidad.PENDIENTE,
            metodo_verificacion=None,
            celular_verificado=False,
            email_verificado=False,
            fecha_alta=datetime.now(UTC),
            perfiles=[Perfil(tipo=TipoPerfil.CIUDADANO)],
        )
        persona.record_event(PersonaRegistrada(id_persona=str(persona.id)))
        return persona

    @classmethod
    def rehidratar(cls, **kwargs: object) -> Persona:
        """Reconstituye desde persistencia sin emitir eventos."""
        return cls(**kwargs)  # type: ignore[arg-type]

    # --- estado --------------------------------------------------------------
    @property
    def estado_identidad(self) -> EstadoIdentidad:
        return self._estado_identidad

    @property
    def puede_canjear(self) -> bool:
        # §3.1: una cuenta sin verificar puede navegar pero no canjear.
        return self._estado_identidad is EstadoIdentidad.VERIFICADA

    def _transicionar(self, destino: EstadoIdentidad, permitidos: set[EstadoIdentidad]) -> None:
        if self._estado_identidad not in permitidos:
            raise TransicionIdentidadInvalida(
                f"No se puede pasar de {self._estado_identidad} a {destino}."
            )
        self._estado_identidad = destino

    def verificar_identidad(self, metodo: MetodoVerificacion) -> None:
        self._transicionar(EstadoIdentidad.VERIFICADA, {EstadoIdentidad.PENDIENTE})
        self.metodo_verificacion = metodo
        self.record_event(
            IdentidadVerificada(id_persona=str(self.id), dni=str(self.dni), metodo=str(metodo))
        )

    def rechazar_identidad(self, motivo: str) -> None:
        self._transicionar(EstadoIdentidad.RECHAZADA, {EstadoIdentidad.PENDIENTE})
        self.record_event(IdentidadRechazada(id_persona=str(self.id), motivo=motivo))

    def reintentar_identidad(self) -> None:
        self._transicionar(EstadoIdentidad.PENDIENTE, {EstadoIdentidad.RECHAZADA})

    def suspender(self, motivo: str) -> None:
        self._transicionar(EstadoIdentidad.SUSPENDIDA, {EstadoIdentidad.VERIFICADA})
        self.record_event(PersonaSuspendida(id_persona=str(self.id), motivo=motivo))

    def reactivar(self) -> None:
        self._transicionar(EstadoIdentidad.VERIFICADA, {EstadoIdentidad.SUSPENDIDA})

    # --- contacto ------------------------------------------------------------
    def verificar_celular(self) -> None:
        self.celular_verificado = True
        self.record_event(CelularVerificado(id_persona=str(self.id)))

    def verificar_email(self) -> None:
        self.email_verificado = True

    # --- perfiles ------------------------------------------------------------
    @property
    def perfiles(self) -> list[Perfil]:
        return list(self._perfiles)

    def agregar_perfil(self, perfil: Perfil) -> None:
        if perfil.tipo is TipoPerfil.CIUDADANO and any(
            p.tipo is TipoPerfil.CIUDADANO for p in self._perfiles
        ):
            raise PerfilDuplicado("La persona ya tiene un perfil ciudadano.")
        if perfil.clave() in {p.clave() for p in self._perfiles}:
            raise PerfilDuplicado(f"Perfil duplicado: {perfil.clave()}")
        self._perfiles.append(perfil)

    def tiene_perfil(self, clave: str) -> bool:
        return any(p.clave() == clave for p in self._perfiles)

    def otorgar_perfil_municipal(self, rol: str) -> None:
        """Otorga (o reasigna el rol de) el perfil municipal. Fuente de verdad del hecho."""
        self._perfiles = [p for p in self._perfiles if p.tipo is not TipoPerfil.MUNICIPAL]
        self._perfiles.append(Perfil(tipo=TipoPerfil.MUNICIPAL, rol=rol))
        self.record_event(PerfilMunicipalOtorgado(id_persona=str(self.id), rol=rol))

    def revocar_perfil_municipal(self) -> None:
        """Quita el perfil municipal. gobierno desactiva al agente al consumir el evento."""
        if not any(p.tipo is TipoPerfil.MUNICIPAL for p in self._perfiles):
            raise PerfilNoAsignado("La persona no tiene perfil municipal.")
        self._perfiles = [p for p in self._perfiles if p.tipo is not TipoPerfil.MUNICIPAL]
        self.record_event(PerfilMunicipalRevocado(id_persona=str(self.id)))
