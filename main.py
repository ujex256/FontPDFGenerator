import traceback
import uuid
from os import listdir
from os.path import getsize
from time import time
from typing import Optional

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from utils import *
from colors import CSS_COLORS

app = FastAPI()


@app.get("/color/{filetype}", status_code=status.HTTP_200_OK)
def _generate_color_pdf(filetype: str, width: int, height: int, color: str):
    start = time()
    filetype = filetype.lower()
    responce = {
        "color": color,
        "size": f"{width}x{height}",
        "filesize": 0,
        "base64": "",
        "time": 0,
    }
    if (color.lower() not in CSS_COLORS) and ("#" not in color):
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"msg": "Please specify a valid color."},
        )

    file_name = uuid.uuid4()
    svg_path = f"/tmp/{file_name}.svg"
    export_path = f"/tmp/{file_name}.{filetype}"
    generate_color_svg(size=[width, height], color=color, out=svg_path)

    if filetype == "pdf":
        svg2pdf(svg_path, export_path)
    elif filetype == "png":
        svg2png(svg_path, export_path, 50)
    responce["base64"] = get_base64(export_path)
    responce["filesize"] = getsize(export_path)
    responce["time"] = time() - start
    return responce


@app.get("/font/{filetype}", status_code=status.HTTP_200_OK)
def _generate_font_pdf(
    filetype: str,
    fontname: str,
    text: str,
    color: str = "black",
    iszip: bool = True,
    weight: Optional[str] = None,
    dpi: int = 72,
):
    start = time()
    responce = {
        "font": fontname,
        "base64": "",
        "color": color,
        "weight": weight,
        "dl_time": None,
    }
    filetype = filetype.lower()

    font_path = download_font(fontname, iszip, weight)
    if isinstance(font_path, dict):
        responce["dl_time"] = font_path["download_time"]
        font_path = font_path["path"]
    if isinstance(font_path, list):
        responce["weight_list"] = font_path
        responce["selected_weight"] = font_path[0]
        font_path = font_path[0]
    if "error" in font_path:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": "Download failed.", "status_code": font_path[6:]},
        )

    file_name = uuid.uuid4()
    svg_path = f"/tmp/{file_name}.svg"
    export_path = f"/tmp/{file_name}.{filetype}"
    generate_font_svg(font_path, text, 32, svg_path, color)

    try:
        if filetype == "pdf":
            svg2pdf(svg_path, export_path)
        elif filetype == "png":
            svg2png(svg_path, export_path, dpi)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": traceback.format_exception_only((type(e), e))[0][:-2]},
        )
    responce["base64"] = get_base64(export_path)
    responce["filesize"] = getsize(export_path)
    responce["time"] = time() - start
    return responce


@app.get("/debug/ls")
@app.get("/debug/ls/{path}")
def _file_tree(path: str = "."):
    try:
        return {"result": listdir(path)}
    except:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"msg": "path is not found."},
        )
