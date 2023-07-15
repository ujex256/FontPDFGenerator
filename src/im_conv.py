from reportlab.graphics import renderPDF, renderPM
from svglib.svglib import svg2rlg


def svg2pdf(filepath: str) -> None:
    draw_data = svg2rlg(filepath)
    return renderPDF.drawToString(draw_data)


def svg2png(filepath: str, dpi: int) -> None:
    draw_data = svg2rlg(filepath)
    return renderPM.drawToString(draw_data, fmt="PNG", dpi=dpi)
