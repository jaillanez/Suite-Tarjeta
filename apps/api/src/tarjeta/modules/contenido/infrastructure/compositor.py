"""Compositor de piezas con PIL (§11.5, §11.6).

Recorta el fondo al formato, superpone el texto de la promoción (porcentaje/vigencia/nombre) con
tipografía controlada —nunca lo escribe la IA— y, si la imagen fue generada por IA, agrega una
marca de agua discreta y un metadato de origen. El número que se dibuja es SIEMPRE el de la
promoción: no hay forma de que la pieza muestre otro.
"""

from __future__ import annotations

from io import BytesIO

from PIL import Image, ImageDraw, ImageFont, ImageOps
from PIL.PngImagePlugin import PngInfo

from tarjeta.modules.contenido.domain.pieza import Superposicion
from tarjeta.modules.contenido.domain.plantillas import Plantilla
from tarjeta.modules.contenido.domain.tipos import TAMANOS, FormatoPieza

MARCA_AGUA = "Imagen generada por IA"


def _hex(color: str) -> tuple[int, int, int]:
    c = color.lstrip("#")
    return (int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16))


def _fuente(tam: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    try:
        return ImageFont.load_default(size=tam)
    except TypeError:  # pragma: no cover - Pillow viejo sin size
        return ImageFont.load_default()


class CompositorPIL:
    def componer(
        self,
        *,
        fondo: bytes,
        superposicion: Superposicion,
        plantilla: Plantilla,
        formato: FormatoPieza,
        con_marca_agua: bool,
    ) -> bytes:
        ancho, alto = TAMANOS[formato]
        base = Image.open(BytesIO(fondo)).convert("RGB")
        img = ImageOps.fit(base, (ancho, alto))
        draw = ImageDraw.Draw(img)
        acento = _hex(plantilla.color_acento)
        texto = _hex(plantilla.color_texto)

        # Banda inferior para dar contraste al texto controlado.
        banda_alto = max(90, alto // 4)
        draw.rectangle([0, alto - banda_alto, ancho, alto], fill=_hex(plantilla.color_fondo))

        margen = max(16, ancho // 30)
        y = alto - banda_alto + margen
        draw.text((margen, y), superposicion.porcentaje, fill=acento, font=_fuente(alto // 12))
        draw.text(
            (margen, y + alto // 10),
            superposicion.nombre,
            fill=texto,
            font=_fuente(alto // 26),
        )
        draw.text(
            (margen, y + alto // 10 + alto // 22),
            superposicion.vigencia,
            fill=texto,
            font=_fuente(alto // 34),
        )

        info = PngInfo()
        info.add_text("origen", "IA" if con_marca_agua else "FOTO_PROPIA")
        if con_marca_agua:
            # Marca de agua discreta arriba a la derecha (§11.6).
            fuente_wm = _fuente(max(14, alto // 45))
            caja = draw.textbbox((0, 0), MARCA_AGUA, font=fuente_wm)
            draw.text(
                (ancho - (caja[2] - caja[0]) - margen, margen),
                MARCA_AGUA,
                fill=acento,
                font=fuente_wm,
            )

        out = BytesIO()
        img.save(out, format="PNG", pnginfo=info)
        return out.getvalue()
