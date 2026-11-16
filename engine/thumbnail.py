"""Miniaturas 1280x720 para YouTube a partir del bloque `thumb` del guion.

Uso: python -m engine.thumbnail videos/01-....yaml [--out output]
"""
import argparse
import os

import numpy as np
import skia
import yaml

from .backgrounds import Backdrop, theme
from .gfx import cap_h, draw_text, fit_size, icon, lin_grad, mix, paint, rad_grad, rrect, text_w

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TW, TH = 1280, 720


def render_thumb(spec, brand, path):
    tb = spec["thumb"]
    tname = tb.get("theme", spec.get("theme", "sunset"))
    th = theme(tname)
    arr = np.zeros((TH, TW, 4), np.uint8)
    surf = skia.Surface(arr)
    c = surf.getCanvas()
    # fondo a 1920x1080 escalado
    c.save()
    c.scale(TW / 1920, TH / 1080)
    Backdrop(1920, 1080).draw(c, tb.get("bg", "scenery"), tname, 3.3)
    c.restore()
    # oscurecer zona de texto
    c.drawRect(skia.Rect.MakeWH(TW, TH), skia.Paint(Shader=lin_grad(0, 0, TW * 0.78, 0, ["#000000", "#000000"],
                                                                    alphas=[0.82, 0.0])))
    # icono grande a la derecha
    ix, iy = TW * 0.815, TH * 0.53
    c.drawCircle(ix, iy, 235, paint(th["a1"], 0.45, blur=60))
    c.drawCircle(ix, iy, 185, paint(th["a1"], 1, shader=lin_grad(ix - 185, iy - 185, ix + 185, iy + 185,
                                                                 [th["a1"], mix(th["a1"], "#0B0618", 0.55)])))
    c.drawCircle(ix, iy, 185, paint("#FFFFFF", 0.55, stroke=5))
    icon(c, tb.get("icon", "star"), ix, iy, 200, "#FFFFFF", 1, stroke=2.0)
    # textos
    x = 52
    top = tb.get("top", "").upper()
    main = tb.get("main", "").upper()
    s1 = fit_size(top, "display", 112, 730)
    s2 = fit_size(main, "display", 210, 740)
    y1 = 215
    draw_text(c, top, x, y1, "display", s1, "#FFFFFF", 1, stroke=14, stroke_color="#000000",
              shadow=(0, 8, 14, 0.8))
    draw_text(c, top, x, y1, "display", s1, "#FFFFFF", 1)
    y2 = y1 + cap_h("display", s2) + 40
    grad = lin_grad(0, y2 - cap_h("display", s2), 0, y2, [th["a3"], th["a1"]])
    draw_text(c, main, x, y2, "display", s2, th["a3"], 1, stroke=18, stroke_color="#000000",
              glow=th["a1"], glow_a=0.9, glow_blur=26)
    draw_text(c, main, x, y2, "display", s2, th["a3"], 1, shader=grad)
    if tb.get("sub"):
        sub = tb["sub"].upper()
        ss = fit_size(sub, "black", 34, 760)
        w = text_w(sub, "black", ss) + 44
        rrect(c, x, y2 + 40, w, ss + 30, 14, paint("#000000", 0.85))
        rrect(c, x, y2 + 40, 10, ss + 30, 5, paint(th["a1"]))
        draw_text(c, sub, x + 26, y2 + 40 + 15 + cap_h("black", ss), "black", ss, "#FFFFFF", 1)
    # pegatina
    if tb.get("badge"):
        b = tb["badge"].upper()
        bs = fit_size(b, "display", 74, 330)
        bw, bh = text_w(b, "display", bs) + 64, bs * 1.25
        c.save()
        c.translate(TW - 60 - bw / 2, 92)
        c.rotate(6)
        rrect(c, -bw / 2, -bh / 2 + 8, bw, bh, 22, paint("#000000", 0.6, blur=10))
        rrect(c, -bw / 2, -bh / 2, bw, bh, 22, paint(th["a3"]))
        rrect(c, -bw / 2, -bh / 2, bw, bh, 22, paint("#000000", 1, stroke=6))
        draw_text(c, b, 0, cap_h("display", bs) / 2, "display", bs, "#0B0618", 1, align="center")
        c.restore()
    # marca del canal
    bx, by, bsz = 46, TH - 86, 50
    rrect(c, bx, by, bsz, bsz, 12, paint(th["a1"], 1, shader=lin_grad(bx, by, bx + bsz, by + bsz, [th["a1"], th["a2"]])))
    draw_text(c, "6", bx + bsz / 2, by + bsz / 2 + cap_h("display", 36) / 2, "display", 36, "#0B0618", 1,
              align="center")
    draw_text(c, brand["name"], bx + bsz + 14, by + bsz / 2 + cap_h("bebas", 40) / 2, "bebas", 40, "#FFFFFF", 1,
              tracking=0.06, shadow=(0, 2, 6, 0.9))
    surf.makeImageSnapshot().save(path, skia.kPNG)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("specs", nargs="+")
    ap.add_argument("--out", default=os.path.join(ROOT, "output"))
    a = ap.parse_args()
    with open(os.path.join(ROOT, "channel", "brand.yaml"), encoding="utf-8") as f:
        brand = yaml.safe_load(f)
    for sp in a.specs:
        with open(sp, encoding="utf-8") as f:
            spec = yaml.safe_load(f)
        name = f"{spec['id']}-{spec['slug']}"
        d = os.path.join(a.out, name)
        os.makedirs(d, exist_ok=True)
        p = os.path.join(d, f"{name}-miniatura.png")
        render_thumb(spec, brand, p)
        print(p)


if __name__ == "__main__":
    main()
