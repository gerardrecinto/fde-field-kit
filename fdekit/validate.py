"""Check a customer's config file and say exactly what to change."""
import json

# type, required, extra rule. Kept in code so the tool has no dependencies.
SCHEMA = {
    "site": (str, True, None),
    "region": (str, True, lambda v: v in {"us", "eu", "apac"} or "must be one of us, eu, apac"),
    "replicas": (int, True, lambda v: 1 <= v <= 20 or "must be between 1 and 20"),
    "timeout_seconds": (int, False, lambda v: 1 <= v <= 300 or "must be between 1 and 300"),
    "tls_enabled": (bool, True, None),
    "admin_email": (str, True, lambda v: ("@" in v and "." in v.split("@")[-1]) or "does not look like an email"),
}


def validate(cfg):
    errs = []
    if not isinstance(cfg, dict):
        return ["config: top level must be an object"]
    for key, (typ, required, rule) in SCHEMA.items():
        if key not in cfg:
            if required:
                errs.append(f"{key}: missing, add it")
            continue
        v = cfg[key]
        # bool is an int in Python; do not let true pass for replicas
        if typ is int and isinstance(v, bool) or not isinstance(v, typ):
            errs.append(f"{key}: expected {typ.__name__}, got {type(v).__name__} ({v!r})")
            continue
        if rule:
            res = rule(v)
            if res is not True:
                errs.append(f"{key}: {v!r} {res}")
    for key in cfg:
        if key not in SCHEMA:
            hint = _closest(key)
            errs.append(f"{key}: unknown key" + (f", did you mean {hint}?" if hint else ""))
    return errs


def _closest(key):
    best, score = None, 0
    for k in SCHEMA:
        s = sum(1 for a, b in zip(k, key) if a == b)
        if s > score and s >= max(3, len(k) // 2):
            best, score = k, s
    return best


def load_and_validate(path):
    try:
        with open(path) as f:
            return validate(json.load(f))
    except json.JSONDecodeError as e:
        return [f"{path}: not valid JSON at line {e.lineno}, column {e.colno}: {e.msg}"]
