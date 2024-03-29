import base64
import pathlib
import shutil
import uuid
from collections import deque
from os import sep
from textwrap import dedent
from typing import Optional

import requests
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.ttLib import TTFont
from svglib.svglib import svg2rlg


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

def download_font(url: str, zip: bool, weight: Optional[str] = None):
    result = {
        "path": "",
        "download_time": 0
    }
    if not weight is None:
        weight = weight.lower()
    # fontsフォルダに元々入っているならダウンロードしない
    if "http" in url and "://" in url:
        _url = url.split("?")[0]
        _url = _url.replace(".zip", "").split("/")
        KEYS = ["\\", "/", ":", "*", "?", '"', "<", ">", "|"]
        d = dict.fromkeys(KEYS, None)
        d = str.maketrans(d)
        _url = (_url[-2] + _url[-1]).translate(d)
        font_assets_dir = pathlib.Path(f"fonts/{_url}")
    else:
        font_assets_dir = pathlib.Path(f"fonts/{url.replace(' ', '-')}")
    if font_assets_dir.exists():
        assets = list(font_assets_dir.iterdir())
        if len(assets) > 1:
            if weight is None:
                return [str(i) for i in assets]
            else:
                try:
                    return [str(i) for i in assets if weight in i.name.lower()][0]
                except:
                    return "error:指定されたサイズが存在しない"
        else:
            return str(assets[0])

    # なかったらダウンロード
    filename = str(uuid.uuid4())
    if "http" in url and "://" in url:
        response = requests.get(url)
    else:
        response = requests.get(f"https://fonts.google.com/download?family={url}")
    if not (response.status_code >= 200 and response.status_code < 300):
        return f"error:{response.status_code}"
    result["download_time"] = response.elapsed.total_seconds()

    if zip:
        # zipの展開
        with open(f"/tmp/{filename}.zip", "wb") as f:
            f.write(response.content)
        unzipped_dir = pathlib.Path("/tmp", filename)
        shutil.unpack_archive(f"/tmp/{filename}.zip", str(unzipped_dir), "zip")

        # ディレクトリからファイルのパスを選ぶ
        candidates = list(unzipped_dir.rglob("*.[ot]tf"))
        if not candidates:
            return "error:ダウンロードしたzipにフォントが存在しない"  # そもそもフォントがない
        levels = [str(i).count(sep) for i in candidates]
        top_level = min(levels)
        top_level_files = [candidates[i] for i, l in enumerate(levels) if l == top_level]
        if len(top_level_files) > 1:
            if weight is None:
                result["path"] = list(map(str, top_level_files))
            else:
                filtered_path = [i for i in top_level_files if weight in i.name.lower()]
                x = len(filtered_path)
                if x == 0:
                    result["path"] = "error:ないんですけど()"
                elif x == 1:
                    result["path"] = str(filtered_path[0])
                else:
                    result["path"] = list(map(str, filtered_path))
        else:
            result["path"] = str(top_level_files[0])
    else:
        with open(f"/tmp/{filename}.ttf", "wb") as f:
            f.write(response.content)
        result["path"] = f"/tmp/{filename}.ttf"
    return result

def generate_font_svg(
        fontpath: str, text: str, size: int, out: str, color: str = "black"
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
        except:
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
            {"".join(g_list)}
        </svg>"""
    )
    with open(out, "w") as f:
        f.write(result)

def svg2pdf(filepath: str, out: str) -> None:
    from reportlab.graphics import renderPDF
    draw_data = svg2rlg(filepath)
    renderPDF.drawToFile(draw_data, out)

def svg2png(filepath: str, out: str, dpi: int) -> None:
    from reportlab.graphics import renderPM
    draw_data = svg2rlg(filepath)
    renderPM.drawToFile(draw_data, out, fmt="PNG", dpi=dpi)

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
