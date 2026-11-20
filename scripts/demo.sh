#!/usr/bin/env bash
# Runs the whole site visit on your machine in under a minute. Needs python3.11+.
set -u
cd "$(dirname "$0")/.."
export PYTHONPATH="$PWD"
run() { python3 -m fdekit.cli "$@"; }
step() { printf '\n== %s\n' "$*"; }

step "1. Preflight on a good environment"
run preflight examples/acme/env.toml || exit 1

step "2. Preflight on a broken one (exit 1 is expected)"
run preflight examples/acme/env-broken.toml && { echo "expected a failure"; exit 1; }

step "3. Validate the customer config"
run validate examples/acme/config-good.json || exit 1
run validate examples/acme/config-bad.json && { echo "expected a failure"; exit 1; }

step "4. Roll out v2 to three sites; site-b fails its health check and rolls back"
W=$(mktemp -d)
for s in site-a site-b site-c; do
  mkdir -p "$W/$s/releases/v1" "$W/$s/releases/v2"
  printf 'exit 0\n' > "$W/$s/releases/v1/health.sh"
  printf 'exit 0\n' > "$W/$s/releases/v2/health.sh"
  ln -s releases/v1 "$W/$s/current"
done
printf 'exit 1\n' > "$W/site-b/releases/v2/health.sh"
run rollout v2 "$W/site-a" "$W/site-b" "$W/site-c" --check sh health.sh --record "$W/record.json"
echo "site-b is on: $(readlink "$W/site-b/current")   site-c is on: $(readlink "$W/site-c/current")"

step "5. Handoff note"
run handoff "$W/record.json"
