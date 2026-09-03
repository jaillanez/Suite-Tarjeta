"""Servicio de parametría: lee/escribe parámetros del programa con auditoría (§5.5)."""

from __future__ import annotations

from tarjeta.modules.gobierno.domain.auditoria import RegistroAuditoria
from tarjeta.modules.gobierno.domain.parametro import CATALOGO, validar_valor

from .deps import GobiernoPuertos


class ParametriaService:
    def __init__(self, puertos: GobiernoPuertos) -> None:
        self.p = puertos

    async def obtener(self, clave: str) -> int:
        valor = await self.p.parametros.obtener(clave)
        if valor is not None:
            return valor
        return CATALOGO[clave].default

    async def todos(self) -> dict[str, int]:
        guardados = await self.p.parametros.todos()
        return {clave: guardados.get(clave, d.default) for clave, d in CATALOGO.items()}

    async def cambiar(self, *, clave: str, valor: int, actor: str, rol: str, motivo: str) -> None:
        validar_valor(clave, valor)  # rango inválido -> ValidationError (dominio)
        anterior = await self.obtener(clave)
        await self.p.parametros.guardar(clave, valor)
        await self.p.auditoria.agregar(
            RegistroAuditoria.crear(
                accion="parametria:editar",
                entidad="parametro",
                id_entidad=clave,
                id_persona_actor=actor,
                rol_actor=rol,
                valor_anterior={"valor": anterior},
                valor_nuevo={"valor": valor},
                motivo=motivo,
            )
        )
        await self.p.uow.commit()
