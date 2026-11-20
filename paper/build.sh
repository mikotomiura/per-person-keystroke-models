#!/usr/bin/env bash
# Build the manuscript (main.pdf) and Online Resource 1 (supplement.pdf) with pdfLaTeX and BibTeX.
#
#   bash build.sh <template-dir> <out-dir>
#
# <template-dir> holds sn-jnl.cls and sn-basic.bst of the Springer Nature LaTeX template (BUILD.md says where to
# obtain it). <out-dir> receives the PDFs and the logs; it must lie outside the directory of this repository.
set -euo pipefail
if [ "$#" -ne 2 ]; then echo "usage: bash build.sh <template-dir> <out-dir>" >&2; exit 2; fi
here=$(cd "$(dirname "$0")" && pwd -P)
root=$(cd "$here/.." && pwd -P)
template=$(cd "$1" && pwd -P)
if [ ! -f "$template/sn-jnl.cls" ] || [ ! -f "$template/sn-basic.bst" ]; then
  echo "build.sh: ${template} does not hold sn-jnl.cls and sn-basic.bst" >&2; exit 2
fi
mkdir -p "$2"; out=$(cd "$2" && pwd -P)
case "$out/" in "$root"/*) echo "build.sh: give an output directory outside ${root}" >&2; exit 2 ;; esac
export TEXINPUTS="${template}:" BSTINPUTS="${template}:" BIBINPUTS="${here}:"
cd "$here"
build() {  # <name>
  local n="$1"
  run() { pdflatex -no-shell-escape -interaction=nonstopmode -halt-on-error -output-directory="$out" "$n.tex" \
            > "$out/$n.run.log" || { echo "build.sh: pdflatex failed on $n; see ${out}/$n.run.log" >&2; exit 1; }; }
  run
  (cd "$out" && bibtex "$n" > "$n.bibtex.log") || [ $? -eq 1 ] || { echo "build.sh: bibtex failed on $n" >&2; exit 1; }
  run; run
  local log="$out/$n.log"
  echo "$n: $(grep -c '^!' "$log" || true) errors, $(grep -c 'LaTeX Warning: Reference' "$log" || true) undefined references, $(grep -c 'Warning: Citation' "$log" || true) undefined citations, $(grep -c '^Overfull' "$log" || true) overfull boxes"
}
build main
build supplement
