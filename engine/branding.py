"""Imagen de canal: banner 2560x1440, avatar 800x800 y marca de agua 150x150.

Uso: python -m engine.branding [--out output/canal]
"""
import argparse
import os

import numpy as np
import skia
import yaml

from .backgrounds import Backdrop, theme
from .gfx import cap_h, draw_text, lin_grad, mix, paint, rrect

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


_KEEP = []


def _surface(w, h):
    arr = np.zeros((h, w, 4), np.uint8)
    _KEEP.append(arr)  # Skia usa este buffer: debe seguir vivo mientras exista la superficie
    return skia.Surface(arr)


def logo_mark(c, cx, cy, size, th):
    r = size * 0.22
    x, y = cx - size / 2, cy - size / 2
    c.drawCircle(cx, cy, size * 0.62, paint(th["a1"], 0.35, blur=size * 0.18))
    rrect(c, x, y, size, size, r, paint(th["a1"], 1, shader=lin_grad(x, y, x + size, y + size, [th["a1"], th["a2"]])))
    rrect(c, x, y, size, size, r, paint("#FFFFFF", 0.5, stroke=size * 0.025))
    fs = size * 0.78
    draw_text(c, "6", cx, cy + cap_h("display", fs) / 2, "display", fs, "#0B0618", 1, align="center")


def banner(brand, path):
    th = theme("sunset")
    W, H = 2560, 1440
    s = _surface(W, H)
    c = s.getCanvas()
    c.save()
    c.scale(W / 1920, H / 1080)
    Backdrop(1920, 1080).draw(c, "scenery", "sunset", 2.0)
    c.restore()
    # zona segura de YouTube: 1546x423 centrada
    c.drawRect(skia.Rect.MakeXYWH(0, H / 2 - 300, W, 600), skia.Paint(Shader=lin_grad(
        0, H / 2 - 300, 0, H / 2 + 300, ["#000000", "#000000", "#000000"], [0, 0.5, 1], alphas=[0.0, 0.55, 0.0])))
    logo_mark(c, W / 2 - 560, H / 2, 210, th)
    draw_text(c, brand["name"], W / 2 - 420, H / 2 + cap_h("display", 190) / 2 - 20, "display", 190, "#FFFFFF", 1,
              glow=th["a1"], glow_a=0.8, tracking=0.03, shadow=(0, 8, 16, 0.7))
    draw_text(c, brand["tagline"].upper(), W / 2 - 414, H / 2 + 140, "xbold", 40, th["a3"], 1, tracking=0.06,
              shadow=(0, 3, 8, 0.8))
    s.makeImageSnapshot().save(path, skia.kPNG)


def avatar(brand, path, size=800):
    th = theme("sunset")
    s = _surface(size, size)
    c = s.getCanvas()
    c.drawRect(skia.Rect.MakeWH(size, size), skia.Paint(Shader=lin_grad(0, 0, 0, size, ["#1C0833", "#4A1060", "#C2266F"])))
    # sol con rendijas
    cx, cy, R = size / 2, size * 0.60, size * 0.30
    c.save()
    for i in range(5):
        y = cy + R * (0.15 + 0.17 * i)
        c.clipRect(skia.Rect.MakeLTRB(0, y, size, y + R * (0.03 + 0.03 * i)), skia.ClipOp.kDifference)
    c.drawCircle(cx, cy, R, skia.Paint(AntiAlias=True, Shader=lin_grad(cx, cy - R, cx, cy + R, th["sun"])))
    c.restore()
    fs = size * 0.62
    draw_text(c, "6", cx, size * 0.5 + cap_h("display", fs) / 2, "display", fs, "#FFFFFF", 1, stroke=size * 0.03,
              stroke_color="#0B0618", glow=th["a1"], glow_a=0.9, glow_blur=size * 0.04, align="center")
    draw_text(c, "6", cx, size * 0.5 + cap_h("display", fs) / 2, "display", fs, "#FFFFFF", 1, align="center")
    s.makeImageSnapshot().save(path, skia.kPNG)


def watermark(path, size=150):
    th = theme("sunset")
    s = _surface(size, size)
    c = s.getCanvas()
    c.clear(skia.ColorTRANSPARENT)
    logo_mark(c, size / 2, size / 2, size * 0.78, th)
    s.makeImageSnapshot().save(path, skia.kPNG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(ROOT, "output", "canal"))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    with open(os.path.join(ROOT, "channel", "brand.yaml"), encoding="utf-8") as f:
        brand = yaml.safe_load(f)
    banner(brand, os.path.join(a.out, "banner-2560x1440.png"))
    avatar(brand, os.path.join(a.out, "avatar-800x800.png"))
    watermark(os.path.join(a.out, "marca-de-agua-150x150.png"))
    print("ok", a.out)


if __name__ == "__main__":
    main()
