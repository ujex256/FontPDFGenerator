import traceback
import time
import base64
import enum
from io import BytesIO
from os import listdir
from typing import Optional

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import utils
import expressions as exp
import im_conv
import colors


app = FastAPI()
DEBUG = True


class ColorPDFResponse(BaseModel):
    color: str
    base64: str


class FontPDFResponse(BaseModel):
    font_url: str
    weight: str | None = None
    base64: str
    color: str
    dl_time: float


class FileType(str, enum.Enum):
    PDF = "pdf"
    PNG = "png"


@app.middleware("http")
async def add_process_time(req, call_next):
    s = time.perf_counter()
    try:
        resp = await call_next(req)
    except Exception as e:
        if DEBUG:
            raise e
        else:
            content = {
                "msg": traceback.format_exception_only(type(e), e)[0],
                "id": "UNKNOWN_ERROR",
            }
            resp = JSONResponse(content, status.HTTP_500_INTERNAL_SERVER_ERROR)
    process = time.perf_counter() - s
    resp.headers["X-Process-Time"] = str(process)
    return resp


@app.get("/color/{filetype}", status_code=status.HTTP_200_OK)
def generate_color_pdf(filetype: str, width: int, height: int, color: str):
    filetype = filetype.lower()
    if not colors.is_color(color):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"msg": "Please specify a valid color."},
        )

    svg = utils.generate_color_svg(size=[width, height], color=color)

    if filetype == "pdf":
        d = im_conv.svg2pdf(svg)
    elif filetype == "png":
        d = im_conv.svg2png(svg, 72)
    decoded = base64.b64encode(d)
    return ColorPDFResponse(color=color, base64=decoded)


@app.get("/font/{filetype}", status_code=status.HTTP_200_OK)
def generate_font_pdf(
    filetype: FileType,
    fontname: str,
    text: str,
    color: str = "black",
    bg_color: str = "white",
    weight: Optional[str] = None,
    dpi: int = 72,
):
    filetype = filetype.lower()
    if not utils.is_url(fontname):
        fontname = f"https://fonts.google.com/download?family={fontname}"
    if not all(colors.is_color(i) for i in [color, bg_color]):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"msg": "Please specify a valid color."},
        )

    try:
        id = None
        code = None
        font = utils.download_font(fontname, weight)
    except exp.InvalidUrlError:
        msg = "invalid url"
        id = "INVALID_URL"
    except exp.DownloadFailed as e:
        msg = "Download failed."
        id = "DOWNLOAD_FAILED"
        code = e.args[1]
    except exp.FontNotFoundError:
        msg = "Font is not found."
        id = "FONT_NOT_FOUND"
    except exp.WeightNotFoundError:
        msg = "Weight is no found."
        id = "WEIGHT_NOT_FOUND"
    finally:
        if code:
            return JSONResponse(
                {"msg": msg, "returned_status_code": code, "id": id},
                status.HTTP_400_BAD_REQUEST,
            )
        elif id is not None:
            return JSONResponse({"msg": msg, "id": id}, status.HTTP_400_BAD_REQUEST)

    font_path = font["font"]
    if bg_color == "none" and filetype != "png":
        bg_color = "white"

    svg = utils.generate_font_svg(BytesIO(font_path), text, 32, color, bg_color)

    if filetype == "pdf":
        d = im_conv.svg2pdf(svg)
    elif filetype == "png":
        d = im_conv.svg2png(svg, dpi)
        if bg_color == "none":
            img = im_conv.add_alpha_channel(im_conv.bytes2img(d))
            d = im_conv.img2bytes(img)
    decoded = base64.b64encode(d)
    return FontPDFResponse(
        font_url=fontname, weight=weight, base64=decoded,
        color=color, dl_time=font["download_time"]
    )


@app.get("/debug/ls")
@app.get("/debug/ls/{path}")
def file_tree(path: str = "."):
    try:
        return {"result": listdir(path)}
    except FileNotFoundError:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"msg": "path is not found."},
        )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", port=8000, reload=True)
