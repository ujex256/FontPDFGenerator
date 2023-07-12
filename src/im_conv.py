from reportlab.graphics import renderPDF, renderPM
from svglib.svglib import svg2rlg


def svg2pdf(filepath: str, out: str) -> None:
    draw_data = svg2rlg(filepath)
    renderPDF.drawToFile(draw_data, out)


def svg2png(filepath: str, out: str, dpi: int) -> None:
    draw_data = svg2rlg(filepath)
    renderPM.drawToFile(draw_data, out, fmt="PNG", dpi=dpi)
