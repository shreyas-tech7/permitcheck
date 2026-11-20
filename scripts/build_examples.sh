#!/usr/bin/env bash
# Rebuild examples/ from two dev applications with a fixed audit timestamp, so the files are reproducible.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -rf examples/LH-APP-0018 examples/LH-APP-0064
for app in LH-APP-0018 LH-APP-0064; do
  .venv/bin/permitcheck check "data/applications/$app.txt" --out examples --now 2026-11-20T00:00:00Z > "examples/$app.stdout.txt"
done
