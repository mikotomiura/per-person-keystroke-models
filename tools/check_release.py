#!/usr/bin/env python3
"""Check that the release holds no raw data, no per-writer values of real writers, no secrets and no local paths.

Usage:
  python3 -I tools/check_release.py [--root DIR] [--private DATA_DIR]

The checks are structural: they look for shapes, not for meaning, so a per-writer value written as prose would pass.
Without the options, anyone can run them:
  - files: no raw data by extension and no file over 2 MB, except the files named in ALLOWED_RAW and LARGE_OK (each
    with its reason); every file must be UTF-8 text, gzip-compressed UTF-8 text for the two synthetic conformance
    files of the kit (their text is searched for identifiers, secrets and paths), or, for the README animations
    named in IMAGES, a GIF image;
  - identifiers of the shapes the public datasets use for writers (CS1 2019 "S" and three digits, CS1 2021 "Student"
    and digits, CoAuthor worker ids), in any file except where ID_ALLOWED says otherwise (the per-record hashes of the
    kit are keyed by the datasets' public identifiers);
  - containers large enough to be per writer. The smallest panel in the analyses has 9 writers, so a JSON array of 9
    or more entries is reported unless its place is listed in SYNTHETIC (arrays over synthetic writers, replicate
    numbers and lists of categories, each with its reason); a JSON object is reported if it has 30 or more keys, 9 or
    more keys that look like identifiers, or 9 or more keys that count up from 0 or 1, unless listed in BIG_OBJECTS or
    CONSECUTIVE_OK; a Markdown or TeX table of 9 or more rows is reported unless its file is listed in TABLES; the
    allowed CSV files must keep their columns (ids, counts, hashes) and the figure data at most 30 rows;
  - CoAuthor session ids (32 hex digits) and e-mail addresses other than the author's;
  - the same identifier and local-path shapes in the file paths;
  - secrets of common shapes (private keys, age secret keys, GitHub, Slack, Google, AWS and API tokens) and local
    paths (/Users/, /home/, C:\\, host names ending in .local);
  - in a git repository: the files are the committed ones (no uncommitted change); the author, committer and
    message of every commit and the ref names and tag messages pass the identifier, secret and local-path checks; and
    every older or deleted file reachable in the history passes the same checks as the files of the work tree.
With --private (for the authors, who hold the data), it also searches for each writer identifier of the holdout and
skip lists and for the SHA-256 of each identifier (full, or any prefix of 8 or more hex digits).

Exit code: 0 = nothing found / 1 = something found / 2 = usage error, missing root or nothing to check.
"""
import csv
import gzip
import hashlib
import json
import os
import re
import subprocess
import sys

RAW_EXT = {".csv", ".tsv", ".zip", ".gz", ".bz2", ".xz", ".7z", ".zst", ".tar", ".ndjson", ".jsonl", ".parquet",
           ".feather", ".arrow", ".h5", ".hdf5", ".pkl", ".npy", ".npz", ".xls", ".xlsx", ".db", ".sqlite", ".age",
           ".rds", ".sav", ".dta"}
ALLOWED_RAW = {
    # provenance tables at the root, written by the assembly
    "gse-commits.tsv", "gse-source.tsv",
    # per-record SHA-256 of the symbol sequences, keyed by the datasets' public identifiers (no symbols, no values)
    "kit/symbols/hashes/coauthor_sha256.csv", "kit/symbols/hashes/cs1_2021_sha256.csv",
    # synthetic key presses (seed 20261107) and the expected symbol traces of the conformance check
    "kit/symbols/conformance/data/inputs.json.gz", "kit/symbols/conformance/data/expected.json.gz",
}
FIGDATA = re.compile(r"paper/figdata/fig\d+_[a-z0-9_]+\.csv")  # aggregate values plotted in the manuscript's figures
MAX_BYTES = 2 * 1024 * 1024
LARGE_OK = {  # aggregate summaries over the grids of k, structure and tau; the synthetic conformance traces
    "experiments/20261104-coauthor-ml-improve/results/summary.json",
    "experiments/20261104-timeseries-tau-extend/results/summary.json",
    "experiments/20261106-tau-mode-candidate/results/summary.json",
    "experiments/20261107-structure-deficit-test/results/summary.json",
    "kit/symbols/conformance/data/expected.json.gz",
}
LARGE_MAX = 10 * 1024 * 1024
IMAGES = re.compile(r"docs/media/symbols(_ja)?\.gif")  # animations drawn by tools/readme_media.py from made-up key presses
GZ_TEXT = {"kit/symbols/conformance/data/inputs.json.gz", "kit/symbols/conformance/data/expected.json.gz"}
PANEL_MIN = 9
BIG = 30
_SENS = r"experiments/2026111[0-3]-(per-person-sensitivity|sensitivity-mode-decomposition|sensitivity-ten-seeds|" \
        r"null-from-shared)/results/"
SYNTHETIC = [  # (file, place in the JSON, reason); [#] stands for any index, # for any numeric key
    (_SENS + r"(replicates/\d+|rerep_\d+)\.json", r"/(lams|planted|writers)", "synthetic writers of one replicate"),
    (_SENS + r"summary\.json", r"/cells(\[#\]/values/(main|g))?",
     "cells of the synthetic design, and values over the synthetic writers of a cell"),
    (_SENS + r"(summary|machine_check)\.json", r"/(cells/#/)?replicates", "replicate numbers or one summary per replicate"),
    (_SENS + r"(plan|summary|provenance)\.json", r"/(plan/|plan\.json/content/)?(kept|rows)", "plan of the replicates"),
    (_SENS + r"gate(_parts/[^/]+)?\.json", r"(/alphas/#/per_seed\[#\])?/b",
     "synthetic writers of the gate of the second null"),
    (r"kit/symbols/constants\.json", r"/key_categories/feature", "list of key categories"),
    (r"\.zenodo\.json", r"", "archive metadata"),
]
BIG_OBJECTS = [  # (file, place, reason)
    (r"experiments/[^/]+/results/provenance\.json", r"/files_sha256", "SHA-256 of the scripts and inputs"),
    (r"experiments/[^/]+/results/(selftest|selftest_inherited|mutations[^/]*/[^/]+)\.json", r"/P-LEAK/medians",
     "positive control on synthetic data"),
    (r"experiments/20261106-tau-mode-candidate/results/selftest\.json", r"", "the named checks of the self-test"),
    (_SENS + r"(plan|summary)\.json", r"/(plan/)?seconds", "run time of each replicate"),
]
TABLES = {  # files whose tables of 9 or more rows were read: rows are cells of the designs, settings, checks or
           # manuscript tables, not writers. A table of 9 or more rows anywhere else is reported.
    "README.md",
    "README.ja.md",
    "paper/supplement.tex",
    "experiments/20261103-coauthor-per-person/conditions.md",
    "experiments/20261103-coauthor-per-person/notes.md",
    "experiments/20261104-coauthor-ml-improve/conditions.md",
    "experiments/20261104-coauthor-ml-improve/notes.md",
    "experiments/20261104-coauthor-ml-improve/tables.md",
    "experiments/20261104-cs1-landscape/conditions.md",
    "experiments/20261104-cs1-landscape/notes.md",
    "experiments/20261104-timeseries-tau-extend/notes.md",
    "experiments/20261104-timeseries-tau-extend/tables.md",
    "experiments/20261106-tau-mode-candidate/conditions.md",
    "experiments/20261106-tau-mode-candidate/notes.md",
    "experiments/20261106-tau-mode-candidate/tables.md",
    "experiments/20261107-structure-deficit-test/conditions.md",
    "experiments/20261107-structure-deficit-test/notes.md",
    "experiments/20261107-structure-deficit-test/tables.md",
    "experiments/20261107-unsmoothed-residual-check/conditions.md",
    "experiments/20261107-unsmoothed-residual-check/notes.md",
    "experiments/20261107-unsmoothed-residual-check/results/tables.md",
    "experiments/20261110-per-person-sensitivity/conditions.md",
    "experiments/20261110-per-person-sensitivity/results/tables.md",
    "experiments/20261111-mode-in-selection/results/tables.md",
    "experiments/20261111-objective-and-pause/results/tables.md",
    "experiments/20261111-sensitivity-mode-decomposition/results/tables.md",
    "experiments/20261112-selection-split-and-smoothing/conditions.md",
    "experiments/20261112-selection-split-and-smoothing/results/ctrl_tables.md",
    "experiments/20261112-selection-split-and-smoothing/results/sym_tables.md",
    "experiments/20261112-selection-split-and-smoothing/results/tables.md",
    "experiments/20261113-null-from-shared/conditions.md",
}
ID_ALLOWED = {"kit/symbols/hashes/cs1_2021_sha256.csv": {"cs1-2021-subject"},
              "kit/symbols/hashes/coauthor_sha256.csv": {"coauthor-session"}}
CSV_HEADERS = {  # the allowed CSV files must keep these columns (and only hashes, counts and flags in them)
    "kit/symbols/hashes/coauthor_sha256.csv": "session_id,n_blocks,n_rows,sha256_symbols,sha256_rows,in_analysis",
    "kit/symbols/hashes/cs1_2021_sha256.csv": "subject_assignment,n_blocks,n_rows,sha256_symbols,sha256_rows",
}
FIGDATA_HEADERS = ("k,model,pp_minus_shared,pp_minus_chain", "k,pp_minus_shared,pp_minus_chain")
FIGDATA_MAX_ROWS = 30
CONSECUTIVE_OK = [  # (file, place) of objects keyed by consecutive integers that are not writers
    (r"experiments/20261107-unsmoothed-residual-check/results/(summary|parts/res\.(coauthor|cs1)\.[onu])\.json",
     r".*/acf_[xy]", "lags 1 to 10"),
    (_SENS + r"provenance\.json", r"/seconds", "run time of each replicate"),
] 
PRIVATE_LISTS = ("cs1/holdout.json", "cs1/skip_seen_2019.json", "cs1/skip_holdout_2021.json",
                 "cs1/rehearsal_holdout.json", "landscape/holdout.json", "extend/holdout.json")
# Shapes are assembled at run time so that this file does not match itself.
_D = r"\d"
ID_PATTERNS = {
    "cs1-2019-subject": re.compile(r"(?<![A-Za-z0-9_])S" + _D + "{3}(?![A-Za-z0-9_])"),
    "cs1-2021-subject": re.compile(r"(?<![A-Za-z0-9_])Stu" + "dent" + _D + r"+(?![A-Za-z0-9_])"),
    "coauthor-worker": re.compile(r"(?<![A-Za-z0-9_])A[0-9A-Z]{11,20}(?![A-Za-z0-9_])"),
    "coauthor-session": re.compile(r"(?<![0-9a-fA-F])[0-9a-f]{3" + r"2}(?![0-9a-fA-F])"),
}
ID_KEY = re.compile(r"(?i)(w|s|u|writer|session|student|subject)[_-]?\d+|[0-9a-f]{32}")
SECRET_PATTERNS = {
    "private-key": re.compile("-----BEGIN [A-Z ]*PRIV" + "ATE KEY-----"),
    "age-key": re.compile("AGE-SEC" + "RET-KEY-1[0-9A-Z]{20,}"),
    "github-token": re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{30,}|github_" + r"pat_[A-Za-z0-9_]{30,})\b"),
    "slack-token": re.compile(r"\bxo" + r"x[abprs]-[A-Za-z0-9-]{10,}"),
    "google-key": re.compile(r"\bAI" + r"za[0-9A-Za-z_-]{35}\b"),
    "aws-key": re.compile(r"\bAK" + r"IA[0-9A-Z]{16}\b"),
    "api-token": re.compile(r"\bsk-[A-Za-z0-9_-]{30,}\b"),
}
LOCAL_PATTERNS = {
    "local-path": re.compile(r"/Us" + r"ers/[A-Za-z0-9._-]+|/ho" + r"me/[a-z][a-z0-9._-]+/|[A-Z]:\\" + r"Users"),
    "local-host": re.compile(r"@[A-Za-z0-9-]+\.lo" + r"cal\b"),
    "e-mail": re.compile(r"(?<![A-Za-z0-9._%+-])[A-Za-z0-9._%+-]{1,64}@(?!example\.org\b)(?!" + r"[A-Za-z0-9-]+\.lo" + r"cal\b)[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    "local-volume": re.compile(r"/Vol" + r"umes/[A-Za-z0-9._ -]+|[A-Z]:\\\\" + r"Users"),
}
PUBLIC_EMAILS = ("mmiura.network" + "@gmail.com",  # the author's address, as in the manuscript
                 "noreply" + "@anthropic.com")  # the co-author line of the commit messages
TABLE_ROW = re.compile(r"^\s*\|.*\|\s*$|\\\\\s*$")
NUMERIC_KEY = re.compile(r"-?[0-9][0-9.e+-]*|inf")


def listing(root):
    """Files to check: in a git repository the tracked and the untracked-not-ignored files, otherwise all files."""
    inside = subprocess.run(["git", "-C", root, "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if inside.returncode == 0 and os.path.realpath(inside.stdout.strip()) == os.path.realpath(root):
        out = subprocess.run(["git", "-C", root, "ls-files", "-co", "--exclude-standard", "-z"],
                             capture_output=True, check=True).stdout
        return [p.decode() for p in out.split(b"\0") if p], True
    paths = []
    for d, ds, fs in os.walk(root):
        ds[:] = sorted(x for x in ds if not (d == root and x == ".git"))
        paths += [os.path.relpath(os.path.join(d, f), root) for f in sorted(fs)]
    return paths, False


def _listed(rules, rel, place):
    return any(re.fullmatch(f, rel) and re.fullmatch(p, place) for f, p, _ in rules)


def json_findings(rel, obj, path="", place=""):
    """path: the exact place in the JSON (reported); place: the same with [#] for indices and # for numeric keys."""
    out = []
    if isinstance(obj, dict):
        if len(obj) >= BIG and not _listed(BIG_OBJECTS, rel, place):
            out.append("object with %d keys at %s" % (len(obj), path or "/"))
        keys = [str(k) for k in obj]
        ints = sorted(int(k) for k in keys if re.fullmatch(r"\d+", k))
        run = max((sum(1 for j in range(i, len(ints)) if ints[j] == ints[i] + (j - i)) for i in range(len(ints))
                   if ints[i] in (0, 1)), default=0)
        if run >= PANEL_MIN and not _listed(BIG_OBJECTS + CONSECUTIVE_OK, rel, place):
            out.append("object keyed by %d consecutive numbers at %s" % (run, path or "/"))
        n_id = sum(1 for k in keys if ID_KEY.fullmatch(k))
        if n_id >= PANEL_MIN:
            out.append("object with %d identifier-like keys at %s" % (n_id, path or "/"))
        for k, v in obj.items():
            k = str(k)
            out += json_findings(rel, v, path + "/" + k, place + "/" + ("#" if NUMERIC_KEY.fullmatch(k) else k))
    elif isinstance(obj, list):
        if len(obj) >= PANEL_MIN and not _listed(SYNTHETIC, rel, place):
            out.append("array of %d entries at %s" % (len(obj), path or "/"))
        for i, v in enumerate(obj):
            out += json_findings(rel, v, "%s[%d]" % (path, i), place + "[#]")
    return out


def longest_table(text):
    best = run = 0
    for line in text.splitlines():
        run = run + 1 if TABLE_ROW.search(line) else 0
        best = max(best, run)
    return best


def private_needles(data_dir):
    """Writer identifiers of the holdout and skip lists (values and keys), and the SHA-256 of each."""
    ids, missing = set(), []
    for rel in PRIVATE_LISTS:
        p = os.path.join(data_dir, rel)
        if not os.path.exists(p):
            missing.append(rel)
            continue
        with open(p) as fh:
            stack = [json.load(fh)]
        while stack:
            x = stack.pop()
            if isinstance(x, dict):
                stack += list(x.values())
                if len(x) >= PANEL_MIN:  # a map keyed by ids; small objects are the lists' structure (dataset, year)
                    ids.update(str(k) for k in x)
            elif isinstance(x, list):
                stack += x
            elif isinstance(x, (str, int)) and not isinstance(x, bool):
                ids.add(str(x))
    if "landscape/holdout.json" in missing or "cs1/holdout.json" in missing:
        print("landscape/holdout.json or cs1/holdout.json not found under %s" % data_dir, file=sys.stderr)
        sys.exit(2)
    for rel in missing:
        print("note: private list not found, not searched: %s" % rel)
    words = {i for i in ids if len(i) >= 4 and not i.isdigit()}  # numeric ids are covered by the container checks
    hashes = {hashlib.sha256(i.encode()).hexdigest() for i in ids}
    print("private lists: %d identifiers searched, with their SHA-256" % len(words))
    if not words:
        print("private lists hold no identifier", file=sys.stderr)
        sys.exit(2)
    return words, hashes


def text_findings(text, label, allowed=()):
    found = []
    for e in PUBLIC_EMAILS:
        text = text.replace(e, "")
    for name, pat in list(ID_PATTERNS.items()) + list(SECRET_PATTERNS.items()) + list(LOCAL_PATTERNS.items()):
        if name in allowed:
            continue
        n = len(pat.findall(text))
        if n:
            found.append((label, "%s x%d" % (name, n)))
    return found


def needle_findings(text, label, words, hashes):
    found = []
    if words:
        pat = re.compile(r"(?<![A-Za-z0-9])(?:%s)(?![A-Za-z0-9])"
                         % "|".join(re.escape(w) for w in sorted(words, key=len, reverse=True)))
        if pat.search(text):
            found.append((label, "listed id"))
    if hashes:
        prefixes = {h[:8] for h in hashes}
        for t in set(m.lower() for m in re.findall(r"[0-9a-fA-F]{8,64}", text)):
            if t[:8] in prefixes and any(h.startswith(t) for h in hashes):
                found.append((label, "sha256 (or prefix) of a listed id"))
                break
    return found


def gif_findings(b):
    """Walk the blocks of a GIF: no comment or plain-text extension, no application extension but the loop count,
    nothing after the trailer."""
    if not (b.startswith(b"GIF89a") or b.startswith(b"GIF87a")) or len(b) < 13:
        return ["not a GIF image"]
    i = 13 + (3 * 2 ** ((b[10] & 7) + 1) if b[10] & 0x80 else 0)
    def skip_sub(i):
        while i < len(b) and b[i]:
            i += b[i] + 1
        return i + 1
    while i < len(b):
        c = b[i]
        if c == 0x3B:
            return [] if i == len(b) - 1 else ["bytes after the GIF trailer"]
        if c == 0x21 and i + 1 < len(b):
            label = b[i + 1]
            if label == 0xFE:
                return ["GIF comment extension"]
            if label == 0x01:
                return ["GIF plain-text extension"]
            if label == 0xFF and b[i + 3:i + 14] != b"NETSCAPE2.0":
                return ["GIF application extension other than the loop count"]
            i = skip_sub(i + 2)
        elif c == 0x2C and i + 10 <= len(b):
            flags = b[i + 9]
            i += 10 + (3 * 2 ** ((flags & 7) + 1) if flags & 0x80 else 0)
            i = skip_sub(i + 1)
        else:
            return ["malformed GIF block at byte %d" % i]
    return ["GIF without a trailer"]


def csv_findings(rel, text):
    lines = text.splitlines()
    if rel in CSV_HEADERS:
        if not lines or lines[0] != CSV_HEADERS[rel]:
            return ["unexpected columns"]
        n = len(lines[0].split(","))
        bad = [j for j, l in enumerate(lines[1:], 2) if not re.fullmatch(
            r'("[^"]*"|[0-9a-f]{32}),\d+,\d+,[0-9a-f]{64},[0-9a-f]{64}(,[01])?', l) or len(next(csv.reader([l]))) != n]
        return ["row %d is not an id, counts and hashes" % bad[0]] if bad else []
    if FIGDATA.fullmatch(rel):
        if not lines or lines[0] not in FIGDATA_HEADERS:
            return ["unexpected columns"]
        if len(lines) - 1 > FIGDATA_MAX_ROWS:
            return ["%d rows (more than %d)" % (len(lines) - 1, FIGDATA_MAX_ROWS)]
    return []


def check_file(rel, b, words, hashes):
    """Findings for the content b of the file at rel (used for the work tree and for every blob in the history)."""
    found = [("(path) " + rel, w) for _, w in text_findings(rel, rel)]
    ext = os.path.splitext(rel)[1].lower()
    if ext in RAW_EXT and rel not in ALLOWED_RAW and not FIGDATA.fullmatch(rel):
        found.append((rel, "raw data extension " + ext))
    cap = LARGE_MAX if rel in LARGE_OK else MAX_BYTES
    if len(b) > cap:
        found.append((rel, "file over %d MB" % (cap // 2 ** 20)))
    if IMAGES.fullmatch(rel):
        return found + [(rel, w) for w in gif_findings(b)]  # pixels only: the block walk rejects any text block
    if rel in GZ_TEXT:
        try:
            b = gzip.decompress(b)
        except OSError:
            return found + [(rel, "not gzip (content not checkable)")]
    try:
        text = b.decode("utf-8")
    except UnicodeDecodeError:
        return found + [(rel, "not UTF-8 text (content not checkable)")]
    found += text_findings(text, rel, ID_ALLOWED.get(rel, ()))
    found += needle_findings(text, rel, words, hashes)
    if rel in GZ_TEXT:
        return found  # synthetic traces with large arrays by design; tools/verify.sh regenerates and checks them
    if ext == ".csv":
        found += [(rel, w) for w in csv_findings(rel, text)]
    if ext == ".json":
        try:
            found += [(rel, f) for f in json_findings(rel, json.loads(text))]
        except ValueError:
            found.append((rel, "unparsable JSON"))
    if ext in (".md", ".tex") and rel not in TABLES and longest_table(text) >= PANEL_MIN:
        found.append((rel, "table of %d rows" % longest_table(text)))
    return found


def history_findings(root, words, hashes):
    """Every blob reachable from any ref that is not a file of the work tree: deleted or older versions."""
    head = subprocess.run(["git", "-C", root, "ls-files", "-s", "-z"], capture_output=True, check=True).stdout
    current = {e.split(b" ")[1].decode() for e in head.split(b"\0") if e}
    objs = subprocess.run(["git", "-C", root, "rev-list", "--all", "--objects"], capture_output=True, text=True,
                          check=True).stdout.splitlines()
    found, n = [], 0
    for line in objs:
        oid, _, path = line.partition(" ")
        if not path or oid in current:
            continue
        kind = subprocess.run(["git", "-C", root, "cat-file", "-t", oid], capture_output=True, text=True, check=True)
        if kind.stdout.strip() != "blob":
            continue
        b = subprocess.run(["git", "-C", root, "cat-file", "blob", oid], capture_output=True, check=True).stdout
        n += 1
        found += [("(history) " + rel, w) for rel, w in check_file(path, b, words, hashes)]
    return found, n


def main(argv):
    root, data_dir = ".", None
    while argv:
        a = argv.pop(0)
        if a == "--root" and argv:
            root = argv.pop(0)
        elif a == "--private" and argv:
            data_dir = argv.pop(0)
        else:
            print(__doc__, file=sys.stderr)
            return 2
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        print("root is not a directory: %s" % root, file=sys.stderr)
        return 2
    words, hashes = private_needles(data_dir) if data_dir else (set(), set())
    paths, in_git = listing(root)
    if not paths:
        print("nothing to check under %s" % root, file=sys.stderr)
        return 2
    found = []
    for rel in paths:
        p = os.path.join(root, rel)
        if os.path.islink(p):
            found.append((rel, "symbolic link"))
            continue
        with open(p, "rb") as fh:
            found += check_file(rel, fh.read(), words, hashes)
    n_hist = 0
    if in_git:
        st = subprocess.run(["git", "-C", root, "status", "--porcelain"], capture_output=True, text=True, check=True)
        if st.stdout.strip():
            found.append(("(git)", "uncommitted changes: the checked files are not the committed ones"))
        log = subprocess.run(["git", "-C", root, "log", "--all", "--format=%an <%ae>%n%cn <%ce>%n%B%n----"],
                             capture_output=True, text=True, check=True).stdout
        found += [(l.replace("(log)", "(git log)"), w) for l, w in text_findings(log, "(log)")]
        found += needle_findings(log, "(git log)", words, hashes)
        refs = subprocess.run(["git", "-C", root, "for-each-ref", "--format=%(refname)%0a%(contents)"],
                              capture_output=True, text=True, check=True).stdout
        found += [("(git refs)", w) for _, w in text_findings(refs, "(refs)")]
        hist, n_hist = history_findings(root, words, hashes)
        found += hist
    for rel, what in found:
        print("FOUND %s: %s" % (rel, what))
    print("checked %d files%s%s; %d findings" % (
        len(paths), " and the git history (%d older blobs)" % n_hist if in_git else "",
        " (with the private lists)" if data_dir else "", len(found)))
    return 1 if found else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
