import json
import os
import socket
from pathlib import Path

from fdekit import preflight, validate, rollout, handoff
from fdekit.cli import main


def test_validate_good():
    assert validate.validate(json.load(open("examples/acme/config-good.json"))) == []


def test_validate_bad_names_each_problem():
    errs = validate.validate(json.load(open("examples/acme/config-bad.json")))
    text = "\n".join(errs)
    assert "region: 'us-west' must be one of" in text
    assert "replicas: expected int, got str" in text
    assert "tls_enabeld: unknown key, did you mean tls_enabled?" in text
    assert "tls_enabled: missing" in text
    assert "admin_email" in text


def test_bool_is_not_an_int():
    cfg = json.load(open("examples/acme/config-good.json"))
    cfg["replicas"] = True
    assert any("replicas: expected int" in e for e in validate.validate(cfg))


def test_invalid_json_points_at_the_spot(tmp_path):
    p = tmp_path / "c.json"
    p.write_text('{"site": ')
    assert "line 1" in validate.load_and_validate(p)[0]


def test_tcp_open_and_closed():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    s.listen()
    port = s.getsockname()[1]
    assert preflight.check_tcp("127.0.0.1", port).ok
    s.close()
    r = preflight.check_tcp("127.0.0.1", port, timeout=1)
    assert not r.ok and r.fix


def test_disk_and_tool():
    assert preflight.check_disk("/", 0.001).ok
    assert not preflight.check_disk("/", 10**9).ok
    assert not preflight.check_tool("definitely-not-installed", "1.0").ok
    assert preflight.check_tool("python3", "3.0").ok


def test_preflight_cli_exit_codes():
    assert main(["preflight", "examples/acme/env.toml"]) == 0
    assert main(["preflight", "examples/acme/env-broken.toml"]) == 1


def _site(root: Path, name, v2_ok=True):
    for v, ok in (("v1", True), ("v2", v2_ok)):
        d = root / name / "releases" / v
        d.mkdir(parents=True)
        (d / "health.sh").write_text("exit 0\n" if ok else "exit 1\n")
    (root / name / "current").symlink_to("releases/v1")
    return root / name


def test_rollout_rolls_back_and_stops(tmp_path):
    a, b, c = _site(tmp_path, "a"), _site(tmp_path, "b", v2_ok=False), _site(tmp_path, "c")
    rec = rollout.rollout([a, b, c], "v2", ["sh", "health.sh"], record_path=tmp_path / "r.json")
    assert rec["status"] == "failed"
    assert [s["result"] for s in rec["sites"]] == ["upgraded", "rolled_back", "not_started"]
    assert rollout.current(a) == "v2"
    assert rollout.current(b) == "v1"
    assert rollout.current(c) == "v1"  # later wave never started


def test_rollout_all_ok(tmp_path):
    sites = [_site(tmp_path, n) for n in "ab"]
    rec = rollout.rollout(sites, "v2", ["sh", "health.sh"], wave_size=2)
    assert rec["status"] == "ok" and all(rollout.current(s) == "v2" for s in sites)


def test_rollout_missing_release_is_skipped(tmp_path):
    a = _site(tmp_path, "a")
    rec = rollout.rollout([a], "v9", ["sh", "health.sh"])
    assert rec["sites"][0]["result"] == "skipped" and rollout.current(a) == "v1"


def test_handoff_mentions_failure(tmp_path):
    a, b = _site(tmp_path, "a"), _site(tmp_path, "b", v2_ok=False)
    rollout.rollout([a, b], "v2", ["sh", "health.sh"], record_path=tmp_path / "r.json")
    note = handoff.render(tmp_path / "r.json")
    assert "rolled_back" in note and "Not finished" in note and "back on v1" in note
