from io import BytesIO

from reportlab.graphics import renderPDF, renderPM
from svglib.svglib import svg2rlg


def svg2pdf(svg: str) -> bytes:
    draw_data = svg2rlg(BytesIO(svg.encode()))
    return renderPDF.drawToString(draw_data)


def svg2png(svg: str, dpi: int) -> bytes:
    draw_data = svg2rlg(BytesIO(svg.encode()))
    return renderPM.drawToString(draw_data, fmt="PNG", dpi=dpi)
