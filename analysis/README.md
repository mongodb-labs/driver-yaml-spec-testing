# analysis/ --- CRUD spec test bug-prevention analysis

Quantitative analysis for the ISSRE 2026 resubmission: do YAML spec tests
for the CRUD specification catch nonconformance bugs, and do fewer new bugs
appear after a driver syncs those tests?

## What's here

```
analysis/
├── README.md                 this file
├── requirements.txt          Python deps
├── prompts/
│   └── classify.md           per-ticket classifier prompt
├── scripts/
│   ├── count_volume.py       counts tickets per driver project
│   ├── pull_tickets.py       bulk-pulls Jira tickets to data/tickets/
│   ├── classify.py           Haiku classifier (superseded by classify_sonnet.py)
│   ├── classify_sonnet.py    Sonnet classifier with exp02 N-gate prompt
│   ├── drivers_timeline.py   per-driver monthly YAML/JSON test file counts
│   ├── drivers_submodule_timeline.py  submodule-based drivers (JAVA, GODRIVER, PHPLIB)
│   └── crud_analysis.py      CRUD-focused panel, charts, and summary stats
└── data/
    ├── tickets/              raw Jira JSONL dumps (gitignored)
    ├── chunks/               50-ticket chunks for subagent classification
    ├── sonnet_results/       per-chunk Sonnet classification results
    ├── classified_sonnet.csv aggregated Sonnet classifications (17,501 unique)
    ├── gold_corpus.csv       200-ticket gold corpus for precision/recall
    ├── drivers_timeline.csv  per-driver monthly spec-test file counts
    ├── drivers_submodule_timeline.csv  submodule-based driver file counts
    ├── crud_panel.csv        (driver, month) panel for CRUD analysis
    └── plots/crud_*.png      CRUD analysis charts
```

## Setup on a fresh macOS checkout

```sh
cd analysis
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The Jira PAT is kept **outside** the repo:

```sh
echo 'YOUR_TOKEN' > ~/.jira_pat
chmod 600 ~/.jira_pat
```

## Running the full pipeline

```sh
# 1. Pull all resolved Bug + Improvement tickets from driver Jira projects
.venv/bin/python scripts/pull_tickets.py

# 2. Classify tickets (uses Sonnet subagents via Claude Code)
#    Output: data/sonnet_results/chunk_NNNN.results.jsonl
#    Then aggregate: data/classified_sonnet.csv
.venv/bin/python scripts/classify_sonnet.py

# 3. Clone driver repos (bare) for timeline mining
mkdir -p data/driver_repos
for r in mongo-c-driver mongo-csharp-driver mongo-cxx-driver \
         node-mongodb-native mongo-python-driver mongo-perl-driver \
         mongo-ruby-driver mongo-rust-driver mongo-swift-driver \
         mongo-java-driver mongo-go-driver mongo-php-library; do
  git clone --bare https://github.com/mongodb/$r data/driver_repos/${r}.git
done

# 4. Build per-driver YAML/JSON test timelines
.venv/bin/python scripts/drivers_timeline.py             # ~10 min
.venv/bin/python scripts/drivers_submodule_timeline.py   # ~3 min

# 5. Run CRUD-focused analysis
.venv/bin/python scripts/crud_analysis.py
```

## Key results

- **254 CRUD nonconformance bugs** across 12 drivers (2009--2026)
- **Spike at adoption**: bug rate jumps 1.9x in the 6 months after a driver
  first syncs CRUD test files (0.306 vs 0.164 pre-sync)
- **Long-run decline**: rate drops to 0.58x pre-sync after 24+ months (0.095)
- 7 of 10 drivers with pre-sync history show lower post-sync bug rates
