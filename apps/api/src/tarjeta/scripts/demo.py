"""Modo demostración (§13.5): un recorrido listo para mostrar el sistema andando.

Con UN comando deja: un vecino Platino y uno Black, un grupo familiar, un comercio con cajero y
turno abierto, promociones de distintas mecánicas y un saldo de puntos con movimientos. Es
idempotente (ids derivados por uuid5): correrlo de nuevo restablece el mismo estado conocido, sin
duplicar. Nota: `movimiento_billetera` es append-only e inmutable para el rol de runtime
(§09), así que "reiniciable" acá significa re-ejecutar hasta el mismo estado, no borrar el libro.

Uso:  uv run python -m tarjeta.scripts.demo
"""

from __future__ import annotations

import asyncio
import os
import uuid
from datetime import UTC, date, datetime

from tarjeta.config import get_settings
from tarjeta.modules.ciudadania.infrastructure.models import PerfilCiudadanoModel
from tarjeta.modules.comercios.infrastructure.models import TurnoModel, UsuarioComercioModel
from tarjeta.modules.comercios.infrastructure.pin import Argon2PinHasher
from tarjeta.modules.grupo.infrastructure.models import GrupoModel, MiembroModel
from tarjeta.modules.identidad.domain.perfil import Perfil, TipoPerfil
from tarjeta.modules.identidad.domain.persona import (
    EstadoIdentidad,
    MetodoVerificacion,
    Persona,
)
from tarjeta.modules.identidad.infrastructure.argon2_hasher import Argon2Hasher
from tarjeta.modules.identidad.infrastructure.mappers import persona_to_model
from tarjeta.modules.identidad.infrastructure.models import CredencialModel, PersonaModel
from tarjeta.modules.padron.infrastructure.models import EstadoPadronModel
from tarjeta.modules.puntos.infrastructure.models import (
    BilleteraModel,
    LotePuntosModel,
    MovimientoBilleteraModel,
)
from tarjeta.scripts.cargar_comercios import _cargar as cargar_comercios
from tarjeta.scripts.cargar_comercios import _id as _id_comercio
from tarjeta.shared.domain.types import Cuil, Dni, EntityId, cuil_check_digit
from tarjeta.shared.infrastructure.crypto import FieldCipher
from tarjeta.shared.infrastructure.database import get_sessionmaker

_NS = uuid.uuid5(uuid.NAMESPACE_DNS, "suite-tarjeta.demo")  # namespace estable de la demo
_PASSWORD = "demo-contrasena-123"  # noqa: S105 - contraseña de datos de demostración
_PIN = "1234"


def _did(*p: str) -> uuid.UUID:
    return uuid.uuid5(_NS, "|".join(p))


def _cuil(dni: str) -> str:
    # Elige un prefijo cuyo dígito verificador sea 0-9 (descarta el 10, que no es CUIL real).
    for prefijo in ("20", "27", "23", "24", "30"):
        base = prefijo + dni
        cd = cuil_check_digit(base)
        if cd < 10:
            return base + str(cd)
    raise ValueError(f"sin CUIL válido para DNI {dni}")


def _luhn16(semilla: uuid.UUID) -> str:
    quince = f"{semilla.int % 10**15:015d}"
    suma = 0
    for i, ch in enumerate(reversed(quince)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        suma += d
    return quince + str((10 - suma % 10) % 10)


def _persona(
    dni: str, cuil: str, nombre: str, apellido: str, id_comercio: uuid.UUID | None = None
) -> Persona:
    perfiles = [Perfil(tipo=TipoPerfil.CIUDADANO)]
    if id_comercio is not None:
        perfiles.append(
            Perfil(tipo=TipoPerfil.COMERCIO, id_comercio=uuid_a_entity(id_comercio), rol="CAJERO")
        )
    ahora = datetime.now(UTC)
    return Persona(
        id=uuid_a_entity(_did("persona", dni)),
        dni=Dni(dni),
        cuil=Cuil(cuil),
        fecha_nacimiento=date(1985, 6, 15),
        estado_identidad=EstadoIdentidad.VERIFICADA,
        metodo_verificacion=MetodoVerificacion.AUTODECLARADA,
        celular_verificado=True,
        email_verificado=False,
        fecha_alta=ahora,
        perfiles=perfiles,
        apellido=apellido,
        nombre=nombre,
    )


def uuid_a_entity(u: uuid.UUID) -> EntityId:
    return EntityId(u)


# --- comercio de demo (reusa el loader de precarga) --------------------------
_CUIT_DEMO = "30777888991"
_COMERCIO_DEMO = {
    "cuit": _CUIT_DEMO,
    "razon_social": "Demo Comercio SRL",
    "nombre_fantasia": "Comercio Demostración",
    "rubro": "gastronomia",
    "origen": "demo (§13.5)",
    "sucursal": {
        "nombre": "Casa Central",
        "direccion": "Av. Libertador 1000 Oeste, Rivadavia",
        "telefono": "264 4999000",
        "lat": -31.5360,
        "lon": -68.6000,
        "horarios": [
            {
                "dia": d,
                "franjas": [
                    {"desde": "09:00", "hasta": "13:00"},
                    {"desde": "17:00", "hasta": "21:00"},
                ],
            }
            for d in range(0, 6)
        ],
    },
    "promociones": [
        {
            "titulo": "20% en el total",
            "mecanica": "PORCENTAJE",
            "segmento": "AMBOS",
            "valor_platino": 15,
            "valor_black": 20,
        },
        {
            "titulo": "2x1 en postres",
            "mecanica": "DOS_POR_UNO",
            "segmento": "SOLO_BLACK",
            "valor_black": 0,
        },
        {
            "titulo": "Puntos x2",
            "mecanica": "MULTIPLICADOR_PUNTOS",
            "segmento": "AMBOS",
            "valor_platino": 2,
            "valor_black": 3,
        },
    ],
}


async def _sembrar() -> None:
    settings = get_settings()
    cipher = FieldCipher(
        settings.field_encryption_key.get_secret_value(),
        settings.field_encryption_key_version,
    )
    pepper = settings.field_pepper.get_secret_value()
    hasher = Argon2Hasher(
        time_cost=settings.argon2_time_cost,
        memory_cost=settings.argon2_memory_cost,
        parallelism=settings.argon2_parallelism,
    )
    ahora = datetime.now(UTC)

    # Comercio + sucursal + promos (ACTIVA, precarga) reutilizando el loader.
    await cargar_comercios([_COMERCIO_DEMO])
    id_comercio = _id_comercio("comercio", _CUIT_DEMO)
    id_sucursal = _id_comercio("sucursal", _CUIT_DEMO, "Casa Central")

    # Vecinos: uno Black (al día) y uno Platino.
    black = _persona("20111222", _cuil("20111222"), "Ana", "Gómez")
    platino = _persona("27333444", _cuil("27333444"), "Luis", "Pérez")
    cajero = _persona("23555666", _cuil("23555666"), "Caja", "Demo", id_comercio=id_comercio)

    sm = get_sessionmaker()
    async with sm() as s:
        for p, nivel, al_dia in ((black, "BLACK", True), (platino, "PLATINO", False)):
            pid = p.id.value
            if await s.get(PersonaModel, pid) is None:
                s.add(persona_to_model(p, cipher, pepper))
                await s.flush()
            if await s.get(CredencialModel, _did("cred", str(pid))) is None:
                s.add(
                    CredencialModel(
                        id=_did("cred", str(pid)), id_persona=pid, hash=hasher.hash(_PASSWORD)
                    )
                )
            # Nivel (lo que lee /ciudadania/mi-estado).
            pc = await s.get(PerfilCiudadanoModel, pid)
            if pc is None:
                pc = PerfilCiudadanoModel(
                    id_persona=pid, numero_tarjeta=_luhn16(pid), tiene_tarjeta_fisica=False
                )
                s.add(pc)
            pc.nivel = nivel
            pc.nivel_origen = "PROPIO"
            pc.estado_tarjeta = "ACTIVA"
            pc.fecha_ultimo_calculo = ahora
            # Estado de padrón coherente (por si se corre "actualizar estado").
            ep = await s.get(EstadoPadronModel, pid)
            if ep is None:
                ep = EstadoPadronModel(id_persona=pid, dni_cifrado=cipher.encrypt(str(p.dni)))
                s.add(ep)
            ep.al_dia = al_dia
            ep.es_comerciante = False
            ep.fecha_ultima_consulta = ahora

        # Cajero (persona + credencial + usuario_comercio + turno abierto).
        cpid = cajero.id.value
        if await s.get(PersonaModel, cpid) is None:
            s.add(persona_to_model(cajero, cipher, pepper))
            await s.flush()
        if await s.get(CredencialModel, _did("cred", str(cpid))) is None:
            s.add(
                CredencialModel(
                    id=_did("cred", str(cpid)), id_persona=cpid, hash=hasher.hash(_PASSWORD)
                )
            )
        id_usuario = _did("usuario", _CUIT_DEMO, str(cpid))
        uc = await s.get(UsuarioComercioModel, id_usuario)
        if uc is None:
            uc = UsuarioComercioModel(id=id_usuario, id_comercio=id_comercio, id_persona=cpid)
            s.add(uc)
        uc.rol = "CAJERO"
        uc.sucursales = [str(id_sucursal)]
        uc.estado = "ACTIVO"
        uc.pin_hash = Argon2PinHasher().hash(_PIN)
        # Para probar la caja en un teléfono real: exportá TARJETA_DEMO_HUELLA con la huella del
        # dispositivo (Preferences: tarjeta_huella_dispositivo) antes de correr el demo.
        uc.huella_dispositivo = os.environ.get("TARJETA_DEMO_HUELLA", "demo-dispositivo")
        uc.pin_intentos = 0
        # Turno abierto = cerrado_en NULL. id_cajero = id del UsuarioComercio (no de la persona).
        id_turno = _did("turno", str(id_usuario))
        turno = await s.get(TurnoModel, id_turno)
        if turno is None:
            turno = TurnoModel(
                id=id_turno, id_sucursal=id_sucursal, id_cajero=id_usuario, resumen={}
            )
            s.add(turno)
        turno.abierto_en = ahora
        turno.cerrado_en = None

        # Puntos del vecino Black: billetera PC en el comercio demo, con 2 movimientos.
        id_bill = _did("billetera", str(black.id.value), _CUIT_DEMO)
        bill = await s.get(BilleteraModel, id_bill)
        if bill is None:
            bill = BilleteraModel(
                id=id_bill,
                tipo_titular="PERSONA",
                id_titular=str(black.id.value),
                tipo_moneda="PC",
                id_comercio=str(id_comercio),
                creada_en=ahora,
            )
            s.add(bill)
        bill.saldo = 500
        id_lote = _did("lote", str(id_bill))
        if await s.get(LotePuntosModel, id_lote) is None:
            s.add(
                LotePuntosModel(
                    id=id_lote,
                    id_billetera=id_bill,
                    monto_original=600,
                    saldo_restante=500,
                    vence_en=date(2028, 1, 1),
                    origen_puntos="INDIVIDUAL",
                    creado_en=ahora,
                    vencido=False,
                )
            )
        # Movimientos append-only: solo se agregan si no existen (idempotente).
        for suf, tipo, monto in (("acred", "ACREDITACION", 600), ("consumo", "CONSUMO", -100)):
            mid = _did("mov", str(id_bill), suf)
            if await s.get(MovimientoBilleteraModel, mid) is None:
                s.add(
                    MovimientoBilleteraModel(
                        id=mid,
                        id_billetera=id_bill,
                        tipo=tipo,
                        monto=monto,
                        origen_puntos="INDIVIDUAL",
                        creado_en=ahora,
                        concepto="demo",
                    )
                )

        # Grupo familiar: Black titular, Platino miembro, billetera común.
        id_grupo = _did("grupo", str(black.id.value))
        grupo = await s.get(GrupoModel, id_grupo)
        if grupo is None:
            grupo = GrupoModel(id=id_grupo, creado_en=ahora)
            s.add(grupo)
        grupo.id_titular = str(black.id.value)
        grupo.modo_billetera = "COMUN"
        grupo.estado = "ACTIVO"
        for persona_grupo, rol in ((black, "TITULAR"), (platino, "MIEMBRO")):
            mid = _did("miembro", str(id_grupo), str(persona_grupo.id.value))
            miembro = await s.get(MiembroModel, mid)
            if miembro is None:
                miembro = MiembroModel(
                    id=mid, id_grupo=id_grupo, fecha_alta=ahora, tope_mensual=None
                )
                s.add(miembro)
            miembro.id_persona = str(persona_grupo.id.value)
            miembro.rol = rol
            miembro.estado = "ACTIVO"

        await s.commit()


def main() -> None:
    asyncio.run(_sembrar())
    print(
        "Demo cargada. Vecinos: DNI 20111222 (Black) y 27333444 (Platino), contraseña "
        f"'{_PASSWORD}'. Cajero: DNI 23555666, PIN {_PIN}. Comercio 'Comercio Demostración' "
        "con turno abierto y promos activas."
    )


if __name__ == "__main__":
    main()
