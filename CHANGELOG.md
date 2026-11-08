# Changelog

All notable changes to this project are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Walk-and-talk scenes: `"set": {"corridor": {...}}` draws a one-point-perspective hallway with the camera tracking backward: doors with brass room plaques, ceiling lights, a runner and a chair rail all recede as the cast walks. `speed`, `plaques` and `color` are configurable.
- Cast `"walk": true` adds a walking gait (step bounce and sway, `cadence` in steps/s).
- Cast `"enter": "left"|"right"` makes a walk-on: the character slides into frame for each burst of their lines and peels off afterwards (`linger` sets how long a gap still counts as the same burst).
- Per-cast `scale`/`top` and episode-level `"layout"` for waist-up framing.
- Masks: `chief`, `counsel`, `clerk`.
- Episode 006, *The Lame Duck*: an original walk-and-talk. Two senior Senate staffers (outgoing and incoming majority) speed-walk the Capitol through the Nov. 2026 lame-duck session while a floor aide and a press secretary cut in.
- Walk-and-talk smoke test (`tests/walk`).

### Planned
- 003 Davos: replace the WEF credit line with "Source: Office of the Prime Minister" and re-render the end card.
- Host full-quality renders as GitHub Release assets instead of in-tree.
- More test episodes: another historical speech or two.

## [0.4.0] - 2026-11-08

### Added
- Ensemble scenes: any number of on-screen speakers with automatic layout (sized for 1, 2, 3 or 4+).
- Voice-only cast members: `"mask": null` (e.g. a narrator) speaks with a caption label but no figure; on-screen figures dim while they talk.
- Set dressing via `"set"` in `episode.json`: a table with per-speaker tent cards (`"card"` in the cast entry), a wall placard, and a phone lockbox.
- Masks: `rancher`, `organizer`, `official`, `aide`.
- Episode 005, *Staff Level*: a fictional recreation, set in a SCIF, of the reported 2025 meetings between Alberta separatist organizers and U.S. State Department staff. Four invented characters plus a narrator who sets out what was reported, what is unconfirmed, and the October 2026 referendum result.

## [0.3.0] - 2026-11-08

### Added
- Dialogue mode: tag lines `SPEAKER: text` in `script.txt` and define a `"cast"` in `episode.json` (per-speaker mask, voice, position, label, colour). Each face animates from its own voice; the non-speaker dims; the speaker's name shows above the caption.
- Masks: `anchor` (sleek bob, earpiece) and `expert` (bald dome, round glasses, goatee, permanent smile).
- Episode 004, *Record Extremes*: an original two-hander. A deadpan anchor interviews a relentlessly positive (fictional) government messaging official about the 2026 State of the Climate report.
- Dialogue smoke test (`tests/dialogue`).
- `tools/loop_clip.py`: cut a seamless, crossfaded loop from any rendered episode by caption-line prefix (`--repeat N` for a posting copy).
- Episode 002 clip: "If destruction be our lot… or die by suicide" (`clips/destruction_loop.mp4`, 13.5s; `destruction_x4.mp4`).

### Fixed
- `loop_clip.py` produced clips with no audio track (ffmpeg `asplit`+`acrossfade` emitted nothing). The audio crossfade is now done in numpy, and the tool refuses to write a clip without audible sound.

## [0.2.0] - 2026-11-07

### Added
- Mask system (`persona/masks.py`): each episode picks its head with `"mask"` in `episode.json`; masks animate with the voice.
- `lincoln` mask: pale Lincoln face with stovepipe hat, hollow eyes, chin-curtain beard and a jaw that talks.
- `moth` mask now flutters its wings with the voice.
- Version control process: `CONTRIBUTING.md` (branches, conventional commits, semver), `tools/release.py` (bump, changelog roll, tag, `--check`), PR template, `episodes/_template/`.
- Output provenance: renderer version + commit (captured at render start, `-dirty` if `persona/` has uncommitted changes) stamped into MP4 metadata; `render.json` manifest written beside each video.
- CI (`.github/workflows/check.yml`): compile, VERSION check, preview smoke test for every mask (`tools/smoke.py`).

### Changed
- Episode 002 (*Lyceum Address*) re-rendered with the `lincoln` mask.

## [0.1.0] - 2026-11-07

### Added
- `persona/render.py`: one renderer driven by per-episode `script.txt` + `episode.json`
  (espeak-ng robot voice, drone bed, moth-in-a-suit emblem, glitch/grain, light cue, "EXPECT US." end card, parallel chunked rendering).
- Episode 001 — *Greetings, Podiatrist* (the moth joke, for Norm). 2:44.
- Episode 002 — *Lyceum Address*, Lincoln, 1838, ~4-minute cut. 4:12.
- Episode 003 — *Middle Powers*, Carney at Davos, January 20, 2026, full speech. 18:16.
  Repo copy is re-encoded to 540p to stay under the push size limit; render locally for 720p.
- Versioning: `VERSION`, this changelog, semver git tags.

[Unreleased]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.4.0...HEAD
[0.4.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/releases/tag/v0.1.0
