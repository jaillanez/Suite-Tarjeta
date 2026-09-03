"""Parámetros del programa editables sin desarrollo (§5.5)."""

from __future__ import annotations

from dataclasses import dataclass

from .errors import ParametroFueraDeRango


@dataclass(frozen=True, slots=True)
class DefinicionParametro:
    clave: str
    descripcion: str
    default: int
    minimo: int
    maximo: int


# Catálogo de parámetros enteros con su rango válido (§5.5).
CATALOGO: dict[str, DefinicionParametro] = {
    d.clave: d
    for d in [
        DefinicionParametro(
            "puntos_vencimiento_meses", "Vencimiento de puntos (meses)", 24, 1, 120
        ),
        DefinicionParametro("grupo_max_miembros", "Máximo de miembros del grupo", 6, 1, 20),
        DefinicionParametro(
            "grupo_cooldown_dias", "Cooldown para reingresar a un grupo", 90, 0, 365
        ),
        DefinicionParametro("grupo_max_altas_anuales", "Altas de grupo por año", 4, 0, 50),
        DefinicionParametro("grupo_max_bajas_anuales", "Bajas de grupo por año", 4, 0, 50),
        DefinicionParametro(
            "cambio_modo_billetera_dias", "Cambio de modo de billetera (días)", 180, 0, 365
        ),
        DefinicionParametro("anulacion_ventana_minutos", "Ventana de anulación (min)", 15, 1, 240),
        DefinicionParametro(
            "sesion_municipal_timeout_minutos", "Timeout sesión municipal (min)", 10, 1, 60
        ),
        DefinicionParametro(
            "cuota_ia_mensual_por_comercio", "Cuota IA mensual por comercio", 10, 0, 1000
        ),
    ]
}


def validar_valor(clave: str, valor: int) -> None:
    definicion = CATALOGO.get(clave)
    if definicion is None:
        from .errors import ParametroInexistente

        raise ParametroInexistente(f"Parámetro desconocido: {clave}")
    if not definicion.minimo <= valor <= definicion.maximo:
        raise ParametroFueraDeRango(
            f"{clave} debe estar entre {definicion.minimo} y {definicion.maximo}."
        )
