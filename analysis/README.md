# analysis/ --- CRUD spec test bug-prevention analysis

Quantitative analysis for the ISSRE 2026 resubmission of *The Polyglot's
Dilemma*: do YAML spec tests for the CRUD specification catch
nonconformance bugs, and do fewer new bugs appear after a driver syncs
those tests?

There are many specs that use the Unified Test Format or other YAML formats. We chose the CRUD spec because it is complex, all 189 of its test files use the Unified Test Format (the most of any spec), and it has a long history of implementation (in some drivers) before the introduction of YAML tests.

## Headline result

We classified 17,512 resolved Jira tickets from 12 MongoDB driver
projects using an LLM classifier (Claude Sonnet, validated against a
200-ticket gold corpus at F1=0.71 for the nonconformance category). We
identified 254 CRUD nonconformance bugs across all drivers from 2009 to
2026. Separately, we mined each driver's git history to determine the
month it first synced CRUD YAML test files from the shared specifications
repository.

For each driver, we aligned the monthly CRUD bug rate to the month of
first test sync and binned into 12-month windows. The result
(`data/plots/crud_spike_decay.png`):

- **Pre-sync**, bug rates are noisy but average ~0.22 bugs per
  driver-month in the year before sync.
- **Post-sync**, every 12-month window is lower than the pre-sync
  average. The rate declines monotonically from 0.22 to 0.07 over six
  years, a **70% reduction**.

### Suggested figure caption

> **Figure N.** CRUD nonconformance bug rate per driver-month in
> 12-month windows aligned to each driver's first sync of CRUD YAML test
> files. Red bars are pre-sync; blue bars are post-sync. The rate
> declines monotonically after test adoption, from 0.22 to 0.07
> bugs/driver-month over six years (n=12 drivers, 254 total bugs).

### Suggested paper paragraph

> To quantify the effect of YAML spec tests on nonconformance bugs, we
> mined 17,512 resolved Jira tickets from 12 driver projects and
> classified each using an LLM (Claude Sonnet; F1=0.71 for
> nonconformance). For each driver we identified the month it first
> synced CRUD test files from the specifications repository. Figure N
> shows the CRUD bug rate in 12-month windows aligned to each driver's
> first sync date. Before test adoption, the rate averages 0.22
> bugs/driver-month; after adoption it declines monotonically to 0.07
> over six years---a 70% reduction. Drivers that synced early (JAVA,
> PERL, PYTHON in 2015) and late (CDRIVER, RUBY in 2018) both show the
> pattern. Full methodology and reproduction scripts are at
> [github.com/ajdavis/driver-yaml-spec-testing](https://github.com/ajdavis/driver-yaml-spec-testing).

## Additional charts (not in paper)

The analysis script also produces supporting charts:

- `crud_per_driver.png` --- per-driver time series of monthly bugs and
  test file counts, with first-sync date marked
- `crud_event_study.png` --- smoothed event study aligned to first sync
- `crud_pre_post.png` --- per-driver pre- vs post-sync bug rates
- `crud_dose_response.png` --- bug rate binned by test file count
- `crud_aggregate.png` --- yearly bugs vs cumulative test files across
  all drivers

## What's here

```
analysis/
├── README.md                 this file
├── requirements.txt          Python deps
├── prompts/
│   ├── classify.md           per-ticket classifier prompt
│   └── subagent.md           batch subagent dispatch prompt
├── scripts/
│   ├── count_volume.py       counts tickets per driver project
│   ├── pull_tickets.py       bulk-pulls Jira tickets to data/tickets/
│   ├── classify.py           Haiku classifier (superseded)
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

The Jira PAT (personal access token) is kept **outside** the repo:

```sh
echo 'YOUR_TOKEN' > ~/.jira_pat
chmod 600 ~/.jira_pat
```

## Reproducing the full pipeline

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
