import traceback
import uuid
from os import listdir
from os.path import getsize
from time import time
from typing import Optional

from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

import utils
import expressions as exp
import im_conv
import colors


app = FastAPI()


@app.get("/color/{filetype}", status_code=status.HTTP_200_OK)
def _generate_color_pdf(filetype: str, width: int, height: int, color: str):
    start = time()
    filetype = filetype.lower()
    response = {
        "color": color,
        "size": f"{width}x{height}",
        "filesize": 0,
        "base64": "",
        "time": 0,
    }
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
        utils.svg2pdf(svg_path, export_path)
    elif filetype == "png":
        utils.svg2png(svg_path, export_path, 50)
    response["base64"] = utils.get_base64(export_path)
    response["filesize"] = getsize(export_path)
    response["time"] = time() - start
    return response


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
    response = {
        "font": fontname,
        "base64": "",
        "color": color,
        "weight": weight,
        "dl_time": None,
    }
    filetype = filetype.lower()

    try:
        id = None
        font_path = utils.download_font(fontname, iszip, weight)
    except exp.DownloadFailed:
        msg = "Download failed."
        id = "DOWNLOAD_FAILED"
    except exp.FontNotFoundError:
        msg = "Font is not found."
        id = "FONT_NOT_FOUND"
    except exp.WeightNotFoundError:
        msg = "Weight is no found."
        id = "WEIGHT_NOT_FOUND"
    finally:
        if id is not None:
            return JSONResponse({"msg": msg, "id": id}, status.HTTP_400_BAD_REQUEST)

    if isinstance(font_path, dict):
        response["dl_time"] = font_path["download_time"]
        font_path = font_path["path"]
    if isinstance(font_path, list):
        response["weight_list"] = font_path
        response["selected_weight"] = font_path[0]
        font_path = font_path[0]


    file_name = uuid.uuid4()
    svg_path = f"/tmp/{file_name}.svg"
    export_path = f"/tmp/{file_name}.{filetype}"
    utils.generate_font_svg(font_path, text, 32, svg_path, color)

    try:
        if filetype == "pdf":
            im_conv.svg2pdf(svg_path, export_path)
        elif filetype == "png":
            im_conv.svg2png(svg_path, export_path, dpi)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"msg": traceback.format_exception_only((type(e), e))[0][:-2]},
        )
    response["base64"] = utils.get_base64(export_path)
    response["filesize"] = getsize(export_path)
    response["time"] = time() - start
    return response


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
