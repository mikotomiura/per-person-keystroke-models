#!/usr/bin/env python3
"""Check that the SHA-256 records of the experiments close inside this release.

Usage: python3 -I -B tools/check_pins.py

1. Each experiment that reuses another experiment's code loads it through a module pinned*.py, which stops when the
   SHA-256 of a loaded script or summary at its exact path differs from the value fixed in its conditions. Every
   pinned*.py is imported here in a fresh process (no data is read; the environment variables that let a pinned
   module only report, or load from elsewhere, are removed); it must import without stopping.
2. Every results/provenance*.json records the SHA-256 of the files that a computation used, under keys that name
   them in several ways (a path, a path relative to another experiment, a bare file name). For each record:
   - if a file of that name exists in the release, some file of that name must have the recorded SHA-256, either as
     released or with CRLF line ends (the computations run on Windows saw CRLF files), unless KNOWN_LATER lists it;
   - if no file of that name exists, the name must be listed in OUTSIDE (the data, the holdout list and the
     per-writer files kept by the authors). Any other missing file fails.
   Records are matched by content, not by path: check 1 is the check of exact paths for the reused code.

Needs Python 3 and NumPy (the pinned modules import the fitting code). Exit code 0 only if both checks pass.
"""
import glob
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KNOWN_LATER = {
    ("experiments/20261110-per-person-sensitivity/results/provenance.json", "sens_report.py"):
        "the report script was extended on 2026-11-11 to read the six added replicates (plan_add.json); "
        "it summarizes the replicate files and does not fit models",
    ("experiments/20261110-per-person-sensitivity/results/provenance.pre.json", "sens_report.py"): "same as above",
}
OUTSIDE = {  # file name -> why it is not in the release
    "holdout.json": "list of holdout writers (redrawn by the scripts from the data and the seed)",
    "keystrokes.csv": "CS1 raw data (public, not redistributed)",
    "coauthor.zip": "CoAuthor raw data (public, not redistributed)",
}
OUTSIDE_RE = re.compile(  # per-writer files kept by the authors: symbol series, fitted parameters, per-writer values
    r"unsmoothed_residual_writer_values\.(coauthor|cs1)\.[onu]\.json|unsmoothed_residual_(coauthor|cs1)\.json\.gz|"
    r"unsmoothed_residual_params\.(coauthor|cs1)\.[onu]\.npz")
UNSAFE_ENV = ("PIN_REPORT_ONLY", "TAU_SCRIPTS", "PYTHONPATH")
HEX = re.compile(r"[0-9a-fA-F]{64}")
FILELIKE = re.compile(r".*\.[A-Za-z0-9]{1,5}$|.*SEED$")


def sha(b):
    return hashlib.sha256(b).hexdigest()


def check_imports():
    mods = sorted(glob.glob(os.path.join(ROOT, "experiments", "*", "scripts", "pinned*.py")))
    ok = bool(mods)
    if not mods:
        print("FAIL no pinned*.py found")
    env = {k: v for k, v in os.environ.items() if k not in UNSAFE_ENV}
    for p in mods:
        d, m = os.path.dirname(p), os.path.splitext(os.path.basename(p))[0]
        r = subprocess.run([sys.executable, "-I", "-B", "-c", "import sys; sys.path.insert(0, sys.argv[1]); import " + m, d],
                           capture_output=True, text=True, env=env)
        rel = os.path.relpath(p, ROOT)
        if r.returncode == 0:
            print("ok   import %s" % rel)
        else:
            ok = False
            print("FAIL import %s: %s" % (rel, (r.stderr.strip().splitlines() or ["exit %d" % r.returncode])[-1]))
    return ok, len(mods)


def release_files():
    """Released files by name, with the SHA-256 of their bytes as released and with CRLF line ends."""
    by_name = {}
    for d, ds, fs in os.walk(ROOT):
        ds[:] = [x for x in ds if x not in (".git", "__pycache__")]
        for f in fs:
            p = os.path.join(d, f)
            with open(p, "rb") as fh:
                b = fh.read()
            crlf = b.replace(b"\r\n", b"\n").replace(b"\n", b"\r\n")
            by_name.setdefault(f, []).append((os.path.relpath(p, ROOT), sha(b), sha(crlf)))
    return by_name


def check_provenance():
    by_name = release_files()
    counts = {"match": 0, "match_crlf": 0, "known_later": 0, "outside": 0}
    bad = []
    provs = sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, "experiments", "*", "results",
                                                                            "provenance*.json")))

    def record(prov, key, v):
        name = re.split(r"[\\/:]", key)[-1]
        v = v.lower()
        files = by_name.get(name)
        if not files:
            if name in OUTSIDE or OUTSIDE_RE.fullmatch(name):
                counts["outside"] += 1
            else:
                bad.append((prov, key, "no file of this name in the release, and the name is not listed as outside"))
            return
        if any(v == h for _, h, _ in files):
            counts["match"] += 1
        elif any(v == c for _, _, c in files):
            counts["match_crlf"] += 1
        elif (prov, name) in KNOWN_LATER:
            counts["known_later"] += 1
            print("note %s: %s was edited later: %s" % (prov, name, KNOWN_LATER[(prov, name)]))
        else:
            bad.append((prov, key, "no released file of this name has the recorded SHA-256 (%s)"
                        % ", ".join(p for p, _, _ in files)))

    def walk(o, prov):
        if isinstance(o, dict):
            for k, v in o.items():
                if isinstance(v, str) and HEX.fullmatch(v) and FILELIKE.fullmatch(k):
                    record(prov, k, v)
                walk(v, prov)
        elif isinstance(o, list):
            for v in o:
                walk(v, prov)

    for prov in provs:
        with open(os.path.join(ROOT, prov)) as fh:
            walk(json.load(fh), prov)
    for prov, k, why in bad:
        print("FAIL %s records %s: %s" % (prov, k, why))
    print("provenance: %d files, %s, failures %d"
          % (len(provs), ", ".join("%s %d" % kv for kv in counts.items()), len(bad)))
    return not bad and counts["match"] > 0 and len(provs) > 0


def main():
    ok1, n = check_imports()
    ok2 = check_provenance()
    print("pinned modules: %d imported%s" % (n, "" if ok1 else " (some failed)"))
    return 0 if ok1 and ok2 else 1


if __name__ == "__main__":
    sys.exit(main())
