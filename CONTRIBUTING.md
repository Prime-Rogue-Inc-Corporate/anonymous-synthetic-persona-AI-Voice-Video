# Contributing

Everything goes through version control: branches, pull requests, a changelog and semver tags.

## Branches

- `main` is always releasable. Don't commit to it directly.
- Work on a short-lived branch, named by type:
  - `feat/<thing>`: renderer or mask features
  - `fix/<thing>`: bug fixes and corrections
  - `episode/<NNN-slug>`: a new or re-rendered episode
  - `release/vX.Y.Z`: release prep
- Open a pull request into `main` and merge it with a merge commit, so the branch history stays visible.

## Commits

Use [Conventional Commits](https://www.conventionalcommits.org/): `feat(persona): …`, `fix(render): …`, `episode(002): …`, `docs: …`, `release: vX.Y.Z`.

## Changelog

Every PR adds a line under `## [Unreleased]` in `CHANGELOG.md` (`### Added`, `### Changed`, `### Fixed`).
Ideas that aren't done yet go under `### Planned`; those stay in Unreleased across releases.

## Versions

Semantic versioning in `VERSION`:

| bump | when |
|------|------|
| patch `0.2.x` | fixes, re-renders, credit or caption corrections |
| minor `0.x.0` | new episodes, masks or renderer features |
| major `x.0.0` | breaking changes to `episode.json` or the output format |

## Releasing

```bash
python tools/release.py minor        # or patch / major / an explicit 0.3.0
git push origin HEAD --follow-tags
python tools/release.py --check      # VERSION, CHANGELOG and tags agree?
```

`release.py` rolls the Unreleased notes into a dated section, updates `VERSION`, commits `release: vX.Y.Z` and creates the annotated tag. Then publish a GitHub Release from the tag.

## Rendered outputs are versioned too

Every render writes:
- a version stamp into the MP4's `comment` metadata (`anonymous-synthetic-persona v0.2.0 (abc1234) | episode 002-…`), and
- `render.json` beside the video: renderer version, commit, timestamp, duration, mask.

Commit `render.json` with the video, so any output can be traced back to the exact code that made it.
Keep committed videos under ~50 MB (re-encode to 540p if needed) and note it in the changelog.

## Adding an episode

Copy `episodes/_template/`, write `script.txt`, set `episode.json`, preview, render, and open an `episode/NNN-slug` PR.
