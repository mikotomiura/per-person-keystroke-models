#!/usr/bin/env bash
# Positive controls for tools/check_pins.py: on a copy of the committed files, change one byte of a file that a
# pinned*.py fixes, change one byte of a script recorded in a provenance file, and delete a recorded script; each must
# make the check exit 1 with the expected FAIL line, also when the environment variable that would let a pinned module
# only report is set. The clean copy must exit 0.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"; ROOT="$(cd "$HERE/.." && pwd -P)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
git -C "$ROOT" archive --format=tar HEAD | (mkdir -p "$TMP/clean" && tar -x -C "$TMP/clean")
fail=0
run() {  # <label> <dir> <want exit> <pattern or ->
  local out rc
  set +e; out="$(python3 -I -B "$2/tools/check_pins.py" 2>&1)"; rc=$?; set -e
  if [ "$rc" != "$3" ]; then echo "FAIL $1 (exit $rc, expected $3)"; fail=1; return; fi
  if [ "$4" != "-" ] && ! printf '%s\n' "$out" | grep -q -- "$4"; then echo "FAIL $1 (no line matching: $4)"; fail=1; return; fi
  echo "ok   $1 (exit $rc)"
}
flip() { python3 -I -c 'import sys; p=sys.argv[1]; b=open(p,"rb").read(); open(p,"wb").write(b+b"\n# x\n")' "$1"; }
run "clean copy" "$TMP/clean" 0 "failures 0"
rm -rf "$TMP/p"; cp -R "$TMP/clean" "$TMP/p"; flip "$TMP/p/experiments/20261112-sensitivity-ten-seeds/scripts/ten.py"
run "pinned file changed" "$TMP/p" 1 "FAIL import experiments/20261113-null-from-shared/scripts/pinned6.py"
rm -rf "$TMP/p"; cp -R "$TMP/clean" "$TMP/p"; flip "$TMP/p/experiments/20261103-coauthor-per-person/scripts/perperson.py"
run "recorded script changed" "$TMP/p" 1 "FAIL experiments/20261103-coauthor-per-person/results/provenance.json records"
rm -rf "$TMP/p"; cp -R "$TMP/clean" "$TMP/p"; rm "$TMP/p/experiments/20261103-coauthor-per-person/scripts/check_same.py"
run "recorded script missing" "$TMP/p" 1 "check_same.py: no file of this name in the release"
rm -rf "$TMP/p"; cp -R "$TMP/clean" "$TMP/p"; flip "$TMP/p/experiments/20261104-timeseries-tau-extend/scripts/ml.py"
PIN_REPORT_ONLY=1 run "pinned file changed, report-only variable set" "$TMP/p" 1 "FAIL import experiments/20261107-unsmoothed-residual-check/scripts/pinned.py"
exit "$fail"
