#!/usr/bin/env python3
"""Cut a release: bump VERSION, roll CHANGELOG's Unreleased section, commit, tag.

    python tools/release.py patch|minor|major      # bump and release
    python tools/release.py 0.3.0                  # release an explicit version
    python tools/release.py --check                # verify VERSION, CHANGELOG and tags agree

If VERSION already holds the target (e.g. set earlier on a release branch), it is kept.
The script never pushes; it prints the push command.
"""
import datetime, os, re, subprocess, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_URL = "https://github.com/Prime-Rogue-Inc-Corporate/anonymous-synthetic-persona-AI-Voice-Video"
VFILE, CFILE = os.path.join(ROOT, "VERSION"), os.path.join(ROOT, "CHANGELOG.md")
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def git(*a, check=True):
    return subprocess.run(["git", "-C", ROOT, *a], capture_output=True, text=True, check=check).stdout.strip()


def released_versions(changelog):
    return re.findall(r"^## \[(\d+\.\d+\.\d+)\]", changelog, re.M)


def bump(cur, part):
    M, m, p = map(int, SEMVER.match(cur).groups())
    return {"major": f"{M + 1}.0.0", "minor": f"{M}.{m + 1}.0", "patch": f"{M}.{m}.{p + 1}"}[part]


def check():
    ver = open(VFILE).read().strip()
    log = open(CFILE).read()
    rel = released_versions(log)
    tags = git("tag", "--list", "v*").split()
    problems = []
    if not SEMVER.match(ver): problems.append(f"VERSION {ver!r} is not semver")
    if rel and rel[0] != ver and f"v{ver}" in tags: problems.append(f"VERSION {ver} is tagged but not the newest CHANGELOG entry ({rel[0]})")
    for v in rel:
        if f"v{v}" not in tags: problems.append(f"CHANGELOG has {v} but tag v{v} is missing locally")
    print("VERSION:", ver, "| changelog:", ", ".join(rel) or "-", "| tags:", ", ".join(tags) or "-")
    for p in problems: print("  !", p)
    return not problems


def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    arg = sys.argv[1]
    if arg == "--check":
        sys.exit(0 if check() else 1)
    if git("status", "--porcelain"):
        sys.exit("working tree is dirty; commit or stash first")

    log = open(CFILE).read()
    prev = (released_versions(log) or ["0.0.0"])[0]
    cur = open(VFILE).read().strip()
    new = arg if SEMVER.match(arg) else bump(prev, arg)
    if new in released_versions(log):
        sys.exit(f"{new} is already in CHANGELOG")
    if f"v{new}" in git("tag", "--list").split():
        sys.exit(f"tag v{new} already exists")

    m = re.search(r"^## \[Unreleased\]\n(.*?)(?=^## \[)", log, re.M | re.S)
    if not m or not m.group(1).strip():
        sys.exit("CHANGELOG has nothing under [Unreleased]")
    body = m.group(1).strip()
    # keep "### Planned" items in Unreleased; release everything else
    planned = re.search(r"^### Planned\n.*?(?=^### |\Z)", body, re.M | re.S)
    keep = planned.group(0).strip() if planned else ""
    released = (body.replace(planned.group(0), "") if planned else body).strip()
    if not released:
        sys.exit("only Planned items under [Unreleased]; nothing to release")

    today = datetime.date.today().isoformat()
    log = log[:m.start(1)] + ("\n" + keep + "\n\n" if keep else "\n") + f"## [{new}] - {today}\n\n{released}\n\n" + log[m.end(1):]
    log = re.sub(r"^\[Unreleased\]: .*$", f"[Unreleased]: {REPO_URL}/compare/v{new}...HEAD", log, flags=re.M)
    link = f"[{new}]: {REPO_URL}/compare/v{prev}...v{new}"
    log = re.sub(r"(^\[Unreleased\]: .*$)", r"\1\n" + link, log, count=1, flags=re.M)
    open(CFILE, "w").write(log)
    if cur != new:
        open(VFILE, "w").write(new + "\n")

    git("add", "VERSION", "CHANGELOG.md")
    git("commit", "-m", f"release: v{new}")
    git("tag", "-a", f"v{new}", "-m", f"v{new}")
    print(f"released v{new} (from {prev}). Push with:\n  git push origin HEAD --follow-tags")


if __name__ == "__main__":
    main()
