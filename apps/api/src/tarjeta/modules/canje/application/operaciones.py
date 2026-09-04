"""Casos de uso del canje: iniciar, confirmar, anular, disputar, cierre de turno (§08)."""

from __future__ import annotations

from datetime import UTC, datetime

from tarjeta.modules.canje.domain.descuento import calcular_descuento
from tarjeta.modules.canje.domain.errors import ConfirmadorInvalido, MontoInvalido
from tarjeta.modules.canje.domain.ports import ResumenTurno
from tarjeta.modules.canje.domain.transaccion import (
    Confirmador,
    Transaccion,
    ViaCanje,
)
from tarjeta.shared.domain.errors import NotFoundError
from tarjeta.shared.domain.types import EntityId

from .deps import CanjePuertos


def formato_comprobante(prefijo: str, numero: int) -> str:
    return f"{prefijo}-{numero:09d}"


class IniciarOperacion:
    def __init__(
        self, puertos: CanjePuertos, *, prefijo_comprobante: str, ttl_confirmacion_seg: int
    ) -> None:
        self.p = puertos
        self.prefijo = prefijo_comprobante
        self.ttl = ttl_confirmacion_seg

    async def ejecutar(
        self,
        *,
        id_persona: str,
        nivel: str,
        id_comercio: str,
        id_sucursal: str,
        id_cajero: str,
        id_promocion: str | None,
        mecanica: str | None,
        valor: int,
        monto: int,
        via: ViaCanje,
        clave_idempotencia: str,
        geo_lat: float | None = None,
        geo_lon: float | None = None,
        distancia_m: float | None = None,
    ) -> Transaccion:
        if monto <= 0:
            raise MontoInvalido("El monto debe ser mayor a cero.")
        # §08.4: misma clave => misma operación (no se duplica el descuento).
        existente = await self.p.transacciones.por_idempotencia(clave_idempotencia)
        if existente is not None:
            return existente

        descuento = calcular_descuento(mecanica, valor, monto) if id_promocion and mecanica else 0
        hoy = datetime.now(UTC).date()
        if id_promocion:
            # Reserva los tres topes; lanza TopeAgotado si no hay cupo.
            await self.p.reserva.reservar(id_promocion, id_persona, hoy)

        numero = formato_comprobante(self.prefijo, await self.p.secuencia.siguiente())
        t = Transaccion.crear(
            numero_comprobante=numero,
            id_persona=id_persona,
            nivel_aplicado=nivel,
            id_comercio=id_comercio,
            id_sucursal=id_sucursal,
            id_cajero=id_cajero,
            id_promocion=id_promocion,
            monto_bruto=monto,
            descuento=descuento,
            via=via,
            clave_idempotencia=clave_idempotencia,
            ttl_confirmacion_seg=self.ttl,
            geo_lat=geo_lat,
            geo_lon=geo_lon,
            distancia_m=distancia_m,
        )
        await self.p.transacciones.agregar(t)
        await self.p.outbox.escribir(t.pull_events())
        await self.p.uow.commit()
        return t


class DecidirOperacion:
    """Confirmar / rechazar la operación pendiente (§08.3)."""

    def __init__(self, puertos: CanjePuertos) -> None:
        self.p = puertos

    async def _cargar(self, id_transaccion: str) -> Transaccion:
        t = await self.p.transacciones.obtener(EntityId.from_str(id_transaccion))
        if t is None:
            raise NotFoundError("Operación inexistente.")
        return t

    async def confirmar(
        self, *, id_transaccion: str, por: Confirmador, id_actor: str | None = None
    ) -> Transaccion:
        t = await self._cargar(id_transaccion)
        # Si confirma el ciudadano, debe ser el titular de la operación.
        if por is Confirmador.CIUDADANO and id_actor is not None and id_actor != t.id_persona:
            raise ConfirmadorInvalido("Solo el titular puede confirmar su operación.")
        t.confirmar(por=por)
        await self.p.transacciones.guardar(t)
        await self.p.outbox.escribir(t.pull_events())
        await self.p.uow.commit()
        return t

    async def rechazar(self, *, id_transaccion: str, id_actor: str | None = None) -> None:
        t = await self._cargar(id_transaccion)
        if id_actor is not None and id_actor != t.id_persona:
            raise ConfirmadorInvalido("Solo el titular puede rechazar su operación.")
        t.rechazar()
        await self._liberar(t)
        await self.p.transacciones.guardar(t)
        await self.p.uow.commit()

    async def _liberar(self, t: Transaccion) -> None:
        if t.id_promocion:
            await self.p.reserva.liberar(t.id_promocion, t.id_persona, t.creada_en.date())


class ExpirarPendientes:
    def __init__(self, puertos: CanjePuertos) -> None:
        self.p = puertos

    async def ejecutar(self) -> int:
        vencidas = await self.p.transacciones.vencidas(datetime.now(UTC))
        for t in vencidas:
            t.expirar()
            if t.id_promocion:
                await self.p.reserva.liberar(t.id_promocion, t.id_persona, t.creada_en.date())
            await self.p.transacciones.guardar(t)
        await self.p.uow.commit()
        return len(vencidas)


class AnularOperacion:
    def __init__(self, puertos: CanjePuertos, *, ventana_minutos: int) -> None:
        self.p = puertos
        self.ventana = ventana_minutos

    async def ejecutar(self, *, id_transaccion: str, motivo: str, es_admin: bool) -> None:
        t = await self.p.transacciones.obtener(EntityId.from_str(id_transaccion))
        if t is None:
            raise NotFoundError("Operación inexistente.")
        t.anular(motivo=motivo, ventana_minutos=self.ventana, es_admin=es_admin)
        if t.id_promocion:
            await self.p.reserva.liberar(t.id_promocion, t.id_persona, t.creada_en.date())
        await self.p.transacciones.guardar(t)
        await self.p.outbox.escribir(t.pull_events())
        await self.p.uow.commit()


class GestionCiudadano:
    """Acciones del ciudadano sobre su operación: disputa, calificación, historial."""

    def __init__(self, puertos: CanjePuertos) -> None:
        self.p = puertos

    async def _cargar_propia(self, id_transaccion: str, id_persona: str) -> Transaccion:
        t = await self.p.transacciones.obtener(EntityId.from_str(id_transaccion))
        if t is None or t.id_persona != id_persona:
            raise NotFoundError("Operación inexistente.")
        return t

    async def disputar(self, *, id_transaccion: str, id_persona: str, motivo: str) -> None:
        t = await self._cargar_propia(id_transaccion, id_persona)
        t.abrir_disputa(motivo)
        await self.p.transacciones.guardar(t)
        await self.p.outbox.escribir(t.pull_events())
        await self.p.uow.commit()

    async def calificar(self, *, id_transaccion: str, id_persona: str, estrellas: int) -> None:
        t = await self._cargar_propia(id_transaccion, id_persona)
        t.calificar(estrellas)
        await self.p.transacciones.guardar(t)
        await self.p.uow.commit()

    async def historial(self, *, id_persona: str, limite: int = 100) -> list[Transaccion]:
        return await self.p.transacciones.historial_de_persona(id_persona, limite)


class ResumenCajero:
    def __init__(self, puertos: CanjePuertos) -> None:
        self.p = puertos

    async def ejecutar(self, *, id_cajero: str, desde: datetime) -> ResumenTurno:
        return await self.p.transacciones.resumen_cajero(id_cajero, desde)
