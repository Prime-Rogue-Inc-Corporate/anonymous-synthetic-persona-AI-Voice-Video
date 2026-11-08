# anonymous-synthetic-persona-AI-Voice-Video

A synthetic persona for audio-video generation: give it text, get back an old-school "We are Anonymous" broadcast with a flat robot voice, glitchy captions and a moth-in-a-suit emblem.

Current version: see [`VERSION`](VERSION) · history in [`CHANGELOG.md`](CHANGELOG.md).

## Episodes

| # | Episode | Source | Length |
|---|---------|--------|--------|
| 001 | [Greetings, Podiatrist](episodes/001-greetings-podiatrist) | The moth joke, for Norm | 2:44 |
| 002 | [Lyceum Address](episodes/002-lyceum-address) | Abraham Lincoln, Springfield, 1838 (cut) · `lincoln` mask | 4:12 |
| 003 | [Middle Powers](episodes/003-davos-middle-powers) | Mark Carney, Davos, Jan 20 2026 (full) | 18:16 |

Each episode folder holds `script.txt`, `episode.json`, the rendered `.mp4` and (from v0.2.0) `render.json`, which records the renderer version and commit that produced it.

## Masks

The persona's head changes per episode and moves with the voice.

| mask | look | animation |
|------|------|-----------|
| `moth` (default) | moth-in-a-suit, the Prime Rogue emblem | wings flutter with the voice |
| `lincoln` | pale Lincoln mask, stovepipe hat, chin-curtain beard | jaw opens with the voice |

Add one by writing a function in `persona/masks.py` decorated with `@mask("name")`. It gets the frame's voice loudness (`amp`, 0–1) and time (`t`), and draws on a 520×520 canvas with the suit's collar at y=300.

## Requirements

- `ffmpeg` and `espeak-ng` on your PATH (`apt install ffmpeg espeak-ng`)
- Python 3.10+ and `pip install -r requirements.txt`
- DejaVu fonts (`/usr/share/fonts/truetype/dejavu`, standard on most Linux)

## Making an episode

1. Create `episodes/NNN-slug/script.txt`, one caption line per line. Follow the format:
   `Greetings, <target>.` → `We are Anonymous.` → the text → the five sign-off lines
   (`We are Anonymous.` / `We are Legion.` / `We do not forgive.` / `We do not forget.` / `Expect us.`).
2. Add `episode.json` (every key is optional; see `DEFAULTS` in `persona/render.py`):

```json
{
  "subtitle": "message to podiatry",
  "mask": "moth",
  "credits": ["for Norm"],
  "voice": {"speed": 138},
  "pronounce": {"Qatar": "Kuh-tar"},
  "gaps": {"after": {"\"'Cause": 2.2}},
  "light": {"line": "\"'Cause", "color": [255, 210, 120], "ramp": 0.15, "tint": [0.45, 0.38, 0.18]},
  "output": "greetings_podiatrist.mp4"
}
```

   - `light.line`: the caption line where the light comes up (prefix match).
   - `gaps.after`: extra pause (seconds) after lines starting with the given prefix — use it for comic beats.
   - `pronounce`: respellings sent to the voice only; captions keep the original text.
3. Check a few frames, then render:

```bash
python persona/render.py episodes/NNN-slug --preview   # PNGs in episodes/NNN-slug/build/
python persona/render.py episodes/NNN-slug --jobs 4    # full render
```

Rendering runs at roughly 2× real time per core, so an 18-minute speech takes about 30 minutes on two cores.

## Loop clips

Pull a seamless loop out of any rendered episode by naming its first and last caption lines:

```bash
python tools/loop_clip.py episodes/002-lyceum-address --from "If destruction" --to "As a nation of freemen" --name destruction --repeat 4
```

Writes `episodes/<ep>/clips/<name>_loop.mp4` (one cycle, crossfaded tail-into-head) and `<name>_x4.mp4`.

## Versioning

Branches, pull requests, a changelog and semver tags. See [`CONTRIBUTING.md`](CONTRIBUTING.md). Short version:

```bash
git checkout -b feat/my-thing           # never commit straight to main
# ...work, add a line under [Unreleased] in CHANGELOG.md, open a PR...
python tools/release.py minor           # bump VERSION, roll the changelog, tag
git push origin HEAD --follow-tags
```

## Licence

Code: MIT, © 2026 Prime Rogue Inc. The emblem, persona name and episode content are **not** covered by the MIT licence — see [`TRADEMARKS.md`](TRADEMARKS.md).
