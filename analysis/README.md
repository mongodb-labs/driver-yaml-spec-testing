# analysis/ --- Jira ticket mining for Proposal A

Quantitative bug-class analysis for the ISSRE 2026 resubmission. See
`../CLAUDE.md` § Proposal A and `plan.md` in this directory for the
overall plan and live status.

## What's here

```
analysis/
├── README.md             this file
├── plan.md               execution status, updated as work progresses
├── requirements.txt      Python deps
├── prompts/
│   └── classify.md       per-ticket classifier prompt (used by Haiku)
├── scripts/
│   ├── count_volume.py   counts tickets per driver project
│   ├── pull_tickets.py   bulk-pulls Jira tickets to data/tickets/
│   └── classify.py       runs classifier, writes data/classified.csv
└── data/
    ├── projects.json     authoritative project list (committed)
    ├── tickets/          raw Jira JSONL dumps (gitignored)
    ├── pull.log          last bulk-pull log (gitignored)
    └── classified.csv    classification output (committed once stable)
```

## Setup on a fresh macOS checkout

```sh
cd analysis
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

The Jira PAT and Anthropic API key are kept **outside** the repo:

```sh
# Jira: generate a PAT at https://jira.mongodb.org/tokens and save it
echo 'YOUR_TOKEN' > ~/.jira_pat
chmod 600 ~/.jira_pat

# Anthropic: export your key in your shell rc
export ANTHROPIC_API_KEY=sk-ant-...
```

## Running

```sh
# 1. Sanity-check ticket volumes per project
.venv/bin/python scripts/count_volume.py

# 2. Bulk-pull resolved Bug + Improvement tickets in the paper window.
#    Output: data/tickets/<PROJECT>.jsonl, one ticket per line.
.venv/bin/python scripts/pull_tickets.py

# 3. Classify each ticket via Haiku. Resumable; safe to ctrl-C and re-run.
#    Output: data/classified.csv
.venv/bin/python scripts/classify.py

# To smoke-test the classifier on a small project first:
.venv/bin/python scripts/classify.py --projects MGO --limit 20 --workers 4
```

## Notes

- Driver projects: see `data/projects.json`. We exclude MONGOCRYPT and MONGOID per Jesse.
- Window: all time → 2026-04-28. We initially used a 2015-01-01 lower bound but later removed it; the all-time pull is now the default and recovers ~3,974 pre-2015 tickets (mostly in JAVA, PHP, CSHARP, RUBY, PYTHON, CDRIVER, PERL, NODE).
- We pull issuetype `Bug` and `Improvement` only. Spec-authoring tickets in `DRIVERS`/`SPEC` are filed as `Task` --- pull those separately if needed (`--types "Task"`).
- The classifier emits one CSV row per ticket with: `category`, `spec_area`, `mentions_other_driver`, `confidence`, `rationale`. See `prompts/classify.md` for the category definitions.
