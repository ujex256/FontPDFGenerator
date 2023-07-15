import traceback
import uuid
import time
import base64
from os import listdir
from os.path import getsize
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
    size: int


class FontPDFResponse(BaseModel):
    font_url: str
    weight: str | None = None
    base64: str
    color: str
    dl_time: float


@app.middleware("http")
async def add_process_time(req, call_next):
    s = time.perf_counter()
    try:
        resp = await call_next(req)
    except Exception as e:
        if DEBUG:
            raise e
        else:
            content = {"msg": traceback.format_exception_only((type(e), e))[0][:-2],
                       "id": "UNKNOWN_ERROR"}
            resp = JSONResponse(content, status.HTTP_500_INTERNAL_SERVER_ERROR)
    process = time.perf_counter() - s
    resp.headers["X-Process-Time"] = str(process)
    return resp


@app.get("/color/{filetype}", status_code=status.HTTP_200_OK)
def _generate_color_pdf(filetype: str, width: int, height: int, color: str):
    filetype = filetype.lower()
    if not colors.is_color(color):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"msg": "Please specify a valid color."},
        )

    file_name = uuid.uuid4()
    svg_path = f"/tmp/{file_name}.svg"
    export_path = f"/tmp/{file_name}.{filetype}"
    utils.generate_color_svg(size=[width, height], color=color, out=svg_path)

    if filetype == "pdf":
        im_conv.svg2pdf(svg_path, export_path)
    elif filetype == "png":
        im_conv.svg2png(svg_path, export_path, 50)
    return ColorPDFResponse(color=color, base64=utils.get_base64(export_path),
                            size=getsize(export_path))


@app.get("/font/{filetype}", status_code=status.HTTP_200_OK)
def _generate_font_pdf(
    filetype: str,
    fontname: str,
    text: str,
    color: str = "black",
    bg_color: str = "white",
    weight: Optional[str] = None,
    dpi: int = 72,
):
    response = {
        "font": fontname,
        "base64": "",
        "color": color,
        "weight": weight,
        "dl_time": None,
    }
    filetype = filetype.lower()
    if not utils.is_url(fontname):
        fontname = f"https://fonts.google.com/download?family={fontname}"

    try:
        id = None
        code = None
        font_path = utils.download_font(fontname, weight)
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
            return JSONResponse({"msg": msg, "returned_status_code": code, "id": id},
                                status.HTTP_400_BAD_REQUEST)
        elif id is not None:
            return JSONResponse({"msg": msg, "id": id}, status.HTTP_400_BAD_REQUEST)

    dl_time = font_path["download_time"]
    if isinstance(font_path, dict):
        font_path = font_path["path"]
    if isinstance(font_path, list):
        response["weight_list"] = font_path
        response["selected_weight"] = font_path[0]
        font_path = font_path[0]

    file_name = uuid.uuid4()
    svg_path = f"/tmp/{file_name}.svg"
    utils.generate_font_svg(font_path, text, 32, svg_path, color, bg_color=bg_color)

    if filetype == "pdf":
        d = im_conv.svg2pdf(svg_path)
    elif filetype == "png":
        d = im_conv.svg2png(svg_path, dpi)
    decoded = base64.b64encode(d)
    return FontPDFResponse(font_url=fontname, weight=weight,
                           base64=decoded,
                           color=color, dl_time=dl_time)


@app.get("/debug/ls")
@app.get("/debug/ls/{path}")
def _file_tree(path: str = "."):
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
