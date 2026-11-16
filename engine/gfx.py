"""Primitivas de dibujo sobre Skia: colores, fuentes, texto, iconos, formas y easing."""
import functools
import math
import os
import re

import skia

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FONT_DIR = os.path.join(ROOT, "assets", "fonts")
ICON_DIR = os.path.join(ROOT, "assets", "icons")

FONT_FILES = {
    "display": "Anton-Regular.ttf",
    "bebas": "BebasNeue-Regular.ttf",
    "medium": "Montserrat-Medium.ttf",
    "semi": "Montserrat-SemiBold.ttf",
    "bold": "Montserrat-Bold.ttf",
    "xbold": "Montserrat-ExtraBold.ttf",
    "black": "Montserrat-Black.ttf",
}


# --------------------------------------------------------------------------- colores
def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def col(h, a=1.0):
    """Color Skia (int ARGB) a partir de '#RRGGBB' y alfa 0..1."""
    if isinstance(h, int):
        return h
    r, g, b = hex2rgb(h)
    return skia.ColorSetARGB(int(max(0, min(1, a)) * 255), r, g, b)


def mix(h1, h2, t):
    a, b = hex2rgb(h1), hex2rgb(h2)
    return "#%02X%02X%02X" % tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


# --------------------------------------------------------------------------- easing
def clamp(x, a=0.0, b=1.0):
    return max(a, min(b, x))


def lerp(a, b, t):
    return a + (b - a) * t


def ease_out_cubic(t):
    t = clamp(t)
    return 1 - (1 - t) ** 3


def ease_in_out(t):
    t = clamp(t)
    return 3 * t * t - 2 * t * t * t


def ease_out_back(t, s=1.70158):
    t = clamp(t) - 1
    return t * t * ((s + 1) * t + s) + 1


def ease_out_expo(t):
    t = clamp(t)
    return 1 if t >= 1 else 1 - 2 ** (-10 * t)


def prog(t, t0, dur):
    """Progreso lineal 0..1 de una animación que empieza en t0 y dura dur."""
    if dur <= 0:
        return 1.0 if t >= t0 else 0.0
    return clamp((t - t0) / dur)


def appear(t, t0, dur=0.5, fn=ease_out_cubic):
    return fn(prog(t, t0, dur))


# --------------------------------------------------------------------------- fuentes
@functools.lru_cache(None)
def typeface(kind):
    return skia.Typeface.MakeFromFile(os.path.join(FONT_DIR, FONT_FILES[kind]))


@functools.lru_cache(4096)
def font(kind, size):
    f = skia.Font(typeface(kind), float(size))
    f.setSubpixel(True)
    f.setEdging(skia.Font.Edging.kAntiAlias)
    f.setHinting(skia.FontHinting.kNone)
    return f


def text_w(text, kind, size, tracking=0.0):
    f = font(kind, size)
    w = f.measureText(text)
    if tracking:
        w += tracking * size * max(0, len(text) - 1)
    return w


def cap_h(kind, size):
    return font(kind, size).getMetrics().fCapHeight


def wrap(text, kind, size, max_w):
    """Ajuste de línea voraz; respeta '\n' explícitos."""
    lines = []
    for para in str(text).split("\n"):
        words = para.split(" ")
        cur = ""
        for w in words:
            cand = (cur + " " + w).strip()
            if cur and text_w(cand, kind, size) > max_w:
                lines.append(cur)
                cur = w
            else:
                cur = cand
        lines.append(cur)
    return lines


def fit_size(text, kind, size, max_w, min_size=10):
    while size > min_size and text_w(text, kind, size) > max_w:
        size -= 2
    return size


def paint(color="#FFFFFF", a=1.0, stroke=None, blur=None, shader=None, cap_round=False):
    p = skia.Paint(AntiAlias=True)
    p.setColor(col(color, a))
    if stroke:
        p.setStyle(skia.Paint.kStroke_Style)
        p.setStrokeWidth(stroke)
        if cap_round:
            p.setStrokeCap(skia.Paint.kRound_Cap)
            p.setStrokeJoin(skia.Paint.kRound_Join)
    if blur:
        p.setMaskFilter(skia.MaskFilter.MakeBlur(skia.kNormal_BlurStyle, blur))
    if shader is not None:
        p.setShader(shader)
        p.setAlphaf(clamp(a))
    return p


def draw_text(c, text, x, y, kind, size, color="#FFFFFF", a=1.0, align="left",
              tracking=0.0, glow=None, glow_a=0.8, glow_blur=None, stroke=None,
              stroke_color="#000000", shader=None, shadow=None):
    """Dibuja texto con línea base en y. align: left|center|right.

    glow: color del resplandor; stroke: grosor del contorno; shadow: (dx, dy, blur, alpha).
    """
    if a <= 0.003 or not text:
        return 0
    f = font(kind, size)
    w = text_w(text, kind, size, tracking)
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w

    def _draw(p):
        if tracking:
            cx = x
            for ch in text:
                c.drawString(ch, cx, y, f, p)
                cx += f.measureText(ch) + tracking * size
        else:
            c.drawString(text, x, y, f, p)

    if shadow:
        dx, dy, sb, sa = shadow
        c.save()
        c.translate(dx, dy)
        _draw(paint("#000000", a * sa, blur=sb))
        c.restore()
    if glow:
        _draw(paint(glow, a * glow_a, blur=glow_blur or max(4, size * 0.12)))
    if stroke:
        _draw(paint(stroke_color, a, stroke=stroke))
    _draw(paint(color, a, shader=shader))
    return w


def draw_lines(c, lines, x, y, kind, size, leading=1.15, **kw):
    """Dibuja varias líneas; y es la línea base de la primera. Devuelve y final."""
    for i, ln in enumerate(lines):
        draw_text(c, ln, x, y + i * size * leading, kind, size, **kw)
    return y + (len(lines) - 1) * size * leading


# --------------------------------------------------------------------------- formas
def rrect(c, x, y, w, h, r, p):
    c.drawRRect(skia.RRect.MakeRectXY(skia.Rect.MakeXYWH(x, y, w, h), r, r), p)


def lin_grad(x0, y0, x1, y1, colors, pos=None, alphas=None):
    cs = []
    for i, h in enumerate(colors):
        cs.append(col(h, alphas[i] if alphas else 1.0))
    return skia.GradientShader.MakeLinear([(x0, y0), (x1, y1)], cs, pos)


def rad_grad(cx, cy, r, colors, pos=None, alphas=None):
    cs = []
    for i, h in enumerate(colors):
        cs.append(col(h, alphas[i] if alphas else 1.0))
    return skia.GradientShader.MakeRadial((cx, cy), r, cs, pos)


def panel(c, x, y, w, h, accent="#FF2E88", a=1.0, r=28, fill="#140A28", fill_a=0.78,
          border_a=0.55, shadow=True):
    """Tarjeta translúcida con borde de acento y sombra."""
    if a <= 0.003:
        return
    if shadow:
        rrect(c, x, y + 14, w, h, r, paint("#000000", 0.45 * a, blur=26))
    rrect(c, x, y, w, h, r, paint(fill, fill_a * a))
    g = lin_grad(x, y, x + w, y + h, ["#FFFFFF", fill], alphas=[0.07 * a, 0.0])
    rrect(c, x, y, w, h, r, skia.Paint(AntiAlias=True, Shader=g))
    rrect(c, x + 1, y + 1, w - 2, h - 2, r, paint(accent, border_a * a, stroke=2.5))


def pill(c, x, y, text, kind="xbold", size=26, color="#0B0618", bg="#FFD23F", a=1.0,
         pad_x=22, pad_y=12, tracking=0.08, align="left"):
    w = text_w(text, kind, size, tracking) + pad_x * 2
    h = cap_h(kind, size) + pad_y * 2
    if align == "center":
        x -= w / 2
    elif align == "right":
        x -= w
    rrect(c, x, y, w, h, h / 2, paint(bg, a))
    draw_text(c, text, x + pad_x, y + pad_y + cap_h(kind, size), kind, size, color, a,
              tracking=tracking)
    return w, h


# --------------------------------------------------------------------------- iconos
@functools.lru_cache(512)
def _icon_picture(name, color, size, stroke):
    path = os.path.join(ICON_DIR, name + ".svg")
    if not os.path.exists(path):
        path = os.path.join(ICON_DIR, "circle-help.svg")
    svg = open(path, encoding="utf-8").read()
    svg = re.sub(r"<!--.*?-->", "", svg, flags=re.S)
    svg = svg.replace("currentColor", color)
    svg = re.sub(r'width="24"', f'width="{size}"', svg, count=1)
    svg = re.sub(r'height="24"', f'height="{size}"', svg, count=1)
    if stroke:
        svg = re.sub(r'stroke-width="[\d.]+"', f'stroke-width="{stroke}"', svg, count=1)
    dom = skia.SVGDOM.MakeFromStream(skia.MemoryStream(svg.encode("utf-8")))
    dom.setContainerSize(skia.Size(size, size))
    rec = skia.PictureRecorder()
    cv = rec.beginRecording(skia.Rect.MakeWH(size, size))
    dom.render(cv)
    return rec.finishRecordingAsPicture()


def icon(c, name, cx, cy, size, color="#FFFFFF", a=1.0, stroke=2.0, glow=None):
    """Icono Lucide centrado en (cx, cy)."""
    if a <= 0.003:
        return
    size = int(round(size))
    pic = _icon_picture(name, color, size, stroke)
    if glow:
        gp = _icon_picture(name, glow, size, stroke + 1.2)
        p = skia.Paint(AntiAlias=True)
        p.setImageFilter(skia.ImageFilters.Blur(size * 0.08, size * 0.08))
        p.setAlphaf(0.9 * a)
        c.save()
        c.translate(cx - size / 2, cy - size / 2)
        c.drawPicture(gp, None, p)
        c.restore()
    p = skia.Paint(AntiAlias=True)
    p.setAlphaf(clamp(a))
    c.save()
    c.translate(cx - size / 2, cy - size / 2)
    c.drawPicture(pic, None, p)
    c.restore()


def icon_badge(c, name, cx, cy, r, accent, a=1.0, fill="#0B0618", icon_color="#FFFFFF"):
    """Círculo con degradado y un icono dentro."""
    if a <= 0.003:
        return
    c.drawCircle(cx, cy, r * 1.25, paint(accent, 0.28 * a, blur=r * 0.5))
    sh = lin_grad(cx - r, cy - r, cx + r, cy + r, [accent, mix(accent, fill, 0.55)])
    c.drawCircle(cx, cy, r, paint(accent, a, shader=sh))
    c.drawCircle(cx, cy, r - 1.5, paint("#FFFFFF", 0.25 * a, stroke=2))
    icon(c, name, cx, cy, r * 1.05, icon_color, a, stroke=2.2)


def set_trim(p, amount):
    """Recorta el trazo al porcentaje indicado (Skia devuelve None para 0 o 1)."""
    if amount >= 0.999:
        return p
    pe = skia.TrimPathEffect.Make(0.0, max(0.001, amount))
    if pe is not None:
        p.setPathEffect(pe)
    return p


def check_mark(c, cx, cy, s, p_amt, color="#00E0A4", a=1.0, width=6):
    """Marca de verificación que se dibuja progresivamente (p_amt 0..1)."""
    if p_amt <= 0 or a <= 0:
        return
    path = skia.Path()
    path.moveTo(cx - s * 0.42, cy + s * 0.02)
    path.lineTo(cx - s * 0.12, cy + s * 0.32)
    path.lineTo(cx + s * 0.45, cy - s * 0.30)
    p = paint(color, a, stroke=width, cap_round=True)
    set_trim(p, clamp(p_amt))
    c.drawPath(path, p)


def cross_mark(c, cx, cy, s, p_amt, color="#FF4D6D", a=1.0, width=6):
    if p_amt <= 0 or a <= 0:
        return
    p = paint(color, a, stroke=width, cap_round=True)
    k1 = clamp(p_amt * 2)
    k2 = clamp(p_amt * 2 - 1)
    h = s * 0.32
    c.drawLine(cx - h, cy - h, cx - h + 2 * h * k1, cy - h + 2 * h * k1, p)
    if k2 > 0:
        c.drawLine(cx + h, cy - h, cx + h - 2 * h * k2, cy - h + 2 * h * k2, p)
