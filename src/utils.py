import base64
import pathlib
import shutil
import uuid
import re
from collections import deque
from os import sep
from textwrap import dedent
from typing import Optional

import requests
import expressions
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont


def generate_color_svg(size: list, color: str, out: str) -> None:
    base_svg = dedent(
        f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size[0]} {size[1]}">
            <rect width="{size[0]}" height="{size[1]}" fill="{color}" />
        </svg>"""
    )
    with open(out, "w", encoding="utf8") as file:
        file.write(base_svg)


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
    filename = str(uuid.uuid4())
    if is_url(url):
        resp = requests.get(url)
    else:
        raise expressions.DownloadFailed("invaild url")
    if not resp.ok:
        raise expressions.DownloadFailed("download failed.", resp.status_code)
    result["download_time"] = resp.elapsed.total_seconds()

    if resp.content[:2] == b"PK":  # is_zip
        # zipの展開
        with open(f"/tmp/{filename}.zip", "wb") as f:
            f.write(resp.content)
        unzipped_dir = pathlib.Path("/tmp", filename)
        shutil.unpack_archive(f"/tmp/{filename}.zip", str(unzipped_dir), "zip")

        # ディレクトリからファイルのパスを選ぶ
        candidates = list(unzipped_dir.rglob("*.[ot]tf"))
        if not candidates:
            raise expressions.FontNotFoundError("Font not found")

        if weight is not None:
            candidates = [i for i in candidates if weight in i.name.lower()]
            if len(candidates) == 0:
                raise expressions.WeightNotFoundError("weight not found.")

        levels = [str(i).count(sep) for i in candidates]
        top_level = min(levels)
        top_level_files = [candidates[i] for i, l in enumerate(levels) if l == top_level]
        if len(top_level_files) > 1:
            result["path"] = list(map(str, top_level_files))
        else:
            result["path"] = str(top_level_files[0])
    else:
        with open(f"/tmp/{filename}.ttf", "wb") as f:
            f.write(resp.content)
        result["path"] = f"/tmp/{filename}.ttf"
    return result


def generate_font_svg(
    fontpath: str,
    text: str,
    size: int,
    out: str,
    color: str = "black",
    bg_color: str = "white"
) -> None:

    font = TTFont(fontpath)
    glyph_set = font.getGlyphSet()
    cmap = font.getBestCmap()
    hhea = font["hhea"]
    scale = size / 750  # default: 750pt
    font_height = int((hhea.ascender - hhea.descender + hhea.lineGap) * scale)
    text_x = 0
    x = 0

    def get_glyph(glyph_set, cmap, char):
        try:
            glyph_name = cmap[ord(char)]
        except KeyError:
            glyph_name = cmap[33]
        return glyph_set[glyph_name]

    g_list = deque()  # 一応高速化?
    for char in text:
        # グリフのアウトラインを SVGPathPen でなぞる
        glyph = get_glyph(glyph_set, cmap, char)
        svg_path_pen = SVGPathPen(glyph_set)
        glyph.draw(svg_path_pen)

        width = glyph.width
        outline = svg_path_pen.getCommands()
        formatted_d = "".join([f" {c} " if c.isalpha() and i != 0 else c for i, c in enumerate(outline)])

        content = f"""
            <g transform="translate({int(x)}, {font_height}) scale(1, -1) scale({scale})">
                <path d="{formatted_d}" fill="{color}"/>
            </g>"""
        g_list.append(content)
        text_x += width
        x = text_x * scale

    font.close()
    result = dedent(
        f"""
        <svg xmlns="http://www.w3.org/2000/svg" viewBox="0, 0, {int(x+5)}, {font_height+15}">
            <rect width="100%" height="100%" fill="{bg_color}"/>
            {"".join(g_list)}
        </svg>"""
    )
    with open(out, "w") as f:
        f.write(result)


def is_url(d: str) -> bool:
    return bool(re.match(r"https?://[\w!?/+\-_~;.,*&@#$%()'[\]]+", d))


def return_replace(url):
    """デバッグ用"""
    url = url.split("?")[0]
    url = url.replace(".zip", "").split("/")
    KEYS = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
    d = dict.fromkeys(KEYS, None)
    d = str.maketrans(d)
    url = (url[-2] + url[-1]).translate(d)
    return url


if __name__ == "__main__":
    import time
    start = time.time()
    path = download_font("http://ymnk-design.com/wordpress/wp-content/themes/ymnkweb2018/font/fontdownload/pugnomincho_mini.zip", True)  # キャッシュされているならどちらでもok
    print(time.time()-start)
    if isinstance(path, dict):
        print(path["download_time"])
        path = path["path"]
        if isinstance(path, list):
            print("path:", path[0])
            generate_font_svg(path[0], "こんにちわ~Aa!'@:;", 32, "out.svg")
        else:
            print("path:", path)
            generate_font_svg(path, "こんにちわ~Aa!'@:;", 32, "out.svg")
    else:
        generate_font_svg(path, "こんにちわ~Aa!'@:;", 32, "out.svg")
