"""Check a customer environment before anything is installed."""
import json
import re
import shutil
import socket
import ssl
import subprocess
import time
import tomllib
from dataclasses import dataclass, asdict


@dataclass
class Result:
    name: str
    ok: bool
    detail: str
    fix: str = ""


def _ver(text):
    m = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text)
    return tuple(int(x or 0) for x in m.groups()) if m else None


def check_dns(host):
    try:
        ip = socket.gethostbyname(host)
        return Result(f"dns {host}", True, ip)
    except OSError as e:
        return Result(f"dns {host}", False, str(e), "Ask the customer for the right resolver or a hosts entry.")


def check_tcp(host, port, timeout=3):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return Result(f"tcp {host}:{port}", True, "open")
    except OSError as e:
        return Result(f"tcp {host}:{port}", False, str(e), "Ask for a firewall rule or a proxy for this host and port.")


def check_tls(host, port=443, min_days=14, timeout=5):
    name = f"tls {host}:{port}"
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, port), timeout=timeout) as raw:
            with ctx.wrap_socket(raw, server_hostname=host) as s:
                cert = s.getpeercert()
        days = int((ssl.cert_time_to_seconds(cert["notAfter"]) - time.time()) // 86400)
    except (OSError, ssl.SSLError) as e:
        return Result(name, False, str(e), "A private CA is common here. Get the CA bundle from the customer.")
    return Result(name, days >= min_days, f"{days} days left", "" if days >= min_days else "Ask the customer to renew the certificate.")


def check_disk(path, min_gb):
    free = shutil.disk_usage(path).free / 1e9
    return Result(f"disk {path}", free >= min_gb, f"{free:.1f} GB free, need {min_gb}",
                  "" if free >= min_gb else "Ask for more space or a different mount.")


def check_tool(cmd, min_version):
    exe = shutil.which(cmd)
    if not exe:
        return Result(f"tool {cmd}", False, "not found", f"Install {cmd} {min_version} or newer, or use the offline bundle.")
    out = subprocess.run([exe, "--version"], capture_output=True, text=True, timeout=10)
    have, need = _ver(out.stdout + out.stderr), _ver(min_version)
    if have is None:
        return Result(f"tool {cmd}", False, "could not read version", "Run it by hand and check the version.")
    ok = have >= need
    return Result(f"tool {cmd}", ok, ".".join(map(str, have)), "" if ok else f"Upgrade to {min_version} or newer.")


def run(spec_path):
    with open(spec_path, "rb") as f:
        spec = tomllib.load(f)
    out = []
    for h in spec.get("dns", []):
        out.append(check_dns(h))
    for t in spec.get("tcp", []):
        out.append(check_tcp(t["host"], t["port"]))
    for t in spec.get("tls", []):
        out.append(check_tls(t["host"], t.get("port", 443), t.get("min_days", 14)))
    for d in spec.get("disk", []):
        out.append(check_disk(d["path"], d["min_gb"]))
    for t in spec.get("tools", []):
        out.append(check_tool(t["name"], t["min_version"]))
    return out


def render(results, as_json=False):
    if as_json:
        return json.dumps([asdict(r) for r in results], indent=2)
    lines = []
    for r in results:
        lines.append(f"{'PASS' if r.ok else 'FAIL'}  {r.name}: {r.detail}")
        if not r.ok and r.fix:
            lines.append(f"      next: {r.fix}")
    bad = sum(1 for r in results if not r.ok)
    lines.append(f"{len(results) - bad} passed, {bad} failed")
    return "\n".join(lines)
