"""Fondos animados originales: atardecer neón, océano, abstracto y mapa.

Todo se genera por código (sin material de terceros). Las partes estáticas se
pre-renderizan una vez por tema; las animadas (sol, rejilla, palmeras,
partículas) se dibujan en cada fotograma.
"""
import functools
import math
import random

import numpy as np
import skia

from .gfx import clamp, col, lin_grad, mix, paint, rad_grad

THEMES = {
    "sunset": dict(sky=["#07030F", "#1C0833", "#4A1060", "#C2266F"], sun=["#FFE45E", "#FF2E88"],
                   grid="#FF2E88", a1="#FF2E88", a2="#22E4FF", a3="#FFD23F", ground="#0E0419",
                   dark="#0B0618", blob="#6A1B9A"),
    "miami": dict(sky=["#020812", "#08223A", "#0F4A6E", "#FF6F91"], sun=["#FFF1A8", "#FF6F91"],
                  grid="#22E4FF", a1="#22E4FF", a2="#FF6F91", a3="#FFE66D", ground="#03121F",
                  dark="#041120", blob="#0E5A7A"),
    "dusk": dict(sky=["#090410", "#250A2E", "#6B1A3A", "#FF7A3D"], sun=["#FFE9A0", "#FF5E3A"],
                 grid="#FF8A3D", a1="#FF8A3D", a2="#FFD23F", a3="#FF2E88", ground="#140612",
                 dark="#10060F", blob="#8A2A3A"),
    "night": dict(sky=["#03030B", "#0C0A2E", "#2A1A6E", "#7B3FE4"], sun=["#F1EBFF", "#9C7BFF"],
                  grid="#9C7BFF", a1="#9C7BFF", a2="#22E4FF", a3="#FF2E88", ground="#06051A",
                  dark="#070614", blob="#3A2A9E"),
}

HORIZON = 0.64


def theme(name):
    return THEMES.get(name, THEMES["sunset"])


def _img_from_canvas(w, h, fn):
    arr = np.zeros((h, w, 4), np.uint8)
    s = skia.Surface(arr)
    fn(s.getCanvas())
    return s.makeImageSnapshot()


@functools.lru_cache(16)
def sky_image(tname, w, h):
    th = theme(tname)
    hy = h * HORIZON

    def draw(c):
        sh = lin_grad(0, 0, 0, hy, th["sky"], [0, 0.35, 0.72, 1.0])
        c.drawRect(skia.Rect.MakeWH(w, hy + 2), skia.Paint(Shader=sh))
        rnd = random.Random(7)
        for _ in range(260):
            x, y = rnd.random() * w, rnd.random() * hy * 0.8
            r = rnd.random() * 1.6 + 0.3
            c.drawCircle(x, y, r, paint("#FFFFFF", (1 - y / hy) * rnd.uniform(0.2, 0.9)))
        # bruma del horizonte
        c.drawRect(skia.Rect.MakeXYWH(0, hy - h * 0.18, w, h * 0.18),
                   skia.Paint(Shader=lin_grad(0, hy - h * 0.18, 0, hy, [th["sky"][3], th["sun"][1]],
                                              alphas=[0.0, 0.55])))
    return _img_from_canvas(w, h, draw)


@functools.lru_cache(16)
def skyline_image(tname, w, h, seed=3):
    """Silueta de ciudad costera generada proceduralmente."""
    th = theme(tname)
    hy = h * HORIZON
    rnd = random.Random(seed)

    def layer(c, base_col, light_a, scale, xoff):
        x = -40 + xoff
        while x < w + 40:
            bw = rnd.uniform(28, 92) * scale
            dist = min(1.0, abs((x + bw / 2) - w * 0.5) / (w * 0.5))
            hmax = (360 * (1 - dist) ** 1.6 + 70) * scale
            bh = rnd.uniform(0.35, 1.0) * hmax
            top = hy - bh
            p = paint(base_col)
            c.drawRect(skia.Rect.MakeXYWH(x, top, bw, bh + 2), p)
            if rnd.random() < 0.25:  # azotea escalonada
                c.drawRect(skia.Rect.MakeXYWH(x + bw * 0.2, top - bh * 0.08, bw * 0.6, bh * 0.08 + 1), p)
            if rnd.random() < 0.18:  # antena
                c.drawRect(skia.Rect.MakeXYWH(x + bw * 0.5 - 1.5, top - 40 * scale, 3, 40 * scale), p)
            if light_a > 0:
                for wy in np.arange(top + 10, hy - 8, 14 * scale):
                    for wx in np.arange(x + 6, x + bw - 6, 11 * scale):
                        if rnd.random() < 0.10:
                            c.drawRect(skia.Rect.MakeXYWH(wx, wy, 4 * scale, 6 * scale),
                                       paint(rnd.choice(["#FFD9A0", "#FFE9C8", th["a2"]]),
                                             light_a * rnd.uniform(0.4, 1.0)))
            x += bw + rnd.uniform(-6, 10)

    def draw(c):
        layer(c, mix(th["sky"][2], "#000000", 0.35), 0.0, 0.8, 13)
        layer(c, mix(th["ground"], th["sky"][1], 0.4), 0.85, 1.0, 0)
    return _img_from_canvas(w, h, draw)


@functools.lru_cache(16)
def vignette_image(w, h, strength=0.62):
    def draw(c):
        sh = rad_grad(w / 2, h / 2, w * 0.72, ["#000000", "#000000", "#000000"], [0, 0.55, 1.0],
                      alphas=[0.0, 0.08, strength])
        c.drawRect(skia.Rect.MakeWH(w, h), skia.Paint(Shader=sh))
    return _img_from_canvas(w, h, draw)


# --------------------------------------------------------------------------- piezas animadas
def draw_sun(c, w, h, th, t, scale=1.0, cy_off=0.0):
    hy = h * HORIZON
    R = h * 0.23 * scale
    cx, cy = w * 0.5, hy - R * 0.42 + cy_off
    c.drawCircle(cx, cy, R * 1.9, skia.Paint(AntiAlias=True, Shader=rad_grad(
        cx, cy, R * 1.9, [th["sun"][1], th["sun"][1]], alphas=[0.45, 0.0])))
    c.save()
    # rendijas horizontales que se desplazan hacia abajo
    phase = (t * 0.06) % 1.0
    n = 7
    for i in range(n):
        k = (i + phase) / n
        y = cy + R * (0.05 + 0.95 * k)
        gap = R * 0.018 + R * 0.075 * k
        c.clipRect(skia.Rect.MakeLTRB(cx - R - 2, y, cx + R + 2, y + gap), skia.ClipOp.kDifference)
    sh = lin_grad(cx, cy - R, cx, cy + R, th["sun"])
    c.drawCircle(cx, cy, R, skia.Paint(AntiAlias=True, Shader=sh))
    c.restore()


def draw_grid(c, w, h, th, t, alpha=1.0, speed=0.55):
    hy = h * HORIZON
    c.drawRect(skia.Rect.MakeLTRB(0, hy, w, h), skia.Paint(Shader=lin_grad(
        0, hy, 0, h, [th["ground"], "#000000"])))
    gcol = th["grid"]
    vx = w * 0.5
    # líneas de fuga
    for i in range(-22, 23):
        xb = vx + i * w * 0.085
        p = paint(gcol, 0.55 * alpha, stroke=2.0)
        p.setShader(lin_grad(vx, hy, xb, h, [gcol, gcol], alphas=[0.0, 0.75 * alpha]))
        c.drawLine(vx + i * 6, hy, xb * 1.0 + (xb - vx) * 1.6, h * 1.6, p)
    # líneas transversales con perspectiva
    phase = (t * speed) % 1.0
    F = (h - hy) * 1.15
    for k in range(0, 26):
        d = 1.0 + (k + 1 - phase) * 0.9
        y = hy + F / d
        if y > h + 4:
            continue
        a = clamp((y - hy) / (h - hy)) ** 0.8
        c.drawLine(0, y, w, y, paint(gcol, 0.8 * a * alpha, stroke=1.2 + 2.0 * a))
    # resplandor del horizonte
    c.drawRect(skia.Rect.MakeLTRB(0, hy - 3, w, hy + 3), paint(gcol, 0.9 * alpha, blur=6))


def palm(c, bx, by, height, lean, sway, color="#06020C", fronds=9, seed=0):
    """Palmera en silueta. lean: inclinación (-1..1); sway: oscilación actual."""
    rnd = random.Random(seed)
    tx = bx + lean * height * 0.45 + sway * height * 0.03
    ty = by - height
    mx = bx + lean * height * 0.08
    my = by - height * 0.55
    # tronco como polígono que se estrecha
    pts_l, pts_r = [], []
    N = 24
    for i in range(N + 1):
        s = i / N
        x = (1 - s) ** 2 * bx + 2 * (1 - s) * s * mx + s * s * tx
        y = (1 - s) ** 2 * by + 2 * (1 - s) * s * my + s * s * ty
        dx = 2 * (1 - s) * (mx - bx) + 2 * s * (tx - mx)
        dy = 2 * (1 - s) * (my - by) + 2 * s * (ty - my)
        ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / ln, dx / ln
        wdt = height * (0.034 - 0.016 * s)
        pts_l.append((x + nx * wdt, y + ny * wdt))
        pts_r.append((x - nx * wdt, y - ny * wdt))
    path = skia.Path()
    path.moveTo(*pts_l[0])
    for p_ in pts_l[1:]:
        path.lineTo(*p_)
    for p_ in reversed(pts_r):
        path.lineTo(*p_)
    path.close()
    pnt = paint(color)
    c.drawPath(path, pnt)
    # anillos del tronco
    ring = paint(mix(color, "#3A1A4A", 0.35), 0.6, stroke=1.4)
    for i in range(3, N, 2):
        c.drawLine(*pts_l[i], *pts_r[i], ring)
    # copa
    c.drawCircle(tx, ty, height * 0.035, pnt)
    L = height * 0.42
    for f in range(fronds):
        base_ang = -math.pi / 2 + (f - (fronds - 1) / 2) * (math.pi * 1.25 / fronds)
        base_ang += rnd.uniform(-0.12, 0.12) + sway * 0.06 * (1 if f % 2 else -1)
        ln = L * rnd.uniform(0.78, 1.08)
        droop = 1.15 + rnd.uniform(-0.2, 0.25)
        pts = []
        M = 18
        for i in range(M + 1):
            s = i / M
            ang = base_ang + droop * s * s * (1 if math.cos(base_ang) >= 0 else -1) * 0.9
            if i == 0:
                x, y = tx, ty
            else:
                x = pts[-1][0] + math.cos(ang) * ln / M
                y = pts[-1][1] + math.sin(ang) * ln / M + s * ln * 0.012 * droop
            pts.append((x, y))
        # hoja central gruesa
        fp = skia.Path()
        fp.moveTo(*pts[0])
        for p_ in pts[1:]:
            fp.lineTo(*p_)
        c.drawPath(fp, paint(color, stroke=height * 0.010, cap_round=True))
        # foliolos
        lp = paint(color, stroke=height * 0.0065, cap_round=True)
        for i in range(2, M):
            s = i / M
            x, y = pts[i]
            x2, y2 = pts[i + 1]
            ang = math.atan2(y2 - y, x2 - x)
            ll = height * 0.11 * math.sin(math.pi * min(1, s * 1.1)) + height * 0.02
            for side in (-1, 1):
                a2 = ang + side * 1.05 + 0.35
                c.drawLine(x, y, x + math.cos(a2) * ll, y + math.sin(a2) * ll + ll * 0.35, lp)


def draw_particles(c, w, h, th, t, n=46, seed=11, alpha=1.0):
    rnd = random.Random(seed)
    cols = [th["a1"], th["a2"], th["a3"], "#FFFFFF"]
    for i in range(n):
        x0, y0 = rnd.random() * w, rnd.random() * h
        sp = rnd.uniform(8, 26)
        r = rnd.uniform(1.0, 3.2)
        ph = rnd.random() * 6.28
        y = (y0 - t * sp) % (h + 20) - 10
        x = x0 + math.sin(t * 0.4 + ph) * 18
        a = (0.25 + 0.35 * (0.5 + 0.5 * math.sin(t * 1.3 + ph))) * alpha
        c.drawCircle(x, y, r, paint(rnd.choice(cols), a))


def draw_blobs(c, w, h, th, t, alpha=1.0):
    specs = [(th["a1"], 0.22, 0.30, 0.55, 0.07, 0.0), (th["a2"], 0.80, 0.70, 0.50, 0.05, 2.0),
             (th["blob"], 0.55, 0.15, 0.65, 0.04, 4.0)]
    for cc, fx, fy, fr, sp, ph in specs:
        cx = w * (fx + 0.08 * math.sin(t * sp * 6.28 * 0.25 + ph))
        cy = h * (fy + 0.07 * math.cos(t * sp * 6.28 * 0.2 + ph))
        r = w * fr * 0.5
        c.drawCircle(cx, cy, r, skia.Paint(AntiAlias=True, Shader=rad_grad(
            cx, cy, r, [cc, cc], alphas=[0.30 * alpha, 0.0])))


# --------------------------------------------------------------------------- fondos completos
class Backdrop:
    def __init__(self, w, h):
        self.w, self.h = w, h

    def draw(self, c, kind, tname, t, intensity=1.0):
        w, h = self.w, self.h
        th = theme(tname)
        if kind == "scenery":
            self._scenery(c, th, tname, t)
        elif kind == "ocean":
            self._ocean(c, th, tname, t)
        elif kind == "map":
            self._mapbg(c, th, t)
        else:
            self._abstract(c, th, t)
        c.drawImage(vignette_image(w, h), 0, 0)

    def _scenery(self, c, th, tname, t):
        w, h = self.w, self.h
        c.drawImage(sky_image(tname, w, h), 0, 0)
        draw_sun(c, w, h, th, t)
        drift = math.sin(t * 0.05) * 14
        c.drawImage(skyline_image(tname, w, h), drift, 0)
        draw_grid(c, w, h, th, t)
        sway = math.sin(t * 0.9)
        palm(c, w * 0.06, h * 1.04, h * 0.95, 0.38, sway, seed=1)
        palm(c, w * 0.17, h * 1.06, h * 0.70, 0.10, math.sin(t * 0.8 + 1), seed=2, fronds=8)
        palm(c, w * 0.94, h * 1.05, h * 0.88, -0.42, math.sin(t * 0.85 + 2), seed=3)
        draw_particles(c, w, h, th, t, n=30, alpha=0.7)

    def _ocean(self, c, th, tname, t):
        w, h = self.w, self.h
        hy = h * HORIZON
        c.drawImage(sky_image(tname, w, h), 0, 0)
        draw_sun(c, w, h, th, t, scale=0.9, cy_off=h * 0.02)
        c.drawRect(skia.Rect.MakeLTRB(0, hy, w, h), skia.Paint(Shader=lin_grad(
            0, hy, 0, h, [mix(th["sky"][2], "#000000", 0.3), "#000000"])))
        rnd = random.Random(5)
        cx = w * 0.5
        for i in range(70):
            k = i / 70
            y = hy + 6 + (h - hy) * (k ** 1.6)
            spread = 60 + 520 * k
            wob = math.sin(t * 1.6 + i * 1.7) * 18 * (0.3 + k)
            ln = spread * rnd.uniform(0.25, 1.0)
            c.drawLine(cx - ln / 2 + wob, y, cx + ln / 2 + wob, y,
                       paint(mix(th["sun"][0], th["sun"][1], k), (1 - k) * 0.75, stroke=2 + 4 * k))
        for i in range(30):
            k = i / 30
            y = hy + 10 + (h - hy) * k
            x = (rnd.random() * w + t * 20 * (0.5 + k)) % w
            c.drawLine(x, y, x + 40 + 120 * k, y, paint(th["a2"], 0.18 * (1 - k), stroke=1.5))
        c.drawRect(skia.Rect.MakeLTRB(0, hy - 2, w, hy + 2), paint(th["sun"][1], 0.7, blur=5))
        palm(c, w * 0.05, h * 1.05, h * 0.92, 0.42, math.sin(t * 0.9), seed=4)
        palm(c, w * 0.955, h * 1.04, h * 0.78, -0.35, math.sin(t * 0.8 + 2), seed=6, fronds=8)
        draw_particles(c, w, h, th, t, n=24, alpha=0.6)

    def _abstract(self, c, th, t):
        w, h = self.w, self.h
        c.drawRect(skia.Rect.MakeWH(w, h), skia.Paint(Shader=lin_grad(
            0, 0, w * 0.3, h, [th["dark"], mix(th["dark"], th["blob"], 0.35), th["dark"]], [0, 0.6, 1])))
        draw_blobs(c, w, h, th, t)
        # rejilla tenue en perspectiva en la parte baja
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(0, h * HORIZON, w, h))
        hy = h * HORIZON
        gcol = th["grid"]
        vx = w * 0.5
        for i in range(-16, 17):
            xb = vx + i * w * 0.11
            c.drawLine(vx + i * 4, hy, xb + (xb - vx) * 1.6, h * 1.6, paint(gcol, 0.10, stroke=1.5))
        phase = (t * 0.35) % 1.0
        F = (h - hy) * 1.15
        for k in range(0, 20):
            d = 1.0 + (k + 1 - phase) * 0.9
            y = hy + F / d
            a = clamp((y - hy) / (h - hy))
            c.drawLine(0, y, w, y, paint(gcol, 0.16 * a, stroke=1.4))
        c.restore()
        c.drawRect(skia.Rect.MakeLTRB(0, h * HORIZON - 160, w, h * HORIZON + 40), skia.Paint(
            Shader=lin_grad(0, h * HORIZON - 160, 0, h * HORIZON + 40, [th["dark"], th["dark"], th["dark"]],
                            [0, 0.8, 1], alphas=[0.0, 0.85, 0.0])))
        draw_particles(c, w, h, th, t, n=40, alpha=0.8)

    def _mapbg(self, c, th, t):
        w, h = self.w, self.h
        c.drawRect(skia.Rect.MakeWH(w, h), skia.Paint(Shader=rad_grad(
            w * 0.45, h * 0.45, w * 0.8, ["#0A2A44", "#04101E", "#02070F"], [0, 0.6, 1])))
        # retícula náutica
        step = 80
        off = (t * 6) % step
        for x in np.arange(-step + off, w + step, step):
            c.drawLine(x, 0, x, h, paint("#22E4FF", 0.05, stroke=1))
        for y in np.arange(-step + off, h + step, step):
            c.drawLine(0, y, w, y, paint("#22E4FF", 0.05, stroke=1))
        draw_particles(c, w, h, th, t, n=20, alpha=0.4)
