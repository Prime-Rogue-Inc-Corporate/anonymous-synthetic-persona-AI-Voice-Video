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
        spoken = line.replace('"', "")
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


def mix_audio(path, clips, starts, total, speakers=None):
    """Write the final mix; return {speaker: voice track} for per-speaker mask animation."""
    rng = np.random.default_rng(7)
    N = int(total * SR)
    speakers = speakers or [None] * len(clips)
    tracks = {sp: np.zeros(N, np.float32) for sp in set(speakers)}
    for s, c, sp in zip(starts, clips, speakers):
        a = int(s * SR); tracks[sp][a:a + len(c)] += c
    voice = sum(tracks.values())
    tt = np.arange(N) / SR
    drone = np.zeros(N, np.float32)
    for f, amp in [(55, .5), (55.4, .4), (82.4, .25), (110.2, .12)]:
        drone += amp * (2 * ((tt * f) % 1) - 1)
    drone = gaussian_filter(drone, 6)
    drone = (drone + gaussian_filter(rng.standard_normal(N).astype(np.float32), 40) * 3) * (0.6 + 0.4 * np.sin(2 * np.pi * tt / 11))
    drone *= 0.27 / (np.abs(drone).max() + 1e-9)
    drone *= np.clip(tt / 2.0, 0, 1) * np.clip((total - tt) / 2.0, 0, 1)
    mix = voice * 0.9 + drone
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
            n = len(cfg["cast"])
            self.figures = [(sp, c["mask"], c.get("x", (k + 1) / (n + 1))) for k, (sp, c) in enumerate(cfg["cast"].items())]
        else:
            self.figures = [(None, cfg["mask"], 0.5)]
        for _, m, _ in self.figures:
            if m not in MASKS:
                raise SystemExit(f"unknown mask {m!r}; available: {', '.join(MASKS)}")
        self.suits = {m: suit(MASKS[m].tie) for _, m, _ in self.figures}
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
            duo = len(self.figures) > 1
            base_scale = 0.74 if duo else 1.0
            top = 78 if duo else 40
            active = self.active_speaker(t)
            if glow > 0:
                halo = Image.new("RGBA", (W, H), (0, 0, 0, 0))
                ImageDraw.Draw(halo).ellipse([W / 2 - 330, top + 50, W / 2 + 330, top + 360], fill=(*cfg["light"]["color"], int(85 * glow)))
                halo = halo.filter(ImageFilter.GaussianBlur(60))
                im.paste(halo, (0, 0), halo)
            for k, (sp, m, xf) in enumerate(self.figures):
                s = base_scale * (1 + 0.015 * math.sin(t * 0.4 + k * 1.7))
                head = self.suits[m].copy()
                MASKS[m](ImageDraw.Draw(head), self.amp(sp, fi), t + k * 0.9)
                if duo and sp != active:                       # dim whoever isn't speaking
                    r_, g_, b_, a_ = head.split()
                    dimmed = Image.merge("RGB", (r_, g_, b_)).point(lambda v: int(v * 0.62))
                    head = Image.merge("RGBA", (*dimmed.split(), a_))
                e = head.resize((int(520 * s), int(520 * s)), Image.BICUBIC)
                ex = int(xf * W - e.width / 2)
                ey = top + int(4 * math.sin(t * 1.3 + k * 2.1))
                im.paste(e, (ex, ey), e)
            ci = self.caption(t)
            if ci is not None:
                rows = self.wrap(self.lines[ci])
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
    tracks = mix_audio(audio, clips, starts, total, speakers)
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
