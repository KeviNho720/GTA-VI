"""Música synthwave original generada por código, efectos de sonido y mezcla con ducking."""
import numpy as np
from scipy.signal import butter, sosfilt, sosfiltfilt

SR = 48000

# Pistas originales: tempo, tónica (MIDI) y progresión (acordes como intervalos sobre la tónica).
TRACKS = {
    "neon": dict(bpm=100, root=45, prog=[[0, 3, 7], [-4, 0, 3], [-9, -5, -2], [-2, 2, 5]], seed=1),   # Am F C G
    "sunrise": dict(bpm=92, root=48, prog=[[0, 4, 7], [-3, 0, 4], [-7, -3, 0], [-5, -1, 2]], seed=2),  # C Am F G
    "drive": dict(bpm=108, root=43, prog=[[0, 3, 7], [3, 7, 10], [-2, 2, 5], [-4, 0, 3]], seed=3),     # Gm Bb F Eb
    "tension": dict(bpm=96, root=40, prog=[[0, 3, 7], [1, 5, 8], [0, 3, 7], [-2, 2, 5]], seed=4),      # Em F Em D
    "ocean": dict(bpm=86, root=50, prog=[[0, 4, 7, 11], [-3, 0, 4, 7], [5, 9, 12, 16], [-5, -1, 2, 5]], seed=5),
}


def mtof(m):
    return 440.0 * 2 ** ((m - 69) / 12)


def saw(f, t, harm=10, detune=0.0):
    out = np.zeros_like(t)
    for k in range(1, harm + 1):
        if f * k > SR * 0.45:
            break
        out += np.sin(2 * np.pi * f * (1 + detune) * k * t) / k
    return out * 0.55


def env_adsr(n, a, d, s, r, sr=SR):
    e = np.ones(n) * s
    na, nd, nr = int(a * sr), int(d * sr), int(r * sr)
    na = min(na, n)
    e[:na] = np.linspace(0, 1, na, endpoint=False) if na else e[:na]
    nd = min(nd, n - na)
    if nd > 0:
        e[na:na + nd] = np.linspace(1, s, nd, endpoint=False)
    if nr > 0 and n > nr:
        e[-nr:] *= np.linspace(1, 0, nr)
    return e


def lowpass(x, fc, order=2):
    sos = butter(order, fc / (SR / 2), btype="low", output="sos")
    return sosfilt(sos, x, axis=0)


def highpass(x, fc, order=2):
    sos = butter(order, fc / (SR / 2), btype="high", output="sos")
    return sosfilt(sos, x, axis=0)


def bandpass(x, lo, hi, order=2):
    sos = butter(order, [lo / (SR / 2), hi / (SR / 2)], btype="band", output="sos")
    return sosfilt(sos, x, axis=0)


def make_loop(name, bars=8):
    """Genera un bucle estéreo de `bars` compases."""
    cfg = TRACKS[name]
    rng = np.random.default_rng(cfg["seed"])
    beat = 60.0 / cfg["bpm"]
    bar = beat * 4
    n = int(bar * bars * SR)
    out = np.zeros((n, 2))
    chords = cfg["prog"]
    bars_per_chord = bars // len(chords)

    # Pad
    for ci, ch in enumerate(chords):
        start = int(ci * bars_per_chord * bar * SR)
        ln = int(bars_per_chord * bar * SR)
        t = np.arange(ln) / SR
        e = env_adsr(ln, 0.6, 0.4, 0.8, 0.9)
        for iv in ch:
            f = mtof(cfg["root"] + 12 + iv)
            l = saw(f, t, 8, -0.004) + saw(f, t, 8, 0.003)
            r = saw(f, t, 8, 0.005) + saw(f, t, 8, -0.002)
            out[start:start + ln, 0] += l * e * 0.05
            out[start:start + ln, 1] += r * e * 0.05
    out = lowpass(out, 2200)

    # Bajo en corcheas
    eighth = beat / 2
    for i in range(int(bars * 8)):
        ci = (i // 8) // bars_per_chord
        f = mtof(cfg["root"] - 12 + chords[ci][0])
        st = int(i * eighth * SR)
        ln = int(eighth * SR * 0.95)
        t = np.arange(ln) / SR
        tone = saw(f, t, 6) * env_adsr(ln, 0.005, 0.12, 0.35, 0.03)
        out[st:st + ln, :] += (tone * (0.16 if i % 2 == 0 else 0.11))[:, None]

    # Arpegio en semicorcheas con retardo
    six = beat / 4
    arp = np.zeros(n)
    pattern = [0, 1, 2, 1, 2, 0, 1, 2]
    for i in range(int(bars * 16)):
        ci = (i // 16) // bars_per_chord
        ch = chords[ci]
        note = cfg["root"] + 24 + ch[pattern[i % len(pattern)] % len(ch)]
        st = int(i * six * SR)
        ln = int(six * SR * 0.9)
        t = np.arange(ln) / SR
        f = mtof(note)
        tone = (np.sin(2 * np.pi * f * t) + 0.3 * np.sin(2 * np.pi * 2 * f * t)) * np.exp(-t * 14)
        arp[st:st + ln] += tone * 0.045
    d = int(beat * 0.75 * SR)
    arp_l = arp.copy()
    arp_r = arp.copy()
    arp_l[d:] += 0.35 * arp[:-d]
    arp_r[2 * d:] += 0.25 * arp[:-2 * d]
    out[:, 0] += arp_l
    out[:, 1] += arp_r

    # Batería
    def kick():
        ln = int(0.35 * SR)
        t = np.arange(ln) / SR
        f = 45 + 90 * np.exp(-t * 28)
        ph = 2 * np.pi * np.cumsum(f) / SR
        return np.sin(ph) * np.exp(-t * 9) * 0.55

    def snare():
        ln = int(0.25 * SR)
        t = np.arange(ln) / SR
        nz = bandpass(rng.standard_normal(ln), 900, 6000) * np.exp(-t * 18)
        tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 25)
        return (nz * 0.22 + tone * 0.15)

    def hat():
        ln = int(0.05 * SR)
        t = np.arange(ln) / SR
        return highpass(rng.standard_normal(ln), 7000) * np.exp(-t * 90) * 0.06

    K, S_, Hh = kick(), snare(), hat()
    for b in range(bars * 4):
        st = int(b * beat * SR)
        if b % 2 == 0:
            out[st:st + len(K), :] += K[: max(0, min(len(K), n - st))][:, None]
        else:
            seg = S_[: max(0, min(len(S_), n - st))]
            out[st:st + len(seg), 0] += seg
            out[st:st + len(seg), 1] += seg * 0.9
        for h in range(2):
            sth = st + int(h * eighth * SR)
            seg = Hh[: max(0, min(len(Hh), n - sth))]
            out[sth:sth + len(seg), 0] += seg * (0.7 if h else 1.0)
            out[sth:sth + len(seg), 1] += seg * (1.0 if h else 0.7)

    out = highpass(out, 30)
    out /= max(1e-6, np.abs(out).max())
    return out * 0.9


def music_bed(name, seconds):
    loop = make_loop(name)
    reps = int(np.ceil(seconds * SR / len(loop))) + 1
    full = np.tile(loop, (reps, 1))[: int(seconds * SR)]
    # entrada suave del primer compás y salida final
    fi = int(1.5 * SR)
    fo = int(3.0 * SR)
    full[:fi] *= np.linspace(0, 1, fi)[:, None]
    full[-fo:] *= np.linspace(1, 0, fo)[:, None]
    return full


# --------------------------------------------------------------------------- efectos
def sfx_whoosh(dur=0.55, seed=0):
    rng = np.random.default_rng(seed)
    n = int(dur * SR)
    nz = rng.standard_normal(n)
    out = np.zeros(n)
    chunks = 24
    for i in range(chunks):
        a, b = i * n // chunks, (i + 1) * n // chunks
        k = i / chunks
        fc = 400 + 5000 * np.sin(np.pi * k) ** 2
        out[a:b] = bandpass(nz[a:b], fc * 0.6, min(fc * 1.6, 20000))
    env = np.sin(np.pi * np.linspace(0, 1, n)) ** 2
    out *= env
    pan = np.linspace(0, 1, n)
    st = np.stack([out * (1 - pan * 0.7), out * (0.3 + pan * 0.7)], 1)
    return st / max(1e-6, np.abs(st).max()) * 0.5


def sfx_tick():
    n = int(0.07 * SR)
    t = np.arange(n) / SR
    f = 900 + 600 * t / t[-1]
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 60)
    return np.stack([x, x], 1) * 0.35


def sfx_impact():
    n = int(0.9 * SR)
    t = np.arange(n) / SR
    f = 38 + 70 * np.exp(-t * 12)
    x = np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 4.5)
    rng = np.random.default_rng(9)
    nz = lowpass(rng.standard_normal(n), 900) * np.exp(-t * 14) * 0.5
    y = x + nz
    return np.stack([y, y], 1) * 0.55


SFX = {"whoosh": sfx_whoosh, "tick": sfx_tick, "impact": sfx_impact}


# --------------------------------------------------------------------------- mezcla
def envelope(x, win=0.05):
    w = int(win * SR)
    pad = np.pad(np.abs(x), (w, w))
    c = np.cumsum(pad)
    env = (c[2 * w:] - c[:-2 * w])[: len(x)] / (2 * w)
    return env


def smooth_gain(target, attack=0.08, release=0.45):
    out = np.empty_like(target)
    g = target[0]
    a = 1 - np.exp(-1 / (attack * SR))
    r = 1 - np.exp(-1 / (release * SR))
    # vectorizado por bloques para no iterar muestra a muestra
    step = 240
    for i in range(0, len(target), step):
        tg = target[i:i + step].min()
        k = a if tg < g else r
        g_new = g + (tg - g) * (1 - (1 - k) ** step)
        out[i:i + step] = np.linspace(g, g_new, len(out[i:i + step]))
        g = g_new
    return out


def mix(voice, music, sfx_events, music_level=0.20, duck_level=0.065):
    """voice: mono (n,), music: estéreo (n,2), sfx_events: lista de (t, nombre, ganancia)."""
    n = len(voice)
    music = music[:n]
    if len(music) < n:
        music = np.pad(music, ((0, n - len(music)), (0, 0)))
    env = envelope(voice, 0.08)
    active = (env > 0.01).astype(float)
    # mantener el ducking entre frases cercanas
    hold = int(0.35 * SR)
    c = np.cumsum(np.pad(active, (hold, hold)))
    held = ((c[2 * hold:] - c[:-2 * hold])[:n] > 0).astype(float)
    target = music_level - (music_level - duck_level) * held
    g = smooth_gain(target)
    out = music * g[:, None]
    v = highpass(voice, 75)
    out += np.stack([v, v], 1) * 0.92
    for (t, name, gain) in sfx_events:
        s = SFX[name]() if name != "whoosh" else sfx_whoosh(seed=int(t * 10))
        st = int(t * SR)
        if st >= n:
            continue
        seg = s[: n - st]
        out[st:st + len(seg)] += seg * gain
    peak = np.abs(out).max()
    if peak > 0.98:
        out *= 0.98 / peak
    return out.astype(np.float32)


def write_wav(path, x):
    import wave
    x = np.clip(x, -1, 1)
    data = (x * 32767).astype(np.int16)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2 if x.ndim == 2 else 1)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(data.tobytes())
