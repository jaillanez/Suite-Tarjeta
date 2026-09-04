"""Agregado Transaccion (§1.7, §08.6): el canje aplica un descuento con comprobante."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from enum import StrEnum

from tarjeta.shared.domain.entity import AggregateRoot
from tarjeta.shared.domain.types import EntityId

from .errors import (
    ConfirmacionVencida,
    ConfirmadorInvalido,
    FueraDeVentanaAnulacion,
    TransicionCanjeInvalida,
)
from .events import CanjeAnulado, CanjeAplicado, DisputaAbierta, OperacionCreada


class EstadoTransaccion(StrEnum):
    PENDIENTE_CONFIRMACION = "PENDIENTE_CONFIRMACION"
    APLICADA = "APLICADA"
    RECHAZADA = "RECHAZADA"
    EXPIRADA = "EXPIRADA"
    ANULADA = "ANULADA"


class ViaCanje(StrEnum):
    CAJERO_ESCANEA = "CAJERO_ESCANEA"  # caso normal: confirma el ciudadano
    CIUDADANO_ESCANEA = "CIUDADANO_ESCANEA"  # comercio sin cámara: confirma el comercio
    CODIGO = "CODIGO"  # sin conexión / cámara falla: confirma el ciudadano
    TARJETA_FISICA = "TARJETA_FISICA"  # sin teléfono: confirma el cajero


class Confirmador(StrEnum):
    CIUDADANO = "CIUDADANO"
    CAJERO = "CAJERO"


class Transaccion(AggregateRoot):
    def __init__(
        self,
        *,
        id: EntityId,
        numero_comprobante: str,
        id_persona: str,
        nivel_aplicado: str,
        id_comercio: str,
        id_sucursal: str,
        id_cajero: str,
        id_promocion: str | None,
        monto_bruto: int,
        descuento: int,
        via: ViaCanje,
        confirmador: Confirmador,
        estado: EstadoTransaccion,
        clave_idempotencia: str,
        vence_en: datetime | None,
        creada_en: datetime,
        confirmada_en: datetime | None = None,
        sin_conexion: bool = False,
        geo_lat: float | None = None,
        geo_lon: float | None = None,
        distancia_m: float | None = None,
        calificacion: int | None = None,
        motivo_anulacion: str | None = None,
        en_disputa: bool = False,
        # §09.4: puntos del canje. puntos_ciudadano = PC acreditados; puntos_consumidos = PC que
        # el ciudadano usó para pagar y pesos_cubiertos_puntos, los pesos que esos puntos cubren.
        puntos_ciudadano: int = 0,
        puntos_municipio: int = 0,
        puntos_consumidos: int = 0,
        pesos_cubiertos_puntos: int = 0,
    ) -> None:
        super().__init__(id)
        self.numero_comprobante = numero_comprobante
        self.id_persona = id_persona
        self.nivel_aplicado = nivel_aplicado
        self.id_comercio = id_comercio
        self.id_sucursal = id_sucursal
        self.id_cajero = id_cajero
        self.id_promocion = id_promocion
        self.monto_bruto = monto_bruto
        self.descuento = descuento
        self.via = via
        self.confirmador = confirmador
        self._estado = estado
        self.clave_idempotencia = clave_idempotencia
        self.vence_en = vence_en
        self.creada_en = creada_en
        self.confirmada_en = confirmada_en
        self.sin_conexion = sin_conexion
        self.geo_lat = geo_lat
        self.geo_lon = geo_lon
        self.distancia_m = distancia_m
        self.calificacion = calificacion
        self.motivo_anulacion = motivo_anulacion
        self.en_disputa = en_disputa
        self.puntos_ciudadano = puntos_ciudadano
        self.puntos_municipio = puntos_municipio
        self.puntos_consumidos = puntos_consumidos
        self.pesos_cubiertos_puntos = pesos_cubiertos_puntos

    @property
    def estado(self) -> EstadoTransaccion:
        return self._estado

    @property
    def total_pagar(self) -> int:
        # Los puntos usados por el ciudadano cubren parte del total (§09.4).
        return max(0, self.monto_bruto - self.descuento - self.pesos_cubiertos_puntos)

    def acreditar_puntos(self, puntos_ciudadano: int) -> None:
        """PC otorgados por el canje (solo una vez aplicado)."""
        self.puntos_ciudadano = puntos_ciudadano

    def registrar_consumo_puntos(self, puntos: int, pesos_cubiertos: int) -> None:
        """PC que el ciudadano usó para pagar y los pesos que cubrieron."""
        self.puntos_consumidos = puntos
        self.pesos_cubiertos_puntos = pesos_cubiertos

    @classmethod
    def crear(
        cls,
        *,
        numero_comprobante: str,
        id_persona: str,
        nivel_aplicado: str,
        id_comercio: str,
        id_sucursal: str,
        id_cajero: str,
        id_promocion: str | None,
        monto_bruto: int,
        descuento: int,
        via: ViaCanje,
        clave_idempotencia: str,
        ttl_confirmacion_seg: int,
        sin_conexion: bool = False,
        geo_lat: float | None = None,
        geo_lon: float | None = None,
        distancia_m: float | None = None,
    ) -> Transaccion:
        # Quién confirma según la vía (§08.3).
        confirmador = (
            Confirmador.CAJERO
            if via in (ViaCanje.CIUDADANO_ESCANEA, ViaCanje.TARJETA_FISICA)
            else Confirmador.CIUDADANO
        )
        ahora = datetime.now(UTC)
        t = cls(
            id=EntityId.new(),
            numero_comprobante=numero_comprobante,
            id_persona=id_persona,
            nivel_aplicado=nivel_aplicado,
            id_comercio=id_comercio,
            id_sucursal=id_sucursal,
            id_cajero=id_cajero,
            id_promocion=id_promocion,
            monto_bruto=monto_bruto,
            descuento=descuento,
            via=via,
            confirmador=confirmador,
            estado=EstadoTransaccion.PENDIENTE_CONFIRMACION,
            clave_idempotencia=clave_idempotencia,
            vence_en=ahora + timedelta(seconds=ttl_confirmacion_seg),
            creada_en=ahora,
            sin_conexion=sin_conexion,
            geo_lat=geo_lat,
            geo_lon=geo_lon,
            distancia_m=distancia_m,
        )
        t.record_event(
            OperacionCreada(
                id_transaccion=str(t.id), id_persona=id_persona, id_comercio=id_comercio
            )
        )
        return t

    def _pendiente_vigente(self, ahora: datetime) -> None:
        if self._estado is not EstadoTransaccion.PENDIENTE_CONFIRMACION:
            raise TransicionCanjeInvalida("La operación no está pendiente de confirmación.")
        if self.vence_en is not None and ahora > self.vence_en:
            raise ConfirmacionVencida("La confirmación venció.")

    def confirmar(self, *, por: Confirmador) -> None:
        ahora = datetime.now(UTC)
        self._pendiente_vigente(ahora)
        if por is not self.confirmador:
            raise ConfirmadorInvalido("Esta operación la confirma la otra parte.")
        self._estado = EstadoTransaccion.APLICADA
        self.confirmada_en = ahora
        self.record_event(
            CanjeAplicado(
                id_transaccion=str(self.id),
                id_persona=self.id_persona,
                id_comercio=self.id_comercio,
                monto=self.monto_bruto,
                descuento=self.descuento,
            )
        )

    def aplicar_directo(self) -> None:
        """Aplicación sin confirmación remota (cola sin conexión ya aceptada en el mostrador)."""
        if self._estado is not EstadoTransaccion.PENDIENTE_CONFIRMACION:
            raise TransicionCanjeInvalida("La operación no está pendiente.")
        self._estado = EstadoTransaccion.APLICADA
        self.confirmada_en = datetime.now(UTC)
        self.record_event(
            CanjeAplicado(
                id_transaccion=str(self.id),
                id_persona=self.id_persona,
                id_comercio=self.id_comercio,
                monto=self.monto_bruto,
                descuento=self.descuento,
            )
        )

    def rechazar(self) -> None:
        self._pendiente_vigente(datetime.now(UTC))
        self._estado = EstadoTransaccion.RECHAZADA

    def expirar(self) -> None:
        if self._estado is EstadoTransaccion.PENDIENTE_CONFIRMACION:
            self._estado = EstadoTransaccion.EXPIRADA

    def anular(self, *, motivo: str, ventana_minutos: int, es_admin: bool) -> None:
        if self._estado is not EstadoTransaccion.APLICADA:
            raise TransicionCanjeInvalida("Solo se anula una operación aplicada.")
        ahora = datetime.now(UTC)
        base = self.confirmada_en or self.creada_en
        dentro_de_ventana = ahora <= base + timedelta(minutes=ventana_minutos)
        if not dentro_de_ventana and not es_admin:
            raise FueraDeVentanaAnulacion(
                "Fuera de la ventana de anulación: solo un administrador del comercio puede."
            )
        self._estado = EstadoTransaccion.ANULADA
        self.motivo_anulacion = motivo
        self.record_event(
            CanjeAnulado(
                id_transaccion=str(self.id),
                id_persona=self.id_persona,
                id_comercio=self.id_comercio,
                motivo=motivo,
                fuera_de_ventana=not dentro_de_ventana,
            )
        )

    def calificar(self, estrellas: int) -> None:
        self.calificacion = max(1, min(5, estrellas))

    def abrir_disputa(self, motivo: str) -> None:
        # "Esto no está bien": abre un caso con el municipio como árbitro (§08.4).
        self.en_disputa = True
        self.record_event(
            DisputaAbierta(
                id_transaccion=str(self.id),
                id_persona=self.id_persona,
                id_comercio=self.id_comercio,
                motivo=motivo,
            )
        )
