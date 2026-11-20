#!/usr/bin/env bash
# Positive controls for tools/check_release.py. The clean copy must pass (exit 0). Each planted file must make the
# check exit 1 AND print a FOUND line naming the expected detector (an exit 1 from a crash does not count). A missing
# root and an empty root must exit 2. The planted strings are built at run time, so no file of the release holds them.
# Usage: control_check_release.sh [DATA_DIR]   (with DATA_DIR, also plants an id and a hash prefix from the lists)
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd -P)"; ROOT="$(cd "$HERE/.." && pwd -P)"
TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
# a plain copy of the committed files (no .git), so that the checks see exactly what was committed
git -C "$ROOT" archive --format=tar HEAD | (mkdir -p "$TMP/clean" && tar -x -C "$TMP/clean")
CHK="$TMP/clean/tools/check_release.py"
fail=0
# expect <exit> <label> <dir> <pattern in output or -> [data_dir]
expect() {
  local want="$1" label="$2" dir="$3" pat="$4" data="${5:-}" out rc
  set +e; out="$(python3 -I "$CHK" --root "$dir" ${data:+--private "$data"} 2>&1)"; rc=$?; set -e
  if [ "$rc" != "$want" ]; then echo "FAIL $label (exit $rc, expected $want)"; fail=1; return; fi
  if [ "$pat" != "-" ] && ! printf '%s\n' "$out" | grep -q -- "$pat"; then
    echo "FAIL $label (exit $rc but no line matching: $pat)"; fail=1; return
  fi
  echo "ok   $label (exit $rc)"
}
plant() { rm -rf "$TMP/p"; cp -R "$TMP/clean" "$TMP/p"; }
py() { python3 -I -c "$1" "$TMP/p"; }
expect 0 "clean copy" "$TMP/clean" "0 findings"
expect 2 "missing root" "$TMP/nonexistent" -
mkdir "$TMP/empty"; expect 2 "empty root" "$TMP/empty" -
plant; py 'import sys; open(sys.argv[1]+"/x.md","w").write("writer " + "S" + "123" + " stalled\n")'
expect 1 "CS1 2019 id" "$TMP/p" "FOUND x.md: cs1-2019-subject"
plant; py 'import sys; open(sys.argv[1]+"/x.md","w").write("Stu" + "dent" + "42\n")'
expect 1 "CS1 2021 id" "$TMP/p" "FOUND x.md: cs1-2021-subject"
plant; py 'import sys; open(sys.argv[1]+"/x.md","w").write("worker " + "A" + "1B2C3D4E5F6G7H" + "\n")'
expect 1 "CoAuthor worker id" "$TMP/p" "FOUND x.md: coauthor-worker"
plant; py 'import json,sys; json.dump({"w%d" % i: 0.5 for i in range(35)}, open(sys.argv[1]+"/x.json","w"))'
expect 1 "object with many keys" "$TMP/p" "FOUND x.json: object with 35 keys"
# the smallest panel has 9 writers: an array of 9 values outside the listed synthetic places is reported
plant; py 'import json,sys; json.dump({"values": [0.5]*9}, open(sys.argv[1]+"/x.json","w"))'
expect 1 "array of 9 numbers" "$TMP/p" "FOUND x.json: array of 9 entries"
plant; py 'import json,sys; json.dump(["id%d" % i for i in range(17)], open(sys.argv[1]+"/x.json","w"))'
expect 1 "array of 17 strings" "$TMP/p" "FOUND x.json: array of 17 entries"
plant; py 'import json,sys; json.dump([{"a": i} for i in range(23)], open(sys.argv[1]+"/x.json","w"))'
expect 1 "array of 23 objects" "$TMP/p" "FOUND x.json: array of 23 entries"
# a listed synthetic place in another file is not allowed there
plant; py 'import json,sys; json.dump({"lams": [0.1]*17}, open(sys.argv[1]+"/experiments/20261103-coauthor-per-person/results/x.json","w"))'
expect 1 "synthetic place in a real-data file" "$TMP/p" "FOUND experiments/20261103-coauthor-per-person/results/x.json: array of 17"
# the identifier allowance of the kit's hash list does not extend to other files
plant; py 'import sys; open(sys.argv[1]+"/kit/symbols/hashes/x.md","w").write("Stu" + "dent" + "7\n")'
expect 1 "CS1 2021 id outside the hash list" "$TMP/p" "FOUND kit/symbols/hashes/x.md: cs1-2021-subject"
# the allowed gzip files are searched after decompression
plant; py '
import gzip, sys
p = sys.argv[1] + "/kit/symbols/conformance/data/inputs.json.gz"
b = gzip.decompress(open(p, "rb").read())
open(p, "wb").write(gzip.compress(b + b" /Us" + b"ers/someone/x"))'
expect 1 "local path inside an allowed gzip file" "$TMP/p" "FOUND kit/symbols/conformance/data/inputs.json.gz: local-path"
plant; py 'import sys; open(sys.argv[1]+"/kit/symbols/conformance/data/inputs.json.gz","wb").write(b"not gzip")'
expect 1 "allowed gzip file that is not gzip" "$TMP/p" "FOUND kit/symbols/conformance/data/inputs.json.gz: not gzip"
plant; py 'import sys; open(sys.argv[1]+"/docs/media/symbols.gif","wb").write(b"text, not an image")'
expect 1 "README animation that is not a GIF" "$TMP/p" "FOUND docs/media/symbols.gif: not a GIF image"
# objects keyed like writers, below the 30-key limit
plant; py 'import json,sys; json.dump({str(i): 0.5 for i in range(9)}, open(sys.argv[1]+"/x.json","w"))'
expect 1 "object keyed 0..8" "$TMP/p" "FOUND x.json: object keyed by 9 consecutive numbers"
plant; py 'import json,sys; json.dump({"w%d" % i: 0.5 for i in range(12)}, open(sys.argv[1]+"/x.json","w"))'
expect 1 "object with writer-like keys" "$TMP/p" "FOUND x.json: object with 12 identifier-like keys"
plant; py 'import sys; open(sys.argv[1]+"/x.md","w").write("".join("| w%d | 0.5 |\n" % i for i in range(9)))'
expect 1 "Markdown table of 9 rows" "$TMP/p" "FOUND x.md: table of 9 rows"
plant; py 'import sys; open(sys.argv[1]+"/x.md","w").write("session " + "0123456789abcdef" * 2 + "\n")'
expect 1 "CoAuthor session id" "$TMP/p" "FOUND x.md: coauthor-session"
plant; py 'import sys; open(sys.argv[1]+"/x.md","w").write("mail someone" + "@" + "university.edu\n")'
expect 1 "e-mail address" "$TMP/p" "FOUND x.md: e-mail"
plant; py 'import os,sys; os.makedirs(sys.argv[1]+"/results"); open(sys.argv[1]+"/results/" + "S" + "123.json","w").write("{}")'
expect 1 "identifier in a file name" "$TMP/p" "FOUND (path) results/.*: cs1-2019-subject"
plant; py 'import sys; p=sys.argv[1]+"/kit/symbols/hashes/coauthor_sha256.csv"; t=open(p).read().splitlines(); t[1] += ",0.5"; open(p,"w").write("\n".join(t)+"\n")'
expect 1 "extra column in the hash list" "$TMP/p" "FOUND kit/symbols/hashes/coauthor_sha256.csv: row 2"
plant; py 'import sys; p=sys.argv[1]+"/paper/figdata/fig2_p15.csv"; open(p,"a").write("".join("1,hmm3,0.1,0.1\n" for _ in range(30)))'
expect 1 "figure data with too many rows" "$TMP/p" "FOUND paper/figdata/fig2_p15.csv:"
plant; py '
import sys
p = sys.argv[1] + "/docs/media/symbols.gif"
b = open(p, "rb").read()
open(p, "wb").write(b[:-1] + b"\x21\xfe\x05hello\x00\x3b")'
expect 1 "GIF with a comment extension" "$TMP/p" "FOUND docs/media/symbols.gif: GIF comment extension"
plant; py 'import sys; p=sys.argv[1]+"/docs/media/symbols.gif"; open(p,"ab").write(b"trailing bytes")'
expect 1 "bytes after the GIF trailer" "$TMP/p" "FOUND docs/media/symbols.gif: bytes after the GIF trailer"
plant; py 'import sys; open(sys.argv[1]+"/x.md","w").write("".join("| %d | 0.5 |\n" % i for i in range(35)))'
expect 1 "Markdown table" "$TMP/p" "FOUND x.md: table of 35 rows"
plant; printf 'a,b\n1,2\n' > "$TMP/p/x.csv"
expect 1 "raw data file" "$TMP/p" "FOUND x.csv: raw data extension"
plant; py 'import sys; open(sys.argv[1]+"/x.txt","w").write("a" * (3 * 1024 * 1024))'
expect 1 "large file" "$TMP/p" "FOUND x.txt: file over 2 MB"
plant; py 'import sys; open(sys.argv[1]+"/x.txt","wb").write("text".encode("utf-16"))'
expect 1 "not UTF-8" "$TMP/p" "FOUND x.txt: not UTF-8"
plant; ln -s /etc/hosts "$TMP/p/x.txt"
expect 1 "symbolic link" "$TMP/p" "FOUND x.txt: symbolic link"
plant; py 'import sys; open(sys.argv[1]+"/x.txt","w").write("-----BEGIN " + "PRIVATE KEY-----\n")'
expect 1 "private key" "$TMP/p" "FOUND x.txt: private-key"
plant; py 'import sys; open(sys.argv[1]+"/x.txt","w").write("AGE-SEC" + "RET-KEY-1" + "Q" * 50 + "\n")'
expect 1 "age key" "$TMP/p" "FOUND x.txt: age-key"
plant; py 'import sys; open(sys.argv[1]+"/x.txt","w").write("gh" + "p_" + "a" * 36 + "\n")'
expect 1 "GitHub token" "$TMP/p" "FOUND x.txt: github-token"
plant; py 'import sys; open(sys.argv[1]+"/x.txt","w").write("AK" + "IA" + "A" * 16 + "\n")'
expect 1 "AWS key" "$TMP/p" "FOUND x.txt: aws-key"
plant; py 'import sys; open(sys.argv[1]+"/x.txt","w").write("sk" + "-" + "a" * 40 + "\n")'
expect 1 "API token" "$TMP/p" "FOUND x.txt: api-token"
plant; py 'import sys; open(sys.argv[1]+"/x.md","w").write("/Us" + "ers/someone/data\n")'
expect 1 "local path" "$TMP/p" "FOUND x.md: local-path"
# git: an uncommitted change and a committer with a local host name
plant; (cd "$TMP/p" && git init -q && git add -A && git -c user.name=t -c user.email=t@example.org commit -q -m init) >/dev/null
expect 0 "clean git copy" "$TMP/p" "0 findings"
echo x >> "$TMP/p/README.md"
expect 1 "uncommitted change" "$TMP/p" "uncommitted changes"
(cd "$TMP/p" && git checkout -q -- README.md && python3 -I -c 'open("x.txt","w").write("AK" + "IA" + "B" * 16 + "\n")' \
  && git add x.txt && git -c user.name=t -c user.email=t@example.org commit -q -m add && git rm -q x.txt \
  && git -c user.name=t -c user.email=t@example.org commit -q -m remove)
expect 1 "secret in a deleted file of the history" "$TMP/p" "FOUND (history) x.txt: aws-key"
(cd "$TMP/p" && git checkout -q -- README.md && GIT_COMMITTER_EMAIL="t@host"".lo""cal" git -c user.name=t -c user.email=t@example.org commit -q --allow-empty -m x)
expect 1 "committer with a local host" "$TMP/p" "FOUND (git log): local-host"
if [ -n "${1:-}" ]; then
  expect 0 "clean copy, private lists" "$TMP/clean" "0 findings" "$1"
  plant; python3 -I -c '
import json, sys
h = json.load(open(sys.argv[1] + "/landscape/holdout.json"))["coauthor"][0]
open(sys.argv[2] + "/x.md", "w").write("see " + h + ".\n")' "$1" "$TMP/p"
  expect 1 "holdout id followed by a period" "$TMP/p" "FOUND x.md: listed id" "$1"
  plant; python3 -I -c '
import hashlib, json, sys
c = json.load(open(sys.argv[1] + "/cs1/holdout.json"))["2019"][0]
open(sys.argv[2] + "/x.md", "w").write("hash " + hashlib.sha256(c.encode()).hexdigest()[:10].upper() + "\n")' "$1" "$TMP/p"
  expect 1 "upper-case hash prefix of a holdout id" "$TMP/p" "FOUND x.md: sha256" "$1"
fi
exit "$fail"
