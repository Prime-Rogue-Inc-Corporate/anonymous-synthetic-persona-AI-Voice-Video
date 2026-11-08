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
            "chamber": None, "lectern": None, "chyron": None},
    "layout": {},
    "credits": [],
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
CUE = re.compile(r"\[(gavel)\]\s*", re.I)
CUE_LEAD = 0.55          # seconds of room left before a cued line for the sound effect


def strip_cues(text):
    """Remove inline sound cues like [gavel] from a line (for voice and captions)."""
    return CUE.sub("", text).strip()


def has_cue(text, name="gavel"):
    return any(m.group(1).lower() == name for m in CUE.finditer(text))


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
        v, pron = voice_for(cfg, speakers[i])
        spoken = strip_cues(line).replace('"', "")
        for k, rep in pron.items():
            spoken = spoken.replace(k, rep)
        raw, out = f"{work}/raw_{i:03d}.wav", f"{work}/v_{i:03d}.wav"
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
        if has_cue(lines[i]):
            t += CUE_LEAD
        starts.append(t)
        t += len(c) / SR
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


def mix_audio(path, clips, starts, total, speakers=None, lines=None):
    """Write the final mix; return {speaker: voice track} for per-speaker mask animation."""
    rng = np.random.default_rng(7)
    N = int(total * SR)
    speakers = speakers or [None] * len(clips)
    tracks = {sp: np.zeros(N, np.float32) for sp in set(speakers)}
    for s, c, sp in zip(starts, clips, speakers):
        a = int(s * SR); tracks[sp][a:a + len(c)] += c
    voice = sum(tracks.values())
    sfx = np.zeros(N, np.float32)
    if lines:
        knock = gavel_knock()
        for s, line in zip(starts, lines):
            if has_cue(line):
                a = int((s - CUE_LEAD + 0.02) * SR); sfx[a:a + len(knock)] += knock[:max(0, N - a)]
    tt = np.arange(N) / SR
    drone = np.zeros(N, np.float32)
    for f, amp in [(55, .5), (55.4, .4), (82.4, .25), (110.2, .12)]:
        drone += amp * (2 * ((tt * f) % 1) - 1)
    drone = gaussian_filter(drone, 6)
    drone = (drone + gaussian_filter(rng.standard_normal(N).astype(np.float32), 40) * 3) * (0.6 + 0.4 * np.sin(2 * np.pi * tt / 11))
    drone *= 0.27 / (np.abs(drone).max() + 1e-9)
    drone *= np.clip(tt / 2.0, 0, 1) * np.clip((total - tt) / 2.0, 0, 1)
    mix = voice * 0.9 + drone + sfx
    mix /= max(1.0, np.abs(mix).max() / 0.95)
    with wave.open(path, "w") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
        w.writeframes((mix * 32767).astype(np.int16).tobytes())
    return tracks


def envelope(voice, total):
    """Per-frame voice loudness 0..1 with fast attack / slow release, for mask animation."""
    nf = int(total * FPS)
    hop = SR // FPS
    rms = np.array([np.sqrt(np.mean(voice[i * hop:(i + 1) * hop] ** 2) + 1e-12) for i in range(nf)])
    ref = np.percentile(rms[rms > 1e-4], 90) if (rms > 1e-4).any() else 1.0
    raw = np.clip(rms / ref, 0, 1)
    env = np.zeros(nf, np.float32)
    for i in range(1, nf):
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
        X, Y = np.meshgrid(np.linspace(-1, 1, W), np.linspace(-1, 1, H))
        self.vign = np.clip(1.15 - 0.75 * (X ** 2 + Y ** 2), 0, 1).astype(np.float32)
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
        self.gavels = [starts[i] - CUE_LEAD for i, l in enumerate(lines) if has_cue(l)]
        if cfg["set"].get("chamber"):
            self.chamber_bg = chamber_backdrop(cfg["set"]["chamber"])
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
        self.sign_t = starts[len(lines) - cfg["signoff_lines"]]

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
            if s - 0.05 <= t <= s + self.durs[i] + 0.35:
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

    def draw_lectern(self, im):
        lc = self.cfg["set"].get("lectern")
        if not lc:
            return
        d = ImageDraw.Draw(im)
        cx, y = lc.get("x", 0.5) * W, lc.get("y", 470)
        for s in (-1, 1):   # two gooseneck mics
            d.line([(cx + s * 40, y + 6), (cx + s * 30, y - 40), (cx + s * 14, y - 70)], fill=(30, 30, 32), width=4)
            d.ellipse([cx + s * 14 - 7, y - 78, cx + s * 14 + 7, y - 62], fill=(20, 20, 22))
        d.polygon([(cx - 150, y), (cx + 150, y), (cx + 120, H), (cx - 120, H)], fill=(78, 54, 38))
        d.rectangle([cx - 160, y - 10, cx + 160, y + 8], fill=(98, 70, 50))
        d.line([(cx - 150, y + 8), (cx + 150, y + 8)], fill=(50, 34, 24), width=3)
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
        return 0.0 if env is None else float(env[min(fi, len(env) - 1)])

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
            base3 = hall * (0.86 + 0.14 * sky[..., None])
            img = base3 + glow * np.stack([tr * self.beam, tg * self.beam, tb * self.beam], -1)
        elif hasattr(self, "corridor"):
            hall = self.corridor.draw(t)
            base3 = hall * (0.82 + 0.18 * sky[..., None])
            img = base3 + glow * np.stack([tr * self.beam, tg * self.beam, tb * self.beam], -1)
        else:
            img = np.stack([base * 0.8 + glow * tr * self.beam, base * 0.85 + glow * tg * self.beam, base + glow * tb * self.beam], -1)
        img = img * self.vign[..., None] * flick
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
            for k, (sp, m, xf) in enumerate(self.figures):
                c = cfg["cast"].get(sp, {}) if sp else {}
                pres = self.presence(sp, t)
                if pres <= 0:
                    continue
                s = c.get("scale", base_scale) * (1 + 0.015 * math.sin(t * 0.4 + k * 1.7))
                head = self.suits[m].copy()
                MASKS[m](ImageDraw.Draw(head), self.amp(sp, fi), t + k * 0.9)
                if duo and sp != active:                       # dim whoever isn't speaking
                    r_, g_, b_, a_ = head.split()
                    dimmed = Image.merge("RGB", (r_, g_, b_)).point(lambda v: int(v * 0.62))
                    head = Image.merge("RGBA", (*dimmed.split(), a_))
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
            self.draw_lectern(im)
            self.draw_chyron(im, t)
            ci = self.caption(t)
            if ci is not None:
                rows = self.wrap(strip_cues(self.lines[ci]))
                sp = self.speakers[ci]
                name = cfg["cast"][sp].get("name", sp) if duo and sp else None
                yb = H - 40 - len(rows) * 40
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
            if t > self.total - 4.2:
                a = int(255 * min(1, (t - (self.total - 4.2)) / 0.5) * min(1, (self.total - t) / 0.6))
                layer = Image.new("RGBA", (W, H), (0, 0, 0, 0)); ld = ImageDraw.Draw(layer)
                ld.rectangle([0, 0, W, H], fill=(0, 0, 0, int(a * 0.85)))
                self.centered(ld, "EXPECT US.", self.big, H / 2 - 50, (235, 235, 235, a))
                for k, line in enumerate(cfg["credits"]):
                    shade = 160 if k == 0 else 120
                    self.centered(ld, line, self.small, H / 2 + 40 + 32 * k, (shade, shade, shade, a))
                im.paste(layer, (0, 0), layer)

        arr = np.asarray(im).astype(np.int16)
        arr += rng.integers(-14, 15, (H, W, 1), dtype=np.int16)
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
    ap.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    a = ap.parse_args()

    ep = os.path.abspath(a.episode)
    commit = git_commit()  # capture before rendering so the stamp matches the code that ran
    cfg, lines, speakers = load_episode(ep)
    build = os.path.join(ep, "build"); os.makedirs(build, exist_ok=True)

    clips = synth(ep, cfg, lines, speakers)
    starts, total = timeline(cfg, lines, clips)
    audio = os.path.join(build, "mix.wav")
    tracks = mix_audio(audio, clips, starts, total, speakers, lines)
    envs = {sp: envelope(v, total) for sp, v in tracks.items()}
    state = (cfg, lines, speakers, [len(c) / SR for c in clips], starts, total, envs)
    who = ", ".join(f"{sp}={c['mask']}" for sp, c in cfg["cast"].items()) if cfg["cast"] else f"mask={cfg['mask']}"
    print(f"persona v{__version__} | {len(lines)} lines, {total:.1f}s, {who}")

    if a.preview:
        r = Renderer(*state)
        moments = [1.2, starts[min(3, len(starts) - 1)] + 0.5, (r.light_t or total / 2) + 0.8, total - 2]
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
