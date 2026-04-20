#!/usr/bin/env bash
# Package the Elemental Powers addon into .mcpack and .mcaddon files.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/dist"
mkdir -p "$OUT"
rm -f "$OUT"/*.mcpack "$OUT"/*.mcaddon

cd "$ROOT/behavior_pack"
zip -r -q "$OUT/elemental_powers_1_0_beta_BP.mcpack" . -x "*.DS_Store"

cd "$ROOT/resource_pack"
zip -r -q "$OUT/elemental_powers_1_0_beta_RP.mcpack" . -x "*.DS_Store"

cd "$OUT"
zip -q "elemental_powers_1_0_beta.mcaddon" \
  "elemental_powers_1_0_beta_BP.mcpack" \
  "elemental_powers_1_0_beta_RP.mcpack"

ls -lh "$OUT"
