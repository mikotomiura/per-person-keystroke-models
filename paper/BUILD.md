# Building the manuscript

The manuscript (`main.tex`) uses the Springer Nature LaTeX template (class `sn-jnl` with the option `sn-basic`,
bibliography style `sn-basic`, version 3.1, December 2024). The template is not part of this directory. Obtain it from
Springer Nature's LaTeX author support page
(<https://www.springernature.com/gp/authors/campaigns/latex-author-support>), unpack it, and use the directory that
holds `sn-jnl.cls` and `sn-basic.bst` (in the template archive, `bst/sn-basic.bst` may have to be copied next to the
class). Online Resource 1 (`supplement.tex`) uses the standard `article` class.

```
bash build.sh <template-dir> <out-dir>
```

`<out-dir>` receives `main.pdf`, `supplement.pdf` and the logs and must lie outside this repository. The script runs
pdfLaTeX without shell escape, then BibTeX, then pdfLaTeX twice, for each document, and reports the number of
errors, undefined references and citations, and overfull boxes. The figures are drawn by PGFPlots from
`figdata/`. Tested with TeX Live 2025 (MacTeX).
