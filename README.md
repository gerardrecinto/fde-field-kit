# fde-field-kit

Tools a forward deployed engineer runs at a customer site: check their environment before you install, validate their config, roll out in waves with automatic rollback, and leave a handoff note.

[![ci](https://github.com/gerardrecinto/fde-field-kit/actions/workflows/ci.yml/badge.svg)](https://github.com/gerardrecinto/fde-field-kit/actions/workflows/ci.yml)
[![codeql](https://github.com/gerardrecinto/fde-field-kit/actions/workflows/codeql.yml/badge.svg)](https://github.com/gerardrecinto/fde-field-kit/actions/workflows/codeql.yml)
[![License: MIT](https://img.shields.io/github/license/gerardrecinto/fde-field-kit)](LICENSE)

**[Real outputs, rebuilt on every push](https://gerardrecinto.github.io/fde-field-kit/)**

## Try it

Needs Python 3.11 or newer and git. No packages to install.

```bash
git clone https://github.com/gerardrecinto/fde-field-kit
cd fde-field-kit
bash scripts/demo.sh
```

It runs a full visit in under a minute: a good and a broken preflight, a good and a bad customer config, a three-site rollout where the second site fails its health check and rolls back, and the handoff note.

## What each command does

| Command | Use it when | Failure looks like |
| :--- | :--- | :--- |
| `fdekit preflight env.toml` | Before install. Checks DNS, ports, TLS days left, disk, tool versions | `FAIL tcp host:443: Connection refused` then `next: Ask for a firewall rule...` |
| `fdekit validate config.json` | The customer sent their config | `FAIL tls_enabeld: unknown key, did you mean tls_enabled?` |
| `fdekit rollout v2 siteA siteB --check sh health.sh` | Upgrading several sites | A failed site goes back to the old version and later sites never start |
| `fdekit handoff deploy-record.json` | Leaving the site | A Markdown note with each site's result and what to do if it breaks |

Each site is a directory with `releases/<version>/` and a `current` symlink. The symlink swap is atomic, so a site is never half upgraded. The health check runs inside `current`.

## Git tricks for field work

`bash scripts/git-tricks.sh` runs each one for real in a throwaway repo and checks the result. CI runs it on every push.

| Situation at a customer | Trick |
| :--- | :--- |
| Hotfix while a change is half done | `git worktree add ../hotfix main` |
| "It worked last release." Find which one | `git bisect run <test command>` |
| Same conflict on every customer branch | `git config rerere.enabled true` |
| Did the rebase change my patches or only move them | `git range-diff main old new` |
| Stack of dependent branches | `git rebase --update-refs main` |
| Tidy commits before review | `git commit --fixup` then `git rebase -i --autosquash` |
| Reset the wrong thing | `git reflog` then `git reset --hard HEAD@{1}` |
| Record what was deployed where, without touching history | `git notes add -m "deployed to acme-east"` |
| Who changed this function, even after a move | `git log -L` and `git blame -w -C -C` |
| Air-gapped site | `git bundle create site.bundle --all` |
| Huge repo, slow link | `git clone --filter=blob:none --sparse` then `git sparse-checkout set <dir>` |
| Force push without clobbering a teammate | `git push --force-with-lease --force-if-includes` |

## GitHub features this repo uses

| Feature | Where | Why it matters on a customer project |
| :--- | :--- | :--- |
| Repository rulesets | `.github/rulesets/main.json` | Main needs a pull request, three green checks, linear history, no force push |
| Artifact attestations | `.github/workflows/release.yml` | Customers can prove a release file came from this repo |
| Immutable releases | repo setting | A published release and its files cannot be edited or swapped |
| Pages from Actions | `.github/workflows/pages.yml` | The site shows real run output, not screenshots |
| Dependabot, grouped | `.github/dependabot.yml` | One weekly pull request for all Action bumps |
| CodeQL, secret scanning with push protection, private vulnerability reporting | repo settings, `SECURITY.md` | Security basics before a customer asks |

Verify a release a customer downloaded:

```bash
gh release verify v0.1.0 --repo gerardrecinto/fde-field-kit
gh release verify-asset v0.1.0 fdekit-0.1.0-py3-none-any.whl --repo gerardrecinto/fde-field-kit
gh attestation verify fdekit-0.1.0-py3-none-any.whl --repo gerardrecinto/fde-field-kit
```

## Limits

- The rollout is local directories and symlinks. It shows the wave, health check and rollback logic, not a real Kubernetes or fleet rollout.
- Preflight TLS and TCP checks run from the machine you are on, so they show what that machine sees.
- The config schema is in `fdekit/validate.py`. Change it per customer.
- Tested on Python 3.11 and 3.13 in CI and 3.14 locally, git 2.50.

MIT licensed.
