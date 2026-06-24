# analysis/ --- CRUD spec test bug-prevention analysis

Quantitative analysis for the ISSRE 2026 resubmission of *The Polyglot's Dilemma*: do YAML spec tests for the CRUD specification reduce nonconformance bug rates?

There are many specs that use the Unified Test Format or other YAML formats. We chose the CRUD spec because it is complex, all 189 of its test files use the Unified Test Format (the most of any spec), and it has a long history of implementation (in some drivers) before the introduction of YAML tests.

## Headline result

We classified 17,512 resolved Jira tickets from 12 MongoDB driver projects using an LLM classifier (Claude Sonnet, validated against a 200-ticket gold corpus at F1=0.71 for the nonconformance category). After manually reviewing ~170 tickets the classifier labeled as CRUD nonconformance and reclassifying 44 that were coordinated spec rollouts, initial feature implementations, or wrong-spec-area misclassifications, 210 CRUD nonconformance bugs remain across all drivers from 2009 to 2026.

Separately, we mined each driver's git history to determine the month it first synced CRUD YAML test files from the shared specifications repository.

### Analysis approach

The **5 late-syncing drivers** --- C, C++, Node.js, Ruby, and PHP --- all adopted CRUD YAML tests after the CRUD spec was already published (February 2015). For each driver the **pre-sync window** (spec published, no YAML tests) and the **post-sync window** (YAML tests adopted) both start after the spec existed, so the comparison isolates the effect of the tests rather than the effect of the spec publication itself.

The 4 early-syncing drivers (C#, Java, Perl, Python --- all synced March 2015) are excluded: they adopted tests almost simultaneously with the spec publication, leaving only one month of post-spec pre-sync history.

| Driver | Sync date | Pre-sync rate | Post-sync rate | Change |
|--------|-----------|--------------|----------------|--------|
| Node.js | 2016-11 | 1.1/yr (21 mo) | 2.4/yr | +114% |
| C++     | 2017-01 | 1.0/yr (23 mo) | 0.4/yr | −59%  |
| C       | 2018-06 | 9.6/yr (40 mo) | 1.6/yr | −83%  |
| Ruby    | 2018-08 | 6.3/yr (42 mo) | 1.2/yr | −81%  |
| PHP     | 2019-07 | 2.0/yr (53 mo) | 0.9/yr | −56%  |

Pre-sync rates computed over months from spec publication (Feb 2015) to each driver's sync date. Post-sync rates computed from sync date to end of data.

Four of five drivers show reductions of 56--83%. Node.js is an outlier (+114%), driven by a BulkWrite result-shape conformance cluster (NODE-1812, NODE-1989, NODE-2383, NODE-2619, NODE-2625, NODE-2923, NODE-2926, NODE-2936, NODE-3055, NODE-4034) spanning 2019--2022. These bugs involve the shape of language-level result objects (`BulkWriteResult`, `BulkWriteError`), which YAML tests structurally cannot catch because YAML tests validate wire protocol, not API surface naming or result-object structure.

The result (`data/plots/crud_late5.png`) shows CRUD nonconformance bug rates (bugs/year) for these 5 drivers, before and after YAML test adoption.

### Why nonconformance bugs persist after YAML test adoption

All 9 drivers that have meaningful CRUD history had synced CRUD YAML tests by mid-2019, yet nonconformance bugs continued. Manual review of the 2019 tickets reveals the main reasons YAML tests reduce but do not eliminate nonconformance:

- **Coverage gaps in the YAML test corpus.** Several bugs were in areas the YAML tests simply didn't cover. PERL-1127 notes explicitly: "there were no tests in the spec for this." Bulk write edge cases (pipeline updates, error index reporting) were underspecified in the test suite.
- **Regressions introduced after tests passed.** CDRIVER-2992 is a regression from a prior fix that changed the BSON type of the arrayFilters option from array to document. The original YAML tests passed before that commit broke things.
- **Behaviors hard to express declaratively.** Multi-server failure paths (CDRIVER-3313: retryable bulk write selects wrong server) and ordered-vs-unordered error handling (CDRIVER-3305) involve stateful server interactions that are difficult to encode in a YAML test.
- **API-level vs wire-level conformance.** NODE-1812 (option named `returnOriginal` instead of spec-mandated `returnDocument`) is an API naming mismatch. The wire-level behavior was correct, but YAML tests validate wire behavior, not API surface naming.

## What's here

```
analysis/
├── README.md                 this file
├── requirements.txt          Python deps (anthropic, matplotlib, numpy, requests)
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
│   └── crud_analysis.py      CRUD panel, pre/post rate comparison, chart
└── data/
    ├── tickets/              raw Jira JSONL dumps (gitignored)
    ├── chunks/               50-ticket chunks for subagent classification
    ├── sonnet_results/       per-chunk Sonnet classification results
    ├── classified_sonnet.csv aggregated Sonnet classifications (17,501 unique)
    ├── gold_corpus.csv       200-ticket gold corpus for precision/recall
    ├── drivers_timeline.csv  per-driver monthly spec-test file counts
    ├── drivers_submodule_timeline.csv  submodule-based driver file counts
    ├── crud_panel.csv        (driver, month) panel for CRUD analysis
    └── plots/
        └── crud_late5.png    pre/post bug-rate chart, 5 late-syncing drivers
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

# 5. Run CRUD-focused analysis and generate chart
.venv/bin/python scripts/crud_analysis.py
```
