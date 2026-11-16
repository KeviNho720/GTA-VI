"""Control de calidad de la voz: sintetiza cada frase y la transcribe con Whisper.

Marca las frases cuya transcripción se aleja del texto (posibles errores de pronunciación).
Uso: python tools/voice_qa.py videos/*.yaml  (requiere faster-whisper)
"""
import difflib
import os
import re
import sys
import unicodedata

import numpy as np
import yaml
from scipy.signal import resample_poly

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from engine.render import CACHE, DEFAULT_VOICE  # noqa: E402
from engine.tts import SR, Voice  # noqa: E402


def norm(s):
    s = unicodedata.normalize("NFKD", s.lower())
    s = "".join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    return s.split()


def main():
    from faster_whisper import WhisperModel
    model = WhisperModel("small", device="cpu", compute_type="int8", cpu_threads=int(os.environ.get("QA_THREADS", 2)),
                         download_root=os.environ.get("WHISPER_DIR"))
    voice = Voice(DEFAULT_VOICE, CACHE, length_scale=1.0)
    bad = 0
    for path in sys.argv[1:]:
        spec = yaml.safe_load(open(path, encoding="utf-8"))
        for si, sc in enumerate(spec["scenes"]):
            for ln in sc.get("lines", []):
                ln = {"text": ln} if isinstance(ln, str) else ln
                if ln.get("silent"):
                    continue
                a = voice.synth(ln["text"], ln.get("say"))
                a16 = resample_poly(a, 1, 3).astype(np.float32)
                segs, _ = model.transcribe(a16, language="es", beam_size=3)
                hyp = " ".join(s.text.strip() for s in segs)
                r = difflib.SequenceMatcher(None, norm(ln["text"]), norm(hyp)).ratio()
                flag = "  " if r >= 0.8 else "!!"
                if r < 0.8:
                    bad += 1
                print(f"{flag} {r:.2f} [{spec['id']}:{si}] {ln['text']}\n        -> {hyp}", flush=True)
    print(f"\nFrases a revisar: {bad}")


if __name__ == "__main__":
    main()
