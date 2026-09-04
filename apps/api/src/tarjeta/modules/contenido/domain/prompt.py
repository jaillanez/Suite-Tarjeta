"""Composición del prompt final (§11.4) con los guardarraíles fijos (§11.6).

El pedido final combina cuatro partes: la idea del comerciante tal como la escribió, datos
estructurados de la promoción, la plantilla de marca del programa y las restricciones fijas de
seguridad. Las restricciones son SIEMPRE las mismas y el comerciante no las puede ver ni cambiar.
"""

from __future__ import annotations

# §11.6: guardarraíles fijos, no configurables por el comerciante y no visibles para él.
RESTRICCIONES_FIJAS = (
    "Restricciones obligatorias: no incluir personas identificables ni rostros realistas; "
    "no incluir marcas, logos ni personajes de terceros; generar SOLO fondos, ambientes y "
    "composiciones (no retratar el producto concreto que vende el comercio); contenido apto para "
    "todo público. La imagen es un fondo: los textos y números se superponen aparte."
)


def componer_prompt(
    idea: str,
    *,
    rubro: str,
    nombre_fantasia: str,
    mecanica: str,
    estilo_plantilla: str,
) -> str:
    """Arma el prompt final. La idea del comerciante va tal cual; las restricciones, siempre."""
    partes = [
        f"Idea del comercio: {idea.strip()}",
        f"Contexto: rubro {rubro}, comercio '{nombre_fantasia}', mecánica {mecanica}.",
        f"Estilo de marca del programa: {estilo_plantilla}.",
        RESTRICCIONES_FIJAS,
    ]
    return "\n".join(partes)
