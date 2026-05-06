# The Polyglot's Dilemma

Research paper for ISSRE 2026 Industry Track: *The Polyglot's Dilemma: Conformance Testing a Dozen Specs in as Many Languages*, an experience report on MongoDB's Unified Test Format (UTF)---a YAML-based DSTL for cross-driver conformance testing.

## Building the paper

Requires `pdflatex` and `bibtex` (install via MacTeX or `brew install --cask mactex`).

```sh
./issre2026/build.sh
```

Output: `issre2026/main.pdf`.

## Analysis pipeline

See [analysis/README.md](analysis/README.md) for the quantitative analysis: ticket classification, CRUD bug-rate panel, and chart generation.
