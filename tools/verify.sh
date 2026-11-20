#!/usr/bin/env bash
# Run every check of the release.
# Usage: tools/verify.sh [DATA_DIR]
#   DATA_DIR (held by the authors, or by a reader who downloaded the public data to the layout in the README) adds the
#   per-record hash check of the kit against the raw data and, if the private lists are there, the search for them.
# Needs: python3 with NumPy, git. Exit code 0 only if every check passes.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"; cd "$ROOT"
export PYTHONDONTWRITEBYTECODE=1
fail=0
step() { echo "== $1"; shift; if "$@"; then :; else echo "FAILED: $*"; fail=1; fi; }
regen() {  # the conformance inputs are the synthetic cases of seed 20261107
  local t; t="$(mktemp -d)"
  python3 -I -B kit/symbols/conformance/generate_inputs.py 20261107 300 "$t/inputs.json" >/dev/null
  python3 -I -B -c 'import gzip,json,sys; a=json.load(open(sys.argv[1])); b=json.load(gzip.open(sys.argv[2],"rt"))
sys.exit(0 if a == b else "conformance inputs differ from the seed")' "$t/inputs.json" kit/symbols/conformance/data/inputs.json.gz
  local rc=$?; rm -rf "$t"; return $rc
}
step "kit: self-test and conformance (300 synthetic cases)" python3 -I -B kit/symbols/selftest.py
step "kit: conformance inputs regenerated from the seed" regen
step "SHA-256 records close inside the release" python3 -I -B tools/check_pins.py
step "SHA-256 records, positive controls" bash tools/control_check_pins.sh
step "README figures against the manuscript's data" python3 -I -B tools/readme_media.py --check
if [ -n "${1:-}" ]; then
  step "kit: per-record hashes, CoAuthor" python3 -I -B kit/symbols/hashes/hashes.py check coauthor "$1/coauthor/raw/coauthor.zip" kit/symbols/hashes/coauthor_sha256.csv
  step "kit: per-record hashes, CS1 2021" python3 -I -B kit/symbols/hashes/hashes.py check cs1 "$1/cs1/raw/2021/keystrokes.csv" kit/symbols/hashes/cs1_2021_sha256.csv
fi
priv=(); [ -n "${1:-}" ] && [ -f "$1/landscape/holdout.json" ] && priv=(--private "$1")
[ "${#priv[@]}" -gt 0 ] || echo "note: private lists not given; the release check runs without them (authors only)"
step "release check" python3 -I -B tools/check_release.py "${priv[@]+"${priv[@]}"}"
step "release check, positive controls" bash tools/control_check_release.sh ${priv[1]:+"${priv[1]}"}
if [ "$fail" -eq 0 ]; then echo "all checks passed"; else echo "some checks failed"; fi
exit "$fail"
