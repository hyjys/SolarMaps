"""조립 가이드 PDF 공용 헬퍼 (reportlab, A4). stand_guide/ · case_guide/ 의 build_pdf.py 가 쓴다.

필요: pip install reportlab pillow
그림은 각 가이드의 render_views.py(Blender)가 만든 투명 PNG + anchors.json(설명선 끝점).
"""
import json
import os

from PIL import Image
from reportlab.lib.colors import HexColor, black, white
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

pdfmetrics.registerFont(TTFont("KR", r"C:\Windows\Fonts\malgun.ttf"))
pdfmetrics.registerFont(TTFont("KRB", r"C:\Windows\Fonts\malgunbd.ttf"))

PW, PH = A4
MARGIN = 16 * mm
TW = PW - 2 * MARGIN
ACCENT = HexColor("#1f4e79")
GREY = HexColor("#555555")
LIGHT = HexColor("#eef3f8")

_CFG = {"img_dir": None, "anchors": {}, "running_title": ""}


def setup(img_dir, running_title):
    """그림 폴더와 머리글 오른쪽 문구를 정한다."""
    _CFG["img_dir"] = img_dir
    _CFG["running_title"] = running_title
    path = os.path.join(img_dir, "anchors.json")
    _CFG["anchors"] = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}


def blender_constants(py_path):
    """build_*.py 상단 상수만 실행해 dict 로 (Blender 모듈 import 줄은 뺀다)."""
    src = open(py_path, encoding="utf-8").read()
    src = "\n".join(l for l in src.split("FONT_PATHS")[0].splitlines()
                    if not l.startswith(("import bmesh", "import bpy", "from mathutils")))
    ns = {"__file__": py_path}
    exec(src, ns)
    return ns


# ---------------------------------------------------------------------
# 그림: 투명 여백 잘라내고 설명선 좌표 보정
# ---------------------------------------------------------------------
def load(name, pad=12):
    img_dir = _CFG["img_dir"]
    crop_dir = os.path.join(img_dir, "crop")
    os.makedirs(crop_dir, exist_ok=True)
    im = Image.open(os.path.join(img_dir, name + ".png")).convert("RGBA")
    W, H = im.size
    x0, y0, x1, y1 = im.getchannel("A").getbbox()
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(W, x1 + pad), min(H, y1 + pad)
    crop = im.crop((x0, y0, x1, y1))
    path = os.path.join(crop_dir, name + ".png")
    crop.save(path)
    pts = {}
    for key, u, v in _CFG["anchors"].get(name, {}).get("points", []):
        px, py = u * W, (1 - v) * H                     # 원본 픽셀 (좌상단 원점)
        pts[key] = ((px - x0) / (x1 - x0), 1 - (py - y0) / (y1 - y0))   # 잘린 그림 (좌하단 원점)
    return path, crop.size, pts


def draw_image(c, name, x, y, w=None, h=None, callouts=()):
    """(x, y) = 좌하단. w/h 중 하나만 주면 비율 유지, 둘 다 주면 그 상자 안에 맞춤.
    callouts: (앵커 키, 글, dx, dy) — 글 상자를 앵커에서 (dx, dy) pt 떨어진 곳에 둔다."""
    path, (iw, ih), pts = load(name)
    if w and h:
        s = min(w / iw, h / ih)
        dw, dh = iw * s, ih * s
        x, y = x + (w - dw) / 2, y + (h - dh) / 2
    elif w:
        dw, dh = w, w * ih / iw
    else:
        dw, dh = h * iw / ih, h
    c.drawImage(path, x, y, dw, dh, mask="auto")
    for key, text, dx, dy in callouts:
        u, v = pts[key]
        ax, ay = x + u * dw, y + v * dh
        callout(c, ax, ay, ax + dx, ay + dy, text)
    return dw, dh


def callout(c, ax, ay, lx, ly, text, size=9):
    tw = pdfmetrics.stringWidth(text, "KRB", size)
    bw, bh = tw + 8, size + 7
    bx, by = lx - bw / 2, ly - bh / 2
    ex = min(max(ax, bx), bx + bw)          # 선은 상자 가장자리에서 시작
    ey = min(max(ay, by), by + bh)
    c.setStrokeColor(black)
    c.setLineWidth(0.9)
    c.line(ex, ey, ax, ay)
    c.setFillColor(black)
    c.circle(ax, ay, 1.8, stroke=0, fill=1)
    c.setFillColor(white)
    c.roundRect(bx, by, bw, bh, 3, stroke=1, fill=1)
    c.setFillColor(black)
    c.setFont("KRB", size)
    c.drawCentredString(lx, by + 4.2, text)


# ---------------------------------------------------------------------
# 글
# ---------------------------------------------------------------------
def wrap(text, font, size, width):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for word in para.split(" "):
            cand = (cur + " " + word).strip()
            if pdfmetrics.stringWidth(cand, font, size) <= width:
                cur = cand
            else:
                if cur:
                    lines.append(cur)
                cur = word
        lines.append(cur)
    return lines


def paragraph(c, text, x, y, width, size=10, font="KR", lead=1.5, color=black, indent=0):
    """위에서 아래로. 다음 y 반환."""
    c.setFont(font, size)
    c.setFillColor(color)
    first = True
    for line in wrap(text, font, size, width - indent):
        c.drawString(x + (0 if first else indent), y - size, line)
        y -= size * lead
        first = False
    return y


def bullets(c, items, x, y, width, size=10, gap=3):
    for it in items:
        mark, body = "•", it
        if it[:1] in "①②③④⑤⑥⑦⑧⑨":
            mark, body = it[0], it[1:].strip()
        c.setFont("KRB", size)
        c.setFillColor(ACCENT)
        c.drawString(x, y - size, mark)
        y = paragraph(c, body, x + 14, y, width - 14, size)
        y -= gap
    return y


def footer(c, page):
    c.setFillColor(GREY)
    c.setFont("KR", 8)
    c.drawCentredString(PW / 2, 9 * mm, f"- {page} -")


def header(c, step, title, page):
    c.setFillColor(ACCENT)
    c.rect(0, PH - 22 * mm, PW, 22 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("KRB", 18)
    c.drawString(MARGIN, PH - 14.5 * mm, f"{step}  {title}" if step else title)
    c.setFont("KR", 8.5)
    c.drawRightString(PW - MARGIN, PH - 14.5 * mm, _CFG["running_title"])
    footer(c, page)


def cover(c, title, lines):
    c.setFillColor(ACCENT)
    c.rect(0, PH - 48 * mm, PW, 48 * mm, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("KRB", 24)
    c.drawString(MARGIN, PH - 24 * mm, title)
    c.setFont("KR", 11.5)
    for i, line in enumerate(lines):
        c.drawString(MARGIN, PH - (33 + 7 * i) * mm, line)


def section(c, text, x, y, size=12):
    c.setFont("KRB", size)
    c.setFillColor(ACCENT)
    c.drawString(x, y - size * 0.35, text)


def table(c, x, y, cols, rows, size=9, row_h=None, head_fill=LIGHT):
    row_h = row_h or size * 2.1
    widths = [w for _, w in cols]
    c.setLineWidth(0.5)
    c.setStrokeColor(HexColor("#999999"))
    all_rows = [[h for h, _ in cols]] + rows
    for r, row in enumerate(all_rows):
        cx = x
        top = y - r * row_h
        if r == 0:
            c.setFillColor(head_fill)
            c.rect(x, top - row_h, sum(widths), row_h, stroke=0, fill=1)
        for i, cell in enumerate(row):
            c.setFillColor(black)
            c.setFont("KRB" if r == 0 else "KR", size)
            c.drawString(cx + 4, top - row_h + (row_h - size) / 2 + 1.5, str(cell))
            c.rect(cx, top - row_h, widths[i], row_h, stroke=1, fill=0)
            cx += widths[i]
    return y - len(all_rows) * row_h


def note_box(c, x, y, w, title, items, size=9.5):
    """위쪽 y 부터 그리고 아래 y 반환."""
    inner = w - 16
    h = 12 + size * 1.6
    for it in items:
        h += len(wrap(it, "KR", size, inner - 14)) * size * 1.5 + 3
    c.setFillColor(LIGHT)
    c.setStrokeColor(ACCENT)
    c.setLineWidth(0.8)
    c.roundRect(x, y - h, w, h, 4, stroke=1, fill=1)
    c.setFillColor(ACCENT)
    c.setFont("KRB", size + 0.5)
    c.drawString(x + 8, y - 8 - size, title)
    bullets(c, items, x + 8, y - 12 - size * 1.6, inner, size)
    return y - h
