import argparse
import sys

from . import preflight, validate, rollout, handoff, __version__


def main(argv=None):
    p = argparse.ArgumentParser(prog="fdekit", description="Tools for a customer site visit.")
    p.add_argument("--version", action="version", version=__version__)
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("preflight", help="check DNS, ports, TLS, disk and tools from a TOML spec")
    a.add_argument("spec")
    a.add_argument("--json", action="store_true")

    b = sub.add_parser("validate", help="check a customer config file")
    b.add_argument("config")

    c = sub.add_parser("rollout", help="upgrade sites in waves with automatic rollback")
    c.add_argument("version")
    c.add_argument("sites", nargs="+")
    c.add_argument("--check", nargs="+", required=True, help="health command, run inside <site>/current")
    c.add_argument("--wave-size", type=int, default=1)
    c.add_argument("--record", default="deploy-record.json")

    d = sub.add_parser("handoff", help="write a handoff note from a deployment record")
    d.add_argument("record")

    args = p.parse_args(argv)
    if args.cmd == "preflight":
        res = preflight.run(args.spec)
        print(preflight.render(res, args.json))
        return 0 if all(r.ok for r in res) else 1
    if args.cmd == "validate":
        errs = validate.load_and_validate(args.config)
        for e in errs:
            print("FAIL", e)
        print("config ok" if not errs else f"{len(errs)} problem(s)")
        return 1 if errs else 0
    if args.cmd == "rollout":
        rec = rollout.rollout(args.sites, args.version, args.check, args.wave_size, args.record)
        for s in rec["sites"]:
            print(s["site"], s["result"])
        print("status:", rec["status"])
        return 0 if rec["status"] == "ok" else 1
    if args.cmd == "handoff":
        sys.stdout.write(handoff.render(args.record))
        return 0


if __name__ == "__main__":
    sys.exit(main())
