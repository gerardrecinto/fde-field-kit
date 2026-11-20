"""Roll a version out to sites in waves. Roll back by itself if a check fails.

A site is a directory with releases/<version>/ and a `current` symlink. The
symlink swap is atomic, so a site is never half upgraded.
"""
import json
import os
import subprocess
import time
from pathlib import Path


def _swap(site: Path, version: str):
    tmp = site / ".current.tmp"
    if tmp.is_symlink() or tmp.exists():
        tmp.unlink()
    tmp.symlink_to(Path("releases") / version)
    os.replace(tmp, site / "current")


def current(site: Path):
    link = site / "current"
    return os.readlink(link).split("/")[-1] if link.is_symlink() else None


def healthy(site: Path, check: list[str], tries=3, wait=0.2):
    for _ in range(tries):
        r = subprocess.run(check, cwd=site / "current", capture_output=True, text=True)
        if r.returncode == 0:
            return True
        time.sleep(wait)
    return False


def rollout(sites, version, check, wave_size=1, record_path=None):
    """Returns the deployment record. Stops at the first failed wave."""
    rec = {"version": version, "started": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "sites": [], "status": "ok"}
    sites = [Path(s) for s in sites]
    for i in range(0, len(sites), wave_size):
        wave = sites[i:i + wave_size]
        done = []
        for site in wave:
            if not (site / "releases" / version).is_dir():
                rec["sites"].append({"site": site.name, "result": "skipped", "reason": f"releases/{version} missing"})
                rec["status"] = "failed"
                break
            prev = current(site)
            _swap(site, version)
            if healthy(site, check):
                rec["sites"].append({"site": site.name, "result": "upgraded", "from": prev})
                done.append((site, prev))
            else:
                if prev:
                    _swap(site, prev)
                rec["sites"].append({"site": site.name, "result": "rolled_back", "to": prev})
                rec["status"] = "failed"
                break
        if rec["status"] == "failed":
            # Sites that passed earlier stay upgraded. Nothing after the failure starts.
            seen = {x["site"] for x in rec["sites"]}
            for later in sites:
                if later.name not in seen:
                    rec["sites"].append({"site": later.name, "result": "not_started"})
            break
    if record_path:
        Path(record_path).write_text(json.dumps(rec, indent=2))
    return rec
