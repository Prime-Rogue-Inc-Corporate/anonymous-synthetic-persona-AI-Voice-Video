#!/usr/bin/env python3
"""Anonymous-style synthetic persona renderer.

Turns an episode folder (script.txt + episode.json) into a captioned,
robot-voiced MP4: title card, moth-in-a-suit emblem, glitch/grain, a light cue
on a chosen line, and an "EXPECT US." end card.

Usage:
    python persona/render.py episodes/<slug>             # full render
    python persona/render.py episodes/<slug> --preview   # a few PNG frames only
    python persona/render.py episodes/<slug> --jobs 4    # parallel chunks

Requires ffmpeg and espeak-ng on PATH, plus numpy, scipy and Pillow.
"""
import argparse, datetime, json, math, os, re, subprocess, sys, wave
from concurrent.futures import ProcessPoolExecutor

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from masks import MASKS, suit  # noqa: E402

W, H, FPS, SR = 1280, 720, 30, 44100
__version__ = open(os.path.join(ROOT, "VERSION")).read().strip()

DEFAULTS = {
    "title": "ANONYMOUS",
    "subtitle": "message",
    "mask": "moth",
    "cast": {},
    "set": {"table": False, "placard": None, "lockbox": False, "corridor": None,
            "chamber": None, "lectern": None, "chyron": None, "barn": None, "desk": None, "dog": None,
            "assembly": None, "commons": None, "rally": None, "arctic": None, "diner": None, "prairie": None, "hall": None, "boardroom": None},
    "layout": {},
    "credits": [],
    "end_title": "EXPECT US.",
    "voice": {"voice": "en-us+m3", "speed": 138, "pitch": 22,
              "filter": "asetrate=22050*0.86,aresample=44100,atempo=1.08,aecho=0.8:0.6:40:0.25,highpass=f=90,lowpass=f=6000,volume=1.6"},
    "pronounce": {},
    "gaps": {"default": 0.45, "after_greeting": 0.6, "after_intro": 1.4, "signoff": 0.7, "after": {}},
    "light": {"line": None, "color": [255, 210, 120], "ramp": 0.15, "tint": [0.45, 0.38, 0.18]},
    "signoff_lines": 5,
    "output": "out.mp4",
    "crf": 28,
}

FONT_DIR = "/usr/share/fonts/truetype/dejavu"


def merge(a, b):
    out = dict(a)
    for k, v in b.items():
        out[k] = merge(a[k], v) if isinstance(v, dict) and isinstance(a.get(k), dict) else v
    return out


# ---------------------------------------------------------------- script
SPEAKER = re.compile(r"^([A-Z][A-Z0-9 .'-]{0,24}):\s+(.*)$")
CUE = re.compile(r"\[(gavel|bark|cackle|hear|cheer|slam|shot|ding|laugh|jet|ring)\]\s*", re.I)
CUE_LEAD = 0.55          # seconds of room left before a gavelled line (kept for compatibility)
CUE_LEN = {"gavel": 0.55, "bark": 0.75, "cackle": 1.45, "hear": 1.6, "cheer": 2.4, "slam": 0.7, "shot": 0.9, "ding": 0.6, "laugh": 1.7, "jet": 2.6, "ring": 2.2}   # room each sound effect takes on the timeline
CUE_OWNER = {"gavel": None, "bark": "_dog", "cackle": "speaker", "hear": None, "cheer": None, "slam": None, "shot": None, "ding": None, "laugh": None, "jet": None, "ring": None}   # whose mouth moves with it


TRANS = re.compile(r"\s*\{=\s*(.*?)\s*\}\s*$")


def strip_cues(text):
    """Remove inline sound cues like [gavel] and any trailing {= translation} from a line (for voice and captions)."""
    return TRANS.sub("", CUE.sub("", text)).strip()


def translation(text):
    """The subtitle translation of a line written as `Bonjour. {= Hello.}`, or None."""
    m = TRANS.search(CUE.sub("", text))
    return m.group(1) if m else None


def has_cue(text, name="gavel"):
    return any(m.group(1).lower() == name for m in CUE.finditer(text))


def cue_split(text):
    """(cues before the words, cues after the words). A line that is only cues counts them all as 'before'."""
    pre, post = [], []
    lead = re.match(r"^(?:\s*\[(?:gavel|bark|cackle)\]\s*)+", text, re.I)
    if lead:
        pre = [m.group(1).lower() for m in CUE.finditer(lead.group(0))]
        rest = text[lead.end():]
    else:
        rest = text
    post = [m.group(1).lower() for m in CUE.finditer(rest)]
    return pre, post


def cue_events(lines, starts, durs):
    """[(time, cue, line_index)] for every sound cue in the script."""
    ev = []
    for i, (l, s, d) in enumerate(zip(lines, starts, durs)):
        pre, post = cue_split(l)
        t = s - sum(CUE_LEN[c] for c in pre)
        for c in pre:
            ev.append((t, c, i)); t += CUE_LEN[c]
        t = s + d + 0.08
        for c in post:
            ev.append((t, c, i)); t += CUE_LEN[c]
    return ev


def load_episode(ep):
    """Read episode.json + script.txt. Returns (cfg, lines, speakers).

    Dialogue: prefix lines with an upper-case speaker tag defined in cfg["cast"],
    e.g. ``ANCHOR: Welcome.`` Untagged lines go to the first cast member (or the solo persona).
    """
    cfg = merge(DEFAULTS, json.load(open(os.path.join(ep, "episode.json"))))
    lines, speakers = [], []
    first = next(iter(cfg["cast"]), None)
    for raw in open(os.path.join(ep, "script.txt"), encoding="utf-8"):
        raw = raw.strip()
        if not raw:
            continue
        m = SPEAKER.match(raw)
        if m and cfg["cast"]:
            if m.group(1) not in cfg["cast"]:
                raise SystemExit(f"speaker {m.group(1)!r} is not in cast: {', '.join(cfg['cast'])}")
            speakers.append(m.group(1)); lines.append(m.group(2))
        else:
            speakers.append(first); lines.append(raw)
    return cfg, lines, speakers


def voice_for(cfg, speaker):
    if speaker is None:
        return cfg["voice"], cfg["pronounce"]
    c = cfg["cast"][speaker]
    return merge(cfg["voice"], c.get("voice", {})), {**cfg["pronounce"], **c.get("pronounce", {})}


# ---------------------------------------------------------------- voice
def synth(ep_dir, cfg, lines, speakers=None):
    work = os.path.join(ep_dir, "build", "voice")
    os.makedirs(work, exist_ok=True)
    speakers = speakers or [None] * len(lines)
    clips = []
    for i, line in enumerate(lines):
        duet = (cfg["cast"].get(speakers[i]) or {}).get("duet") if speakers[i] else None
        if duet:                                                   # two cast members saying the same line at once
            parts = []
            for j, who in enumerate(duet):
                v, pron = voice_for(cfg, who)
                spoken = strip_cues(line).replace('"', "")
                for k, rep_ in pron.items():
                    spoken = spoken.replace(k, rep_)
                raw, part = f"{work}/raw_{i:03d}_{j}.wav", f"{work}/v_{i:03d}_{j}.wav"
                subprocess.run(["espeak-ng", "-v", v["voice"], "-s", str(v["speed"]), "-p", str(v["pitch"]), "-w", raw, spoken], check=True)
                subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-af", v["filter"], "-ar", str(SR), "-ac", "1", part], check=True)
                with wave.open(part) as w:
                    parts.append(np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768)
            n = max(len(x) for x in parts)
            mix = sum(np.pad(x, (0, n - len(x))) for x in parts) * 0.75
            clips.append(mix.astype(np.float32))
            with wave.open(f"{work}/v_{i:03d}.wav", "w") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
                w.writeframes((np.clip(mix, -1, 1) * 32767).astype(np.int16).tobytes())
            continue
        v, pron = voice_for(cfg, speakers[i])
        spoken = strip_cues(line).replace('"', "")
        for k, rep in pron.items():
            spoken = spoken.replace(k, rep)
        raw, out = f"{work}/raw_{i:03d}.wav", f"{work}/v_{i:03d}.wav"
        if not spoken.strip():                     # a cue-only line, e.g. "HOST: [cackle]"
            clips.append(np.zeros(int(0.05 * SR), np.float32))
            with wave.open(out, "w") as w:
                w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(b"\0\0" * int(0.05 * SR))
            continue
        subprocess.run(["espeak-ng", "-v", v["voice"], "-s", str(v["speed"]), "-p", str(v["pitch"]), "-w", raw, spoken], check=True)
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", raw, "-af", v["filter"], "-ar", str(SR), "-ac", "1", out], check=True)
        with wave.open(out) as w:
            clips.append(np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768)
    return clips


def timeline(cfg, lines, clips):
    g = cfg["gaps"]
    t, starts = 2.5, []
    n = len(lines)
    for i, c in enumerate(clips):
        pre, post = cue_split(lines[i])
        t += sum(CUE_LEN[x] for x in pre)
        starts.append(t)
        t += len(c) / SR
        t += sum(CUE_LEN[x] for x in post)
        gap = g["default"]
        if i == 0: gap = g["after_greeting"]
        if i == 1: gap = g["after_intro"]
        for prefix, sec in g["after"].items():
            if lines[i].startswith(prefix): gap = sec
        if i >= n - cfg["signoff_lines"]: gap = g["signoff"]
        t += gap
    return starts, t + 2.5


def gavel_knock():
    """Two sharp wooden knocks, synthesized."""
    rng = np.random.default_rng(3)
    n = int(0.42 * SR); out = np.zeros(n, np.float32)
    for at in (0.0, 0.19):
        k = int(0.12 * SR); tt = np.arange(k) / SR
        env = np.exp(-tt * 55)
        hit = (np.sin(2 * np.pi * 190 * tt) * 0.9 + np.sin(2 * np.pi * 620 * tt) * 0.35) * env
        hit += gaussian_filter(rng.standard_normal(k).astype(np.float32), 1.2) * np.exp(-tt * 140) * 0.8
        a = int(at * SR); out[a:a + k] += hit
    return out / np.abs(out).max() * 0.5


def _white(i0, i1, seed=7, seg=SR):
    """Deterministic white noise for samples [i0, i1): built from fixed 1-second segments, so any block of the
    timeline gets identical values in overlapping regions (no seams when the mix is rendered in blocks)."""
    out = np.empty(i1 - i0, np.float32)
    k0, k1 = i0 // seg, (i1 - 1) // seg
    for k in range(k0, k1 + 1):
        noise = np.random.default_rng((seed, k)).standard_normal(seg).astype(np.float32)
        s0, s1 = max(i0, k * seg), min(i1, (k + 1) * seg)
        out[s0 - i0:s1 - i0] = noise[s0 - k * seg:s1 - k * seg]
    return out


def _drone(i0, i1, N):
    """Unnormalized drone bed for samples [i0, i1) of an N-sample timeline (padded so block edges are seamless)."""
    pad = 600
    j0, j1 = max(0, i0 - pad), min(N, i1 + pad)
    tt = np.arange(j0, j1) / SR
    d = np.zeros(j1 - j0, np.float32)
    for f, amp in [(55, .5), (55.4, .4), (82.4, .25), (110.2, .12)]:
        d += (amp * (2 * ((tt * f) % 1) - 1)).astype(np.float32)
    d = gaussian_filter(d, 6) + gaussian_filter(_white(j0, j1), 40) * 3
    d *= (0.6 + 0.4 * np.sin(2 * np.pi * tt / 11)).astype(np.float32)
    return d[i0 - j0:i1 - j0], tt[i0 - j0:i1 - j0]


def bark():
    """Two short dog barks, synthesized."""
    rng = np.random.default_rng(5)
    out = np.zeros(int(0.7 * SR), np.float32)
    for at, f0 in ((0.0, 560), (0.3, 500)):
        k = int(0.2 * SR); tt = np.arange(k) / SR
        f = f0 - 260 * tt / 0.2
        ph = 2 * np.pi * np.cumsum(f) / SR
        tone = sum(np.sin(ph * h) / h for h in (1, 2, 3, 4))
        env = np.minimum(1, tt / 0.012) * np.exp(-tt * 14)
        b = (tone * 0.8 + gaussian_filter(rng.standard_normal(k), 2) * 0.5) * env
        a = int(at * SR); out[a:a + k] += b.astype(np.float32)
    return out / np.abs(out).max() * 0.55


def cackle():
    """A high, delighted cackle (espeak at a silly pitch), fixed length."""
    tmp = "/tmp/_persona_cackle"
    subprocess.run(["espeak-ng", "-v", "en-us+m2", "-s", "290", "-p", "99", "-w", tmp + "_r.wav",
                    "heh heh heh. hah hah hah hah hah"], check=True)
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-i", tmp + "_r.wav", "-af",
                    "asetrate=22050*1.06,aresample=44100,aecho=0.8:0.5:30:0.2,volume=1.5", "-ar", str(SR), "-ac", "1", tmp + ".wav"], check=True)
    with wave.open(tmp + ".wav") as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
    n = int((CUE_LEN["cackle"] - 0.1) * SR)
    x = x[:n]
    x[-int(0.08 * SR):] *= np.linspace(1, 0, int(0.08 * SR))
    return x * 0.8


def hear_hear():
    """A bench of members growling "hear, hear": a dozen espeak voices at scattered pitches and offsets,
    muffled, over a low rumble of shuffling. Fixed length."""
    rng = np.random.default_rng(21)
    n = int((CUE_LEN["hear"] - 0.1) * SR); out = np.zeros(n, np.float32)
    tmp = "/tmp/_persona_hear"
    for k in range(12):
        v = ["en-gb+m1", "en-gb+m3", "en-gb+m5", "en-gb+m7", "en-gb+f2", "en-us+m4"][k % 6]
        subprocess.run(["espeak-ng", "-v", v, "-s", str(int(rng.integers(120, 170))), "-p", str(int(rng.integers(10, 60))),
                        "-w", tmp + ".wav", "hear, hear" if k % 3 else "hear, hear, hear"], check=True)
        with wave.open(tmp + ".wav") as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        x = np.interp(np.arange(0, len(x), 22050 / SR), np.arange(len(x)), x).astype(np.float32)   # to 44.1k
        a = int(rng.uniform(0, 0.45) * SR); m = min(len(x), n - a)
        out[a:a + m] += x[:m] * rng.uniform(0.25, 0.5)
    out = gaussian_filter(out, 1.6)                                    # muffle: they're across the chamber
    rumble = gaussian_filter(rng.standard_normal(n).astype(np.float32), 30) * 6
    out += rumble * np.hanning(n).astype(np.float32)
    env = np.minimum(1, np.minimum(np.arange(n) / (0.08 * SR), (n - np.arange(n)) / (0.3 * SR))).astype(np.float32)
    out *= env
    return out / (np.abs(out).max() + 1e-6) * 0.5


def phone_ring():
    """A phone ringing: the North American 440 + 480 Hz pair, two short bursts, with a cheap-speaker buzz."""
    n = int((CUE_LEN["ring"] - 0.05) * SR); tt = np.arange(n) / SR
    tone = (np.sin(2 * np.pi * 440 * tt) + np.sin(2 * np.pi * 480 * tt)) * 0.5
    gate = (((tt % 1.0) < 0.4) & (tt < 1.9)).astype(np.float32)
    buzz = np.sign(np.sin(2 * np.pi * 20 * tt)) * 0.15 + 0.85
    out = (tone * gate * buzz).astype(np.float32)
    return gaussian_filter(out, 0.6) * 0.3


def jet_pass():
    """A fighter passing low overhead: filtered roar swelling and falling, with a Doppler-ish drop in the whine."""
    rng = np.random.default_rng(71)
    n = int((CUE_LEN["jet"] - 0.05) * SR); tt = np.arange(n) / SR
    roar = gaussian_filter(rng.standard_normal(n), 2.5)
    f = 1800 - 900 * (tt / tt[-1])
    whine = np.sin(2 * np.pi * np.cumsum(f) / SR) * 0.15
    env = np.exp(-((tt - 1.0) / 0.55) ** 2)
    out = ((roar * 1.2 + whine) * env).astype(np.float32)
    return out / np.abs(out).max() * 0.55


def gunshot():
    """A rifle shot outdoors: a sharp crack, a low thump, and a long flat echo off open ground."""
    rng = np.random.default_rng(51)
    n = int((CUE_LEN["shot"] - 0.05) * SR); tt = np.arange(n) / SR
    crack = rng.standard_normal(n) * np.exp(-tt * 90)
    thump = np.sin(2 * np.pi * 55 * tt) * np.exp(-tt * 20) * 0.9
    echo = gaussian_filter(rng.standard_normal(n), 3) * np.exp(-np.clip(tt - 0.18, 0, None) * 6) * (tt > 0.18) * 0.35
    out = (crack + thump + echo).astype(np.float32)
    return out / np.abs(out).max() * 0.6


def steel_ding():
    """A steel target ringing at distance: a few inharmonic partials, decaying."""
    n = int((CUE_LEN["ding"] - 0.05) * SR); tt = np.arange(n) / SR
    out = sum(a * np.sin(2 * np.pi * f * tt) for f, a in ((880, 1.0), (1370, 0.6), (2210, 0.35), (3020, 0.2)))
    out = (out * np.exp(-tt * 7) * np.minimum(1, tt / 0.003)).astype(np.float32)
    return out / np.abs(out).max() * 0.32


def group_laugh():
    """A few people cracking up: several espeak voices on "ha ha ha", scattered, muffled by parkas."""
    rng = np.random.default_rng(61)
    n = int((CUE_LEN["laugh"] - 0.1) * SR); out = np.zeros(n, np.float32)
    tmp = "/tmp/_persona_laugh"
    for k in range(5):
        v = ["en-us+m2", "en-us+f4", "en-gb+m4", "en-us+m7", "en-us+f2"][k]
        subprocess.run(["espeak-ng", "-v", v, "-s", str(int(rng.integers(190, 260))), "-p", str(int(rng.integers(40, 90))),
                        "-w", tmp + ".wav", "ha ha ha ha. ha ha"], check=True)
        with wave.open(tmp + ".wav") as w:
            x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        x = np.interp(np.arange(0, len(x), 22050 / SR), np.arange(len(x)), x).astype(np.float32)
        a = int(rng.uniform(0, 0.35) * SR); m = min(len(x), n - a)
        out[a:a + m] += x[:m] * rng.uniform(0.35, 0.6)
    out = gaussian_filter(out, 1.2)
    env = np.minimum(1, (n - np.arange(n)) / (0.3 * SR)).astype(np.float32)
    return out * env / (np.abs(out).max() + 1e-6) * 0.5


def door_slam():
    """A door flung open into a wall: a deep thump, a wooden crack, a short rattle."""
    rng = np.random.default_rng(41)
    n = int((CUE_LEN["slam"] - 0.05) * SR); tt = np.arange(n) / SR
    thump = np.sin(2 * np.pi * 70 * tt) * np.exp(-tt * 18)
    crack = gaussian_filter(rng.standard_normal(n), 0.8) * np.exp(-tt * 60) * 0.8
    rattle = gaussian_filter(rng.standard_normal(n), 1.5) * (np.sin(2 * np.pi * 22 * tt) > 0.6) * np.exp(-(tt - 0.12).clip(0) * 12) * 0.25
    out = (thump + crack + rattle).astype(np.float32)
    return out / np.abs(out).max() * 0.6


def cheer():
    """An arena crowd: applause (thousands of tiny claps as shaped noise), a roar underneath, a few whoops."""
    rng = np.random.default_rng(31)
    n = int((CUE_LEN["cheer"] - 0.1) * SR); out = np.zeros(n, np.float32)
    claps = np.zeros(n, np.float32)
    idx = rng.integers(0, n - 400, 9000)
    for i in idx:                                                      # individual claps: short noise bursts
        claps[i:i + 220] += rng.standard_normal(220).astype(np.float32) * np.exp(-np.arange(220) / 40)
    claps = claps - gaussian_filter(claps, 6)                          # keep it crisp
    roar = gaussian_filter(rng.standard_normal(n).astype(np.float32), 8)
    out = claps * 0.5 + roar * 2.5
    for k in range(5):                                                 # whoops: rising sine glides
        a = int(rng.uniform(0.1, 1.4) * SR); m = int(0.35 * SR); tt = np.arange(m) / SR
        f = rng.uniform(600, 900) + 700 * tt / 0.35
        out[a:a + m] += np.sin(2 * np.pi * np.cumsum(f) / SR).astype(np.float32) * np.hanning(m).astype(np.float32) * 0.25
    env = np.minimum(1, np.minimum(np.arange(n) / (0.25 * SR), (n - np.arange(n)) / (0.7 * SR))).astype(np.float32)
    out *= env
    return out / (np.abs(out).max() + 1e-6) * 0.42


SFX = {"gavel": lambda: gavel_knock(), "bark": lambda: bark(), "cackle": lambda: cackle(), "hear": lambda: hear_hear(),
       "cheer": lambda: cheer(), "slam": lambda: door_slam(),
       "shot": lambda: gunshot(), "ding": lambda: steel_ding(), "laugh": lambda: group_laugh(),
       "jet": lambda: jet_pass(), "ring": lambda: phone_ring()}


def mix_audio(path, clips, starts, total, speakers=None, lines=None, block_s=60):
    """Write the final mix in blocks (constant memory, fine for hour-long episodes).

    Returns {speaker: per-video-frame RMS of that speaker's voice}, for mask animation (see envelope_from_rms).
    """
    N = int(total * SR)
    hop, nf = SR // FPS, int(total * FPS)
    speakers = speakers or [None] * len(clips)
    # per-speaker loudness per video frame, without materialising full-length tracks
    energy = {sp: np.zeros(nf + 2) for sp in set(speakers)}
    events = []
    for s, c, sp in zip(starts, clips, speakers):
        a = int(s * SR); events.append((a, c))
        f0 = a // hop
        idx = (a - f0 * hop + np.arange(len(c))) // hop
        bins = np.bincount(idx, weights=c.astype(np.float64) ** 2)
        e = energy[sp]; m = max(0, min(len(bins), len(e) - f0)); e[f0:f0 + m] += bins[:m]
    # sound effects from inline cues; voice-like ones (cackle, bark) also drive a mouth
    bank, hits = {}, []
    if lines:
        for t, cue, i in cue_events(lines, starts, [len(c) / SR for c in clips]):
            if cue not in bank:
                bank[cue] = SFX[cue]()
            snd = bank[cue]; a = int((t + 0.02) * SR); hits.append((a, snd))
            owner = CUE_OWNER[cue]
            owner = speakers[i] if owner == "speaker" else owner
            if owner is not None:
                e = energy.setdefault(owner, np.zeros(nf + 2))
                f0 = a // hop
                idx = (a - f0 * hop + np.arange(len(snd))) // hop
                bins = np.bincount(idx, weights=snd.astype(np.float64) ** 2)
                m = max(0, min(len(bins), len(e) - f0)); e[f0:f0 + m] += bins[:m]
    rms = {sp: np.sqrt(e[:nf] / hop).astype(np.float32) for sp, e in energy.items()}
    ref, _ = _drone(0, min(N, 60 * SR), N)
    dscale = 0.27 / (np.abs(ref).max() + 1e-9)

    def block(b0, b1):
        out = np.zeros(b1 - b0, np.float32)
        for a, c in events:                      # voice
            lo, hi = max(a, b0), min(a + len(c), b1)
            if lo < hi: out[lo - b0:hi - b0] += c[lo - a:hi - a] * 0.9
        for a, snd in hits:                      # sound effects
            lo, hi = max(a, b0), min(a + len(snd), b1)
            if lo < hi: out[lo - b0:hi - b0] += snd[lo - a:hi - a]
        d, tt = _drone(b0, b1, N)
        fade = (np.clip(tt / 2.0, 0, 1) * np.clip((total - tt) / 2.0, 0, 1)).astype(np.float32)
        return out + d * dscale * fade

    B = block_s * SR
    peak = max(np.abs(block(b, min(N, b + B))).max() for b in range(0, N, B))
    gain = 1.0 / max(1.0, peak / 0.95)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        for b in range(0, N, B):
            w.writeframes((block(b, min(N, b + B)) * gain * 32767).astype(np.int16).tobytes())
    return rms


def envelope(voice, total):
    """Per-frame voice loudness 0..1 from a voice track (kept for small/ad-hoc uses)."""
    nf = int(total * FPS); hop = SR // FPS
    rms = np.array([np.sqrt(np.mean(voice[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(nf)])
    return envelope_from_rms(rms)


def envelope_from_rms(rms):
    """Per-frame RMS -> 0..1 loudness with fast attack / slow release, for mask animation."""
    rms = np.asarray(rms, np.float64)
    ref = np.percentile(rms[rms > 1e-4], 90) if (rms > 1e-4).any() else 1.0
    raw = np.clip(rms / ref, 0, 1)
    env = np.zeros(len(raw), np.float32)
    for i in range(1, len(raw)):
        a = 0.6 if raw[i] > env[i - 1] else 0.25
        env[i] = env[i - 1] + a * (raw[i] - env[i - 1])
    return env


# ---------------------------------------------------------------- visuals
class Renderer:
    def __init__(self, cfg, lines, speakers, durs, starts, total, envs):
        self.cfg, self.lines, self.speakers, self.starts, self.total, self.envs = cfg, lines, speakers, starts, total, envs
        self.durs = durs
        self.label = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono-Bold.ttf", 20)
        self.mono = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono.ttf", 30)
        self.big = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono-Bold.ttf", 64)
        self.small = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono.ttf", 20)
        rng = np.random.default_rng(7)
        cw = W * 2
        a = gaussian_filter(rng.random((H // 4, cw // 4)).astype(np.float32), 6, mode="wrap") * 0.6
        b = gaussian_filter(rng.random((H // 4, cw // 4)).astype(np.float32), 2, mode="wrap") * 0.4
        cl = a + b; cl = (cl - cl.min()) / (cl.max() - cl.min())
        self.cloud = np.array(Image.fromarray((cl * 255).astype(np.uint8)).resize((cw, H), Image.BICUBIC)).astype(np.float32) / 255
        self.cw = cw
        gr = np.random.default_rng(11)
        self.grain = [gr.integers(-14, 15, (H, W, 1), dtype=np.int16) for _ in range(12)]   # reused film grain
        X, Y = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
        self.vign = np.clip(1.15 - 0.75 * (X ** 2 + Y ** 2), 0, 1).astype(np.float32)
        self.vign3 = self.vign[..., None]
        self.beam = np.clip(1 - (X ** 2 + (Y + 0.9) ** 2) / 1.2, 0, 1).astype(np.float32)
        # figures: one solo persona, or one per cast member (left to right in cast order)
        if cfg["cast"]:
            shown = [(sp, c) for sp, c in cfg["cast"].items() if c.get("mask")]   # mask: null = voice only (narrator)
            n = len(shown)
            self.figures = [(sp, c["mask"], c.get("x", (k + 1) / (n + 1))) for k, (sp, c) in enumerate(shown)]
        else:
            self.figures = [(None, cfg["mask"], 0.5)]
        self.windows = self.appearances()
        for _, m, _ in self.figures:
            if m not in MASKS:
                raise SystemExit(f"unknown mask {m!r}; available: {', '.join(MASKS)}")
        self.suits = {m: suit(MASKS[m].tie) for _, m, _ in self.figures}
        n = len(self.figures)
        lay = cfg["layout"]
        self.fig_scale = lay.get("scale", {1: 1.0, 2: 0.74, 3: 0.64}.get(n, 0.58))
        self.fig_top = lay.get("top", {1: 40, 2: 78, 3: 130}.get(n, 165))
        if cfg["set"].get("corridor"):
            self.corridor = Corridor(cfg["set"]["corridor"])
        self.gavels = [t for t, c, _ in cue_events(lines, starts, durs) if c == "gavel"]
        self.cheers = [t for t, c, _ in cue_events(lines, starts, durs) if c == "cheer"]
        evs = cue_events(lines, starts, durs)
        self.shots = [(t, speakers[i]) for t, c, i in evs if c == "shot"]
        self.dings = [t for t, c, _ in evs if c == "ding"]
        self.jets = [t for t, c, _ in evs if c == "jet"]
        sl = cfg["set"].get("slides")
        self.slides = [(self.phrase_time(p), txt) for p, txt in sl["cues"]] if sl else []
        if cfg["set"].get("chamber"):
            self.chamber_bg = chamber_backdrop(cfg["set"]["chamber"])
        if cfg["set"].get("barn"):
            self.chamber_bg = barn_backdrop(cfg["set"]["barn"])          # same static-backdrop path
        if cfg["set"].get("boardroom"):
            self.chamber_bg = boardroom_backdrop(cfg["set"]["boardroom"])
        if cfg["set"].get("hall"):
            self.chamber_bg = hall_backdrop(cfg["set"]["hall"])
        if cfg["set"].get("prairie"):
            self.chamber_bg = prairie_backdrop(cfg["set"]["prairie"])
        if cfg["set"].get("diner"):
            self.chamber_bg = diner_backdrop(cfg["set"]["diner"])
        if cfg["set"].get("arctic"):
            self.chamber_bg = arctic_backdrop(cfg["set"]["arctic"])
            yy, xx = np.mgrid[0:H // 4, 0:W // 4].astype(np.float32)
            self.aur_grid = (xx / (W // 4), yy / (H // 4))
        if cfg["set"].get("rally"):
            self.chamber_bg = rally_backdrop(cfg["set"]["rally"])
            self.crowd = Crowd(cfg["set"]["rally"])
        if cfg["set"].get("commons"):
            self.chamber_bg = commons_backdrop(cfg["set"]["commons"])
        if cfg["set"].get("assembly"):
            asm = cfg["set"]["assembly"]
            self.chamber_bg = assembly_backdrop(asm)
            self.swap_t = self.phrase_time(asm.get("terrazzo_at"))
            if self.swap_t is not None:                       # the marble wall turns out to be terrazzo
                self.swap_bg = assembly_backdrop({**asm, "terrazzo": True})
            self.esc_stop = self.phrase_time(asm.get("escalator_stops"))
            self.prompt_on = self.phrase_time(asm.get("teleprompter_on"))
        ch = cfg["set"].get("chyron")
        self.clock = None
        if ch and ch.get("clock"):
            ck = ch["clock"]
            find = lambda pre: next((starts[i] for i, l in enumerate(lines) if strip_cues(l).startswith(pre)), None)
            self.clock = (ck.get("from", 3600), find(ck["start"]), find(ck["zero"]))
        self.chy_big = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono-Bold.ttf", 22)
        self.card_font = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono-Bold.ttf", 15)
        lt = cfg["light"]["line"]
        self.light_t = next((starts[i] for i, l in enumerate(lines) if lt and l.startswith(lt)), None)
        self.sign_t = starts[len(lines) - cfg["signoff_lines"]] if cfg["signoff_lines"] else float("inf")

    def phrase_time(self, phrase):
        """When a phrase is spoken: its line's start plus its share of the line (by characters)."""
        if not phrase:
            return None
        for i, l in enumerate(self.lines):
            txt = strip_cues(l)
            k = txt.find(phrase)
            if k >= 0:
                return self.starts[i] + self.durs[i] * k / max(1, len(txt))
        raise SystemExit(f"phrase not found in script: {phrase!r}")

    def aurora(self, t):
        """Moving green curtains of aurora over the upper sky (computed at quarter resolution, then upscaled)."""
        u, v = self.aur_grid
        a = np.zeros_like(u)
        for k, (f, sp, ph, y0) in enumerate(((3.0, 0.07, 0.0, 0.22), (5.0, -0.05, 1.7, 0.32), (2.2, 0.04, 3.1, 0.15))):
            band = y0 + 0.06 * np.sin(2 * np.pi * (u * f * 0.5 + t * sp) + ph)
            curtain = np.exp(-((v - band) / 0.05) ** 2)
            rays = 0.6 + 0.4 * np.sin(2 * np.pi * (u * f * 6 + t * sp * 3) + ph) ** 2
            tail = np.clip((v - band + 0.02) / 0.25, 0, 1) * np.exp(-np.clip(v - band, 0, None) / 0.12)
            a += (curtain + tail * 0.8) * rays * (0.55 - 0.1 * k)
        a = np.clip(a, 0, 1.2) * np.clip(1.6 - v * 2.4, 0, 1)
        big = np.array(Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR)).astype(np.float32) / 255
        return big[..., None] * np.array([0.12, 0.62, 0.36], np.float32)

    def draw_range(self, im, t):
        """Steel plates on stakes far down the range; each [ding] swings the next plate. Each [shot] puts a brief
        muzzle flash at the shooter's shoulder."""
        rg = (self.cfg["set"].get("arctic") or {}).get("range")
        if not rg:
            return
        d = ImageDraw.Draw(im)
        xs = rg.get("plates", [0.52, 0.6, 0.68, 0.76])
        hits = [i for i, dt in enumerate(self.dings) if dt <= t]
        for k, xf in enumerate(xs):
            x, y = xf * W, rg.get("y", 392)
            swing = 0.0
            for i in hits:
                if i % len(xs) == k:
                    age = t - self.dings[i]
                    swing = 10 * math.exp(-age * 2.5) * math.sin(age * 18)
            d.line([(x, y), (x, y + 22)], fill=(40, 40, 44), width=3)
            d.line([(x - 8, y), (x + 8, y)], fill=(40, 40, 44), width=2)
            d.ellipse([x - 7 + swing, y + 2, x + 7 + swing, y + 16], fill=(230, 120, 40))
        for st, sp in self.shots:
            if 0 <= t - st < 0.12 and sp:
                c = self.cfg["cast"].get(sp, {}); xf = c.get("x", 0.5)
                s = c.get("scale", self.fig_scale); top = c.get("top", self.fig_top)
                fx, fy = xf * W + 150 * s, top + 360 * s
                d.polygon([(fx, fy - 14), (fx + 46, fy), (fx, fy + 14), (fx + 12, fy)], fill=(255, 230, 150))

    def draw_jets(self, im, t):
        """A fighter jet streaking across the top of the sky on each [jet]."""
        if not self.jets:
            return
        d = ImageDraw.Draw(im)
        for jt in self.jets:
            p = (t - jt) / 2.4
            if 0 <= p <= 1:
                x, y = -120 + p * (W + 240), 70 + 20 * p
                d.line([(x - 260, y + 6), (x - 20, y + 1)], fill=(230, 232, 236), width=2)      # contrail
                d.polygon([(x, y), (x - 46, y - 4), (x - 60, y - 16), (x - 54, y), (x - 60, y + 8), (x - 46, y + 4)], fill=(80, 86, 96))
                d.polygon([(x - 30, y), (x - 40, y - 14), (x - 34, y)], fill=(70, 76, 86))

    def draw_breath(self, im, fi, t):
        """Puffs of breath from whoever is speaking (cold sets)."""
        if not (self.cfg["set"].get("arctic") or {}).get("breath"):
            return
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        for sp, m, xf in self.figures:
            if self.presence(sp, t) < 1 or self.amp(sp, fi) < 0.12:
                continue
            c = self.cfg["cast"].get(sp, {})
            s = c.get("scale", self.fig_scale); top = c.get("top", self.fig_top)
            mx, my = xf * W, top + 262 * s
            for k in range(4):
                age = ((t * 1.6 + k / 4) % 1)
                r = (8 + 26 * age) * s
                x = mx + (18 + 60 * age) * s * (1 if xf < 0.5 else -1); y = my - 30 * age * s
                d.ellipse([x - r, y - r * 0.7, x + r, y + r * 0.7], fill=(235, 240, 250, int(110 * (1 - age))))
        im.paste(layer.filter(ImageFilter.GaussianBlur(4)), (0, 0), layer.filter(ImageFilter.GaussianBlur(4)))

    def draw_slides(self, im, t):
        """A projector screen behind the table; its slide changes on phrases. A slide is lines of text joined
        by \\n; the special slide "MAP" draws a crude map of Canada with the north shaded and an arrow."""
        sl = self.cfg["set"].get("slides")
        if not sl:
            return
        cur = sl.get("first", "")
        for at, txt in self.slides:
            if at is not None and t >= at:
                cur = txt
        d = ImageDraw.Draw(im)
        cx, y0, w, h = sl.get("x", 0.5) * W, sl.get("y", 30), sl.get("w", 420), sl.get("h", 200)
        x0 = cx - w / 2
        d.rectangle([x0 - 6, y0 - 6, x0 + w + 6, y0 + h + 6], fill=(40, 40, 44))
        d.rectangle([x0, y0, x0 + w, y0 + h], fill=(236, 238, 242))
        d.rectangle([x0, y0, x0 + w, y0 + 22], fill=(30, 60, 130))
        d.text((x0 + 8, y0 + 4), sl.get("banner", "UNCLASSIFIED//FOUO"), font=self.card_font, fill=(240, 240, 240))
        if cur == "MAP":
            pts = [(0.05, 0.75), (0.2, 0.72), (0.3, 0.8), (0.45, 0.78), (0.55, 0.86), (0.7, 0.8), (0.85, 0.86), (0.95, 0.7),
                   (0.9, 0.5), (0.8, 0.45), (0.75, 0.25), (0.6, 0.18), (0.45, 0.3), (0.35, 0.15), (0.2, 0.2), (0.1, 0.35)]
            P = [(x0 + 10 + px * (w - 20), y0 + 26 + py * (h - 30)) for px, py in pts]
            d.polygon(P, fill=(200, 210, 200), outline=(80, 90, 80))
            d.polygon([(x0 + 10 + px * (w - 20), y0 + 26 + min(py, 0.62) * (h - 30)) for px, py in pts], fill=(170, 200, 230))
            d.line([(x0 + 10, y0 + 26 + 0.62 * (h - 30)), (x0 + w - 10, y0 + 26 + 0.62 * (h - 30))], fill=(200, 40, 40), width=2)
            d.text((x0 + w * 0.36, y0 + 26 + 0.4 * (h - 30)), "HERE BE RANGERS", font=self.card_font, fill=(150, 30, 30))
            d.text((x0 + w * 0.42, y0 + 26 + 0.68 * (h - 30)), "TORONTO (LUNCH)", font=self.card_font, fill=(40, 40, 60))
        else:
            for k, line in enumerate(cur.split("\n")):
                f = self.chy_big if k == 0 else self.card_font
                d.text((x0 + 16, y0 + 34 + (0 if k == 0 else 12 + k * 22)), line, font=f, fill=(30, 30, 50) if k == 0 else (60, 60, 80))

    def draw_escalator(self, im, t):
        """A side-wall escalator whose steps climb until it stops dead."""
        asm = self.cfg["set"].get("assembly")
        if not asm or not asm.get("escalator"):
            return
        d = ImageDraw.Draw(im)
        x0, y0, x1, y1 = 6, 470, 236, 140                   # bottom-left to top-right
        d.polygon([(x0, y0), (x0 + 70, y0), (x1 + 70, y1), (x1, y1)], fill=(70, 72, 78))
        tt = t if self.esc_stop is None else min(t, self.esc_stop)
        phase = (tt * 0.6) % 1
        for k in range(12):
            f = (k + phase) / 12
            sx, sy = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
            d.line([(sx + 4, sy), (sx + 66, sy)], fill=(120, 124, 132), width=3)
        for off in (0, 70):                                   # handrails
            d.line([(x0 + off, y0 - 34), (x1 + off, y1 - 34)], fill=(24, 24, 26), width=7)
        if self.esc_stop is not None and t >= self.esc_stop:
            sx, sy = (x0 + x1) / 2 + 35, (y0 + y1) / 2         # stopped right in the middle
            if int(t * 2) % 2 == 0 or t - self.esc_stop > 6:
                d.rectangle([sx - 54, sy - 62, sx + 54, sy - 36], fill=(150, 30, 30))
                d.text((sx - 46, sy - 58), "STOPPED", font=self.card_font, fill=(250, 230, 230))

    def draw_commons_table(self, im):
        """The Table of the House in front of the frontbenches: green baize, the mace lying along it, and a
        brass-bound despatch box in front of each speaker's place."""
        cm = self.cfg["set"].get("commons")
        if not cm:
            return
        d = ImageDraw.Draw(im)
        y = cm.get("table_y", 470)
        d.polygon([(120, y), (W - 120, y), (W - 40, H), (40, H)], fill=(60, 40, 28))
        d.polygon([(150, y), (W - 150, y), (W - 110, y + 46), (110, y + 46)], fill=(40, 88, 58))     # baize top
        d.line([(120, y), (W - 120, y)], fill=(110, 80, 50), width=4)
        mx0, mx1, my = W * 0.42, W * 0.6, y + 26                                                      # the mace
        d.line([(mx0, my), (mx1, my)], fill=(214, 176, 74), width=9)
        d.ellipse([mx1 - 6, my - 18, mx1 + 34, my + 18], fill=(224, 186, 80))
        d.polygon([(mx1 + 8, my - 18), (mx1 + 14, my - 30), (mx1 + 20, my - 18)], fill=(224, 186, 80))
        for xf in cm.get("boxes", [0.3, 0.78]):                                                      # despatch boxes
            bx = xf * W
            d.rectangle([bx - 70, y - 40, bx + 70, y + 6], fill=(92, 60, 38), outline=(200, 166, 84), width=3)
            for cxk in (bx - 70, bx + 70):
                d.rectangle([cxk - 6, y - 40, cxk + 6, y + 6], fill=(190, 156, 76))

    def draw_teleprompters(self, im, t):
        """Two glass teleprompter panes on poles: dead, then (on cue) flicker back to life."""
        asm = self.cfg["set"].get("assembly")
        if not asm or not asm.get("teleprompters"):
            return
        layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
        on = self.prompt_on is not None and t >= self.prompt_on
        if on and t - self.prompt_on < 0.8:
            on = int((t - self.prompt_on) * 12) % 2 == 0     # flicker
        for xf in asm.get("teleprompters_x", [0.3, 0.7]):
            cx = xf * W
            d.line([(cx, 330), (cx, 520)], fill=(30, 30, 34, 255), width=6)
            pane = [(cx - 70, 230), (cx + 70, 230), (cx + 60, 340), (cx - 60, 340)]
            d.polygon(pane, fill=(150, 190, 210, 70) if on else (20, 24, 28, 150), outline=(200, 210, 220, 160))
            if on:
                scroll = (t * 14) % 16
                for r in range(6):
                    y = 246 + r * 16 - scroll
                    if 236 < y < 330:
                        d.line([(cx - 48, y), (cx + 20 + 18 * ((r * 7) % 3), y)], fill=(225, 240, 250, 150), width=4)
            else:
                d.text((cx - 50, 276), "NO SIGNAL", font=self.card_font, fill=(150, 60, 60, 200))
        im.paste(layer, (0, 0), layer)

    def wrap_font(self, text, font, width=None):
        """Greedy word wrap for any font."""
        width = width or W - 160
        rows, cur = [], ""
        for word in text.split():
            trial = (cur + " " + word).strip()
            if font.getlength(trial) > width and cur:
                rows.append(cur); cur = word
            else:
                cur = trial
        if cur:
            rows.append(cur)
        return rows

    def wrap(self, text):
        out, cur = [], ""
        for w_ in text.split():
            t = (cur + " " + w_).strip()
            if self.mono.getlength(t) <= W - 200: cur = t
            else: out.append(cur); cur = w_
        return out + ([cur] if cur else [])

    def caption(self, t):
        """Index of the line on screen at time t, or None."""
        for i, s in enumerate(self.starts):
            if s - 0.05 <= t <= s + self.durs[i] + 0.35 and strip_cues(self.lines[i]):
                return i
        return None

    def active_speaker(self, t):
        """Whoever spoke most recently (so the highlight holds through pauses)."""
        last = None
        for i, s in enumerate(self.starts):
            if s - 0.05 <= t: last = self.speakers[i]
            else: break
        return last

    # ---- walk-and-talk
    def appearances(self):
        """For cast members with "enter": time windows when they're on screen (around each burst of their lines)."""
        out = {}
        for sp, c in self.cfg["cast"].items():
            if not c.get("enter"):
                continue
            idx = [i for i, s in enumerate(self.speakers) if s == sp]
            groups, cur = [], [idx[0]] if idx else []
            for a, b in zip(idx, idx[1:]):
                if self.starts[b] - (self.starts[a] + self.durs[a]) > c.get("linger", 10):
                    groups.append(cur); cur = [b]
                else:
                    cur.append(b)
            if cur: groups.append(cur)
            out[sp] = [(self.starts[g[0]] - 0.9, self.starts[g[-1]] + self.durs[g[-1]] + 1.1) for g in groups]
        return out

    def presence(self, sp, t):
        """0..1 how far a walk-on character has slid into frame (1 = in place); 1 for regulars."""
        if sp not in self.windows:
            return 1.0
        for a, b in self.windows[sp]:
            if a <= t <= b:
                p = min(1, (t - a) / 0.6, (b - t) / 0.6)
                return 0.5 - 0.5 * math.cos(math.pi * max(0, p))      # ease in/out
        return 0.0

    # ---- set dressing
    def draw_placard(self, im):
        text = self.cfg["set"].get("placard")
        if not text:
            return
        d = ImageDraw.Draw(im)
        tw = self.card_font.getlength(text)
        x0, y0 = (W - tw) / 2 - 18, 52
        d.rectangle([x0, y0, x0 + tw + 36, y0 + 34], fill=(26, 24, 24), outline=(150, 40, 36), width=2)
        d.text((x0 + 18, y0 + 8), text, font=self.card_font, fill=(214, 70, 60))

    def draw_monitor(self, im, head, c, lit, t):
        """Guest shown inside a TV on a stand: head-and-shoulders crop, blue cast, scanlines, bezel."""
        sw, sh = c.get("screen_w", 300), c.get("screen_h", 210)
        cx, top = c.get("x", 0.8) * W, c.get("top", 120)
        crop = head.crop((60, 70, 460, 350)).resize((sw, sh), Image.BICUBIC)
        scr = Image.new("RGB", (sw, sh), (18, 26, 40))
        scr.paste(crop, (0, 0), crop)
        a = np.asarray(scr).astype(np.float32)
        a *= np.array([0.86, 0.95, 1.12], np.float32) * (1.0 if lit else 0.75)
        a[::2] *= 0.82
        scr = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))
        d = ImageDraw.Draw(im)
        x0, y0 = int(cx - sw / 2), int(top)
        d.rectangle([x0 - 16, y0 - 16, x0 + sw + 16, y0 + sh + 16], fill=(22, 22, 24))
        d.line([(cx, y0 + sh + 16), (cx, y0 + sh + 120)], fill=(30, 30, 32), width=10)
        d.rectangle([cx - 60, y0 + sh + 116, cx + 60, y0 + sh + 126], fill=(30, 30, 32))
        im.paste(scr, (x0, y0))
        if c.get("screen_label"):
            lab = c["screen_label"]; tw = self.card_font.getlength(lab)
            d.rectangle([x0, y0 + sh - 26, x0 + tw + 16, y0 + sh], fill=(150, 30, 34))
            d.text((x0 + 8, y0 + sh - 22), lab, font=self.card_font, fill=(245, 245, 245))
        if int(t * 1.2) % 2 == 0:                                   # LIVE dot
            d.ellipse([x0 + sw - 22, y0 + 10, x0 + sw - 10, y0 + 22], fill=(220, 40, 40))

    def draw_desk(self, im):
        dk = self.cfg["set"].get("desk")
        if not dk:
            return
        d = ImageDraw.Draw(im)
        cx, y, w = dk.get("x", 0.4) * W, dk.get("y", 520), dk.get("w", 620)
        d.polygon([(cx - w / 2, y), (cx + w / 2, y), (cx + w / 2 + 30, H), (cx - w / 2 - 30, H)], fill=(96, 66, 42))
        for k in range(1, 4):                                       # plank seams
            d.line([(cx - w / 2 - 10 * k, y + 50 * k), (cx + w / 2 + 10 * k, y + 50 * k)], fill=(70, 48, 30), width=3)
        d.rectangle([cx - w / 2 - 12, y - 14, cx + w / 2 + 12, y + 4], fill=(120, 86, 56))
        if dk.get("mic"):                                           # boom arm + broadcast mic + pop filter
            mx, my = dk.get("mic_x", cx + 70), dk.get("mic_y", y - 120)
            d.line([(cx + w / 2 - 20, y - 14), (cx + w / 2 - 60, y - 200), (mx + 40, my - 30)], fill=(26, 26, 28), width=8)
            d.rounded_rectangle([mx - 20, my - 46, mx + 20, my + 40], radius=18, fill=(30, 30, 34))
            for k in range(-36, 36, 9):
                d.line([(mx - 18, my + k), (mx + 18, my + k)], fill=(54, 54, 60), width=2)
            d.ellipse([mx - 64, my - 40, mx - 24, my + 34], outline=(20, 20, 22), width=4, fill=(40, 40, 46))
        if dk.get("mug"):
            mx = cx - w / 2 + 60
            d.rectangle([mx, y - 50, mx + 36, y - 14], fill=(170, 40, 40))
            d.arc([mx + 26, y - 44, mx + 50, y - 20], 270, 90, fill=(170, 40, 40), width=5)

    def draw_dog(self, im, fi, t):
        dg = self.cfg["set"].get("dog")
        if not dg:
            return
        d = ImageDraw.Draw(im)
        amp = self.amp("_dog", fi)
        cx, cy, s = dg.get("x", 0.1) * W, dg.get("y", 600), dg.get("scale", 1.0)
        fur, dark = tuple(dg.get("color", [214, 170, 100])), (120, 86, 46)
        P = lambda pts: [(cx + x * s, cy + y * s) for x, y in pts]
        bob = 3 * math.sin(t * 2.0)
        d.ellipse(P([(-70, -60 + bob), (70, 80 + bob)]), fill=fur)                       # head
        for side in (-1, 1):                                                             # floppy ears
            flap = 10 * amp
            d.ellipse(P([(side * 58 - 26, -40 + bob - flap), (side * 58 + 26, 50 + bob - flap)]), fill=dark)
        d.ellipse(P([(-38, 10 + bob), (38, 96 + bob + 22 * amp)]), fill=(230, 196, 140))   # muzzle
        d.ellipse(P([(-14, 14 + bob), (14, 34 + bob)]), fill=(30, 22, 18))                # nose
        for side in (-1, 1):
            d.ellipse(P([(side * 28 - 8, -18 + bob), (side * 28 + 8, -2 + bob)]), fill=(24, 18, 14))
        if amp > 0.08:
            d.ellipse(P([(-24, 52 + bob), (24, 70 + bob + 26 * amp)]), fill=(120, 30, 40))

    def draw_lectern(self, im):
        lc = self.cfg["set"].get("lectern")
        if not lc:
            return
        d = ImageDraw.Draw(im)
        cx, y = lc.get("x", 0.5) * W, lc.get("y", 470)
        for s in (-1, 1):   # two gooseneck mics
            d.line([(cx + s * 40, y + 6), (cx + s * 30, y - 40), (cx + s * 14, y - 70)], fill=(30, 30, 32), width=4)
            d.ellipse([cx + s * 14 - 7, y - 78, cx + s * 14 + 7, y - 62], fill=(20, 20, 22))
        body = tuple(lc.get("color", [78, 54, 38]))
        top = tuple(min(255, v + 20) for v in body); edge = tuple(int(v * 0.64) for v in body)
        d.polygon([(cx - 150, y), (cx + 150, y), (cx + 120, H), (cx - 120, H)], fill=body)
        if lc.get("marble"):                                  # pale veins across the front
            vr = np.random.default_rng(9)
            for _ in range(9):
                x0 = cx - 130 + vr.integers(0, 260); y0 = y + vr.integers(10, H - y - 10)
                d.line([(x0, y0), (x0 + vr.integers(-60, 60), y0 + vr.integers(20, 90))], fill=top, width=1)
        d.rectangle([cx - 160, y - 10, cx + 160, y + 8], fill=top)
        d.line([(cx - 150, y + 8), (cx + 150, y + 8)], fill=edge, width=3)
        if lc.get("seal"):
            d.ellipse([cx - 34, y + 40, cx + 34, y + 108], outline=(190, 160, 90), width=4)
            d.ellipse([cx - 22, y + 52, cx + 22, y + 96], outline=(190, 160, 90), width=2)

    def draw_chyron(self, im, t):
        ch = self.cfg["set"].get("chyron")
        if not ch:
            return
        d = ImageDraw.Draw(im)
        x0, y0 = 24, 22
        title, sub = ch.get("title", ""), ch.get("sub", "")
        w = max(self.card_font.getlength(title), self.card_font.getlength(sub)) + 28
        clock_txt, red = None, False
        if self.clock:
            frm, a, z = self.clock
            if a is None or t < a: rem = frm
            elif z is None or t >= z: rem = 0
            else: rem = frm * (1 - (t - a) / (z - a))
            mm, ss = divmod(int(math.ceil(rem)), 60)
            clock_txt = f"TIME REMAINING  {mm:02d}:{ss:02d}"
            red = rem <= 0
            w = max(w, self.chy_big.getlength(clock_txt) + 28)
        h = 58 + (34 if clock_txt else 0)
        d.rectangle([x0, y0, x0 + w, y0 + h], fill=(14, 22, 44))
        d.rectangle([x0, y0, x0 + 6, y0 + h], fill=(200, 40, 46))
        d.text((x0 + 16, y0 + 9), title, font=self.card_font, fill=(235, 235, 240))
        d.text((x0 + 16, y0 + 31), sub, font=self.card_font, fill=(170, 180, 205))
        if clock_txt:
            col = (240, 70, 60) if red and int(t * 2) % 2 == 0 else ((240, 70, 60) if red else (240, 214, 120))
            d.text((x0 + 16, y0 + 56), clock_txt, font=self.chy_big, fill=col)

    def draw_table(self, im, active):
        st = self.cfg["set"]
        if not st.get("table"):
            return
        d = ImageDraw.Draw(im)
        fig_h = 520 * self.fig_scale
        y = int(self.fig_top + fig_h * 0.72)
        yb = max(y + 70, int(self.fig_top + fig_h) + 8)        # deep enough to hide the suit hems
        d.polygon([(60, y), (W - 60, y), (W - 20, yb), (20, yb)], fill=(44, 32, 26))
        d.line([(60, y), (W - 60, y)], fill=(92, 70, 54), width=3)
        for sp, _, xf in self.figures:                      # tent cards
            label = self.cfg["cast"].get(sp, {}).get("card") if sp else None
            if not label:
                continue
            tw = self.card_font.getlength(label)
            cx = xf * W
            lit = 255 if sp == active else 190
            d.polygon([(cx - tw / 2 - 12, y + 34), (cx + tw / 2 + 12, y + 34), (cx + tw / 2 + 8, y + 8), (cx - tw / 2 - 8, y + 8)], fill=(lit, lit, lit - 8))
            d.text((cx - tw / 2, y + 13), label, font=self.card_font, fill=(30, 30, 34))
        if st.get("lockbox"):                               # the phones-in-the-box box
            bx, by = W / 2 - 34, y + 10
            d.rectangle([bx, by, bx + 68, by + 34], fill=(70, 74, 80), outline=(140, 144, 150), width=2)
            d.rectangle([bx + 28, by + 12, bx + 40, by + 24], fill=(200, 170, 70))

    def amp(self, speaker, fi):
        env = self.envs.get(speaker)
        a = 0.0 if env is None else float(env[min(fi, len(env) - 1)])
        for sp, c in self.cfg["cast"].items():                     # duets move both mouths
            if speaker in (c.get("duet") or []) and sp in self.envs:
                e2 = self.envs[sp]; a = max(a, float(e2[min(fi, len(e2) - 1)]))
        return a

    def centered(self, layer_draw, text, font, y, fill):
        layer_draw.text(((W - font.getlength(text)) / 2, y), text, font=font, fill=fill)

    def frame(self, fi):
        cfg = self.cfg
        rng = np.random.default_rng(fi)
        t = fi / FPS
        off = int(t * 22) % self.cw
        sky = np.concatenate([self.cloud[:, off:], self.cloud[:, :off]], 1)[:, :W]
        base = sky * 0.22 + 0.03
        flick = 1 + 0.05 * math.sin(t * 37) * (rng.random() < 0.3)
        glow = 0.0
        if self.light_t is not None and t >= self.light_t:
            glow = min(1, (t - self.light_t) / cfg["light"]["ramp"]) * (0.85 + 0.15 * (rng.random() > 0.1))
            if t >= self.sign_t: glow *= max(0, 1 - (t - self.sign_t) / 1.5)
        tr, tg, tb = cfg["light"]["tint"]
        if hasattr(self, "chamber_bg"):
            hall = self.chamber_bg
            if getattr(self, "swap_t", None) is not None and t >= self.swap_t:
                m = min(1.0, (t - self.swap_t) / 0.8)
                hall = hall * (1 - m) + self.swap_bg * m
            img = hall * (0.86 + 0.14 * sky[..., None])
            if hasattr(self, "aur_grid") and (cfg["set"].get("arctic") or {}).get("aurora", True):
                img = img + self.aurora(t)
            if glow > 0:
                img = img + glow * np.stack([tr * self.beam, tg * self.beam, tb * self.beam], -1)
        elif hasattr(self, "corridor"):
            hall = self.corridor.draw(t)
            base3 = hall * (0.82 + 0.18 * sky[..., None])
            img = base3 + glow * np.stack([tr * self.beam, tg * self.beam, tb * self.beam], -1)
        else:
            img = np.stack([base * 0.8 + glow * tr * self.beam, base * 0.85 + glow * tg * self.beam, base + glow * tb * self.beam], -1)
        img = img * (self.vign3 * np.float32(flick))
        im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))

        if t < 2.4:
            a = int(255 * min(1, t / 0.6) * min(1, (2.4 - t) / 0.4))
            layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
            self.centered(ld, cfg["title"], self.big, H / 2 - 60, (235, 235, 235, a))
            self.centered(ld, cfg["subtitle"], self.small, H / 2 + 20, (170, 170, 170, a))
            im.paste(layer, (0, 0), layer)
        else:
            duo = len(self.figures) > 1 or bool(cfg["cast"])
            base_scale, top = self.fig_scale, self.fig_top
            active = self.active_speaker(t)
            if glow > 0:
                hw = 230 if len(self.figures) == 1 else 470
                halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(halo).ellipse([W / 2 - hw, top + 30, W / 2 + hw, top + 330], fill=(*cfg["light"]["color"], int(85 * glow)))
                halo = halo.filter(ImageFilter.GaussianBlur(60))
                im.paste(halo, (0, 0), halo)
            self.draw_placard(im)
            self.draw_slides(im, t)
            self.draw_escalator(im, t)
            for k, (sp, m, xf) in enumerate(self.figures):
                c = cfg["cast"].get(sp, {}) if sp else {}
                pres = self.presence(sp, t)
                if pres <= 0:
                    continue
                s = c.get("scale", base_scale) * (1 + 0.015 * math.sin(t * 0.4 + k * 1.7))
                head = self.suits[m].copy()
                MASKS[m](ImageDraw.Draw(head), self.amp(sp, fi), t + k * 0.9)
                if duo and sp != active and sp not in ((cfg["cast"].get(active) or {}).get("duet") or []):   # dim whoever isn't speaking
                    r_, g_, b_, a_ = head.split()
                    dimmed = Image.merge("RGB", (r_, g_, b_)).point(lambda v: int(v * 0.62))
                    head = Image.merge("RGBA", (*dimmed.split(), a_))
                if c.get("screen"):                                 # remote guest on a TV monitor
                    self.draw_monitor(im, head, c, sp == active, t)
                    continue
                e = head.resize((int(520 * s), int(520 * s)), Image.BICUBIC)
                ex = xf * W - e.width / 2
                ey = c.get("top", top) + 4 * math.sin(t * 1.3 + k * 2.1)
                if c.get("walk"):                                  # gait: bounce on each step, slight sway
                    ph = t * 2 * math.pi * c.get("cadence", 1.9) + k * 1.3
                    ey -= 9 * abs(math.sin(ph / 2))
                    ex += 4 * math.sin(ph / 2)
                if c.get("gavel") and any(0 <= t - g < 0.3 for g in self.gavels):
                    ey += 7                                          # the chair leans into the gavel
                if c.get("enter"):                                  # slide in from the named side
                    side = -1 if c["enter"] == "left" else 1
                    ex += side * (1 - pres) * (W * 0.45)
                im.paste(e, (int(ex), int(ey)), e)
                if c.get("desk"):                                   # seated behind a desk front (e.g. the rostrum)
                    dd = ImageDraw.Draw(im)
                    dy = int(c.get("desk_y", ey + e.height * 0.62))
                    hw = e.width * 0.75
                    dd.rectangle([xf * W - hw, dy, xf * W + hw, dy + 140], fill=(70, 48, 34))
                    dd.line([(xf * W - hw, dy), (xf * W + hw, dy)], fill=(130, 98, 66), width=4)
                    dd.rectangle([xf * W - hw + 14, dy + 16, xf * W + hw - 14, dy + 124], outline=(96, 70, 48), width=2)
            self.draw_table(im, active)
            self.draw_teleprompters(im, t)
            self.draw_commons_table(im)
            self.draw_range(im, t)
            self.draw_jets(im, t)
            self.draw_breath(im, fi, t)
            if hasattr(self, "crowd"):
                hype = max([max(0.0, 1 - abs(t - c - 1.0) / 1.6) for c in self.cheers] + [0.0])
                self.crowd.draw(im, t, hype)
            self.draw_lectern(im)
            self.draw_desk(im)
            self.draw_dog(im, fi, t)
            self.draw_chyron(im, t)
            ci = self.caption(t)
            if ci is not None:
                rows = self.wrap(strip_cues(self.lines[ci]))
                tr = translation(self.lines[ci])
                trows = self.wrap_font(tr, self.small) if tr else []
                sp = self.speakers[ci]
                name = cfg["cast"][sp].get("name", sp) if duo and sp else None
                yb = H - 40 - len(rows) * 40 - len(trows) * 28 - (8 if trows else 0)
                band = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(band).rectangle([0, yb - (46 if name else 18), W, H], fill=(0, 0, 0, 150))
                im.paste(band, (0, 0), band)
                d = ImageDraw.Draw(im)
                if name:
                    col = tuple(cfg["cast"][sp].get("color", [200, 200, 200]))
                    label = name.upper()
                    d.text(((W - self.label.getlength(label)) / 2, yb - 34), label, font=self.label, fill=col)
                for k, row in enumerate(rows):
                    d.text(((W - self.mono.getlength(row)) / 2, yb + k * 40), row, font=self.mono, fill=(238, 238, 238))
                ty = yb + len(rows) * 40 + 8
                for k, row in enumerate(trows):                          # subtitle translation, smaller and dimmer
                    d.text(((W - self.small.getlength(row)) / 2, ty + k * 28), row, font=self.small, fill=(250, 214, 120))
            if t > self.total - 4.2:
                a = int(255 * min(1, (t - (self.total - 4.2)) / 0.5) * min(1, (self.total - t) / 0.6))
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
                ld.rectangle([0, 0, W, H], fill=(0, 0, 0, int(a * 0.85)))
                self.centered(ld, cfg["end_title"], self.big, H / 2 - 50, (235, 235, 235, a))
                for k, line in enumerate(cfg["credits"]):
                    shade = 160 if k == 0 else 120
                    self.centered(ld, line, self.small, H / 2 + 40 + 32 * k, (shade, shade, shade, a))
                im.paste(layer, (0, 0), layer)

        arr = np.asarray(im).astype(np.int16)
        arr += self.grain[fi % len(self.grain)]
        arr[::3] = (arr[::3] * 0.82).astype(np.int16)
        near_light = self.light_t is not None and abs(t - self.light_t) < 0.12
        if rng.random() < 0.06 or near_light:
            for _ in range(rng.integers(2, 7)):
                y0 = rng.integers(0, H - 40); h = rng.integers(4, 40)
                arr[y0:y0 + h] = np.roll(arr[y0:y0 + h], rng.integers(-40, 41), 1)
            arr[..., 0] = np.roll(arr[..., 0], 4, 1)
        return np.clip(arr, 0, 255).astype(np.uint8)


def chamber_backdrop(conf):
    """Static House-chamber backdrop: walnut wall, marble pilasters, rostrum tiers, a flag behind the chair."""
    conf = conf if isinstance(conf, dict) else {}
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):   # wall gradient
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(46 + 20 * k), int(40 + 14 * k), int(44 + 10 * k)))
    for x in range(0, W, 90):   # wall panels
        d.rectangle([x + 8, 30, x + 82, 300], outline=(70, 58, 52), width=2)
    rx0 = int(conf.get("rostrum_x", 0.5) * W)
    # flag behind the chair
    fx, fy, fw, fh = int(conf.get("flag_x", 0.74) * W) - 120, 34, 240, 150
    for k in range(13):
        col = (150, 40, 46) if k % 2 == 0 else (215, 210, 200)
        d.rectangle([fx, fy + k * fh / 13, fx + fw, fy + (k + 1) * fh / 13], fill=col)
    d.rectangle([fx, fy, fx + fw * 0.4, fy + fh * 7 / 13], fill=(40, 52, 100))
    for r in range(4):
        for c in range(5):
            sx, sy = fx + 10 + c * 18, fy + 9 + r * 18
            d.ellipse([sx - 2, sy - 2, sx + 2, sy + 2], fill=(225, 225, 225))
    # marble pilasters
    for px in conf.get("pilasters", [0.47, 0.985]):
        x = int(px * W)
        d.rectangle([x - 18, 0, x + 18, 420], fill=(196, 190, 178))
        d.line([(x - 8, 0), (x - 8, 420)], fill=(170, 164, 152), width=2)
    # rostrum: three walnut tiers on the right
    for k, (y0, y1, inset) in enumerate([(250, 300, 40), (300, 360, 20), (360, 430, 0)]):
        d.rectangle([rx0 + inset, y0, W, y1], fill=(84 - k * 8, 58 - k * 6, 40 - k * 4))
        d.line([(rx0 + inset, y0), (W, y0)], fill=(120, 90, 60), width=3)
    # dark drape on the left
    d.rectangle([0, 0, int(0.06 * W), H], fill=(36, 26, 40))
    # floor
    d.rectangle([0, 430, W, H], fill=(52, 30, 34))
    return np.asarray(im).astype(np.float32) / 255


def assembly_backdrop(conf):
    """Static general-assembly hall: a tall green-marble wall behind the speaker's rostrum, a gold-framed
    panel (deliberately blank: no emblem), wood-panelled side walls and the curve of the delegates' tiers."""
    conf = conf if isinstance(conf, dict) else {}
    rng = np.random.default_rng(12)
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):                               # dim hall above, warm wood below
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(30 + 30 * k), int(34 + 22 * k), int(44 + 8 * k)))
    for x in range(0, W, 64):                        # wood slats on the side walls
        d.line([(x, 0), (x, 470)], fill=(70, 56, 44), width=2)
    cx = int(conf.get("x", 0.5) * W); half = int(conf.get("width", 0.36) * W / 2)
    if conf.get("terrazzo"):                                                   # chips set in cement
        d.rectangle([cx - half, 0, cx + half, 470], fill=(176, 168, 150))
        for _ in range(900):
            x0 = cx - half + int(rng.integers(0, 2 * half)); y0 = int(rng.integers(0, 470)); r = int(rng.integers(2, 7))
            c = [(120, 110, 96), (210, 204, 190), (96, 120, 104), (150, 96, 80), (70, 66, 60)][int(rng.integers(0, 5))]
            d.ellipse([x0 - r, y0 - r * 0.7, x0 + r, y0 + r * 0.7], fill=c)
    else:
        d.rectangle([cx - half, 0, cx + half, 470], fill=(44, 82, 64))      # green marble wall
        for _ in range(70):                                                   # marble veining
            x0 = cx - half + int(rng.integers(0, 2 * half)); y0 = int(rng.integers(0, 470))
            pts = [(x0, y0)]
            for _k in range(5):
                x0 += int(rng.integers(-26, 26)); y0 += int(rng.integers(6, 30)); pts.append((x0, y0))
            d.line(pts, fill=(int(rng.integers(70, 110)), int(rng.integers(118, 150)), int(rng.integers(96, 120))), width=1)
    d.rectangle([cx - half, 0, cx + half, 470], outline=(160, 136, 70), width=6)
    pw, ph = int(half * 0.62), 150                                            # blank gold-framed panel
    d.rectangle([cx - pw, 40, cx + pw, 40 + ph], fill=(36, 66, 52), outline=(190, 160, 84), width=5)
    d.rectangle([cx - pw + 14, 54, cx + pw - 14, 26 + ph], outline=(150, 126, 66), width=2)
    for k in range(4):                                                        # delegates' tiers, curving away
        y0 = 470 + k * 62
        d.chord([-W * 0.3, y0 - 40, W * 1.3, y0 + 260], 180, 360, fill=(58 - k * 6, 42 - k * 4, 38 - k * 4))
        d.arc([-W * 0.3, y0 - 40, W * 1.3, y0 + 260], 180, 360, fill=(110, 84, 58), width=3)
    return np.asarray(im).astype(np.float32) / 255


def commons_backdrop(conf):
    """Static House of Commons: carved oak panelling and a gallery front above, the canopied Speaker's chair at
    the far end, green benches on both sides receding toward it, and green carpet with the two red lines."""
    conf = conf if isinstance(conf, dict) else {}
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(40 + 22 * k), int(30 + 16 * k), int(22 + 10 * k)))
    for x in range(0, W, 56):                                                    # oak panels with pointed tops
        d.rectangle([x + 6, 40, x + 50, 220], outline=(82, 60, 40), width=2)
        d.polygon([(x + 6, 40), (x + 28, 14), (x + 50, 40)], outline=(82, 60, 40))
    d.rectangle([0, 220, W, 244], fill=(66, 46, 30)); d.line([(0, 244), (W, 244)], fill=(110, 80, 50), width=3)   # gallery front
    cx = int(conf.get("chair_x", 0.56) * W)                                     # the Speaker's chair, far end
    d.rectangle([cx - 46, 150, cx + 46, 330], fill=(44, 30, 22))
    d.polygon([(cx - 60, 150), (cx, 70), (cx + 60, 150)], fill=(56, 38, 26))
    d.rectangle([cx - 30, 210, cx + 30, 300], fill=(40, 86, 58))
    d.polygon([(cx - 20, 210), (cx + 20, 210), (cx, 186)], fill=(200, 166, 84))
    # green carpet with the red lines, narrowing toward the chair
    d.polygon([(cx - 70, 330), (cx + 70, 330), (W * 0.84, H), (W * 0.16, H)], fill=(44, 82, 56))
    for side in (-1, 1):
        d.line([(cx + side * 56, 330), (W / 2 + side * W * 0.3, H)], fill=(170, 40, 40), width=4)
    # benches: tiers on both sides converging toward the chair
    for side in (-1, 1):
        for k in range(5):
            near = W / 2 + side * (W * 0.36 + k * 90); far = cx + side * (90 + k * 18)
            ytop_far, ytop_near = 300 - k * 22, 430 - k * 60
            pts = [(far, ytop_far), (near, ytop_near), (near, ytop_near + 40), (far, ytop_far + 10)]
            d.polygon(pts, fill=(48 + k * 4, 104 - k * 6, 70 - k * 4))
            d.line(pts[:2], fill=(90, 140, 100), width=2)
    return np.asarray(im).astype(np.float32) / 255


def boardroom_backdrop(conf):
    """Static Ottawa boardroom at dusk: dark wood panelling, a tall window onto a snowy Parliament Hill with the
    clock tower lit, a flag in the corner, a portrait frame turned to the wall."""
    conf = conf if isinstance(conf, dict) else {}
    rng = np.random.default_rng(23)
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for x in range(0, W, 64):
        d.rectangle([x, 0, x + 64, H], fill=(70 + (x // 64) % 2 * 5, 46, 32))
        d.line([(x, 0), (x, H)], fill=(46, 30, 20), width=2)
    wx0, wx1, wy0, wy1 = int(W * 0.6), W - 50, 50, 380                         # window
    for y in range(wy0, wy1):
        k = (y - wy0) / (wy1 - wy0)
        d.line([(wx0, y), (wx1, y)], fill=(int(40 + 60 * k), int(50 + 40 * k), int(90 + 20 * k)))
    tx = (wx0 + wx1) // 2                                                       # clock tower silhouette
    d.rectangle([tx - 26, 130, tx + 26, 330], fill=(30, 30, 40))
    d.polygon([(tx - 30, 130), (tx, 70), (tx + 30, 130)], fill=(40, 70, 70))
    d.ellipse([tx - 14, 150, tx + 14, 178], fill=(250, 230, 160))
    d.rectangle([wx0, 300, wx1, wy1], fill=(30, 30, 40))                        # the long building
    for x in range(wx0 + 10, wx1 - 10, 24):
        d.rectangle([x, 316, x + 10, 330], fill=(250, 220, 150))
    for _ in range(120):                                                        # snow
        x, y = int(rng.integers(wx0, wx1)), int(rng.integers(wy0, wy1))
        d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=(235, 235, 240))
    d.rectangle([wx0, wy0, wx1, wy1], outline=(46, 30, 20), width=10)
    d.line([(tx, wy0), (tx, wy1)], fill=(46, 30, 20), width=6)
    d.rectangle([80, 90, 260, 300], fill=(60, 44, 30), outline=(170, 140, 70), width=8)          # portrait, turned to the wall
    d.line([(90, 100), (250, 290)], fill=(80, 60, 40), width=2); d.line([(250, 100), (90, 290)], fill=(80, 60, 40), width=2)
    fx = int(W * 0.53)                                                          # flag on a pole
    d.line([(fx, 80), (fx, 420)], fill=(180, 160, 90), width=4)
    d.rectangle([fx + 2, 90, fx + 82, 130], fill=(240, 240, 236))
    d.rectangle([fx + 2, 90, fx + 22, 130], fill=(200, 30, 40)); d.rectangle([fx + 62, 90, fx + 82, 130], fill=(200, 30, 40))
    d.rectangle([0, 420, W, H], fill=(40, 30, 26))
    return np.asarray(im).astype(np.float32) / 255


def hall_backdrop(conf):
    """Static northern community hall: painted block walls, a bingo board, a coffee urn on a folding table,
    a whiteboard with the search-and-rescue roster, a window full of dark, and a roof patch with a bucket under it."""
    conf = conf if isinstance(conf, dict) else {}
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(0, H, 28):                                                     # painted cinder block
        for x in range(-(y // 28 % 2) * 40, W, 80):
            d.rectangle([x, y, x + 78, y + 26], fill=(196, 202, 188), outline=(170, 176, 162))
    d.rectangle([0, 0, W, 30], fill=(120, 110, 96))                               # ceiling edge
    d.ellipse([W * 0.47, 22, W * 0.47 + 70, 44], fill=(150, 120, 80))           # roof stain
    d.rectangle([60, 70, 300, 230], fill=(30, 30, 34)); d.rectangle([66, 76, 294, 224], fill=(10, 14, 30))   # window, dark
    d.rectangle([W - 330, 70, W - 60, 230], fill=(246, 246, 244), outline=(160, 160, 160), width=4)          # whiteboard
    f = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 18)
    for k, line in enumerate(conf.get("board", ["SAR ROSTER - THURSDAY", "Mary  Jonah  Doug", "Vic (tea)", "Gas: ask Doug"])):
        d.text((W - 316, 82 + k * 32), line, font=f, fill=(30, 60, 150) if k else (180, 30, 30))
    bx = int(W * 0.36)                                                            # bingo board
    d.rectangle([bx, 60, bx + 150, 160], fill=(40, 40, 46))
    for r in range(5):
        for c in range(5):
            on = (r * 5 + c) % 3 == 0
            d.ellipse([bx + 10 + c * 28, 68 + r * 18, bx + 24 + c * 28, 82 + r * 18], fill=(250, 200, 60) if on else (70, 70, 76))
    d.rectangle([0, 390, W, H], fill=(140, 120, 96))                              # floor
    return np.asarray(im).astype(np.float32) / 255


def prairie_backdrop(conf):
    """Static rifle range on the prairie in November: a pale cold sky, a snow-dusted field, a dirt berm with paper
    targets on frames, distance markers, and the edge of the firing-line shelter roof framing the top."""
    conf = conf if isinstance(conf, dict) else {}
    rng = np.random.default_rng(19)
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(150 + 40 * k), int(170 + 30 * k), int(196 + 20 * k)))
    d.polygon([(0, 380), (W, 370), (W, H), (0, H)], fill=(196, 190, 170))                 # field
    for _ in range(500):
        x, y = int(rng.integers(0, W)), int(rng.integers(380, H))
        d.line([(x, y), (x + int(rng.integers(-3, 4)), y - int(rng.integers(3, 9)))], fill=(150, 136, 100))
    d.polygon([(380, 372), (460, 330), (W - 120, 326), (W - 40, 368)], fill=(120, 96, 70))    # berm
    for k, x in enumerate(range(520, W - 160, 110)):                                       # target frames
        d.rectangle([x - 2, 330, x + 2, 366], fill=(110, 80, 50))
        d.rectangle([x + 38, 330, x + 42, 366], fill=(110, 80, 50))
        d.rectangle([x, 318, x + 40, 352], fill=(236, 232, 220))
        for r in (14, 9, 4):
            d.ellipse([x + 20 - r, 335 - r, x + 20 + r, 335 + r], outline=(30, 30, 30), width=2)
    for x, label in ((300, "100"), (700, "200"), (1080, "300")):                           # distance markers
        d.rectangle([x, 372, x + 40, 392], fill=(240, 200, 40)); d.text((x + 6, 376), label, fill=(30, 30, 30))
    d.rectangle([0, 0, W, 40], fill=(90, 84, 76))                                          # shelter roof edge
    for x in (60, W - 60):
        d.rectangle([x - 10, 0, x + 10, H], fill=(110, 100, 88))
    return np.asarray(im).astype(np.float32) / 255


def diner_backdrop(conf):
    """Static highway truck stop at night: wood panelling, a long window onto the lot with semis idling under
    sodium lights, a neon EAT sign, a pie case and a counter with stools."""
    conf = conf if isinstance(conf, dict) else {}
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for x in range(0, W, 48):                                                     # panelling
        d.rectangle([x, 0, x + 48, H], fill=(92 + (x // 48) % 2 * 6, 64, 42))
        d.line([(x, 0), (x, H)], fill=(60, 40, 26), width=2)
    wx0, wx1, wy0, wy1 = 60, W - 60, 60, 330                                     # window onto the lot
    d.rectangle([wx0, wy0, wx1, wy1], fill=(14, 16, 30))
    for x in (260, 640, 1000):                                                    # sodium lights
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([x - 140, wy0 + 10, x + 140, wy1 + 60], fill=(255, 170, 60, 34))
        im.paste(glow.filter(ImageFilter.GaussianBlur(30)), (0, 0), glow.filter(ImageFilter.GaussianBlur(30)))
        d.line([(x, wy0 + 20), (x, wy1)], fill=(40, 40, 46), width=4)
        d.ellipse([x - 10, wy0 + 14, x + 10, wy0 + 26], fill=(255, 190, 90))
    for k, x in enumerate((120, 470, 820)):                                       # semis: cab + trailer
        y = 230 + (k % 2) * 12
        d.rectangle([x, y - 70, x + 230, y + 30], fill=(170, 172, 178))
        d.rectangle([x + 236, y - 50, x + 300, y + 30], fill=[(150, 30, 30), (30, 70, 140), (40, 40, 44)][k])
        d.rectangle([x + 250, y - 40, x + 290, y - 14], fill=(30, 36, 50))
        for wx in (x + 30, x + 70, x + 260):
            d.ellipse([wx - 14, y + 20, wx + 14, y + 48], fill=(18, 18, 20))
        d.ellipse([x + 290, y + 4, x + 302, y + 16], fill=(255, 240, 200))
    d.rectangle([wx0, wy0, wx1, wy1], outline=(60, 40, 26), width=10)
    for x in range(wx0 + 290, wx1, 290):
        d.line([(x, wy0), (x, wy1)], fill=(60, 40, 26), width=8)
    f = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 54)                 # neon EAT
    nx, ny = int(conf.get("neon_x", 0.82) * W), 82
    for blur, alpha in ((14, 160), (0, 255)):
        lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(lay).text((nx, ny), "EAT", font=f, fill=(255, 60, 90, alpha))
        lay = lay.filter(ImageFilter.GaussianBlur(blur)) if blur else lay
        im.paste(lay, (0, 0), lay)
    d = ImageDraw.Draw(im)
    d.rectangle([0, 360, W, 400], fill=(170, 40, 40))                             # counter
    d.rectangle([0, 400, W, H], fill=(60, 44, 34))
    for x in range(80, W, 150):                                                   # stools
        d.ellipse([x - 26, 390, x + 26, 410], fill=(190, 30, 40))
    pc = int(conf.get("pie_x", 0.1) * W)                                          # pie case
    d.rectangle([pc - 60, 296, pc + 60, 360], fill=(200, 220, 230), outline=(160, 160, 170), width=3)
    for k in range(3):
        d.chord([pc - 50 + k * 34, 316, pc - 22 + k * 34, 352], 180, 360, fill=(210, 160, 90))
    return np.asarray(im).astype(np.float32) / 255


def arctic_backdrop(conf):
    """Static Arctic night: deep blue sky with stars, a long low white land, distant hamlet lights, the curved
    roof of a research station on the rise, a snowmobile and a long wooden sled in the foreground."""
    conf = conf if isinstance(conf, dict) else {}
    rng = np.random.default_rng(17)
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        if conf.get("twilight"):                                                     # noon in November: a pink-blue glow, no sun
            d.line([(0, y), (W, y)], fill=(int(40 + 150 * k ** 2), int(60 + 70 * k ** 2), int(110 + 30 * k)))
        else:
            d.line([(0, y), (W, y)], fill=(int(6 + 14 * k), int(10 + 20 * k), int(28 + 40 * k)))
    for _ in range(0 if conf.get("twilight") else 260):
        x, y = int(rng.integers(0, W)), int(rng.integers(0, 380)); b = int(rng.integers(120, 255))
        d.point((x, y), fill=(b, b, b))
    d.polygon([(0, 420), (300, 400), (700, 412), (1000, 396), (W, 410), (W, H), (0, H)], fill=(170, 184, 206))   # snow
    for x in range(40, W, 37):                                                     # hamlet lights, far off
        if rng.random() < 0.6:
            oy = int(rng.integers(-6, 6)); d.ellipse([x - 2, 404 + oy, x + 2, 408 + oy], fill=(255, 214, 140))
    rx = int(conf.get("station_x", 0.83) * W)                                       # the research station's curved roof
    d.rectangle([rx - 110, 360, rx + 110, 402], fill=(40, 46, 60))
    d.chord([rx - 120, 320, rx + 120, 400], 180, 360, fill=(60, 70, 90))
    for k in range(6):
        d.rectangle([rx - 96 + k * 34, 374, rx - 80 + k * 34, 388], fill=(255, 220, 150))
    sx = int(conf.get("sled_x", 0.12) * W)                                         # snowmobile + long sled
    d.polygon([(sx, 560), (sx + 140, 560), (sx + 170, 530), (sx + 110, 500), (sx + 40, 510)], fill=(30, 30, 36))
    d.polygon([(sx + 60, 500), (sx + 100, 470), (sx + 120, 500)], fill=(160, 40, 40))
    d.line([(sx - 10, 566), (sx + 190, 566)], fill=(20, 20, 24), width=5)
    d.rectangle([sx - 260, 540, sx - 20, 554], fill=(120, 90, 60))
    for k in range(7):
        d.line([(sx - 250 + k * 36, 540), (sx - 250 + k * 36, 566)], fill=(90, 66, 44), width=4)
    d.line([(sx - 266, 568), (sx - 12, 568)], fill=(90, 66, 44), width=4)
    return np.asarray(im).astype(np.float32) / 255


def rally_backdrop(conf):
    """Static arena rally: dark hall, truss with stage lights, a big red-and-white banner with a maple leaf and
    a slogan, flags along the back of the stage."""
    conf = conf if isinstance(conf, dict) else {}
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(H):
        k = y / H
        d.line([(0, y), (W, y)], fill=(int(18 + 20 * k), int(18 + 14 * k), int(26 + 12 * k)))
    d.rectangle([0, 30, W, 44], fill=(60, 62, 70))                             # lighting truss
    for x in range(20, W, 40):
        d.line([(x, 30), (x + 20, 44)], fill=(90, 92, 100), width=2)
    for x in range(80, W, 160):                                                 # stage lights + beams
        d.rectangle([x - 12, 44, x + 12, 62], fill=(30, 30, 34))
        beam = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(beam).polygon([(x - 8, 62), (x + 8, 62), (x + 120, 470), (x - 120, 470)], fill=(255, 240, 210, 18))
        im.paste(beam, (0, 0), beam)
    bw = int(conf.get("banner_w", 0.62) * W); bx = (W - bw) // 2                # banner
    d.rectangle([bx, 64, bx + bw, 184], fill=(200, 30, 40))
    d.rectangle([bx + bw // 2 - 70, 64, bx + bw // 2 + 70, 184], fill=(244, 242, 236))
    leaf = [(0, -60), (9, -38), (19, -45), (15, -16), (35, -31), (32, -22), (52, -25), (46, -11), (57, -3),
            (33, 13), (38, 25), (11, 20), (5, 38), (-5, 38), (-11, 20), (-38, 25), (-33, 13), (-57, -3), (-46, -11),
            (-52, -25), (-32, -22), (-35, -31), (-15, -16), (-19, -45), (-9, -38)]
    d.polygon([(bx + bw // 2 + x * 1.0, 128 + y * 1.0) for x, y in leaf], fill=(200, 30, 40))
    f = ImageFont.truetype(f"{FONT_DIR}/DejaVuSans-Bold.ttf", 30)
    for k, word in enumerate(conf.get("banner", ["STRONGER", "TOGETHER"])):
        tx = bx + (bw // 4 if k == 0 else 3 * bw // 4) - f.getlength(word) / 2
        d.text((tx, 106), word, font=f, fill=(244, 242, 236))
    for x in range(40, W, 110):                                                 # flags along the stage back
        if bx - 30 < x < bx + bw + 30:
            continue
        d.line([(x, 120), (x, 330)], fill=(150, 150, 156), width=3)
        d.rectangle([x, 120, x + 60, 156], fill=(244, 242, 236))
        d.rectangle([x, 120, x + 15, 156], fill=(200, 30, 40)); d.rectangle([x + 45, 120, x + 60, 156], fill=(200, 30, 40))
    d.rectangle([0, 420, W, H], fill=(30, 26, 30))                              # stage front
    d.line([(0, 420), (W, 420)], fill=(90, 80, 70), width=4)
    return np.asarray(im).astype(np.float32) / 255


class Crowd:
    """Foreground crowd silhouettes along the bottom of the frame: heads, raised flags and hockey sticks.
    They sway a little all the time and jump, wave and raise everything when hype is high (just after a [cheer])."""

    def __init__(self, conf):
        rng = np.random.default_rng(13)
        self.people = []
        for row, (y, sc) in enumerate(((560, 0.8), (606, 1.0), (656, 1.2))):
            x = -20 + rng.uniform(0, 30)
            while x < W + 40:
                kind = rng.choice(["none", "flag", "stick", "none", "sign"])
                self.people.append((x, y, sc, kind, rng.uniform(0, 6.28), row))
                x += rng.uniform(46, 70) * sc
        self.people.sort(key=lambda p: p[5])

    def draw(self, im, t, hype):
        d = ImageDraw.Draw(im)
        for x, y, sc, kind, ph, row in self.people:
            jump = hype * 14 * sc * max(0, math.sin(t * 9 + ph))
            sway = 3 * math.sin(t * 1.3 + ph)
            hx, hy = x + sway, y - 70 * sc - jump
            shade = 46 - row * 10
            col = (shade + 6, shade, shade + 4)
            up = 0.25 + 0.75 * hype
            if kind != "none":                                         # raised arm with a flag / stick / sign
                ax, ay = hx + 26 * sc, hy - (40 + 60 * up) * sc
                d.line([(hx + 14 * sc, hy + 30 * sc), (ax, ay)], fill=col, width=int(9 * sc))
                if kind == "flag":
                    wav = 6 * math.sin(t * 6 + ph)
                    d.line([(ax, ay), (ax, ay - 60 * sc)], fill=(120, 120, 126), width=3)
                    d.polygon([(ax, ay - 60 * sc), (ax + 50 * sc, ay - 56 * sc + wav), (ax + 50 * sc, ay - 30 * sc + wav), (ax, ay - 34 * sc)],
                              fill=(244, 242, 236))
                    d.polygon([(ax, ay - 60 * sc), (ax + 12 * sc, ay - 59 * sc), (ax + 12 * sc, ay - 33 * sc), (ax, ay - 34 * sc)], fill=(200, 30, 40))
                    d.polygon([(ax + 38 * sc, ay - 57 * sc + wav), (ax + 50 * sc, ay - 56 * sc + wav), (ax + 50 * sc, ay - 30 * sc + wav),
                               (ax + 38 * sc, ay - 31 * sc + wav)], fill=(200, 30, 40))
                elif kind == "stick":
                    d.line([(ax, ay + 10 * sc), (ax + 8 * sc, ay - 90 * sc)], fill=(170, 130, 80), width=int(6 * sc))
                    d.line([(ax + 8 * sc, ay - 90 * sc), (ax + 30 * sc, ay - 96 * sc)], fill=(170, 130, 80), width=int(8 * sc))
                else:
                    d.rectangle([ax - 26 * sc, ay - 50 * sc, ax + 26 * sc, ay - 10 * sc], fill=(200, 30, 40))
                    d.rectangle([ax - 20 * sc, ay - 44 * sc, ax + 20 * sc, ay - 16 * sc], outline=(244, 242, 236), width=2)
            d.ellipse([hx - 24 * sc, hy, hx + 24 * sc, hy + 52 * sc], fill=col)          # head
            d.rounded_rectangle([hx - 44 * sc, hy + 44 * sc, hx + 44 * sc, hy + 160 * sc], radius=int(24 * sc), fill=col)   # shoulders


def barn_backdrop(conf):
    """Static converted-barn studio: vertical planks, a beam, a window onto pines at dusk, a moose mount,
    a framed glossy headshot from the old network days, bookshelves and a hanging lantern."""
    conf = conf if isinstance(conf, dict) else {}
    rng = np.random.default_rng(4)
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    x = 0
    while x < W:                                   # planks
        w = int(rng.integers(52, 78)); k = int(rng.integers(-10, 10))
        d.rectangle([x, 0, x + w, H], fill=(104 + k, 72 + k, 48 + k))
        d.line([(x, 0), (x, H)], fill=(52, 36, 24), width=3)
        for _ in range(3):                         # knots
            ky = int(rng.integers(40, 680)); d.ellipse([x + w / 2 - 5, ky - 3, x + w / 2 + 5, ky + 3], fill=(76, 52, 34))
        x += w
    d.rectangle([0, 60, W, 96], fill=(70, 46, 30)); d.line([(0, 96), (W, 96)], fill=(44, 30, 20), width=4)   # beam
    # window onto the pines at dusk
    wx, wy, ww, wh = int(conf.get("window_x", 0.07) * W), 150, 230, 210
    for yy in range(wh):
        k = yy / wh
        d.line([(wx, wy + yy), (wx + ww, wy + yy)], fill=(int(70 + 90 * k), int(70 + 40 * k), int(110 - 20 * k)))
    for px in range(wx, wx + ww - 36, 30):
        hgt = int(rng.integers(70, 140))
        d.polygon([(px, wy + wh), (px + 20, wy + wh - hgt), (px + 40, wy + wh)], fill=(20, 34, 28))
    d.rectangle([wx, wy, wx + ww, wy + wh], outline=(230, 226, 214), width=10)
    d.line([(wx + ww / 2, wy), (wx + ww / 2, wy + wh)], fill=(230, 226, 214), width=6)
    d.line([(wx, wy + wh / 2), (wx + ww, wy + wh / 2)], fill=(230, 226, 214), width=6)
    # moose mount
    mx, my = int(conf.get("moose_x", 0.6) * W), 210
    d.ellipse([mx - 30, my - 10, mx + 30, my + 30], fill=(60, 40, 26))                    # plaque
    d.polygon([(mx - 34, my - 30), (mx + 34, my - 30), (mx + 22, my + 70), (mx, my + 92), (mx - 22, my + 70)], fill=(92, 62, 40))
    d.ellipse([mx - 24, my + 60, mx + 24, my + 100], fill=(110, 76, 50))
    for side in (-1, 1):                                                                   # palmate antlers
        d.polygon([(mx + side * 26, my - 26), (mx + side * 120, my - 70), (mx + side * 150, my - 120), (mx + side * 126, my - 90),
                   (mx + side * 118, my - 128), (mx + side * 100, my - 94), (mx + side * 86, my - 124), (mx + side * 76, my - 84),
                   (mx + side * 40, my - 44)], fill=(214, 196, 160))
    # framed glossy headshot from the old network days
    fx, fy = int(conf.get("frame_x", 0.86) * W), 140
    d.rectangle([fx - 70, fy, fx + 70, fy + 170], fill=(180, 150, 60))
    d.rectangle([fx - 58, fy + 12, fx + 58, fy + 158], fill=(40, 60, 110))
    try:
        sys.path.insert(0, HERE)
        from masks import render_head
        hs = render_head(conf.get("headshot_mask", "pundit"), 0.0, 0.0).crop((80, 60, 440, 420)).resize((110, 110), Image.BICUBIC)
        im.paste(hs, (fx - 55, fy + 22), hs)
    except Exception:
        pass
    small = ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono-Bold.ttf", 11)
    cap = conf.get("headshot_caption", "PRIME TIME")
    d.text((fx - small.getlength(cap) / 2, fy + 138), cap, font=small, fill=(230, 220, 180))
    # bookshelf
    bx, by = int(conf.get("shelf_x", 0.25) * W), 330
    for row in range(3):
        y0 = by + row * 70
        d.rectangle([bx, y0 + 60, bx + 260, y0 + 68], fill=(64, 42, 26))
        xx = bx + 6
        while xx < bx + 250:
            bw = int(rng.integers(10, 20)); bh = int(rng.integers(38, 58))
            col = [(120, 30, 34), (40, 60, 90), (190, 170, 120), (40, 70, 50), (90, 70, 50)][int(rng.integers(0, 5))]
            d.rectangle([xx, y0 + 60 - bh, xx + bw, y0 + 60], fill=col); xx += bw + 2
    # hanging lantern
    lx = int(conf.get("lantern_x", 0.46) * W)
    d.line([(lx, 96), (lx, 150)], fill=(30, 30, 30), width=3)
    d.rectangle([lx - 16, 150, lx + 16, 196], fill=(250, 210, 120), outline=(40, 40, 40), width=4)
    d.rectangle([lx - 20, 146, lx + 20, 152], fill=(40, 40, 40))
    arr = np.asarray(im).astype(np.float32) / 255
    X, Y = np.meshgrid(np.arange(W), np.arange(H))                                          # warm lantern glow
    glow = np.exp(-(((X - lx) ** 2) / (2 * 220 ** 2) + ((Y - 175) ** 2) / (2 * 180 ** 2))).astype(np.float32)
    arr = arr * (0.62 + 0.5 * glow[..., None] * np.array([1.0, 0.85, 0.6], np.float32))
    return np.clip(arr, 0, 1)


class Corridor:
    """One-point-perspective hallway with the camera tracking backward (walk-and-talk).

    Config (episode.json "set": {"corridor": {...}}): speed (units/s), plaques (list of room labels),
    color ([r,g,b] wall tint 0..255).
    """
    NEAR, FAR = 1.0, 16.0

    def __init__(self, conf):
        conf = conf if isinstance(conf, dict) else {}
        self.speed = conf.get("speed", 1.4)
        self.plaques = conf.get("plaques", ["S-219", "S-230", "CLOAKROOM", "S-207", "S-128", "S-211"])
        self.tint = np.array(conf.get("color", [150, 140, 125]), np.float32) / 255
        self.vx, self.vy = W / 2, 250
        self.fonts = {sz: ImageFont.truetype(f"{FONT_DIR}/DejaVuSansMono-Bold.ttf", sz) for sz in range(8, 31, 2)}
        self.ceil, self.floor = -self.vy / 460, 1.0

    def P(self, X, Y, z):
        return (self.vx + X * (W / 2) / z, self.vy + Y * 460 / z)

    def quad(self, d, X0, X1, Y0, Y1, z0, z1, fill, wall=None):
        if wall is not None:   # vertical strip on a side wall: X fixed, z varies
            pts = [self.P(wall, Y0, z0), self.P(wall, Y0, z1), self.P(wall, Y1, z1), self.P(wall, Y1, z0)]
        else:                  # horizontal patch on ceiling/floor: Y fixed (Y0), X and z vary
            pts = [self.P(X0, Y0, z0), self.P(X1, Y0, z0), self.P(X1, Y0, z1), self.P(X0, Y0, z1)]
        d.polygon(pts, fill=fill)

    def fog(self, z, rgb):
        f = max(0.0, min(1.0, (z - self.NEAR) / (self.FAR - self.NEAR)))
        k = (1 - f) ** 1.3
        return tuple(int(c * (0.18 + 0.82 * k)) for c in rgb)

    def draw(self, t):
        im = Image.new("RGB", (W, H), (0, 0, 0)); d = ImageDraw.Draw(im)
        tint = self.tint
        wall, ceil, floor = (tint * 150).astype(int), (tint * 120).astype(int), (tint * 70).astype(int)
        # base planes (near frame to vanishing box)
        fz = self.FAR
        bx0, by0 = self.P(-1, self.ceil, fz); bx1, by1 = self.P(1, self.floor, fz)
        d.polygon([(0, 0), (W, 0), (bx1, by0), (bx0, by0)], fill=tuple(ceil))
        d.polygon([(0, H), (W, H), (bx1, by1), (bx0, by1)], fill=tuple(floor))
        d.polygon([(0, 0), (bx0, by0), (bx0, by1), (0, H)], fill=tuple(wall))
        d.polygon([(W, 0), (bx1, by0), (bx1, by1), (W, H)], fill=tuple(wall))
        d.rectangle([bx0, by0, bx1, by1], fill=tuple((tint * 40).astype(int)))
        # chair rail + baseboard along both walls
        for side in (-1, 1):
            for Y, col, wdt in ((0.28, (tint * 190).astype(int), 4), (0.95, (tint * 60).astype(int), 6)):
                d.line([self.P(side, Y, self.NEAR), self.P(side, Y, fz)], fill=tuple(col), width=wdt)
        # carpet runner
        r0 = self.P(-0.32, self.floor, self.NEAR); r1 = self.P(0.32, self.floor, self.NEAR)
        r2 = self.P(0.32, self.floor, fz); r3 = self.P(-0.32, self.floor, fz)
        d.polygon([r0, r1, r2, r3], fill=(70, 24, 28))
        # moving elements, far to near; the camera backs away so everything moves away from us... z grows
        spacing = 3.2
        off = (t * self.speed) % spacing
        n = int((self.FAR - self.NEAR) / spacing) + 2
        items = []
        for i in range(n):
            z = self.NEAR + i * spacing + off - spacing
            if z < 0.35 or z > self.FAR: continue
            items.append((z, i))
        for z, i in sorted(items, reverse=True):
            gi = int((t * self.speed + (self.FAR - z)) // spacing)   # stable id for labels as items travel
            # ceiling light
            self.quad(d, -0.22, 0.22, self.ceil, None, z, z + 0.5, self.fog(z, (250, 240, 210)))
            for side in (-1, 1):
                # door: dark wood strip on each wall, offset so sides alternate
                dz = z + (0.0 if side < 0 else spacing / 2)
                if dz > self.FAR: continue
                self.quad(d, None, None, -0.36, self.floor, dz, dz + 0.9, self.fog(dz, (64, 44, 34)), wall=side)
                self.quad(d, None, None, -0.36, -0.30, dz - 0.05, dz + 0.95, self.fog(dz, (120, 100, 70)), wall=side)
                # brass plaque with a room label, readable only when close
                if dz < 5.5:
                    label = self.plaques[(gi * 2 + (side > 0)) % len(self.plaques)]
                    px, py = self.P(side * 0.999, -0.12, dz - 0.25)
                    size = max(8, min(30, int(20 / dz) * 2 // 2))
                    font = self.fonts.get(size - size % 2, self.fonts[8])
                    tw = font.getlength(label)
                    bx = px - tw - 10 if side > 0 else px + 4
                    d.rectangle([bx - 4, py - 3, bx + tw + 4, py + size + 3], fill=self.fog(dz, (150, 124, 64)))
                    d.text((bx, py), label, font=font, fill=self.fog(dz, (30, 24, 16)))
        return np.asarray(im).astype(np.float32) / 255


# ---------------------------------------------------------------- driver
_R = None


def _init(state):
    global _R
    _R = Renderer(*state)


def _chunk(args):
    lo, hi, path, crf = args
    tmp = path[:-4] + ".tmp.mp4"
    p = subprocess.Popen(["ffmpeg", "-loglevel", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                          "-r", str(FPS), "-i", "-", "-vf", "hqdn3d=2:1:3:3", "-c:v", "libx264", "-preset", "veryfast",
                          "-crf", str(crf), "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for fi in range(lo, hi):
        p.stdin.write(_R.frame(fi).tobytes())
    p.stdin.close()
    if p.wait() != 0:
        raise RuntimeError(f"ffmpeg failed on {path}")
    os.replace(tmp, path)
    return path


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode", help="episode folder containing script.txt and episode.json")
    ap.add_argument("--preview", action="store_true", help="write a few PNG frames to build/ and stop")
    ap.add_argument("--at", help="with --preview: comma-separated moments, seconds or quoted phrases "
                                 "from the script (+N to offset), e.g. --at '30,It just went on+1'")
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    a = ap.parse_args()

    ep = os.path.abspath(a.episode)
    commit = git_commit()  # capture before rendering so the stamp matches the code that ran
    cfg, lines, speakers = load_episode(ep)
    build = os.path.join(ep, "build"); os.makedirs(build, exist_ok=True)

    clips = synth(ep, cfg, lines, speakers)
    starts, total = timeline(cfg, lines, clips)
    audio = os.path.join(build, "mix.wav")
    rms = mix_audio(audio, clips, starts, total, speakers, lines)
    envs = {sp: envelope_from_rms(r) for sp, r in rms.items()}
    state = (cfg, lines, speakers, [len(c) / SR for c in clips], starts, total, envs)
    who = ", ".join(f"{sp}={c['mask']}" for sp, c in cfg["cast"].items()) if cfg["cast"] else f"mask={cfg['mask']}"
    print(f"persona v{__version__} | {len(lines)} lines, {total:.1f}s, {who}")

    if a.preview:
        r = Renderer(*state)
        moments = [1.2, starts[min(3, len(starts) - 1)] + 0.5, (r.light_t or total / 2) + 0.8, total - 2]
        if a.at:
            moments = []
            for tok in a.at.split(","):
                tok, _, off = tok.partition("+")
                try: m = float(tok)
                except ValueError: m = r.phrase_time(tok.strip())
                moments.append(m + float(off or 0))
        for m in moments:
            Image.fromarray(r.frame(int(m * FPS))).save(os.path.join(build, f"preview_{m:07.1f}.png"))
        print("previews in", build)
        return

    nf = int(total * FPS)
    K = max(1, a.jobs)
    jobs = [(nf * k // K, nf * (k + 1) // K, os.path.join(build, f"part{k}.mp4"), cfg["crf"]) for k in range(K)]
    with ProcessPoolExecutor(K, initializer=_init, initargs=(state,)) as ex:
        parts = list(ex.map(_chunk, jobs))
    lst = os.path.join(build, "parts.txt")
    open(lst, "w").write("".join(f"file '{p}'\n" for p in parts))
    out = os.path.join(ep, cfg["output"]); tmp = out[:-4] + ".tmp.mp4"
    stamp = f"anonymous-synthetic-persona v{__version__} ({commit}) | episode {os.path.basename(ep)}"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-i", audio,
                    "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-c:a", "aac", "-b:a", "160k", "-shortest",
                    "-metadata", f"comment={stamp}", "-metadata", f"title={cfg['subtitle']}",
                    "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out)
    manifest = {
        "output": cfg["output"],
        "renderer_version": __version__,
        "renderer_commit": commit,
        "rendered_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds"),
        "duration_s": round(total, 2),
        "lines": len(lines),
        "mask": cfg["mask"] if not cfg["cast"] else None,
        "cast": {sp: c["mask"] for sp, c in cfg["cast"].items()} or None,
        "resolution": f"{W}x{H}@{FPS}",
    }
    json.dump(manifest, open(os.path.join(ep, "render.json"), "w"), indent=2)
    print("wrote", out, "|", stamp)


def git_commit():
    """Short HEAD hash, with -dirty if the renderer itself has uncommitted changes."""
    try:
        run = lambda *a: subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True, check=True).stdout.strip()
        dirty = run("status", "--porcelain", "--", "persona", "VERSION")
        return run("rev-parse", "--short", "HEAD") + ("-dirty" if dirty else "")
    except Exception:
        return "unknown"


if __name__ == "__main__":
    main()
