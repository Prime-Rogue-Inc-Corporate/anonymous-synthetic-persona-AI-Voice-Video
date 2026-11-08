#!/usr/bin/env python3
"""Smoke test: preview-render tests/smoke once per registered mask."""
import json, os, shutil, subprocess, sys, tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "persona"))
from masks import MASKS  # noqa: E402

src = os.path.join(ROOT, "tests", "smoke")
for name in MASKS:
    with tempfile.TemporaryDirectory() as tmp:
        ep = os.path.join(tmp, f"smoke-{name}")
        shutil.copytree(src, ep)
        cfg = json.load(open(os.path.join(ep, "episode.json"))); cfg["mask"] = name
        json.dump(cfg, open(os.path.join(ep, "episode.json"), "w"))
        subprocess.run([sys.executable, os.path.join(ROOT, "persona", "render.py"), ep, "--preview"], check=True)
        n = len([f for f in os.listdir(os.path.join(ep, "build")) if f.startswith("preview_")])
        assert n >= 3, f"{name}: expected preview frames, got {n}"
        print(f"ok  {name}: {n} frames")
print("smoke passed")
