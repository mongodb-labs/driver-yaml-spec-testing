#!/bin/sh
cd "$(dirname "$0")"
cp ../analysis/data/plots/crud_spike_decay_balanced.pdf FIG
pdflatex -interaction=nonstopmode main.tex && bibtex main && pdflatex -interaction=nonstopmode main.tex && pdflatex -interaction=nonstopmode main.tex
