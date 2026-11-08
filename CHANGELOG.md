# Changelog

All notable changes to this project are recorded here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/); versions follow [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added
- Barn podcast scenes: `"set": {"barn": {...}}` draws a converted-barn studio (planks, beam, a dusk window onto pines, a moose mount, a framed "prime time" headshot drawn from the host's own mask, bookshelf, lantern glow). `"desk"` adds a plank anchor desk with a boom-arm broadcast mic and a mug; `"dog"` adds a dog that barks on cue.
- Remote guests: cast `"screen": true` shows a speaker inside a TV monitor (head-and-shoulders crop, blue cast, scanlines, red name label, blinking LIVE dot).
- Sound cues generalized: `[gavel]`, `[bark]`, `[cackle]`. Cues before a line's words play first, cues after play after, and a line can be cues only (`DALE: [bark]`, no caption shown). Cackles move the speaker's mouth; barks move the dog's.
- Mask: `pundit`.
- Episode 009, *The Barn*: a fictional ex-cable anchor turned barn podcaster, who broke with the President over the Iran war, reacts to the midterms and brings Rep. Whitlow on by satellite. Same universe as 006–008.
- Barn smoke test (`tests/barn`).

### Planned
- 003 Davos: replace the WEF credit line with "Source: Office of the Prime Minister" and re-render the end card.
- Host full-quality renders as GitHub Release assets instead of in-tree.
- More test episodes: another historical speech or two.

## [0.7.1] - 2026-11-08

### Added
- Episode 008 video in the repo: the full hour at 540p in four ~15-minute parts (`episodes/008-special-order-full-hour/video/`, 27–28 MB each). The 720p original (266 MB) exceeds GitHub's 100 MB per-file limit, and Git LFS uploads are blocked from the authoring environment.

## [0.7.0] - 2026-11-08

### Added
- Episode 008, *Special Order: The Full Hour*: the 60-minute version of 007 (~7,100 words, 59:59). New sections on prices and the court-ordered tariff refunds, the 2027 debt limit, where "lame duck" comes from and the 20th Amendment, war powers votes, FISA 702, how a bill really becomes law, and constituent mail. The C-SPAN clock runs in real time and the chair's time warnings match it. The full video (~266 MB) is not stored in git; a 1:44 highlight (`clips/two_gift_shops.mp4`) and the script are.

### Changed
- Faster frame loop: a reused film-grain bank and skipping glow math when the scene is dark (~33 to ~24 ms per frame).

### Fixed
- Hour-long episodes ran out of memory (killed at ~7 GB): the audio mixer built several full-length float arrays. It now renders the mix in one-minute blocks with seamless, deterministic noise (identical output at any block size) and tracks each speaker's mouth movement from per-frame loudness instead of full voice tracks. Peak memory for a 60-minute mix: ~775 MB.

## [0.6.0] - 2026-11-08

### Added
- House floor scenes: `"set": {"chamber": {...}}` draws the chamber (walnut wall, marble pilasters, rostrum tiers, flag behind the chair); `"lectern"` adds a foreground lectern with gooseneck mics and a seal.
- C-SPAN-style chyron (`"chyron"`): title, subtitle and an optional countdown clock that runs from `from` seconds at the `start` line to 00:00 (blinking red) at the `zero` line.
- Inline sound cues: `[gavel]` anywhere in a line plays a synthesized double knock just before it (stripped from voice and captions); cast members with `"gavel": true` lean into it.
- Cast `"desk": true` seats a figure behind a desk front (e.g. the rostrum), drawn in cast order so walk-ons can still stand in front.
- Masks: `congressman`, `presiding`, `whip`.
- Episode 007, *Special Order*: a fictional lame-duck congressman who lost his primary takes an hour on the House floor in the first week of the lame duck and torches both parties, set in the same universe as 006.
- Floor-speech smoke test (`tests/floor`).

## [0.5.0] - 2026-11-08

### Added
- Walk-and-talk scenes: `"set": {"corridor": {...}}` draws a one-point-perspective hallway with the camera tracking backward: doors with brass room plaques, ceiling lights, a runner and a chair rail all recede as the cast walks. `speed`, `plaques` and `color` are configurable.
- Cast `"walk": true` adds a walking gait (step bounce and sway, `cadence` in steps/s).
- Cast `"enter": "left"|"right"` makes a walk-on: the character slides into frame for each burst of their lines and peels off afterwards (`linger` sets how long a gap still counts as the same burst).
- Per-cast `scale`/`top` and episode-level `"layout"` for waist-up framing.
- Masks: `chief`, `counsel`, `clerk`.
- Episode 006, *The Lame Duck*: an original walk-and-talk. Two senior Senate staffers (outgoing and incoming majority) speed-walk the Capitol through the Nov. 2026 lame-duck session while a floor aide and a press secretary cut in.
- Walk-and-talk smoke test (`tests/walk`).

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

[Unreleased]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.7.1...HEAD
[0.7.1]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.7.0...v0.7.1
[0.7.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.6.0...v0.7.0
[0.6.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.5.0...v0.6.0
[0.5.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.4.0...v0.5.0
[0.4.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.3.0...v0.4.0
[0.3.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.2.0...v0.3.0
[0.2.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/compare/v0.1.0...v0.2.0
[0.1.0]: https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video/releases/tag/v0.1.0
