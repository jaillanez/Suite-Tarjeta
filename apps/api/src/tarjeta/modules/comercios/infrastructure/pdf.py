"""PDF imprimible del QR de establecimiento (§06.3)."""

from __future__ import annotations

from io import BytesIO

from reportlab.graphics import renderPDF
from reportlab.graphics.barcode import qr
from reportlab.graphics.shapes import Drawing
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.pdfgen import canvas


def pdf_establecimiento(*, contenido_qr: str, titulo: str, subtitulo: str) -> bytes:
    """Devuelve un PDF A4 con el QR fijo de la sucursal, listo para imprimir."""
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    ancho, alto = A4

    c.setFont("Helvetica-Bold", 20)
    c.drawCentredString(ancho / 2, alto - 4 * cm, titulo)
    c.setFont("Helvetica", 13)
    c.drawCentredString(ancho / 2, alto - 5 * cm, subtitulo)

    widget = qr.QrCodeWidget(contenido_qr)
    bounds = widget.getBounds()
    w = bounds[2] - bounds[0]
    h = bounds[3] - bounds[1]
    lado = 10 * cm
    d = Drawing(lado, lado, transform=[lado / w, 0, 0, lado / h, 0, 0])
    d.add(widget)
    renderPDF.draw(d, c, (ancho - lado) / 2, alto - 17 * cm)

    c.setFont("Helvetica", 10)
    c.drawCentredString(ancho / 2, alto - 18.5 * cm, "Escaneá para operar en esta sucursal")
    c.showPage()
    c.save()
    return buffer.getvalue()
