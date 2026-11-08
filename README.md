# anonymous-synthetic-persona-AI-Voice-Video

A synthetic persona for audio-video generation: give it text, get back an old-school "We are Anonymous" broadcast with a flat robot voice, glitchy captions and a moth-in-a-suit emblem.

Current version: see [`VERSION`](VERSION) · history in [`CHANGELOG.md`](CHANGELOG.md).

## Episodes

| # | Episode | Source | Length |
|---|---------|--------|--------|
| 001 | [Greetings, Podiatrist](episodes/001-greetings-podiatrist) | The moth joke, for Norm | 2:44 |
| 002 | [Lyceum Address](episodes/002-lyceum-address) | Abraham Lincoln, Springfield, 1838 (cut) · `lincoln` mask | 4:12 |
| 003 | [Middle Powers](episodes/003-davos-middle-powers) | Mark Carney, Davos, Jan 20 2026 (full) | 18:16 |
| 004 | [Record Extremes](episodes/004-record-extremes) | Original two-hander on the 2026 State of the Climate report · `anchor` + `expert` | ~2:45 |
| 005 | [Staff Level](episodes/005-staff-level) | Fictional SCIF recreation of the reported Alberta separatist / State Department meetings · 4 speakers + narrator | ~3:40 |

Each episode folder holds `script.txt`, `episode.json`, the rendered `.mp4` and (from v0.2.0) `render.json`, which records the renderer version and commit that produced it.

## Masks

The persona's head changes per episode and moves with the voice.

| mask | look | animation |
|------|------|-----------|
| `moth` (default) | moth-in-a-suit, the Prime Rogue emblem | wings flutter with the voice |
| `lincoln` | pale Lincoln mask, stovepipe hat, chin-curtain beard | jaw opens with the voice |
| `anchor` | news anchor: sleek bob, earpiece | mouth opens with the voice |
| `expert` | bald dome, round wire glasses, goatee, permanent smile | smile opens with the voice |
| `rancher` | cowboy hat, handlebar moustache, bolo tie | mouth opens under the moustache |
| `organizer` | curly hair, cat-eye glasses, earrings, scarf | mouth opens with the voice |
| `official` | grey side part, heavy brows, flag lapel pin | mouth opens with the voice |
| `aide` | ponytail (sways), lanyard and badge | mouth opens with the voice |

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

## Dialogue

Tag each line with a speaker and define the cast:

```
ANCHOR: Doctor Wren. Seven records. How should people feel?
WREN: Proud. Very few planets set seven records in a single year.
```

```json
"cast": {
  "ANCHOR": {"name": "Dana Kerr, anchor", "mask": "anchor", "x": 0.3, "color": [150, 190, 255],
             "voice": {"voice": "en-us+f3", "speed": 150, "pitch": 40}},
  "WREN":   {"name": "Dr. Ellis Wren", "mask": "expert", "x": 0.7, "color": [255, 205, 120],
             "voice": {"voice": "en-us+m7", "speed": 162, "pitch": 58}}
}
```

Each speaker gets their own espeak-ng voice (anything from `espeak-ng --voices`, plus a `+variant`), their own mask and their own voice-driven animation. Whoever isn't talking is dimmed. Leave `cast` out for a solo persona.

### Ensembles, narrators and sets

Any number of speakers works; the layout scales for 3 and 4+. A cast member with `"mask": null` is voice-only, which is handy for a narrator. Dress the room with `"set"`:

```json
"cast": {
  "NARRATOR": {"name": "Anonymous", "mask": null},
  "WADE":  {"mask": "rancher",  "x": 0.14, "card": "ALBERTA", "voice": {"voice": "en-us+m1", "pitch": 28}},
  "BRENT": {"mask": "official", "x": 0.62, "card": "STATE",   "voice": {"voice": "en-us+m3", "pitch": 48}}
},
"set": {"table": true, "placard": "SCIF · NO PERSONAL ELECTRONIC DEVICES BEYOND THIS POINT", "lockbox": true},
"signoff_lines": 6
```

`signoff_lines` is how many closing lines count as the sign-off (default 5); raise it if the sign-off has an extra button.

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
