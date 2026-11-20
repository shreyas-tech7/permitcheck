#!/usr/bin/env bash
# Write docs/DEMO.md from a real terminal session. Run from the repo root after ./init.sh.
set -euo pipefail
cd "$(dirname "$0")/.."
PC=.venv/bin/permitcheck
TMP=$(mktemp -d)
run() {
  echo '```console'
  echo "\$ $*" | sed "s#$TMP#/tmp/demo#g"
  timeout 300 "$@" 2>&1 | sed "s#$TMP#/tmp/demo#g"
  echo '```'
  echo
}
{
  echo "# Demo"
  echo
  echo "A real terminal session, written by \`scripts/make_demo.sh\` on $(date -u +%Y-%m-%d). Paths under a temp folder show as /tmp/demo."
  echo
  echo "## Check one application"
  echo
  run $PC check data/applications/LH-APP-0064.txt --out "$TMP/out" --now 2026-11-20T00:00:00Z
  echo "## The correction letter it wrote"
  echo
  echo '```markdown'
  cat "$TMP/out/LH-APP-0064/letter.md"
  echo '```'
  echo
  echo "## Rerun the eval and compare it with the committed results"
  echo
  run $PC eval --split both --check
  echo "## Confirm the README tables"
  echo
  run $PC readme --check
} > docs/DEMO.md
rm -rf "$TMP"
echo "wrote docs/DEMO.md"
