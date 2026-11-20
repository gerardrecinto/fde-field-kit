"""Turn a deployment record into a handoff note the customer can keep."""
import json


def render(record_path, contact="your Forward Deployed Engineer"):
    rec = json.load(open(record_path))
    lines = [f"# Handoff: version {rec['version']}", "",
             f"Started {rec['started']}. Status: **{rec['status']}**.", "",
             "| Site | Result | Detail |", "| --- | --- | --- |"]
    for s in rec["sites"]:
        detail = s.get("reason") or (f"was {s['from']}" if s.get("from") else (f"back on {s['to']}" if s.get("to") else ""))
        lines.append(f"| {s['site']} | {s['result']} | {detail} |")
    lines += ["", "## If something looks wrong", "",
              "1. Check the site's `current` link: `readlink <site>/current`.",
              "2. Run the health check by hand from that directory.",
              "3. To go back: point `current` at the previous `releases/<version>` and rerun the check.",
              f"4. Still stuck: contact {contact} with this note."]
    if rec["status"] != "ok":
        lines += ["", "## Not finished", "", "At least one site did not upgrade. The sites after it were not touched."]
    return "\n".join(lines) + "\n"
