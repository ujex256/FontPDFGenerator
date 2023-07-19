import base64
import zipfile
import io
import re
from collections import deque
from os import sep
from textwrap import dedent
from typing import Optional

import requests
import expressions
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont


def generate_color_svg(size: list, color: str) -> None:
    base_svg = dedent(
        f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size[0]} {size[1]}">
            <rect width="{size[0]}" height="{size[1]}" fill="{color}" />
        </svg>"""
    )
    return base_svg


def get_base64(path: str):
    with open(path, "rb") as file:
        return base64.b64encode(file.read())


def download_font(url: str, weight: Optional[str] = None):
    result = {
        "path": "",
        "download_time": 0
    }
    if weight is not None:
        weight = weight.lower()

    # ダウンロード
    if is_url(url):
        resp = requests.get(url)
    else:
        raise expressions.InvalidUrlError()
    if not resp.ok:
        raise expressions.DownloadFailed("download failed.", resp.status_code)
    result["download_time"] = resp.elapsed.total_seconds()

    if resp.content[:2] == b"PK":  # is_zip
        # zipの展開
        z = zipfile.ZipFile(io.BytesIO(resp.content))

        REGEX = r".*\.(ot|tt)f"
        candidates = [i for i in z.namelist() if re.match(REGEX, i)]
        if not candidates:
            raise expressions.FontNotFoundError("Font not found")

        if weight is not None:
            candidates = [i for i in candidates if weight in i.lower()]
            if len(candidates) == 0:
                raise expressions.WeightNotFoundError("weight not found.")

        levels = [str(i).count(sep) for i in candidates]
        top_level = min(levels)
        top_level_files = [candidates[i] for i, l in enumerate(levels) if l == top_level]
        if len(top_level_files) > 1:
            result["path"] = list(map(str, top_level_files))
        else:
            result["path"] = z.open(top_level_files[0], "r").read()
        z.close()
    else:
        result["path"] = resp.content
    return result


def generate_font_svg(
    fontpath: str,
    text: str,
    size: int,
    color: str = "black",
    bg_color: str = "white"
) -> None:

    font = TTFont(fontpath)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    hhea = font["hhea"]
    scale = round(size / 750, 3)  # default: 750pt
    font_height = int((hhea.ascender - hhea.descender + hhea.lineGap) * scale)
    text_width = 0
    x = 0

    def get_glyph(glyph_set, cmap, char):
        try:
            glyph_name = cmap[ord(char)]
        except KeyError:
            glyph_name = cmap[63]
        return glyph_set[glyph_name]

    g_list = deque()  # 一応高速化?
    for char in text:
        # グリフのアウトラインを SVGPathPen でなぞる
        glyph = get_glyph(glyph_set, cmap, char)
        svg_path_pen = SVGPathPen(glyph_set)
        glyph.draw(svg_path_pen)

        outline = svg_path_pen.getCommands()
        content = f"""
            <g transform="translate({int(x)}, {font_height}) scale(1, -1) scale({scale})">
                <path d="{outline}" fill="{color}"/>
            </g>"""
        g_list.append(content)
        text_width += glyph.width
        x = text_width * scale

    font.close()
    result = f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0, 0, {int(x+5)}, {font_height+15}">
            <rect width="100%" height="100%" fill="{bg_color}"/>
            {"".join(g_list)}
        </svg>"""
    return dedent(result)


def is_url(d: str) -> bool:
    return bool(re.match(r"https?://[\w!?/+\-_~;.,*&@#$%()'[\]]+", d))
