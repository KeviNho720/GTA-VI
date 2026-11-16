"""Construye un vídeo completo a partir de un guion YAML.

Uso:
  python -m engine.render videos/01-....yaml [--out output] [--still 3,10.5] [--fast]
"""
import argparse
import json
import math
import os
import subprocess
import sys
import time

import numpy as np
import skia
import yaml

from . import audio as A
from .backgrounds import Backdrop, theme
from .gfx import (appear, cap_h, clamp, col, draw_text, ease_in_out, lin_grad, mix, paint, pill, prog, rrect,
                  text_w, wrap)
from .scenes import DEFAULT_BG, SCENES, item_times, cue, norm_items
from .tts import SR, Voice

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W, H, FPS = 1920, 1080, 30
DEFAULT_VOICE = os.environ.get("ZS_VOICE", os.path.join(ROOT, "voices", "es_ES-davefx-medium.onnx"))
CACHE = os.environ.get("ZS_CACHE", os.path.join(ROOT, ".cache", "tts"))

CAP_SIZE = 42
CAP_MAXW = 1480


class Ctx:
    pass


def load_brand():
    with open(os.path.join(ROOT, "channel", "brand.yaml"), encoding="utf-8") as f:
        return yaml.safe_load(f)


# --------------------------------------------------------------------------- temporización
def norm_line(ln):
    if isinstance(ln, str):
        return {"text": ln}
    return dict(ln)


def caption_chunks(text, start, dur):
    """Divide una frase en bloques de subtítulo de hasta 2 líneas, tiempo proporcional a caracteres."""
    lines = wrap(text, "xbold", CAP_SIZE, CAP_MAXW)
    blocks = [lines[i:i + 2] for i in range(0, len(lines), 2)]
    total = sum(len(" ".join(b)) for b in blocks) or 1
    out, t = [], start
    for b in blocks:
        d = dur * len(" ".join(b)) / total
        out.append({"lines": b, "start": t, "dur": d})
        t += d
    return out


def build_timeline(spec, voice, rate_gap=0.32):
    scenes = []
    t = 0.0
    voice_parts = []
    for si, raw in enumerate(spec["scenes"]):
        sc = dict(raw)
        sc["lines"] = [norm_line(l) for l in raw.get("lines", [])]
        lead = sc.get("lead", 0.45 if si == 0 else 0.3)
        lt = lead
        for ln in sc["lines"]:
            if ln.get("silent"):
                ln["start"], ln["dur"], ln["audio"] = lt, float(ln.get("dur", 1.0)), None
                lt += ln["dur"] + rate_gap
                continue
            a = voice.synth(ln["text"], ln.get("say"))
            rms = np.sqrt(np.mean(a ** 2)) + 1e-9
            a = np.tanh(a * (0.10 / rms) * 1.2) / 1.2
            ln["audio"] = a
            ln["start"] = lt
            ln["dur"] = len(a) / SR
            lt += ln["dur"] + float(ln.get("pause", rate_gap))
        speech_end = lt - rate_gap if sc["lines"] else lead
        tail = sc.get("tail", 0.55)
        dur = max(speech_end + tail, float(sc.get("min", 0)), float(sc.get("hold", 0)) if not sc["lines"] else 0)
        if not sc["lines"]:
            dur = float(sc.get("hold", 2.5))
        sc["start"] = t
        sc["dur"] = dur
        sc["speech_end"] = speech_end
        sc["cues"] = [ln["start"] for ln in sc["lines"]]
        sc["captions"] = []
        for ln in sc["lines"]:
            if ln.get("audio") is not None:
                voice_parts.append((t + ln["start"], ln["audio"]))
            if not ln.get("nocap"):
                sc["captions"] += caption_chunks(ln.get("caption", ln["text"]), t + ln["start"], ln["dur"])
        sc.setdefault("bg", DEFAULT_BG.get(sc["type"], "abstract"))
        scenes.append(sc)
        t += dur
    total = t
    vtrack = np.zeros(int(total * SR) + SR)
    for st, a in voice_parts:
        i = int(st * SR)
        vtrack[i:i + len(a)] += a[: len(vtrack) - i]
    return scenes, total, vtrack[: int(total * SR)]


def scene_sfx(sc):
    ev = []
    typ = sc["type"]
    if typ in ("bullets", "checklist", "cards", "versus", "timeline", "map"):
        key = {"bullets": "items", "checklist": "items", "cards": "cards", "versus": "rows", "timeline": "events",
               "map": "regions"}[typ]
        for tt in item_times(sc, norm_items(sc.get(key)), sc.get("first")):
            ev.append((tt, "tick", 0.22))
    elif typ == "table":
        rows = sc["rows"]
        times = item_times(sc, [r if isinstance(r, dict) else {} for r in rows], sc.get("first"))
        if sc.get("stagger"):
            times = [cue(sc, sc.get("first") or 1) + i * sc["stagger"] for i in range(len(rows))]
        ev += [(tt, "tick", 0.18) for tt in times]
    elif typ == "compare":
        for i, cd in enumerate(sc["columns"]):
            ev.append((cue(sc, cd.get("at", i + 1)), "tick", 0.3))
    elif typ == "stat":
        ev.append(((cue(sc, sc["at"]) if sc.get("at") is not None else 0.1), "impact", 0.5))
    elif typ == "verdict":
        ev.append((cue(sc, sc.get("at", 1)), "impact", 0.65))
    elif typ in ("title", "outro"):
        ev.append((0.15, "impact", 0.35))
    return ev


# --------------------------------------------------------------------------- HUD, subtítulos, transiciones
def draw_hud(c, ctx, T, total, sc):
    th = ctx.th
    a = clamp(T / 0.8)
    if a <= 0:
        return
    x, y, s = 48, 38, 60
    rrect(c, x, y, s, s, 14, paint(th["a1"], a, shader=lin_grad(x, y, x + s, y + s, [th["a1"], th["a2"]])))
    draw_text(c, "6", x + s / 2, y + s / 2 + cap_h("display", 44) / 2, "display", 44, "#0B0618", a, align="center")
    draw_text(c, ctx.brand["name"], x + s + 16, y + s / 2 + cap_h("bebas", 46) / 2, "bebas", 46, "#FFFFFF", a,
              tracking=0.06, shadow=(0, 2, 6, 0.8))
    tag = ctx.spec.get("tag")
    if tag and sc["type"] not in ("title",):
        pill(c, W - 48, y + 10, tag.upper(), "xbold", 20, "#FFFFFF", "#000000", 0.55 * a, align="right")
    # barra de progreso
    pw = W * clamp(T / total)
    c.drawRect(skia.Rect.MakeXYWH(0, H - 6, W, 6), paint("#000000", 0.4))
    c.drawRect(skia.Rect.MakeXYWH(0, H - 6, pw, 6), paint(th["a1"], 1, shader=lin_grad(0, 0, W, 0, [th["a1"], th["a2"]])))


def draw_captions(c, ctx, T, scenes):
    for sc in scenes:
        if sc["start"] - 0.5 <= T <= sc["start"] + sc["dur"] + 0.5:
            for ch in sc["captions"]:
                if ch["start"] <= T < ch["start"] + ch["dur"] + 0.12:
                    a = clamp((T - ch["start"]) / 0.12)
                    lines = ch["lines"]
                    lh = CAP_SIZE * 1.22
                    bw = max(text_w(l, "xbold", CAP_SIZE) for l in lines) + 64
                    bh = len(lines) * lh + 30
                    by = 1046 - bh
                    rrect(c, W / 2 - bw / 2, by, bw, bh, 20, paint("#05020C", 0.70 * a))
                    for i, l in enumerate(lines):
                        draw_text(c, l, W / 2, by + 15 + cap_h("xbold", CAP_SIZE) + 6 + i * lh, "xbold", CAP_SIZE,
                                  "#FFFFFF", a, align="center")
                    return


def draw_sweep(c, ctx, T, s0):
    p = (T - s0 + 0.25) / 0.6
    if not 0 <= p <= 1:
        return
    x = -500 + (W + 1000) * ease_in_out(p)
    path = skia.Path()
    path.moveTo(x - 140, H + 20)
    path.lineTo(x + 120, -20)
    path.lineTo(x + 330, -20)
    path.lineTo(x + 70, H + 20)
    path.close()
    th = ctx.th
    sh = lin_grad(x - 140, 0, x + 330, 0, [th["a1"], th["a2"], th["a1"]], alphas=[0.0, 0.42, 0.0])
    p_ = skia.Paint(AntiAlias=True, Shader=sh)
    c.drawPath(path, p_)
    c.drawLine(x + 225, -20, x - 35, H + 20, paint("#FFFFFF", 0.55 * math.sin(math.pi * p), stroke=3))


# --------------------------------------------------------------------------- render
def render_frame(c, ctx, scenes, total, T):
    i = 0
    while i + 1 < len(scenes) and T >= scenes[i + 1]["start"]:
        i += 1
    sc = scenes[i]
    t = T - sc["start"]
    tname = sc.get("theme", ctx.tname)
    ctx.th = theme(tname)
    prev = scenes[i - 1] if i > 0 else None
    xf = 0.5
    if prev and t < xf and (prev["bg"] != sc["bg"] or prev.get("theme", ctx.tname) != tname):
        ctx.backdrop.draw(c, prev["bg"], prev.get("theme", ctx.tname), T)
        c.saveLayerAlpha(None, int(255 * ease_in_out(t / xf)))
        ctx.backdrop.draw(c, sc["bg"], tname, T)
        c.restore()
    else:
        ctx.backdrop.draw(c, sc["bg"], tname, T)
    a = appear(t, 0.0, 0.3) * (1 - prog(t, sc["dur"] - 0.3, 0.3))
    if a < 0.999:
        c.saveLayerAlpha(None, int(255 * a))
    SCENES[sc["type"]](c, ctx, sc, t)
    if a < 0.999:
        c.restore()
    draw_captions(c, ctx, T, scenes)
    draw_hud(c, ctx, T, total, sc)
    if i > 0:
        draw_sweep(c, ctx, T, sc["start"])


def fmt_ts(s):
    s = int(s)
    return f"{s // 60}:{s % 60:02d}" if s < 3600 else f"{s // 3600}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def srt_ts(s):
    ms = int(round(s * 1000))
    return f"{ms // 3600000:02d}:{(ms // 60000) % 60:02d}:{(ms // 1000) % 60:02d},{ms % 1000:03d}"


def write_srt(path, scenes):
    n = 1
    with open(path, "w", encoding="utf-8") as f:
        for sc in scenes:
            for ch in sc["captions"]:
                f.write(f"{n}\n{srt_ts(ch['start'])} --> {srt_ts(ch['start'] + ch['dur'])}\n")
                f.write("\n".join(ch["lines"]) + "\n\n")
                n += 1


def chapters(scenes):
    out = []
    for sc in scenes:
        if sc.get("chapter"):
            out.append((sc["start"], sc["chapter"]))
    if out and out[0][0] > 0.5:
        out.insert(0, (0, "Intro"))
    elif out:
        out[0] = (0, out[0][1])
    return out


def write_metadata(path, spec, scenes, total, brand):
    m = spec.get("meta", {})
    ch = chapters(scenes)
    desc = m.get("description", "").rstrip() + "\n"
    if ch:
        desc += "\n⏱️ CAPÍTULOS\n" + "\n".join(f"{fmt_ts(t)} {name}" for t, name in ch) + "\n"
    desc += "\n" + brand.get("footer", "").strip() + "\n"
    tags = [str(x) for x in m.get("tags", [])]
    with open(path, "w", encoding="utf-8") as f:
        f.write(f"# {m.get('title', spec.get('slug'))}\n\n")
        f.write(f"**Duración:** {fmt_ts(total)}  \n**Publicar:** {m.get('publish', '-')}  \n")
        if m.get("alt_titles"):
            f.write("**Títulos alternativos (test A/B):**\n")
            for at in m["alt_titles"]:
                f.write(f"- {at}\n")
        f.write("\n## Título\n\n```\n" + m.get("title", "") + "\n```\n")
        f.write("\n## Descripción\n\n```\n" + desc + "```\n")
        f.write("\n## Etiquetas\n\n```\n" + ", ".join(tags) + "\n```\n")
        if m.get("pinned_comment"):
            f.write("\n## Comentario fijado\n\n```\n" + m["pinned_comment"].strip() + "\n```\n")
        f.write("\n## Guion narrado\n\n")
        for sc in scenes:
            if sc.get("chapter"):
                f.write(f"\n### [{fmt_ts(sc['start'])}] {sc['chapter']}\n\n")
            for ln in sc["lines"]:
                if not ln.get("silent"):
                    f.write(ln["text"] + "\n")
    return desc


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec")
    ap.add_argument("--out", default=os.path.join(ROOT, "output"))
    ap.add_argument("--still", default=None, help="tiempos separados por comas para exportar PNG")
    ap.add_argument("--fast", action="store_true", help="vista previa a 960x540 y 15 fps")
    ap.add_argument("--voice", default=DEFAULT_VOICE)
    ap.add_argument("--crf", default="20")
    args = ap.parse_args()

    with open(args.spec, encoding="utf-8") as f:
        spec = yaml.safe_load(f)
    brand = load_brand()
    name = f"{spec['id']}-{spec['slug']}"
    outdir = os.path.join(args.out, name)
    os.makedirs(outdir, exist_ok=True)

    voice = Voice(spec.get("voice_path", args.voice), CACHE, length_scale=spec.get("speed", 1.0))
    t0 = time.time()
    scenes, total, vtrack = build_timeline(spec, voice)
    print(f"[{name}] timeline {fmt_ts(total)} ({total:.1f}s), {len(scenes)} escenas, tts {time.time() - t0:.1f}s",
          flush=True)

    ctx = Ctx()
    ctx.spec, ctx.brand = spec, brand
    ctx.tname = spec.get("theme", "sunset")
    ctx.th = theme(ctx.tname)
    ctx.backdrop = Backdrop(W, H)

    write_srt(os.path.join(outdir, f"{name}.srt"), scenes)
    write_metadata(os.path.join(outdir, "metadata.md"), spec, scenes, total, brand)
    with open(os.path.join(outdir, "timeline.json"), "w", encoding="utf-8") as f:
        json.dump([{k: v for k, v in sc.items() if k not in ("lines", "captions")} for sc in scenes], f,
                  ensure_ascii=False, indent=1, default=str)

    if args.still:
        arr = np.zeros((H, W, 4), np.uint8)
        surf = skia.Surface(arr)
        for ts in args.still.split(","):
            T = float(ts)
            c = surf.getCanvas()
            c.clear(skia.ColorBLACK)
            render_frame(c, ctx, scenes, total, T)
            surf.makeImageSnapshot().save(os.path.join(outdir, f"still_{T:07.2f}.png"), skia.kPNG)
        print("stills ok")
        return

    # audio
    sfx = []
    for i, sc in enumerate(scenes):
        if i > 0:
            sfx.append((max(0, sc["start"] - 0.22), "whoosh", 0.30))
        for (tt, nm, g) in scene_sfx(sc):
            sfx.append((sc["start"] + tt, nm, g))
    music = A.music_bed(spec.get("music", "neon"), total + 1)
    mixed = A.mix(vtrack, music, sfx, music_level=spec.get("music_level", 0.20))
    wav = os.path.join(outdir, "mix.wav")
    A.write_wav(wav, mixed)

    fps = 15 if args.fast else FPS
    ow, oh = (960, 540) if args.fast else (W, H)
    mp4 = os.path.join(outdir, f"{name}{'-preview' if args.fast else ''}.mp4")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgba", "-s", f"{ow}x{oh}",
           "-r", str(fps), "-i", "-", "-i", wav,
           "-c:v", "libx264", "-preset", "medium" if not args.fast else "veryfast", "-tune", "animation",
           "-crf", args.crf, "-pix_fmt", "yuv420p", "-g", str(fps * 2),
           "-af", "loudnorm=I=-14:TP=-1.5:LRA=11", "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
           "-movflags", "+faststart", "-shortest", mp4]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    arr = np.zeros((oh, ow, 4), np.uint8)
    surf = skia.Surface(arr)
    nframes = int(math.ceil(total * fps))
    t1 = time.time()
    for f in range(nframes):
        T = f / fps
        c = surf.getCanvas()
        c.save()
        if args.fast:
            c.scale(0.5, 0.5)
        c.clear(skia.ColorBLACK)
        render_frame(c, ctx, scenes, total, T)
        c.restore()
        proc.stdin.write(arr.tobytes())
        if f % (fps * 30) == 0 and f:
            el = time.time() - t1
            print(f"[{name}] {f}/{nframes} frames, {f / el:.1f} fps, eta {(nframes - f) / (f / el) / 60:.1f} min",
                  flush=True)
    proc.stdin.close()
    proc.wait()
    print(f"[{name}] listo: {mp4} ({total:.1f}s) en {(time.time() - t0) / 60:.1f} min", flush=True)


if __name__ == "__main__":
    main()
