from io import BytesIO

from PIL import Image
from PIL.PngImagePlugin import PngImageFile
from reportlab.graphics import renderPDF, renderPM
from svglib.svglib import svg2rlg


def svg2pdf(svg: str) -> bytes:
    draw_data = svg2rlg(BytesIO(svg.encode()))
    return renderPDF.drawToString(draw_data)


def svg2png(svg: str, dpi: int) -> bytes:
    draw_data = svg2rlg(BytesIO(svg.encode()))
    return renderPM.drawToString(draw_data, fmt="PNG", dpi=dpi)


def bytes2img(img: bytes):
    return Image.open(BytesIO(img))


def add_alpha_channel(img: PngImageFile):
    _img = img.copy().convert("RGBA")
    data = _img.getdata()

    new = []
    for i in data:
        if all(j >= 240 for j in i[:3]):  # 平均値だと誤判定が生まれる可能性
            new.append((255, 255, 255, 0))
        else:
            new.append(i)
    _img.putdata(new)

    img_bytes = BytesIO()
    _img.save(img_bytes, format="PNG")
    img_bytes = img_bytes.getvalue()
    return img_bytes
