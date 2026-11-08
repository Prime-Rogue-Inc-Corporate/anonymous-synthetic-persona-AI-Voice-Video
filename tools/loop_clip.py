#!/usr/bin/env python3
"""Cut a seamless loop from a rendered episode.

    python tools/loop_clip.py episodes/002-lyceum-address \
        --from "If destruction" --to "As a nation of freemen" --name destruction --repeat 4

Finds the caption lines by prefix, cuts from just before the first to just after
the last, then crossfades the tail into the head so the clip loops with no seam.
Writes <episode>/clips/<name>_loop.mp4 (one seamless cycle, set your player to loop)
and, with --repeat N, <name>_x<N>.mp4 (the cycle played N times, for posting).
"""
import argparse, json, os, subprocess, sys, wave

import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "persona"))
import render  # noqa: E402


def find(lines, prefix):
    hits = [i for i, l in enumerate(lines) if l.startswith(prefix)]
    if not hits:
        sys.exit(f"no line starts with {prefix!r}")
    return hits[0]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("episode")
    ap.add_argument("--from", dest="first", required=True, help="prefix of the first line")
    ap.add_argument("--to", dest="last", help="prefix of the last line (default: same as --from)")
    ap.add_argument("--name", required=True)
    ap.add_argument("--pad", type=float, default=0.5, help="seconds kept before/after the lines")
    ap.add_argument("--fade", type=float, default=0.6, help="crossfade length at the loop point")
    ap.add_argument("--repeat", type=int, default=0)
    a = ap.parse_args()

    ep = os.path.abspath(a.episode)
    cfg, lines, speakers = render.load_episode(ep)
    clips = render.synth(ep, cfg, lines, speakers)  # same voice + timeline as the render
    starts, _ = render.timeline(cfg, lines, clips)
    i, j = find(lines, a.first), find(lines, a.last or a.first)
    t0 = starts[i] - a.pad
    t1 = starts[j] + len(clips[j]) / render.SR + a.pad + a.fade
    D, f = t1 - t0, a.fade

    src = os.path.join(ep, cfg["output"])
    out_dir = os.path.join(ep, "clips"); os.makedirs(out_dir, exist_ok=True)
    loop = os.path.join(out_dir, f"{a.name}_loop.mp4"); tmp = loop[:-4] + ".tmp.mp4"
    # video: crossfade the tail into the head
    fc = (f"[0:v]split[va][vb];[va]trim={f}:{D},setpts=PTS-STARTPTS[body];[vb]trim=0:{f},setpts=PTS-STARTPTS[head];"
          f"[body][head]xfade=transition=fade:duration={f}:offset={D - 2 * f:.3f},format=yuv420p[v]")
    # audio: same crossfade done in numpy (ffmpeg's asplit+acrossfade deadlocks and emits nothing)
    raw_wav, loop_wav = os.path.join(out_dir, ".seg.wav"), os.path.join(out_dir, ".loop.wav")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{D:.3f}", "-i", src,
                    "-vn", "-ac", "2", "-ar", str(render.SR), raw_wav], check=True)
    with wave.open(raw_wav) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32).reshape(-1, 2)
    n = int(f * render.SR)
    body, head = x[n:].copy(), x[:n]
    ramp = np.linspace(0, np.pi / 2, n)[:, None]
    body[-n:] = body[-n:] * np.cos(ramp) + head * np.sin(ramp)   # equal-power crossfade
    with wave.open(loop_wav, "w") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(render.SR)
        w.writeframes(np.clip(body, -32768, 32767).astype(np.int16).tobytes())
    stamp = f"anonymous-synthetic-persona v{render.__version__} | loop {a.name} from {os.path.basename(ep)}"
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-ss", f"{t0:.3f}", "-t", f"{D:.3f}", "-i", src, "-i", loop_wav,
                    "-filter_complex", fc, "-map", "[v]", "-map", "1:a", "-c:v", "libx264", "-preset", "veryfast",
                    "-crf", "20", "-c:a", "aac", "-b:a", "160k", "-shortest", "-metadata", f"comment={stamp}",
                    "-movflags", "+faststart", tmp], check=True)
    for p in (raw_wav, loop_wav):
        os.remove(p)
    require_audio(tmp)
    os.replace(tmp, loop)
    print(f"wrote {loop} ({D - f:.2f}s cycle, lines {i + 1}-{j + 1})")

    if a.repeat > 1:
        rep = os.path.join(out_dir, f"{a.name}_x{a.repeat}.mp4"); tmp = rep[:-4] + ".tmp.mp4"
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-stream_loop", str(a.repeat - 1), "-i", loop,
                        "-c", "copy", "-movflags", "+faststart", tmp], check=True)
        require_audio(tmp)
        os.replace(tmp, rep)
        print(f"wrote {rep}")


def require_audio(path):
    """Fail loudly if a clip came out silent or without an audio track."""
    kinds = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", path],
                           capture_output=True, text=True).stdout.split()
    if "audio" not in kinds:
        sys.exit(f"{path}: no audio track")
    vd = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "volumedetect", "-vn", "-f", "null", "-"],
                        capture_output=True, text=True).stderr
    peak = float(vd.split("max_volume:")[1].split("dB")[0])
    if peak < -40:
        sys.exit(f"{path}: audio is silent (peak {peak} dB)")


if __name__ == "__main__":
    main()
