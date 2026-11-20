"""Build site/index.html from real runs of the demo and the git tricks."""
import html
import pathlib
import subprocess

root = pathlib.Path(__file__).resolve().parent.parent


def run(script):
    r = subprocess.run(["bash", str(root / "scripts" / script)], capture_output=True, text=True, cwd=root)
    return r.stdout + r.stderr


demo, tricks = run("demo.sh"), run("git-tricks.sh")
page = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1"><title>fde-field-kit</title>
<style>:root{{--bg:#fff;--fg:#111827;--mut:#4b5563;--box:#f3f4f6}}
@media (prefers-color-scheme:dark){{:root{{--bg:#0b1220;--fg:#e5e7eb;--mut:#9ca3af;--box:#111a2e}}}}
body{{background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,sans-serif;max-width:860px;margin:0 auto;padding:24px 16px}}
pre{{background:var(--box);padding:12px;overflow:auto;font-size:13px;border-radius:6px}}a{{color:inherit}}p{{color:var(--mut)}}</style></head><body>
<h1>fde-field-kit</h1>
<p>Tools a forward deployed engineer runs at a customer site: preflight an environment, validate their config, roll out in waves with automatic rollback, and hand off a note. Below are real outputs, rebuilt on every push.</p>
<p><a href="https://github.com/gerardrecinto/fde-field-kit">Source on GitHub</a></p>
<h2>A site visit: scripts/demo.sh</h2><pre>{html.escape(demo)}</pre>
<h2>Git tricks, each verified: scripts/git-tricks.sh</h2><pre>{html.escape(tricks)}</pre>
</body></html>"""
out = root / "site"
out.mkdir(exist_ok=True)
(out / "index.html").write_text(page)
print("wrote", out / "index.html")
