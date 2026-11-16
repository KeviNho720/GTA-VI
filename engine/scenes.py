"""Escenas animadas. Cada función dibuja una escena en el instante local t.

Contrato de la escena `sc` (dict ya temporizado por render.py):
  sc["dur"]   duración total en segundos
  sc["cues"]  instantes (relativos a la escena) en que empieza cada frase narrada
  resto de campos según el tipo (ver docs/FORMATO.md)
"""
import math
import re

import skia

from .gfx import (appear, set_trim, cap_h, check_mark, clamp, col, cross_mark, draw_text, ease_out_back,
                  ease_out_cubic, ease_in_out, fit_size, icon, icon_badge, lerp, lin_grad, mix, paint,
                  panel, pill, prog, rad_grad, rrect, text_w, wrap)

W, H = 1920, 1080
LEFT, RIGHT = 140, 1780
TOP, BOTTOM = 150, 850

GOOD, BAD, WARN, INFO = "#00E0A4", "#FF4D6D", "#FF8A3D", "#FFD23F"
MUTED = "#C9B8E8"
WHITE = "#FFF6FB"
VERDICT_COLORS = {"si": GOOD, "sí": GOOD, "confirmado": GOOD, "no": BAD, "rumor": WARN,
                  "pendiente": INFO, "info": "#22E4FF"}


# --------------------------------------------------------------------------- utilidades de tiempo
def cue(sc, idx, default=0.35):
    cues = sc.get("cues") or []
    if idx is None:
        return default
    if isinstance(idx, float) and not float(idx).is_integer():
        # fracción de la escena
        return sc["dur"] * idx
    idx = int(idx)
    if 0 <= idx < len(cues):
        return cues[idx]
    if cues:
        return cues[-1] + 0.4 * (idx - len(cues) + 1)
    return default + 0.4 * idx


def item_times(sc, items, first_line=1):
    """Instante de aparición de cada elemento.

    Si el elemento trae `at`, se usa esa frase. Si no, el elemento i aparece con la
    frase first_line+i mientras existan; si hay más elementos que frases, se reparten.
    """
    cues = sc.get("cues") or [0.3]
    n = len(items)
    if first_line is None:
        first_line = 0 if n >= len(cues) else 1
    out = []
    avail = cues[first_line:] if len(cues) > first_line else []
    for i, it in enumerate(items):
        if isinstance(it, dict) and "at" in it:
            out.append(cue(sc, it["at"]) + float(it.get("delay", 0)))
        elif len(avail) >= n:
            out.append(avail[i])
        else:
            t0 = cues[min(first_line, len(cues) - 1)] if cues else 0.3
            t1 = max(t0 + 0.5, sc.get("speech_end", sc["dur"]) - 0.8)
            out.append(t0 + (t1 - t0) * (i / max(1, n)))
    return out


def norm_items(items):
    out = []
    for it in items or []:
        if isinstance(it, str):
            out.append({"text": it})
        else:
            out.append(dict(it))
    return out


# --------------------------------------------------------------------------- componentes
def heading(c, ctx, sc, t, title=None, kicker=None, y=232, align="left"):
    title = title if title is not None else sc.get("heading")
    kicker = kicker if kicker is not None else sc.get("kicker")
    a1 = ctx.th["a1"]
    x = LEFT if align == "left" else W / 2
    if kicker:
        ak = appear(t, 0.0, 0.45)
        pill(c, x + (1 - ak) * -30 if align == "left" else x, y - 112, kicker.upper(), "xbold", 24,
             "#0B0618", ctx.th["a3"], ak, align=align)
    if title:
        at = appear(t, 0.08, 0.55)
        size = fit_size(title, "display", 84, RIGHT - LEFT)
        draw_text(c, title.upper(), x + (1 - at) * (-40 if align == "left" else 0), y, "display", size,
                  WHITE, at, align=align, glow=a1, glow_a=0.35, shadow=(0, 6, 12, 0.6))
        bw = 180 * appear(t, 0.25, 0.7)
        bx = x if align == "left" else x - bw / 2
        rrect(c, bx, y + 22, bw, 7, 3.5, paint(a1, at, shader=lin_grad(bx, 0, bx + 180, 0, [a1, ctx.th["a2"]])))


def source_tag(c, ctx, sc, t, y=None):
    src = sc.get("source")
    if not src:
        return
    a = appear(t, 0.9, 0.5)
    y = y if y is not None else BOTTOM - 4
    txt = "FUENTE: " + src.upper()
    size = 21
    w = text_w(txt, "bold", size, 0.06) + 44
    x = RIGHT - w
    rrect(c, x, y, w, 40, 20, paint("#000000", 0.45 * a))
    icon(c, "badge-check", x + 22, y + 20, 22, ctx.th["a2"], a)
    draw_text(c, txt, x + 38, y + 28, "bold", size, MUTED, a, tracking=0.06)


def bullet_height(it, w, size=42, icon_r=36):
    lines = wrap(it["text"], "bold", size, w - icon_r * 2 - 50)
    return max(icon_r * 2 + 20, len(lines) * size * 1.2 + 34)


def bullet_row(c, ctx, x, y, w, it, a, active, accent, size=42, icon_r=36):
    """Fila de lista con icono. Devuelve la altura usada."""
    lines = wrap(it["text"], "bold", size, w - icon_r * 2 - 50)
    h = max(icon_r * 2 + 20, len(lines) * size * 1.2 + 34)
    if a <= 0.003:
        return h
    dx = (1 - a) * 60
    if active:
        rrect(c, x - 22 + dx, y - 10, w + 44, h + 4, 24, paint(accent, 0.13 * a))
        rrect(c, x - 22 + dx, y - 10, 6, h + 4, 3, paint(accent, a))
    ic = it.get("icon", "chevron-right")
    icon_badge(c, ic, x + icon_r + dx, y + h / 2 - 3, icon_r, it.get("color", accent), a)
    ty = y + h / 2 - (len(lines) * size * 1.2) / 2 + size * 0.88
    for i, ln in enumerate(lines):
        draw_text(c, ln, x + icon_r * 2 + 34 + dx, ty + i * size * 1.2, "bold", size,
                  WHITE if active else mix(WHITE, MUTED, 0.35), a, shadow=(0, 3, 6, 0.5))
    return h


# --------------------------------------------------------------------------- escenas
def s_title(c, ctx, sc, t):
    th = ctx.th
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=rad_grad(W / 2, H * 0.47, W * 0.55,
               ["#000000", "#000000"], alphas=[0.62, 0.0])))
    y = sc.get("y", 470)
    if sc.get("kicker"):
        a = appear(t, 0.05, 0.5)
        pill(c, W / 2, y - 175 - (1 - a) * 20, sc["kicker"].upper(), "xbold", 28, "#0B0618", th["a3"], a,
             align="center", pad_x=26, pad_y=14)
    title = sc["title"].upper()
    size = sc.get("size", 150)
    lines = wrap(title, "display", size, 1640)
    while len(lines) > 2 and size > 70:
        size -= 8
        lines = wrap(title, "display", size, 1640)
    lead = size * 1.02
    y0 = y - (len(lines) - 1) * lead / 2 + cap_h("display", size) / 2
    zoom = 1 + 0.025 * clamp(t / max(1, sc["dur"]))
    c.save()
    c.translate(W / 2, y)
    c.scale(zoom, zoom)
    c.translate(-W / 2, -y)
    for i, ln in enumerate(lines):
        a = appear(t, 0.2 + i * 0.14, 0.6)
        ly = y0 + i * lead
        c.save()
        c.clipRect(skia.Rect.MakeLTRB(0, ly - size * 1.05, W, ly + size * 0.25))
        sh = lin_grad(0, ly - size, 0, ly, ["#FFFFFF", mix("#FFFFFF", th["a3"], 0.35)])
        draw_text(c, ln, W / 2, ly + (1 - a) * size * 0.9, "display", size, WHITE, a, align="center",
                  glow=th["a1"], glow_a=0.75, glow_blur=size * 0.16, shader=sh, shadow=(0, 8, 16, 0.6))
        c.restore()
    c.restore()
    if sc.get("subtitle"):
        a = appear(t, 0.65, 0.6)
        sy = y0 + (len(lines) - 1) * lead + 92
        for i, ln in enumerate(wrap(sc["subtitle"], "bold", 44, 1500)):
            draw_text(c, ln, W / 2, sy + i * 56 + (1 - a) * 18, "bold", 44, WHITE, a, align="center",
                      shadow=(0, 3, 8, 0.8))
    if sc.get("note"):
        a = appear(t, 1.0, 0.6) * 0.9
        draw_text(c, sc["note"], W / 2, sc.get("note_y", 815), "semi", 26, MUTED, a, align="center",
                  shadow=(0, 2, 6, 0.9))


def s_chapter(c, ctx, sc, t):
    th = ctx.th
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=lin_grad(0, 0, W * 0.7, 0, ["#000000", "#000000"],
               alphas=[0.72, 0.0])))
    a = appear(t, 0.0, 0.6)
    num = str(sc.get("number", ""))
    x = 170
    if num:
        draw_text(c, num, x - (1 - a) * 80, 600, "display", 300, th["a1"], a * 0.9, stroke=4,
                  stroke_color=th["a1"], glow=th["a1"], glow_a=0.5)
        draw_text(c, num, x - (1 - a) * 80, 600, "display", 300, "#0B0618", a * 0.85)
    tx = x + (text_w(num, "display", 300) + 60 if num else 0)
    a2 = appear(t, 0.25, 0.6)
    pill(c, tx, 400, sc.get("kicker", "CAPÍTULO").upper(), "xbold", 24, "#0B0618", th["a3"], a2)
    size = 110
    lines = wrap(sc["title"].upper(), "display", size, RIGHT - tx)
    while len(lines) > 2 and size > 60:
        size -= 8
        lines = wrap(sc["title"].upper(), "display", size, RIGHT - tx)
    for i, ln in enumerate(lines):
        ai = appear(t, 0.35 + 0.12 * i, 0.6)
        draw_text(c, ln, tx + (1 - ai) * 50, 540 + i * size * 1.02, "display", size, WHITE, ai,
                  glow=th["a1"], glow_a=0.4, shadow=(0, 6, 14, 0.7))


def s_statement(c, ctx, sc, t):
    """Frase grande palabra a palabra. Palabras entre *asteriscos* van en color de acento."""
    th = ctx.th
    text = sc["text"]
    tokens = re.findall(r"\*[^*]+\*|\S+", text)
    words = []
    for tk in tokens:
        if tk.startswith("*"):
            for w_ in tk.strip("*").split():
                words.append((w_.upper(), True))
        else:
            words.append((tk.upper(), False))
    size = sc.get("size", 120)
    maxw = 1560

    def layout(sz):
        lines, cur, cw = [], [], 0
        sp = sz * 0.28
        for w_, hl in words:
            ww = text_w(w_, "display", sz)
            if cur and cw + sp + ww > maxw:
                lines.append((cur, cw))
                cur, cw = [], 0
            cw = cw + (sp if cur else 0) + ww
            cur.append((w_, hl, ww))
        if cur:
            lines.append((cur, cw))
        return lines

    lines = layout(size)
    while len(lines) > 4 and size > 60:
        size -= 8
        lines = layout(size)
    lead = size * 1.08
    y0 = sc.get("y", 500) - (len(lines) - 1) * lead / 2 + cap_h("display", size) / 2
    total = sum(len(l[0]) for l in lines)
    t_start = cue(sc, sc.get("at", 0)) * 0.0 + 0.15
    span = sc.get("reveal", min(2.2, max(0.8, total * 0.16)))
    k = 0
    for li, (ws, lw) in enumerate(lines):
        x = W / 2 - lw / 2
        for w_, hl, ww in ws:
            a = appear(t, t_start + span * k / max(1, total), 0.35)
            colr = th["a1"] if hl else WHITE
            sc_ = 0.7 + 0.3 * ease_out_back(prog(t, t_start + span * k / max(1, total), 0.4))
            cx = x + ww / 2
            ly = y0 + li * lead
            c.save()
            c.translate(cx, ly)
            c.scale(sc_, sc_)
            draw_text(c, w_, -ww / 2, 0, "display", size, colr, a, glow=th["a1"] if hl else None,
                      glow_a=0.6, shadow=(0, 6, 14, 0.7))
            c.restore()
            x += ww + size * 0.28
            k += 1


def s_bullets(c, ctx, sc, t):
    heading(c, ctx, sc, t)
    items = norm_items(sc.get("items"))
    times = item_times(sc, items, sc.get("first"))
    accent = ctx.th["a1"]
    size = sc.get("size", 46 if len(items) <= 4 else 42)
    x = LEFT + 10
    w = RIGHT - LEFT - 20
    cols = 2 if len(items) > 5 else 1
    if cols == 2:
        w = (RIGHT - LEFT - 60) / 2
        size = min(size, 34)
    per_col = math.ceil(len(items) / cols)
    ir = 32 if cols == 2 else 38
    gap = 18 if cols == 2 else 26
    col_h = max(sum(bullet_height(items[ci * per_col + j], w, size, ir) + gap
                    for j in range(per_col) if ci * per_col + j < len(items)) - gap for ci in range(cols))
    y = max(300, 300 + (560 - col_h) / 2)
    shown = [i for i, tt in enumerate(times) if t >= tt - 0.001]
    active = shown[-1] if shown else -1
    for ci in range(cols):
        yy = y
        for j in range(per_col):
            i = ci * per_col + j
            if i >= len(items):
                break
            a = appear(t, times[i], 0.45)
            h = bullet_row(c, ctx, x + ci * (w + 60), yy, w, items[i], a, i == active, accent, size, ir)
            yy += h + gap
    source_tag(c, ctx, sc, t)


def _count_value(value, p):
    m = re.search(r"(\d+(?:[.,]\d+)?)", value)
    if not m or p >= 1:
        return value
    num = m.group(1)
    dec = 0
    sep = None
    if "," in num:
        sep = ","
        dec = len(num.split(",")[1])
    elif "." in num and len(num.split(".")[1]) != 3:
        sep = "."
        dec = len(num.split(".")[1])
    v = float(num.replace(".", "").replace(",", ".")) if sep == "," else float(num.replace(",", ""))
    cur = v * p
    s = f"{cur:.{dec}f}"
    if sep == ",":
        s = s.replace(".", ",")
    return value[:m.start(1)] + s + value[m.end(1):]


def s_stat(c, ctx, sc, t):
    th = ctx.th
    accent = sc.get("color", th["a1"])
    cx, cy = W / 2, 485
    R = 315
    t0 = cue(sc, sc.get("at", 0)) if sc.get("at") is not None else 0.1
    a = appear(t, t0, 0.5)
    # halo y anillos
    c.drawCircle(cx, cy, R + 120, skia.Paint(AntiAlias=True, Shader=rad_grad(cx, cy, R + 120, [accent, accent],
                 alphas=[0.30 * a, 0.0])))
    c.drawCircle(cx, cy, R - 4, paint("#05020C", 0.35 * a))
    ring = paint(accent, 0.55 * a, stroke=3)
    ring.setPathEffect(skia.DashPathEffect.Make([18, 14], t * 40))
    c.drawCircle(cx, cy, R + 30, ring)
    arc = paint(accent, a, stroke=8, cap_round=True)
    sweep = 360 * appear(t, t0 + 0.1, 1.3, ease_in_out)
    c.drawArc(skia.Rect.MakeLTRB(cx - R, cy - R, cx + R, cy + R), -90, sweep, False, arc)
    if sc.get("kicker"):
        pill(c, cx, 92, sc["kicker"].upper(), "xbold", 24, "#0B0618", th["a3"], appear(t, 0, 0.4),
             align="center")
    if sc.get("icon"):
        icon(c, sc["icon"], cx, cy - 185, 66, WHITE, a, glow=accent)
    val = str(sc["value"])
    shown = _count_value(val, appear(t, t0 + 0.1, 1.2, ease_out_expo_safe)) if sc.get("count", True) else val
    size = fit_size(val, "display", sc.get("size", 220), 2 * R - 90)
    sc_ = 0.85 + 0.15 * ease_out_back(prog(t, t0, 0.6))
    c.save()
    c.translate(cx, cy + cap_h("display", size) / 2 - 10)
    c.scale(sc_, sc_)
    draw_text(c, shown, 0, 0, "display", size, WHITE, a, align="center", glow=accent, glow_a=0.8,
              glow_blur=size * 0.12, shadow=(0, 8, 18, 0.7))
    c.restore()
    if sc.get("label"):
        al = appear(t, t0 + 0.45, 0.5)
        for i, ln in enumerate(wrap(sc["label"].upper(), "xbold", 32, 2 * R - 190)):
            draw_text(c, ln, cx, cy + 150 + i * 40, "xbold", 32, th["a3"], al, align="center",
                      tracking=0.04, shadow=(0, 3, 8, 0.7))
    if sc.get("sub"):
        asb = appear(t, cue(sc, sc.get("sub_at", 1)), 0.5)
        lines = wrap(sc["sub"], "semi", 34, 1300)
        for i, ln in enumerate(lines):
            draw_text(c, ln, cx, 878 + i * 42 - (len(lines) - 1) * 42, "semi", 34, WHITE, asb, align="center",
                      shadow=(0, 3, 8, 0.9))
    source_tag(c, ctx, sc, t, y=805)


def ease_out_expo_safe(x):
    return 1 - (1 - clamp(x)) ** 4


def s_compare(c, ctx, sc, t):
    heading(c, ctx, sc, t)
    cols = sc["columns"]
    n = len(cols)
    gap = 40
    cw = (RIGHT - LEFT - gap * (n - 1)) / n
    need = 0
    for cd in cols:
        isz = cd.get("size", 30 if n == 2 else 27)
        hh = 100 + (108 if cd.get("value") else 0) + 34 + 30
        for it in norm_items(cd.get("items")):
            hh += len(wrap(it["text"], "semi", isz, cw - 120)) * isz * 1.22 + 16
        need = max(need, hh)
    ch = min(560, max(360, need))
    y0 = 300 + (560 - ch) / 2
    accents = [ctx.th["a2"], ctx.th["a1"], ctx.th["a3"]]
    for i, cd in enumerate(cols):
        acc = cd.get("color", accents[i % 3])
        t0 = cue(sc, cd.get("at", i + 1))
        a = appear(t, t0, 0.55)
        if a <= 0.003:
            continue
        x = LEFT + i * (cw + gap)
        yy = y0 + (1 - a) * 60
        panel(c, x, yy, cw, ch, acc, a, border_a=0.8 if cd.get("highlight") else 0.4)
        if cd.get("badge"):
            pill(c, x + cw - 24, yy - 18, cd["badge"].upper(), "xbold", 20, "#0B0618", acc, a, align="right")
        tsize = fit_size(cd["title"].upper(), "display", 58, cw - 60)
        draw_text(c, cd["title"].upper(), x + 32, yy + 82, "display", tsize, WHITE, a)
        ty = yy + 100
        if cd.get("value"):
            vs = fit_size(cd["value"], "display", 88, cw - 60)
            draw_text(c, cd["value"], x + 32, ty + 88, "display", vs, acc, a, glow=acc, glow_a=0.45)
            ty += 108
        rrect(c, x + 32, ty + 10, cw - 64, 2, 1, paint("#FFFFFF", 0.15 * a))
        ty += 34
        items = norm_items(cd.get("items"))
        isize = cd.get("size", 30 if n == 2 else 27)
        for j, it in enumerate(items):
            tj = t0 + 0.35 + 0.18 * j if "at" not in it else cue(sc, it["at"])
            aj = appear(t, tj, 0.4)
            lines = wrap(it["text"], "semi", isize, cw - 120)
            kind = it.get("mark", "check")
            mx_, my_ = x + 52, ty + isize * 0.55
            if kind == "check":
                c.drawCircle(mx_, my_, 17, paint(GOOD, 0.18 * aj))
                check_mark(c, mx_, my_, 26, prog(t, tj, 0.35), GOOD, aj, 4)
            elif kind == "x":
                c.drawCircle(mx_, my_, 17, paint(BAD, 0.18 * aj))
                cross_mark(c, mx_, my_, 26, prog(t, tj, 0.35), BAD, aj, 4)
            else:
                c.drawCircle(mx_, my_, 7, paint(acc, aj))
            for k, ln in enumerate(lines):
                draw_text(c, ln, x + 84 + (1 - aj) * 20, ty + isize * 0.85 + k * isize * 1.22, "semi", isize,
                          WHITE, aj)
            ty += len(lines) * isize * 1.22 + 16
    source_tag(c, ctx, sc, t)


def s_table(c, ctx, sc, t):
    heading(c, ctx, sc, t)
    rows = sc["rows"]
    n = len(rows)
    gap = 12
    rh = min(86, (BOTTOM - 300 - gap * (n - 1) - (50 if sc.get("footer") else 0)) / n)
    block = n * rh + (n - 1) * gap + (50 if sc.get("footer") else 0)
    y0 = 300 + max(0, (550 - block) / 2)
    times = item_times(sc, [r if isinstance(r, dict) else {} for r in rows], sc.get("first"))
    if sc.get("stagger"):
        times = [cue(sc, sc.get("first") or 1) + i * sc["stagger"] for i in range(n)]
    hl = sc.get("highlight", [])
    hl = hl if isinstance(hl, list) else [hl]
    lsize = min(38, rh * 0.45)
    for i, r in enumerate(rows):
        if isinstance(r, dict):
            label, value, ic = r.get("label"), r.get("value"), r.get("icon")
        else:
            label, value, ic = r[0], r[1], (r[2] if len(r) > 2 else None)
        a = appear(t, times[i], 0.4)
        if a <= 0.003:
            continue
        y = y0 + i * (rh + gap)
        x = LEFT + (1 - a) * 50
        is_hl = i in hl
        acc = ctx.th["a1"] if is_hl else ctx.th["a2"]
        rrect(c, x, y, RIGHT - LEFT, rh, 18, paint("#140A28", 0.80 * a))
        if is_hl:
            rrect(c, x, y, RIGHT - LEFT, rh, 18, paint(acc, 0.16 * a))
            rrect(c, x, y, RIGHT - LEFT, rh, 18, paint(acc, 0.8 * a, stroke=2.5))
        rrect(c, x, y, 8, rh, 4, paint(acc, a))
        tx = x + 40
        if ic:
            icon(c, ic, x + 52, y + rh / 2, rh * 0.48, acc, a)
            tx = x + 96
        draw_text(c, label, tx, y + rh / 2 + cap_h("bold", lsize) / 2, "bold", lsize, WHITE, a)
        vs = fit_size(value, "xbold", lsize + 4, (RIGHT - LEFT) * 0.48)
        draw_text(c, value, x + RIGHT - LEFT - 34, y + rh / 2 + cap_h("xbold", vs) / 2, "xbold", vs,
                  ctx.th["a3"] if is_hl else WHITE, a, align="right")
    if sc.get("footer"):
        af = appear(t, cue(sc, sc.get("footer_at", len(sc.get("cues", [])) - 1)), 0.5)
        draw_text(c, sc["footer"], LEFT, y0 + n * (rh + gap) + 34, "semi", 28, MUTED, af)
    source_tag(c, ctx, sc, t)


def s_verdict(c, ctx, sc, t):
    th = ctx.th
    q = sc.get("question", "")
    aq = appear(t, 0.05, 0.5)
    if sc.get("kicker"):
        pill(c, W / 2, 140, sc["kicker"].upper(), "xbold", 24, "#0B0618", th["a3"], aq, align="center")
    lines = wrap(q, "xbold", 56, 1500)
    for i, ln in enumerate(lines):
        draw_text(c, ln, W / 2, 255 + i * 66, "xbold", 56, WHITE, aq, align="center", shadow=(0, 4, 10, 0.7))
    verdict = sc["verdict"]
    colr = sc.get("color") or VERDICT_COLORS.get(verdict.lower(), th["a1"])
    t0 = cue(sc, sc.get("at", 1))
    p = prog(t, t0, 0.45)
    if p > 0:
        s = lerp(1.7, 1.0, ease_out_cubic(p))
        a = clamp(p * 1.6)
        size = fit_size(verdict.upper(), "display", 150, 1100)
        tw = text_w(verdict.upper(), "display", size)
        bw, bh = tw + 110, size * 1.12
        cy = 520 + (len(lines) - 1) * 33
        c.save()
        c.translate(W / 2, cy)
        c.rotate(-5)
        c.scale(s, s)
        rrect(c, -bw / 2, -bh / 2, bw, bh, 26, paint(colr, 0.14 * a))
        rrect(c, -bw / 2, -bh / 2, bw, bh, 26, paint(colr, a, stroke=9))
        rrect(c, -bw / 2 + 16, -bh / 2 + 16, bw - 32, bh - 32, 16, paint(colr, 0.5 * a, stroke=2))
        draw_text(c, verdict.upper(), 0, cap_h("display", size) / 2, "display", size, colr, a, align="center",
                  glow=colr, glow_a=0.55)
        c.restore()
        if p < 1:  # destello del sello
            c.drawCircle(W / 2, cy, 380 * p, paint(colr, 0.25 * (1 - p), blur=40))
    if sc.get("note"):
        an = appear(t, cue(sc, sc.get("note_at", 2)), 0.5)
        nl = wrap(sc["note"], "semi", 38, 1400)
        for i, ln in enumerate(nl):
            draw_text(c, ln, W / 2, 755 + (len(lines) - 1) * 33 + i * 48, "semi", 38, MUTED, an, align="center",
                      shadow=(0, 3, 8, 0.8))
    source_tag(c, ctx, sc, t)


# ---- mapa ilustrativo (forma original, NO es el mapa oficial)
_LAND = [(40, 120), (250, 112), (420, 108), (560, 98), (700, 92), (712, 150), (730, 230), (760, 330),
         (795, 440), (835, 560), (872, 660), (884, 740), (862, 805), (812, 858), (750, 878), (700, 850),
         (660, 790), (628, 700), (598, 620), (566, 545), (546, 470), (528, 400), (490, 330), (430, 278),
         (350, 250), (260, 238), (170, 246), (90, 254), (40, 246)]
_KEYS = [(800, 902, 22, 9), (760, 920, 20, 8), (718, 936, 19, 8), (676, 947, 17, 7), (634, 955, 16, 7),
         (594, 960, 14, 6), (556, 963, 12, 6)]
_LAKE = (712, 575, 46, 38)
MAP_X, MAP_Y, MAP_S = 110, 118, 0.80


def _mp(x, y):
    return MAP_X + x * MAP_S, MAP_Y + y * MAP_S


def _smooth_path(pts):
    path = skia.Path()
    n = len(pts)
    P = [_mp(*p) for p in pts]
    mids = [((P[i][0] + P[(i + 1) % n][0]) / 2, (P[i][1] + P[(i + 1) % n][1]) / 2) for i in range(n)]
    path.moveTo(*mids[-1])
    for i in range(n):
        path.quadTo(P[i][0], P[i][1], mids[i][0], mids[i][1])
    path.close()
    return path


def s_map(c, ctx, sc, t):
    th = ctx.th
    land = _smooth_path(_LAND)
    a = appear(t, 0.0, 0.8)
    c.drawPath(land, paint("#22E4FF", 0.35 * a, blur=26))
    sh = lin_grad(*_mp(100, 100), *_mp(850, 900), ["#123B3F", "#0E2A3A", "#173A2C"])
    c.drawPath(land, paint("#123B3F", a, shader=sh))
    # textura de curvas de nivel
    c.save()
    c.clipPath(land, skia.ClipOp.kIntersect, True)
    for i in range(14):
        cx_, cy_ = _mp(520, 520)
        c.drawCircle(cx_ + 40 * math.sin(i), cy_ + 30 * math.cos(i * 1.3), 40 + i * 42,
                     paint("#5FF5D2", 0.06 * a, stroke=1.4))
    c.restore()
    outline = paint("#5FF5FF", 0.9 * a, stroke=3)
    set_trim(outline, appear(t, 0, 1.6, ease_in_out))
    c.drawPath(land, outline)
    lx, ly = _mp(_LAKE[0], _LAKE[1])
    c.drawOval(skia.Rect.MakeXYWH(lx - _LAKE[2] * MAP_S, ly - _LAKE[3] * MAP_S, 2 * _LAKE[2] * MAP_S,
                                  2 * _LAKE[3] * MAP_S), paint("#0A3A5E", a))
    for (kx, ky, rx, ry) in _KEYS:
        x_, y_ = _mp(kx, ky)
        c.drawOval(skia.Rect.MakeXYWH(x_ - rx * MAP_S, y_ - ry * MAP_S, 2 * rx * MAP_S, 2 * ry * MAP_S),
                   paint("#173A2C", a))
        c.drawOval(skia.Rect.MakeXYWH(x_ - rx * MAP_S, y_ - ry * MAP_S, 2 * rx * MAP_S, 2 * ry * MAP_S),
                   paint("#5FF5FF", 0.8 * a, stroke=2))
    draw_text(c, sc.get("map_label", "LEONIDA"), _mp(250, 560)[0], _mp(250, 560)[1], "display", 46, "#5FF5FF",
              0.30 * a, tracking=0.3, align="center")
    regions = sc.get("regions", [])
    times = item_times(sc, regions, sc.get("first"))
    active = -1
    for i, tt in enumerate(times):
        if t >= tt:
            active = i
    pal = [th["a1"], th["a2"], th["a3"], "#00E0A4", "#FF8A3D", "#9C7BFF"]
    for i, rg in enumerate(regions):
        ai = appear(t, times[i], 0.5)
        if ai <= 0.003:
            continue
        px, py = _mp(*rg["pos"])
        rc = rg.get("color", pal[i % len(pal)])
        is_act = i == active
        if is_act:
            pulse = (t * 1.1) % 1.0
            c.drawCircle(px, py, 18 + 60 * pulse, paint(rc, 0.6 * (1 - pulse) * ai, stroke=3))
            c.drawCircle(px, py, 46, paint(rc, 0.35 * ai, blur=18))
        c.drawCircle(px, py, 13 if is_act else 9, paint(rc, ai))
        c.drawCircle(px, py, 13 if is_act else 9, paint("#FFFFFF", 0.9 * ai, stroke=2.5))
        lab = rg["name"].upper()
        ls = 30 if is_act else 22
        off = rg.get("label_off", (22, -16))
        draw_text(c, lab, px + off[0], py + off[1], "xbold", ls, WHITE if is_act else MUTED, ai,
                  shadow=(0, 2, 6, 0.95), align=rg.get("label_align", "left"))
    # tarjeta de información de la región activa
    if active >= 0:
        rg = regions[active]
        rc = rg.get("color", pal[active % len(pal)])
        ta = times[active]
        ac = appear(t, ta, 0.45)
        tlines = wrap(rg.get("text", ""), "semi", 34, 720 - 80)
        x, w_ = 1060, 720
        h_ = max(380, 270 + len(tlines) * 46 + 40)
        y = 140 + (640 - h_) / 2
        panel(c, x + (1 - ac) * 40, y, w_, h_, rc, ac)
        x += (1 - ac) * 40
        icon_badge(c, rg.get("icon", "map-pin"), x + 80, y + 90, 46, rc, ac)
        ns = fit_size(rg["name"].upper(), "display", 76, w_ - 190)
        draw_text(c, rg["name"].upper(), x + 150, y + 118, "display", ns, WHITE, ac)
        if rg.get("tag"):
            pill(c, x + 40, y + 160, rg["tag"].upper(), "xbold", 20, "#0B0618", rc, ac)
        ty = y + 260
        for k, ln in enumerate(wrap(rg.get("text", ""), "semi", 34, w_ - 80)):
            draw_text(c, ln, x + 40, ty + k * 46, "semi", 34, WHITE, ac)
    draw_text(c, sc.get("disclaimer", "Ilustración aproximada · no es el mapa oficial"), 1780, 815,
              "semi", 22, MUTED, 0.75 * a, align="right")


def s_profile(c, ctx, sc, t):
    th = ctx.th
    acc = sc.get("color", th["a1"])
    a = appear(t, 0.0, 0.6)
    x, y, w_, h_ = LEFT, 170, 600, 660
    panel(c, x - (1 - a) * 60, y, w_, h_, acc, a)
    x -= (1 - a) * 60
    cx, cy = x + w_ / 2, y + 210
    c.drawCircle(cx, cy, 165, paint(acc, 0.35 * a, blur=40))
    c.drawCircle(cx, cy, 140, paint(acc, a, shader=lin_grad(cx - 140, cy - 140, cx + 140, cy + 140,
                                                            [acc, mix(acc, "#0B0618", 0.6)])))
    c.drawCircle(cx, cy, 140, paint("#FFFFFF", 0.4 * a, stroke=3))
    ring = paint(acc, 0.7 * a, stroke=2)
    ring.setPathEffect(skia.DashPathEffect.Make([10, 10], t * 30))
    c.drawCircle(cx, cy, 160, ring)
    if sc.get("icon"):
        icon(c, sc["icon"], cx, cy, 130, "#FFFFFF", 0.9 * a, stroke=1.6)
    else:
        init = sc.get("initials") or "".join(p[0] for p in sc["name"].split()[:2]).upper()
        draw_text(c, init, cx, cy + cap_h("display", 120) / 2, "display", 120, WHITE, a, align="center")
    ns = 64
    nlines = wrap(sc["name"].upper(), "display", ns, w_ - 60)
    while len(nlines) > 2 and ns > 40:
        ns -= 6
        nlines = wrap(sc["name"].upper(), "display", ns, w_ - 60)
    for i, ln in enumerate(nlines):
        draw_text(c, ln, cx, y + 460 + i * ns * 1.05, "display", ns, WHITE, a, align="center")
    if sc.get("role"):
        pill(c, cx, y + 500 + (len(nlines) - 1) * ns * 1.05, sc["role"].upper(), "xbold", 22, "#0B0618", acc, a,
             align="center")
    if sc.get("tag"):
        draw_text(c, sc["tag"], cx, y + h_ - 40, "semi", 24, MUTED, a, align="center")
    facts = norm_items(sc.get("facts"))
    times = item_times(sc, facts, sc.get("first"))
    shown = [i for i, tt in enumerate(times) if t >= tt]
    act = shown[-1] if shown else -1
    fx = 820
    fw = RIGHT - fx
    fsize = sc.get("size", 38)
    total_h = sum(bullet_height(f, fw, fsize, 32) + 18 for f in facts) - 18
    fy = 170 + max(0, (660 - total_h) / 2)
    if sc.get("heading"):
        draw_text(c, sc["heading"].upper(), fx, 222, "display", 56, th["a3"], appear(t, 0.2, 0.5))
        fy = max(fy, 270)
    for i, f in enumerate(facts):
        ai = appear(t, times[i], 0.45)
        f.setdefault("icon", "sparkles")
        hh = bullet_row(c, ctx, fx, fy, fw, f, ai, i == act, acc, fsize, 32)
        fy += hh + 18
    source_tag(c, ctx, sc, t)


def s_timeline(c, ctx, sc, t):
    heading(c, ctx, sc, t)
    ev = sc["events"]
    times = item_times(sc, ev, sc.get("first"))
    th = ctx.th
    spacing = sc.get("spacing", 430)
    ly = 540
    active = 0
    for i, tt in enumerate(times):
        if t >= tt:
            active = i
    # cámara: mantiene el evento activo visible
    total_w = spacing * (len(ev) - 1)
    view_w = RIGHT - LEFT - 300
    target = 0 if total_w <= view_w else clamp((active * spacing - view_w * 0.5) / max(1, total_w - view_w)) * (
        total_w - view_w)
    # interpolación suave hacia el objetivo
    prev_target = 0
    if active > 0 and total_w > view_w:
        prev_target = clamp(((active - 1) * spacing - view_w * 0.5) / max(1, total_w - view_w)) * (total_w - view_w)
    k = appear(t, times[active], 0.8, ease_in_out) if active > 0 else 1
    camx = lerp(prev_target, target, k)
    x0 = LEFT + 150 - camx
    if total_w <= view_w:
        x0 = W / 2 - total_w / 2
    a_line = appear(t, 0.1, 1.0)
    c.drawLine(LEFT - 40, ly, RIGHT + 40, ly, paint("#FFFFFF", 0.18 * a_line, stroke=4))
    prog_x = x0 + active * spacing * 1.0
    c.drawLine(LEFT - 40, ly, min(RIGHT + 40, prog_x), ly, paint(th["a1"], 0.9 * a_line, stroke=5))
    scrolling = total_w > view_w
    c.save()
    c.clipRect(skia.Rect.MakeLTRB(LEFT - 60, 280, RIGHT + 60, BOTTOM + 10))
    if scrolling:
        c.saveLayer(None, None)
    for i, e in enumerate(ev):
        ai = appear(t, times[i], 0.5)
        if ai <= 0.003:
            continue
        x = x0 + i * spacing
        is_act = i == active
        acc = e.get("color", th["a1"] if is_act else th["a2"])
        c.drawCircle(x, ly, 30 if is_act else 20, paint(acc, 0.35 * ai, blur=14))
        c.drawCircle(x, ly, 16 if is_act else 11, paint(acc, ai))
        c.drawCircle(x, ly, 16 if is_act else 11, paint("#FFFFFF", ai, stroke=3))
        ds = fit_size(e["date"].upper(), "display", 72 if is_act else 58, spacing - 30)
        draw_text(c, e["date"].upper(), x, ly - 60 - (1 - ai) * 20, "display", ds, WHITE if is_act else MUTED, ai,
                  align="center", glow=acc if is_act else None, glow_a=0.5)
        tl = wrap(e["text"], "semi", 33, spacing - 50)
        for j, ln in enumerate(tl[:5]):
            draw_text(c, ln, x, ly + 84 + j * 42 + (1 - ai) * 20, "semi", 33, WHITE if is_act else MUTED, ai,
                      align="center")
    if scrolling:
        # desvanecido de los bordes: máscara de alfa sobre la capa de eventos
        mp = skia.Paint(Shader=lin_grad(LEFT - 60, 0, RIGHT + 60, 0, ["#000000"] * 4, [0, 0.1, 0.9, 1],
                                        alphas=[0.0, 1.0, 1.0, 0.0]))
        mp.setBlendMode(skia.BlendMode.kDstIn)
        c.drawRect(skia.Rect.MakeLTRB(LEFT - 60, 280, RIGHT + 60, BOTTOM + 10), mp)
        c.restore()
    c.restore()
    source_tag(c, ctx, sc, t)


def s_checklist(c, ctx, sc, t):
    heading(c, ctx, sc, t)
    items = norm_items(sc["items"])
    times = item_times(sc, items, sc.get("first"))
    n = len(items)
    cols = 2 if n > 5 else 1
    per = math.ceil(n / cols)
    cw = (RIGHT - LEFT - 50 * (cols - 1)) / cols
    size = 40 if cols == 1 else 32
    step = size * 2.65 if cols == 1 else size * 2.9
    y_start = 300 + max(0, (560 - (per * step - (step - size * 2.2))) / 2)
    for i, it in enumerate(items):
        ci, ri = i // per, i % per
        x = LEFT + ci * (cw + 50)
        y = y_start + ri * step
        a = appear(t, times[i], 0.4)
        if a <= 0.003:
            continue
        done = prog(t, times[i] + 0.35, 0.4)
        bx = x + (1 - a) * 40
        rrect(c, bx, y, cw, size * 2.2, 18, paint("#140A28", 0.8 * a))
        box = size * 1.15
        by = y + (size * 2.2 - box) / 2
        rrect(c, bx + 22, by, box, box, 10, paint(GOOD if done > 0 else MUTED, a, stroke=3))
        if done > 0:
            rrect(c, bx + 22, by, box, box, 10, paint(GOOD, 0.2 * a))
        check_mark(c, bx + 22 + box / 2, by + box / 2, box * 0.8, done, GOOD, a, 5)
        lines = wrap(it["text"], "bold", size, cw - box - 70)
        ty = y + size * 1.1 - (len(lines) - 1) * size * 0.6 + cap_h("bold", size) / 2
        for k, ln in enumerate(lines[:2]):
            draw_text(c, ln, bx + 50 + box, ty + k * size * 1.2, "bold", size, WHITE, a)
    source_tag(c, ctx, sc, t)


def s_quote(c, ctx, sc, t):
    th = ctx.th
    a = appear(t, 0.05, 0.6)
    icon(c, "quote", W / 2, 230, 110, th["a1"], a, glow=th["a1"])
    size = sc.get("size", 56)
    lines = wrap(sc["text"], "xbold", size, 1450)
    while len(lines) > 5 and size > 36:
        size -= 4
        lines = wrap(sc["text"], "xbold", size, 1450)
    y0 = 520 - (len(lines) - 1) * size * 1.25 / 2
    for i, ln in enumerate(lines):
        ai = appear(t, 0.25 + i * 0.12, 0.5)
        draw_text(c, ln, W / 2, y0 + i * size * 1.25 + (1 - ai) * 20, "xbold", size, WHITE, ai, align="center",
                  shadow=(0, 4, 10, 0.8))
    if sc.get("source"):
        asr = appear(t, 0.9, 0.5)
        pill(c, W / 2, y0 + len(lines) * size * 1.25 + 30, "— " + sc["source"].upper(), "xbold", 22, "#0B0618",
             th["a3"], asr, align="center")


def s_cards(c, ctx, sc, t):
    heading(c, ctx, sc, t)
    cards = norm_items(sc["cards"])
    times = item_times(sc, cards, sc.get("first"))
    n = len(cards)
    cols = sc.get("cols", 3 if n > 4 or n == 3 else 2)
    rows = math.ceil(n / cols)
    gap = 34
    cw = (RIGHT - LEFT - gap * (cols - 1)) / cols
    top = 300
    ch_max = (BOTTOM - top - gap * (rows - 1)) / rows
    need = 0
    for cd in cards:
        isz = cd.get("size", 28 if rows > 1 else 32)
        need = max(need, 150 + len(wrap(cd.get("text", ""), "semi", isz, cw - 60)[:6]) * isz * 1.28 + 20)
    ch = min(ch_max, max(220, need))
    top = 300 + max(0, (BOTTOM - 300 - (rows * ch + (rows - 1) * gap)) / 2)
    pal = [ctx.th["a1"], ctx.th["a2"], ctx.th["a3"], "#00E0A4", "#FF8A3D", "#9C7BFF"]
    for i, cd in enumerate(cards):
        a = appear(t, times[i], 0.5)
        if a <= 0.003:
            continue
        r, cc = divmod(i, cols)
        x = LEFT + cc * (cw + gap)
        y = top + r * (ch + gap) + (1 - a) * 40
        acc = cd.get("color", pal[i % len(pal)])
        panel(c, x, y, cw, ch, acc, a)
        icon_badge(c, cd.get("icon", "star"), x + 62, y + 66, 34, acc, a)
        ts = fit_size(cd.get("title", "").upper(), "display", 46, cw - 140)
        tl = wrap(cd.get("title", "").upper(), "display", ts, cw - 135)
        for k, ln in enumerate(tl[:2]):
            draw_text(c, ln, x + 118, y + 66 + cap_h("display", ts) / 2 + (k - (len(tl[:2]) - 1) / 2) * ts * 1.02,
                      "display", ts, WHITE, a)
        isz = cd.get("size", 28 if rows > 1 else 32)
        for k, ln in enumerate(wrap(cd.get("text", ""), "semi", isz, cw - 60)[:6]):
            draw_text(c, ln, x + 32, y + 150 + k * isz * 1.28, "semi", isz, mix(WHITE, MUTED, 0.2), a)
    source_tag(c, ctx, sc, t)


def s_versus(c, ctx, sc, t):
    th = ctx.th
    L, R = sc["left"], sc["right"]
    a = appear(t, 0.0, 0.5)
    cx = W / 2
    # cabeceras
    for side, d, acc in ((-1, L, th["a2"]), (1, R, th["a1"])):
        x = cx + side * 470
        draw_text(c, d["title"].upper(), x - side * (1 - a) * 60, 250, "display", 96, WHITE, a, align="center",
                  glow=acc, glow_a=0.6)
        if d.get("sub"):
            draw_text(c, d["sub"], x, 296, "semi", 28, MUTED, a, align="center")
    av = appear(t, 0.2, 0.5)
    c.drawCircle(cx, 220, 52, paint(th["a3"], av))
    draw_text(c, "VS", cx, 220 + cap_h("display", 50) / 2, "display", 50, "#0B0618", av, align="center")
    rows = sc["rows"]
    times = item_times(sc, rows, sc.get("first"))
    rh = min(100, (BOTTOM - 350) / max(1, len(rows)) - 12)
    y0 = 350 + max(0, (BOTTOM - 350 - len(rows) * (rh + 12)) / 2)
    shown = [i for i, tt in enumerate(times) if t >= tt]
    act = shown[-1] if shown else -1
    for i, r in enumerate(rows):
        ai = appear(t, times[i], 0.45)
        if ai <= 0.003:
            continue
        y = y0 + i * (rh + 12)
        is_act = i == act
        rrect(c, LEFT, y, RIGHT - LEFT, rh, 20, paint("#140A28", 0.82 * ai))
        if is_act:
            rrect(c, LEFT, y, RIGHT - LEFT, rh, 20, paint(th["a3"], 0.7 * ai, stroke=2.5))
        lab = r["label"].upper()
        ls = fit_size(lab, "xbold", 26, 330)
        lw = text_w(lab, "xbold", ls, 0.05) + 40
        rrect(c, cx - lw / 2, y + rh / 2 - 22, lw, 44, 22, paint(th["a3"], ai))
        draw_text(c, lab, cx, y + rh / 2 + cap_h("xbold", ls) / 2, "xbold", ls, "#0B0618", ai, align="center",
                  tracking=0.05)
        vs = min(40, rh * 0.42)
        lvs = fit_size(r["l"], "bold", vs, 560)
        rvs = fit_size(r["r"], "bold", vs, 560)
        draw_text(c, r["l"], cx - lw / 2 - 40 - (1 - ai) * 30, y + rh / 2 + cap_h("bold", lvs) / 2, "bold", lvs,
                  mix(WHITE, MUTED, 0.25), ai, align="right")
        draw_text(c, r["r"], cx + lw / 2 + 40 + (1 - ai) * 30, y + rh / 2 + cap_h("bold", rvs) / 2, "bold", rvs,
                  WHITE, ai)
    source_tag(c, ctx, sc, t)


def s_outro(c, ctx, sc, t):
    th = ctx.th
    c.drawRect(skia.Rect.MakeWH(W, H), skia.Paint(Shader=rad_grad(W / 2, H * 0.45, W * 0.6, ["#000000", "#000000"],
               alphas=[0.55, 0.0])))
    a = appear(t, 0.1, 0.5)
    draw_text(c, ctx.brand["name"], W / 2, 250, "display", 110, WHITE, a, align="center", glow=th["a1"],
              glow_a=0.7, tracking=0.04)
    draw_text(c, ctx.brand.get("tagline", ""), W / 2, 312, "semi", 34, MUTED, a, align="center")
    # botón de suscripción
    p = prog(t, cue(sc, sc.get("sub_at", 0)) + 0.3, 0.5)
    s = ease_out_back(p)
    if p > 0:
        bw, bh = 560, 120
        c.save()
        c.translate(W / 2, 450)
        c.scale(s, s)
        rrect(c, -bw / 2, -bh / 2 + 10, bw, bh, 60, paint("#000000", 0.5, blur=20))
        rrect(c, -bw / 2, -bh / 2, bw, bh, 60, paint("#FF1E3C"))
        icon(c, "bell-ring", -bw / 2 + 80, 0, 56, WHITE, 1, stroke=2.4)
        draw_text(c, "SUSCRÍBETE", -bw / 2 + 130, cap_h("display", 66) / 2, "display", 66, WHITE, 1, tracking=0.03)
        c.restore()
        # cursor que "pulsa"
        pc = prog(t, cue(sc, sc.get("sub_at", 0)) + 0.9, 0.6)
        if pc > 0:
            mxp = lerp(W / 2 + 480, W / 2 + 262, ease_out_cubic(pc))
            myp = lerp(590, 478, ease_out_cubic(pc))
            icon(c, "mouse-pointer-2", mxp, myp, 70, WHITE, clamp(pc * 3), stroke=1.8)
            if pc >= 1:
                rp = prog(t, cue(sc, sc.get("sub_at", 0)) + 1.5, 0.5)
                c.drawCircle(W / 2 + 245, 455, 30 + 70 * rp, paint(WHITE, 0.5 * (1 - rp), stroke=4))
    if sc.get("next"):
        an = appear(t, cue(sc, sc.get("next_at", 1)), 0.5)
        x, y, w_, h_ = W / 2 - 520, 580, 1040, 200
        panel(c, x, y + (1 - an) * 30, w_, h_, th["a2"], an)
        y += (1 - an) * 30
        icon_badge(c, "play", x + 90, y + h_ / 2, 50, th["a1"], an)
        draw_text(c, "SIGUIENTE VÍDEO", x + 170, y + 70, "xbold", 26, th["a3"], an, tracking=0.08)
        nl = wrap(sc["next"], "display", 50, w_ - 210)
        for i, ln in enumerate(nl[:2]):
            draw_text(c, ln.upper(), x + 170, y + 128 + i * 52, "display", 50, WHITE, an)


SCENES = {
    "title": s_title, "chapter": s_chapter, "statement": s_statement, "bullets": s_bullets, "stat": s_stat,
    "compare": s_compare, "table": s_table, "verdict": s_verdict, "map": s_map, "profile": s_profile,
    "timeline": s_timeline, "checklist": s_checklist, "quote": s_quote, "cards": s_cards, "versus": s_versus,
    "outro": s_outro,
}

DEFAULT_BG = {"title": "scenery", "chapter": "ocean", "outro": "scenery", "map": "map", "statement": "abstract"}
