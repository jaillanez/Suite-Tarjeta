"""Portal de canje (composition root): el corazón operativo del programa.

Cruza comercios (cajero), ciudadania (nivel), identidad (persona/tarjeta), promociones (motor
y reserva de topes) y gobierno (parametría). Los módulos entre sí no se importan; acá se cablean.
"""

from __future__ import annotations

import json
import secrets
import time as _time
from datetime import UTC, date, datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from tarjeta.config import Settings, get_settings
from tarjeta.gating import filtrar_promos_habilitadas
from tarjeta.modules.canje.application.deps import CanjePuertos
from tarjeta.modules.canje.application.operaciones import (
    AnularOperacion,
    DecidirOperacion,
    GestionCiudadano,
    IniciarOperacion,
    ResumenCajero,
)
from tarjeta.modules.canje.application.ordenar import PromoParaCaja, ordenar_por_descuento
from tarjeta.modules.canje.application.sincronizacion import (
    OperacionEncolada,
    SincronizarSinConexion,
)
from tarjeta.modules.canje.domain.errors import (
    CiudadanoNoIdentificado,
    TokenInvalido,
    TokenVencido,
    TokenYaUsado,
)
from tarjeta.modules.canje.domain.ports import ReservaPromocion
from tarjeta.modules.canje.domain.transaccion import Confirmador, Transaccion, ViaCanje
from tarjeta.modules.canje.infrastructure.composition import construir_puertos_canje
from tarjeta.modules.canje.infrastructure.tokens import FirmadorTokenCiudadano
from tarjeta.modules.ciudadania.infrastructure.repositories import (
    SqlAlchemyPerfilCiudadanoRepository,
)
from tarjeta.modules.comercios.api.deps import ActorComercio, requiere_comercio_habilitado
from tarjeta.modules.comercios.domain.roles import Permiso as PermisoComercio
from tarjeta.modules.comercios.domain.roles import RolComercio
from tarjeta.modules.gobierno.application.parametria import ParametriaService
from tarjeta.modules.gobierno.infrastructure.composition import construir_puertos_gobierno
from tarjeta.modules.grupo.domain.tipos import EstadoMiembro, ModoBilletera
from tarjeta.modules.grupo.infrastructure.repositories import SqlAlchemyGrupoRepository
from tarjeta.modules.identidad.infrastructure.composition import construir_puertos
from tarjeta.modules.promociones.application.resolucion import MotorResolucion
from tarjeta.modules.promociones.infrastructure.composition import (
    construir_puertos_promociones,
)
from tarjeta.modules.promociones.infrastructure.repositories import SqlAlchemyPromocionRepository
from tarjeta.modules.puntos.application.canje import PuntosCanjeServicio
from tarjeta.modules.puntos.application.deps import PuntosConfig
from tarjeta.modules.puntos.domain.moneda import (
    OrigenPuntos,
    TipoTitular,
    puntos_comercio_por_canje,
)
from tarjeta.modules.puntos.infrastructure.composition import construir_puertos_puntos
from tarjeta.shared.api.auth import SesionDep
from tarjeta.shared.api.dependencies import RedisDep, SessionDep, SettingsDep
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

router = APIRouter(prefix="/api/v1/canje", tags=["canje"])

_NONCE_TTL = 130  # segundos: un poco más que la validez del token
_CODIGO_TTL = 90


# ------------------------------------------------------------------ reserva (adapter)


class _ReservaPromo(ReservaPromocion):
    def __init__(self, session: SessionDep) -> None:
        self._repo = SqlAlchemyPromocionRepository(session)

    async def reservar(self, id_promocion: str, id_persona: str, fecha: date) -> None:
        await self._repo.reservar_uso(
            EntityId.from_str(id_promocion), EntityId.from_str(id_persona), fecha
        )

    async def liberar(self, id_promocion: str, id_persona: str, fecha: date) -> None:
        await self._repo.liberar_uso(
            EntityId.from_str(id_promocion), EntityId.from_str(id_persona), fecha
        )


def _puntos_config(settings: Settings) -> PuntosConfig:
    return PuntosConfig(
        vencimiento_meses=settings.puntos_vencimiento_meses,
        base_por_cien=settings.puntos_base_por_cien,
        valor_punto=settings.puntos_valor_peso,
        pm_al_dia=settings.pm_al_dia,
    )


class _PuntosCanje:
    """Adapta el módulo `puntos` al puerto del canje (independencia de módulos, §09.4).

    Traduce la promoción a su mecánica/valor con `promociones` y delega la contabilidad en `puntos`.
    """

    def __init__(self, session: SessionDep) -> None:
        self._session = session
        self._grupos = SqlAlchemyGrupoRepository(session)
        self._svc = PuntosCanjeServicio(
            construir_puertos_puntos(session, _puntos_config(get_settings()))
        )

    async def _billetera(self, id_persona: str) -> tuple[TipoTitular, str, OrigenPuntos]:
        # §10.5: en modo COMÚN los canjes van al pozo del grupo; si no, a la billetera personal.
        # Un miembro suspendido no toca el pozo (cae a su billetera personal).
        miembro = await self._grupos.miembro_de(id_persona)
        if miembro is None or miembro.estado is not EstadoMiembro.ACTIVO:
            return (TipoTitular.PERSONA, id_persona, OrigenPuntos.INDIVIDUAL)
        grupo = await self._grupos.obtener(miembro.id_grupo)
        if grupo is None or not grupo.activo or grupo.modo_billetera is not ModoBilletera.COMUN:
            return (TipoTitular.PERSONA, id_persona, OrigenPuntos.INDIVIDUAL)
        return (TipoTitular.GRUPO, str(grupo.id), OrigenPuntos.GRUPO_COMUN)

    async def acreditar(
        self,
        *,
        id_transaccion: str,
        id_persona: str,
        id_comercio: str,
        id_promocion: str | None,
        nivel: str,
        monto: int,
    ) -> int:
        if not id_promocion:
            return 0
        promo = await SqlAlchemyPromocionRepository(self._session).obtener(
            EntityId.from_str(id_promocion)
        )
        if promo is None:
            return 0
        tipo_titular, id_titular, origen = await self._billetera(id_persona)
        return await self._svc.acreditar_canje(
            id_transaccion=id_transaccion,
            id_titular=id_titular,
            id_comercio=id_comercio,
            mecanica=promo.mecanica.value,
            valor=promo.valor_para(nivel),
            monto=monto,
            tipo_titular=tipo_titular,
            origen=origen,
        )

    async def consumir(
        self,
        *,
        id_transaccion: str,
        id_persona: str,
        id_comercio: str,
        puntos_solicitados: int,
        tope_pesos: int,
    ) -> tuple[int, int]:
        tipo_titular, id_titular, origen = await self._billetera(id_persona)
        return await self._svc.consumir_canje(
            id_transaccion=id_transaccion,
            id_titular=id_titular,
            id_comercio=id_comercio,
            puntos_solicitados=puntos_solicitados,
            tope_pesos=tope_pesos,
            tipo_titular=tipo_titular,
            origen=origen,
        )

    async def revertir(self, *, id_transaccion: str) -> None:
        await self._svc.revertir_canje(id_transaccion=id_transaccion)


def _puertos(session: SessionDep) -> CanjePuertos:
    return construir_puertos_canje(session, _ReservaPromo(session), _PuntosCanje(session))


def _firmador(settings: SettingsDep) -> FirmadorTokenCiudadano:
    return FirmadorTokenCiudadano(settings.jwt_secret.get_secret_value())


async def _nivel(session: SessionDep, id_persona: str) -> str:
    perfil = await SqlAlchemyPerfilCiudadanoRepository(session).obtener(
        EntityId.from_str(id_persona)
    )
    return str(perfil.nivel) if perfil else "PLATINO"


# ------------------------------------------------------------------ schemas


class Mensaje(BaseModel):
    mensaje: str


class TokenOut(BaseModel):
    token: str
    valido_desde: int
    valido_hasta: int


class CodigoOut(BaseModel):
    codigo: str
    valido_seg: int


class ResolverIn(BaseModel):
    via: str
    monto: int
    id_sucursal: str
    token: str | None = None
    codigo: str | None = None
    dni: str | None = None


class OpcionOut(BaseModel):
    id_promocion: str
    titulo: str
    mecanica: str
    descuento: int
    total: int
    puntos: int
    auto_propuesta: bool


class ResolverOut(BaseModel):
    id_persona: str
    nombre: str
    inicial_apellido: str
    nivel: str
    opciones: list[OpcionOut]


class IniciarIn(BaseModel):
    via: str
    monto: int
    id_sucursal: str
    clave_idempotencia: str
    id_promocion: str | None = None
    token: str | None = None
    codigo: str | None = None
    dni: str | None = None
    geo_lat: float | None = None
    geo_lon: float | None = None


class TransaccionOut(BaseModel):
    id: str
    numero_comprobante: str
    estado: str
    monto_bruto: int
    descuento: int
    total_pagar: int
    confirmador: str
    id_promocion: str | None
    nivel_aplicado: str
    puntos_ciudadano: int
    puntos_consumidos: int


class DecisionIn(BaseModel):
    motivo: str = ""


class ConfirmarIn(BaseModel):
    # §09.4: el ciudadano decide en la confirmación si quiere usar puntos.
    usar_puntos: int = 0


class CalificacionIn(BaseModel):
    estrellas: int


class OperacionEncoladaIn(BaseModel):
    clave_idempotencia: str
    id_persona: str
    nivel: str
    id_sucursal: str
    id_promocion: str | None = None
    mecanica: str | None = None
    valor: int = 0
    monto: int
    via: str = "CODIGO"


class SincronizarIn(BaseModel):
    operaciones: list[OperacionEncoladaIn]


def _out(t: Transaccion) -> TransaccionOut:
    return TransaccionOut(
        id=str(t.id),
        numero_comprobante=t.numero_comprobante,
        estado=t.estado.value,
        monto_bruto=t.monto_bruto,
        descuento=t.descuento,
        total_pagar=t.total_pagar,
        confirmador=t.confirmador.value,
        id_promocion=t.id_promocion,
        nivel_aplicado=t.nivel_aplicado,
        puntos_ciudadano=t.puntos_ciudadano,
        puntos_consumidos=t.puntos_consumidos,
    )


# ------------------------------------------------------------------ tokens del ciudadano


@router.get("/mis-tokens", response_model=list[TokenOut])
async def mis_tokens(
    sesion: SesionDep, session: SessionDep, settings: SettingsDep
) -> list[TokenOut]:
    # Pregenera los tokens de las próximas 2 h (para mostrar la tarjeta sin señal, §08.2).
    nivel = await _nivel(session, sesion.id_persona)
    lote = _firmador(settings).emitir_lote(
        id_persona=sesion.id_persona, nivel=nivel, ahora_epoch=int(_time.time()), horas=2
    )
    return [
        TokenOut(token=t.token, valido_desde=t.valido_desde, valido_hasta=t.valido_hasta)
        for t in lote
    ]


@router.post("/codigo", response_model=CodigoOut)
async def generar_codigo(sesion: SesionDep, session: SessionDep, redis: RedisDep) -> CodigoOut:
    # Código de 6 dígitos para la vía sin cámara (§08.2). Vive en Redis 90 s.
    nivel = await _nivel(session, sesion.id_persona)
    codigo = f"{secrets.randbelow(1_000_000):06d}"
    await redis.set(
        f"canje:codigo:{codigo}",
        json.dumps({"id_persona": sesion.id_persona, "nivel": nivel}),
        ex=_CODIGO_TTL,
    )
    return CodigoOut(codigo=codigo, valido_seg=_CODIGO_TTL)


# ------------------------------------------------------------------ resolución del ciudadano


async def _resolver_ciudadano(
    *,
    via: ViaCanje,
    session: SessionDep,
    settings: SettingsDep,
    redis: RedisDep,
    token: str | None,
    codigo: str | None,
    dni: str | None,
    consumir: bool,
) -> tuple[str, str]:
    """Devuelve (id_persona, nivel_congelado) según la vía. `consumir` gasta el token/código."""
    if via in (ViaCanje.CAJERO_ESCANEA,) and token:
        datos = _firmador(settings).verificar(token, ahora_epoch=int(_time.time()))
        if datos is None:
            raise TokenVencido("QR inválido o vencido.")
        if consumir:
            ok = await redis.set(f"canje:nonce:{datos.nonce}", "1", ex=_NONCE_TTL, nx=True)
            if not ok:
                raise TokenYaUsado("Ese QR ya fue usado.")
        return datos.id_persona, datos.nivel
    if via is ViaCanje.CODIGO and codigo:
        clave = f"canje:codigo:{codigo}"
        crudo = await redis.get(clave)
        if crudo is None:
            raise TokenVencido("Código inválido o vencido.")
        if consumir:
            await redis.delete(clave)
        data = json.loads(crudo)
        return str(data["id_persona"]), str(data["nivel"])
    if via is ViaCanje.TARJETA_FISICA and dni:
        id_puertos = construir_puertos(session, settings, redis)
        persona = await id_puertos.personas.obtener_por_dni(dni)
        if persona is None:
            raise CiudadanoNoIdentificado("No hay ciudadano con ese DNI.")
        return str(persona.id), await _nivel(session, str(persona.id))
    raise TokenInvalido("Faltan datos para identificar al ciudadano en esta vía.")


async def _opciones(
    session: SessionDep, settings: SettingsDep, *, nivel: str, id_sucursal: str, monto: int
) -> list[OpcionOut]:
    ahora = datetime.now(ZoneInfo(settings.municipio_timezone))
    promos = await MotorResolucion(construir_puertos_promociones(session)).resolver(
        nivel=nivel, id_sucursal=id_sucursal, momento_local=ahora, monto=monto
    )
    # §12.1: no se ofrecen promos de comercios no aprobados/suspendidos.
    promos = await filtrar_promos_habilitadas(session, promos)
    base = settings.puntos_base_por_cien
    entradas = [
        PromoParaCaja(
            id=str(p.id),
            titulo=p.titulo,
            mecanica=p.mecanica.value,
            valor=p.valor_para(nivel),
            # §09.0.B: el orden incorpora el valor de los puntos que otorga la promoción.
            puntos=puntos_comercio_por_canje(
                p.mecanica.value, p.valor_para(nivel), monto, base_por_cien=base
            ),
        )
        for p in promos
    ]
    return [
        OpcionOut(
            id_promocion=o.id,
            titulo=o.titulo,
            mecanica=o.mecanica,
            descuento=o.descuento,
            total=o.total,
            puntos=o.puntos,
            auto_propuesta=o.auto_propuesta,
        )
        for o in ordenar_por_descuento(entradas, monto, valor_punto=settings.puntos_valor_peso)
    ]


@router.post("/resolver", response_model=ResolverOut)
async def resolver(
    body: ResolverIn,
    session: SessionDep,
    settings: SettingsDep,
    redis: RedisDep,
    _: Annotated[
        ActorComercio, Depends(requiere_comercio_habilitado(PermisoComercio.CANJE_OPERAR))
    ],
) -> ResolverOut:
    via = ViaCanje(body.via)
    id_persona, nivel = await _resolver_ciudadano(
        via=via,
        session=session,
        settings=settings,
        redis=redis,
        token=body.token,
        codigo=body.codigo,
        dni=body.dni,
        consumir=False,
    )
    id_puertos = construir_puertos(session, settings, redis)
    persona = await id_puertos.personas.obtener_por_id(EntityId.from_str(id_persona))
    if persona is None:
        raise CiudadanoNoIdentificado("Ciudadano inexistente.")
    opciones = await _opciones(
        session, settings, nivel=nivel, id_sucursal=body.id_sucursal, monto=body.monto
    )
    return ResolverOut(
        id_persona=id_persona,
        nombre=persona.nombre,
        inicial_apellido=(persona.apellido[:1] if persona.apellido else ""),
        nivel=nivel,
        opciones=opciones,
    )


# ------------------------------------------------------------------ iniciar / confirmar


@router.post("/iniciar", response_model=TransaccionOut)
async def iniciar(
    body: IniciarIn,
    session: SessionDep,
    settings: SettingsDep,
    redis: RedisDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio_habilitado(PermisoComercio.CANJE_OPERAR))
    ],
) -> TransaccionOut:
    via = ViaCanje(body.via)
    # §08.4: idempotencia ANTES de consumir el token: un reintento con la misma clave devuelve
    # la operación original sin gastar de nuevo el QR.
    existente = await _puertos(session).transacciones.por_idempotencia(body.clave_idempotencia)
    if existente is not None:
        return _out(existente)
    id_persona, nivel = await _resolver_ciudadano(
        via=via,
        session=session,
        settings=settings,
        redis=redis,
        token=body.token,
        codigo=body.codigo,
        dni=body.dni,
        consumir=True,
    )
    mecanica: str | None = None
    valor = 0
    if body.id_promocion:
        promo = await construir_puertos_promociones(session).promociones.obtener(
            EntityId.from_str(body.id_promocion)
        )
        if promo is None:
            raise NotFoundError("Promoción inexistente.")
        mecanica = promo.mecanica.value
        valor = promo.valor_para(nivel)
    caso = IniciarOperacion(
        _puertos(session),
        prefijo_comprobante=settings.comprobante_prefijo,
        ttl_confirmacion_seg=settings.canje_confirmacion_ttl_seg,
    )
    t = await caso.ejecutar(
        id_persona=id_persona,
        nivel=nivel,
        id_comercio=str(actor.id_comercio),
        id_sucursal=body.id_sucursal,
        id_cajero=str(actor.usuario.id),
        id_promocion=body.id_promocion,
        mecanica=mecanica,
        valor=valor,
        monto=body.monto,
        via=via,
        clave_idempotencia=body.clave_idempotencia,
        geo_lat=body.geo_lat,
        geo_lon=body.geo_lon,
    )
    return _out(t)


@router.get("/mis-pendientes", response_model=list[TransaccionOut])
async def mis_pendientes(sesion: SesionDep, session: SessionDep) -> list[TransaccionOut]:
    pend = await _puertos(session).transacciones.pendientes_de_persona(sesion.id_persona)
    return [_out(t) for t in pend]


@router.post("/{id_transaccion}/confirmar", response_model=TransaccionOut)
async def confirmar_ciudadano(
    id_transaccion: str,
    sesion: SesionDep,
    session: SessionDep,
    body: ConfirmarIn | None = None,
) -> TransaccionOut:
    t = await DecidirOperacion(_puertos(session)).confirmar(
        id_transaccion=id_transaccion,
        por=Confirmador.CIUDADANO,
        id_actor=sesion.id_persona,
        usar_puntos=body.usar_puntos if body else 0,
    )
    return _out(t)


@router.post("/{id_transaccion}/rechazar", response_model=Mensaje)
async def rechazar_ciudadano(
    id_transaccion: str, sesion: SesionDep, session: SessionDep
) -> Mensaje:
    await DecidirOperacion(_puertos(session)).rechazar(
        id_transaccion=id_transaccion, id_actor=sesion.id_persona
    )
    return Mensaje(mensaje="Operación rechazada.")


@router.get("/comercio/pendientes", response_model=list[TransaccionOut])
async def pendientes_comercio(
    session: SessionDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio_habilitado(PermisoComercio.CANJE_OPERAR))
    ],
) -> list[TransaccionOut]:
    pend = await _puertos(session).transacciones.pendientes_de_comercio(str(actor.id_comercio))
    # Solo las que confirma el comercio (ciudadano_escanea / tarjeta_fisica).
    return [_out(t) for t in pend if t.confirmador is Confirmador.CAJERO]


@router.get("/comercio/operacion/{id_transaccion}", response_model=TransaccionOut)
async def estado_operacion(
    id_transaccion: str,
    session: SessionDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio_habilitado(PermisoComercio.CANJE_OPERAR))
    ],
) -> TransaccionOut:
    t = await _puertos(session).transacciones.obtener(EntityId.from_str(id_transaccion))
    if t is None or t.id_comercio != str(actor.id_comercio):
        raise NotFoundError("Operación inexistente.")
    return _out(t)


@router.post("/comercio/{id_transaccion}/confirmar", response_model=TransaccionOut)
async def confirmar_comercio(
    id_transaccion: str,
    session: SessionDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio_habilitado(PermisoComercio.CANJE_OPERAR))
    ],
) -> TransaccionOut:
    t = await DecidirOperacion(_puertos(session)).confirmar(
        id_transaccion=id_transaccion,
        por=Confirmador.CAJERO,
        id_comercio=str(actor.id_comercio),
    )
    return _out(t)


# ------------------------------------------------------------------ anulación / disputa / rating


@router.post("/{id_transaccion}/anular", response_model=Mensaje)
async def anular(
    id_transaccion: str,
    body: DecisionIn,
    session: SessionDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio_habilitado(PermisoComercio.CANJE_OPERAR))
    ],
) -> Mensaje:
    ventana = await ParametriaService(construir_puertos_gobierno(session)).obtener(
        "anulacion_ventana_minutos"
    )
    es_admin = actor.rol is RolComercio.ADMIN_COMERCIO
    await AnularOperacion(_puertos(session), ventana_minutos=ventana).ejecutar(
        id_transaccion=id_transaccion,
        motivo=body.motivo,
        es_admin=es_admin,
        id_comercio=str(actor.id_comercio),
    )
    return Mensaje(mensaje="Operación anulada; se revirtió el descuento y el cupo.")


@router.post("/{id_transaccion}/disputar", response_model=Mensaje)
async def disputar(
    id_transaccion: str, body: DecisionIn, sesion: SesionDep, session: SessionDep
) -> Mensaje:
    await GestionCiudadano(_puertos(session)).disputar(
        id_transaccion=id_transaccion, id_persona=sesion.id_persona, motivo=body.motivo
    )
    return Mensaje(mensaje="Disputa abierta; el municipio la va a revisar.")


@router.post("/{id_transaccion}/calificar", response_model=Mensaje)
async def calificar(
    id_transaccion: str, body: CalificacionIn, sesion: SesionDep, session: SessionDep
) -> Mensaje:
    await GestionCiudadano(_puertos(session)).calificar(
        id_transaccion=id_transaccion, id_persona=sesion.id_persona, estrellas=body.estrellas
    )
    return Mensaje(mensaje="¡Gracias por calificar!")


@router.get("/historial", response_model=list[TransaccionOut])
async def historial(sesion: SesionDep, session: SessionDep) -> list[TransaccionOut]:
    ops = await GestionCiudadano(_puertos(session)).historial(id_persona=sesion.id_persona)
    return [_out(t) for t in ops]


# ------------------------------------------------------------------ modo sin conexión


@router.post("/sincronizar")
async def sincronizar(
    body: SincronizarIn,
    session: SessionDep,
    settings: SettingsDep,
    _: Annotated[
        ActorComercio, Depends(requiere_comercio_habilitado(PermisoComercio.CANJE_OPERAR))
    ],
) -> dict[str, Any]:
    encoladas = [
        OperacionEncolada(
            clave_idempotencia=o.clave_idempotencia,
            id_persona=o.id_persona,
            nivel=o.nivel,
            id_comercio=str(_.id_comercio),
            id_sucursal=o.id_sucursal,
            id_cajero=str(_.usuario.id),
            id_promocion=o.id_promocion,
            mecanica=o.mecanica,
            valor=o.valor,
            monto=o.monto,
            via=o.via,
        )
        for o in body.operaciones
    ]
    resultados = await SincronizarSinConexion(
        _puertos(session),
        prefijo_comprobante=settings.comprobante_prefijo,
        monto_max=settings.canje_offline_monto_max,
        max_operaciones=settings.canje_offline_max_operaciones,
    ).ejecutar(encoladas)
    return {
        "resultados": [
            {
                "clave": r.clave_idempotencia,
                "aplicada": r.aplicada,
                "id_transaccion": r.id_transaccion,
                "conflicto_tope": r.conflicto_tope,
                "motivo": r.motivo,
            }
            for r in resultados
        ]
    }


# ------------------------------------------------------------------ cierre de turno real


@router.get("/turno/resumen")
async def resumen_turno(
    session: SessionDep,
    settings: SettingsDep,
    actor: Annotated[
        ActorComercio, Depends(requiere_comercio_habilitado(PermisoComercio.TURNO_OPERAR))
    ],
) -> dict[str, Any]:
    from tarjeta.modules.comercios.infrastructure.repositories import SqlAlchemyTurnoRepository

    turno = await SqlAlchemyTurnoRepository(session).turno_abierto_de(actor.usuario.id)
    desde = turno.abierto_en if turno else datetime.now(UTC)
    r = await ResumenCajero(_puertos(session)).ejecutar(
        id_cajero=str(actor.usuario.id), desde=desde
    )
    return {
        "operaciones": r.operaciones,
        "monto_bruto": r.monto_bruto,
        "descuento": r.descuento,
        "por_promocion": r.por_promocion,
    }
