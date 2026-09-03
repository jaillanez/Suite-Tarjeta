"""Conversión entre modelos ORM y objetos de dominio (con cifrado de campos)."""

from __future__ import annotations

from typing import Any

from tarjeta.modules.identidad.domain.consentimiento import Consentimiento, TipoConsentimiento
from tarjeta.modules.identidad.domain.dispositivo import Dispositivo, EstadoDispositivo
from tarjeta.modules.identidad.domain.perfil import Perfil, TipoPerfil
from tarjeta.modules.identidad.domain.persona import EstadoIdentidad, MetodoVerificacion, Persona
from tarjeta.modules.identidad.domain.value_objects import Celular, Email
from tarjeta.shared.domain.types import Cuil, Dni, EntityId
from tarjeta.shared.infrastructure.crypto import FieldCipher, search_hash

from .models import ConsentimientoModel, DispositivoModel, PersonaModel


def _perfiles_to_json(perfiles: list[Perfil]) -> list[dict[str, object]]:
    return [
        {
            "tipo": p.tipo.value,
            "id_comercio": str(p.id_comercio) if p.id_comercio is not None else None,
            "rol": p.rol,
        }
        for p in perfiles
    ]


def _perfiles_from_json(data: list[dict[str, Any]]) -> list[Perfil]:
    perfiles: list[Perfil] = []
    for d in data:
        id_comercio = d.get("id_comercio")
        perfiles.append(
            Perfil(
                tipo=TipoPerfil(d["tipo"]),
                id_comercio=EntityId.from_str(id_comercio) if id_comercio else None,
                rol=d.get("rol"),
            )
        )
    return perfiles


def persona_to_model(p: Persona, cipher: FieldCipher, pepper: str) -> PersonaModel:
    return PersonaModel(
        id=p.id.value,
        dni_hash=search_hash(str(p.dni), pepper),
        dni_cifrado=cipher.encrypt(str(p.dni)),
        cuil_hash=search_hash(str(p.cuil), pepper),
        cuil_cifrado=cipher.encrypt(str(p.cuil)),
        apellido=p.apellido,
        nombre=p.nombre,
        celular=str(p.celular),
        email=str(p.email) if p.email is not None else None,
        celular_verificado=p.celular_verificado,
        email_verificado=p.email_verificado,
        estado_identidad=p.estado_identidad.value,
        metodo_verificacion=p.metodo_verificacion.value if p.metodo_verificacion else None,
        fecha_alta=p.fecha_alta,
        perfiles=_perfiles_to_json(p.perfiles),
    )


def actualizar_model(model: PersonaModel, p: Persona) -> None:
    model.apellido = p.apellido
    model.nombre = p.nombre
    model.celular = str(p.celular)
    model.email = str(p.email) if p.email is not None else None
    model.celular_verificado = p.celular_verificado
    model.email_verificado = p.email_verificado
    model.estado_identidad = p.estado_identidad.value
    model.metodo_verificacion = p.metodo_verificacion.value if p.metodo_verificacion else None
    model.perfiles = _perfiles_to_json(p.perfiles)


def model_to_persona(model: PersonaModel, cipher: FieldCipher) -> Persona:
    return Persona.rehidratar(
        id=EntityId(model.id),
        dni=Dni(cipher.decrypt(model.dni_cifrado)),
        cuil=Cuil(cipher.decrypt(model.cuil_cifrado)),
        apellido=model.apellido,
        nombre=model.nombre,
        celular=Celular(model.celular),
        email=Email(model.email) if model.email else None,
        estado_identidad=EstadoIdentidad(model.estado_identidad),
        metodo_verificacion=(
            MetodoVerificacion(model.metodo_verificacion) if model.metodo_verificacion else None
        ),
        celular_verificado=model.celular_verificado,
        email_verificado=model.email_verificado,
        fecha_alta=model.fecha_alta,
        perfiles=_perfiles_from_json(model.perfiles),
    )


def consentimiento_to_model(c: Consentimiento) -> ConsentimientoModel:
    return ConsentimientoModel(
        id=c.id.value,
        id_persona=c.id_persona.value,
        tipo=c.tipo.value,
        version_texto=c.version_texto,
        otorgado=c.otorgado,
        fecha=c.fecha,
        ip=c.ip,
        user_agent=c.user_agent,
    )


def model_to_consentimiento(m: ConsentimientoModel) -> Consentimiento:
    return Consentimiento(
        id=EntityId(m.id),
        id_persona=EntityId(m.id_persona),
        tipo=TipoConsentimiento(m.tipo),
        version_texto=m.version_texto,
        otorgado=m.otorgado,
        fecha=m.fecha,
        ip=m.ip,
        user_agent=m.user_agent,
    )


def dispositivo_to_model(d: Dispositivo) -> DispositivoModel:
    return DispositivoModel(
        id=d.id.value,
        id_persona=d.id_persona.value,
        nombre_declarado=d.nombre_declarado,
        plataforma=d.plataforma,
        huella=d.huella,
        fecha_alta=d.fecha_alta,
        fecha_ultimo_uso=d.fecha_ultimo_uso,
        estado=d.estado.value,
        autorizado_para_perfil_municipal=d.autorizado_para_perfil_municipal,
    )


def model_to_dispositivo(m: DispositivoModel) -> Dispositivo:
    return Dispositivo(
        id=EntityId(m.id),
        id_persona=EntityId(m.id_persona),
        nombre_declarado=m.nombre_declarado,
        plataforma=m.plataforma,
        huella=m.huella,
        fecha_alta=m.fecha_alta,
        fecha_ultimo_uso=m.fecha_ultimo_uso,
        estado=EstadoDispositivo(m.estado),
        autorizado_para_perfil_municipal=m.autorizado_para_perfil_municipal,
    )
