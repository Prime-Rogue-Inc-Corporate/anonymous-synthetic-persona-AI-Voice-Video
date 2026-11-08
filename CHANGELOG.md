# Changelog

All notable changes to this project are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- `tools/loop_clip.py`: cut a seamless, crossfaded loop from any rendered episode by caption-line prefix (`--repeat N` for a posting copy).
- Episode 002 clip: "If destruction be our lot… or die by suicide" (`clips/destruction_loop.mp4`, 13.5s; `destruction_x4.mp4`).

### Planned
- 003 Davos: replace the WEF credit line with "Source: Office of the Prime Minister" and re-render the end card.
- Host full-quality renders as GitHub Release assets instead of in-tree.
- More test episodes: another historical speech or two and a comedy bit.

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

[Unreleased]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.2.0...HEAD
[0.2.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/releases/tag/v0.1.0
