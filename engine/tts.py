"""Voz neuronal en español (Piper) con normalización de pronunciación y caché."""
import hashlib
import os
import re
import wave

import numpy as np
from scipy.signal import resample_poly

SR = 48000

# Sustituciones para que la voz pronuncie bien siglas, marcas y nombres en inglés.
# Se aplican en orden; las claves son expresiones regulares.
PRON = [
    (r"GTA:?\s?Vice City Stories", "getea, Váis Síti Stóris"),
    (r"GTA:?\s?Vice City", "getea, Váis Síti"),
    (r"GTA\s?VI\b", "getea seis"),
    (r"GTA\s?6\b", "getea seis"),
    (r"GTA\s?V\b", "getea cinco"),
    (r"GTA\s?5\b", "getea cinco"),
    (r"GTA\s?IV\b", "getea cuatro"),
    (r"GTA\s?III\b", "getea tres"),
    (r"GTA\+", "getea plus"),
    (r"\bGTA\b", "getea"),
    (r"\bPS5 Pro\b", "PlayStation cinco Pro"),
    (r"\bPS5\b", "PlayStation cinco"),
    (r"\bPS4\b", "PlayStation cuatro"),
    (r"\bPlayStation 5\b", "PlayStation cinco"),
    (r"\bPlayStation 4\b", "PlayStation cuatro"),
    (r"PlayStation", "Pleisteishon"),
    (r"Xbox Series X\|S", "Xbox Series equis y ese"),
    (r"Xbox Series X", "Xbox Series equis"),
    (r"Xbox Series S", "Xbox Series ese"),
    (r"Xbox One", "Xbox uan"),
    (r"Xbox Cloud Gaming", "Xbox claud guéimin"),
    (r"\bXbox\b", "Ecsbox"),
    (r"\bSeries\b", "siris"),
    (r"\bPSSR\b", "pe ese ese erre"),
    (r"\bFPS\b", "efe pe ese"),
    (r"\bHDR\b", "hache de erre"),
    (r"\bSSD\b", "ese ese de"),
    (r"\bNVMe\b", "ene uve eme e"),
    (r"\bTB\b", "teras"),
    (r"(\d)\s?GB\b", r"\1 gigas"),
    (r"\bGB\b", "gigas"),
    (r"\bPC\b", "pecé"),
    (r"\bDLC\b", "de ele ce"),
    (r"\bTV\b", "tele"),
    (r"\bIA\b", "i a"),
    (r"\bCEO\b", "ce e o"),
    (r"\bEE\.\s?UU\.", "Estados Unidos"),
    (r"Rockstar Games", "Rocstar Geims"),
    (r"Rockstar", "Rocstar"),
    (r"Take-Two", "Téik Tu"),
    (r"Newswire", "niusguáier"),
    (r"Online", "onláin"),
    (r"online", "onláin"),
    (r"Ultimate Edition", "edición áltimeit"),
    (r"Ultimate", "áltimeit"),
    (r"Edition", "edíshon"),
    (r"Standard", "estándar"),
    (r"Vintage Vice City Pack", "víntach Váis Síti pac"),
    (r"Vice City", "Váis Síti"),
    (r"Leonida Keys", "Leonida Kíis"),
    (r"\bKeys\b", "kis"),
    (r"Grassrivers", "Grás Rívers"),
    (r"Port Gellhorn", "Port Guél Jorn"),
    (r"Mount Kalaga", "Maunt Kalága"),
    (r"National Park", "náshonal park"),
    (r"Los Santos", "los santos"),
    (r"Liberty City", "líberti siti"),
    (r"San Andreas", "san andreas"),
    (r"Grand Theft Auto", "Gran Zeft Óto"),
    (r"Vice City Stories", "Váis Síti Stóris"),
    (r"Red Dead Redemption", "Red Ded Ridémshon"),
    (r"Blaine County", "Bléin Cáunti"),
    (r"Everglades", "Éver Gleids"),
    (r"\bTempest\b", "Témpest"),
    (r"\bstriptease\b", "estriptís"),
    (r"\bhacker\b", "jáquer"),
    (r"\bmalware\b", "málguer"),
    (r"\bwifi\b", "güifi"),
    (r"\bPS3\b", "Pleisteishon tres"),
    (r"\bLori\b", "Lóri"),
    (r"Jason Duval", "Yéisson Duvál"),
    (r"Jason", "Yéisson"),
    (r"Lucia Caminos", "Lucía Caminos"),
    (r"\bLucia\b", "Lucía"),
    (r"Cal Hampton", "Cal Jámpton"),
    (r"Boobie Ike", "Búbi Áik"),
    (r"Dre'Quan Priest", "Dré Cuán Príst"),
    (r"Dre'Quan", "Dré Cuán"),
    (r"Real Dimez", "Ríal Dáims"),
    (r"Bae-Luxe", "Béilux"),
    (r"\bRoxy\b", "róxi"),
    (r"Raul Bautista", "Raúl Bautista"),
    (r"Brian Heder", "Bráian Jéder"),
    (r"Tommy Vercetti", "Tómi Verchéti"),
    (r"Michael", "máikol"),
    (r"Trevor", "trévor"),
    (r"Franklin", "fránklin"),
    (r"Grotti Cheetah", "grotti chíta"),
    (r"Strauss Zelnick", "straus sélnik"),
    (r"Zelnick", "sélnik"),
    (r"Game Pass", "guéim pas"),
    (r"Steam", "estim"),
    (r"Twitch", "tuich"),
    (r"YouTube", "yutub"),
    (r"Bloomberg", "blúmberg"),
    (r"Jason Schreier", "yéison shráier"),
    (r"Digital Foundry", "díyital fáundri"),
    (r"\bcloud\b", "claud"),
    (r"\bgaming\b", "guéimin"),
    (r"\bstreaming\b", "estrímin"),
    (r"\bupgrade\b", "ápgreid"),
    (r"\bspoilers?\b", "espóilers"),
    (r"\bshooter\b", "shúter"),
    (r"\btrailer\b", "tráiler"),
    (r"\btráiler\b", "tráiler"),
    (r"\bfreemium\b", "frímium"),
    (r"\bwallpaper\b", "guólpeiper"),
    (r"Weazel", "uícel"),
    (r"Newswire", "niusguáier"),
    (r"\bHawk\b", "jok"),
    (r"Little Morgan", "lítel mórgan"),
    (r"\bstreamers?\b", "estrímers"),
    (r"\bmods?\b", "mods"),
    (r"\bchat\b", "chat"),
    (r"\bsingle player\b", "síngel pléier"),
    (r"\bnerf\b", "nerf"),
    (r"\bkm²", " kilómetros cuadrados"),
    (r"\bkm\b", "kilómetros"),
    (r"€", " euros"),
    (r"\$", " dólares"),
    (r"%", " por ciento"),
    (r"\s+&\s+", " y "),
    (r"·", ","),
    (r"—", ","),
    (r"\bvs\.?\b", "contra"),
    (r"\bnº\b", "número"),
    (r"\b(\d{1,2}):00\b", r"\1 en punto"),
]

NUM_WORDS = None


def _money(m):
    ent, dec = m.group(1), m.group(2)
    return f"{ent} con {dec}"


def normalize(text):
    s = text.strip()
    # los puntos suspensivos de continuación solo sirven en los subtítulos
    s = re.sub(r"^\.\.\.\s*|^…\s*", "", s)
    s = re.sub(r"\s*(\.\.\.|…)$", ",", s)
    s = re.sub(r"\.\.\.|…", ",", s)
    # precios con decimales: 79,99 € -> 79 con 99 euros
    s = re.sub(r"(\d+),(\d{2})(?=\s?[€$])", _money, s)
    for pat, rep in PRON:
        s = re.sub(pat, rep, s)
    s = re.sub(r"\s{2,}", " ", s).strip()
    return s


class Voice:
    def __init__(self, model_path, cache_dir, length_scale=1.0, noise_scale=0.5, noise_w=0.4, speaker=None):
        self.model_path = model_path
        self.cache_dir = cache_dir
        os.makedirs(cache_dir, exist_ok=True)
        self.params = dict(length_scale=length_scale, noise_scale=noise_scale, noise_w_scale=noise_w,
                           speaker_id=speaker)
        self._voice = None

    def _load(self):
        if self._voice is None:
            from piper import PiperVoice
            self._voice = PiperVoice.load(self.model_path)
        return self._voice

    def synth(self, text, say=None):
        """Devuelve audio mono float32 a 48 kHz."""
        spoken = say if say else normalize(text)
        key = hashlib.sha1((os.path.basename(self.model_path) + repr(sorted(self.params.items())) + spoken)
                           .encode("utf-8")).hexdigest()[:20]
        path = os.path.join(self.cache_dir, key + ".wav")
        if not os.path.exists(path):
            from piper import SynthesisConfig
            v = self._load()
            cfg = SynthesisConfig(**{k: v_ for k, v_ in self.params.items() if v_ is not None})
            tmp = f"{path}.{os.getpid()}.tmp"
            with wave.open(tmp, "wb") as wf:
                v.synthesize_wav(spoken, wf, syn_config=cfg)
            os.replace(tmp, path)
        with wave.open(path, "rb") as wf:
            sr = wf.getframerate()
            data = np.frombuffer(wf.readframes(wf.getnframes()), dtype=np.int16).astype(np.float32) / 32768.0
        if sr != SR:
            g = np.gcd(SR, sr)
            data = resample_poly(data, SR // g, sr // g).astype(np.float32)
        return trim_silence(data)


def trim_silence(x, thr=0.008, pad=0.03):
    if len(x) == 0:
        return x
    idx = np.where(np.abs(x) > thr)[0]
    if len(idx) == 0:
        return x[:1]
    a = max(0, idx[0] - int(pad * SR))
    b = min(len(x), idx[-1] + int(pad * SR * 2))
    return x[a:b]
