# Proposal A execution status

Live status of the Jira ticket mining for the ISSRE 2026 resubmission. Updated as work progresses. The full plan lives in `../plan-proposal-a.md`; this file is the running log.

## Current phase

**Phase 2 of 6: bulk pull in progress.** Classifier scripts written and ready; awaiting `ANTHROPIC_API_KEY` from Jesse before running on real tickets.

## Phases

- [x] **0. Setup.** PAT saved at `~/.jira_pat`, smoke-tested. venv at `analysis/.venv`. Project list pulled to `data/projects.json` (372 total Jira projects).
- [x] **1. Volume planning.** `scripts/count_volume.py` ran across 25 candidate projects. Bug+Improvement totals: **13,538 tickets** in the 2015-01-01 → 2026-04-28 window. Per-project counts are in `data/pull.log` once the pull finishes.
- [ ] **2. Bulk pull (in progress).** `scripts/pull_tickets.py` running in background for all driver projects, Bug + Improvement only. Writes `data/tickets/<PROJECT>.jsonl`.
- [ ] **3. Classifier smoke test.** Run `scripts/classify.py` on ~50 tickets across 3 different-style projects (e.g. MGO, PYTHON, NODE). Hand-eyeball outputs. Iterate prompt if the labels look wrong.
- [ ] **4. Full classification.** Run classifier across all ~13.5k tickets via parallel Haiku calls. Estimated cost: ~$30. Writes `data/classified.csv`.
- [ ] **5. Aggregation.** Compute headline metrics: per-driver category breakdown, per-spec-area counts, before-vs-after-UTF rates, fan-out from DRIVERS to per-driver tickets. Plot.
- [ ] **6. Hand-validate sample.** Two-rater check on stratified sample of ~250 tickets to estimate classifier agreement (Cohen's kappa). If kappa < 0.7, revise prompt and re-classify.
- [ ] **7. Case studies.** Pick 2--3 vivid tickets (one per primary category) for narrative paragraphs in the paper.

## Driver projects in scope

Excluded per Jesse: `MONGOCRYPT`, `MONGOID`.

Included (Bug + Improvement counts in the window, from `count_volume.py`):

| Key | Tickets | Notes |
|---|---:|---|
| DRIVERS | 321 | Cross-cutting hub. Most spec-conformance issues fan out from here. |
| PYTHON | 924 | PyMongo. |
| MOTOR | 169 | Async Python. Wind-down; superseded by PyMongo's async API. |
| JAVA | 1705 | Sync + reactive Java driver. |
| JAVARS | 45 | Reactive Streams Java driver. |
| JAVARX | 18 | RxJava Java driver (legacy). |
| SCALA | 109 | Scala driver, on top of Java. |
| NODE | 1779 | Node.js driver. |
| CSHARP | 1396 | .NET driver. |
| GODRIVER | 1183 | Current Go driver. |
| MGO | 31 | Pre-MongoDB Go driver fork; small but historically interesting. |
| RUST | 482 | |
| PHPLIB | 272 | PHP high-level library. |
| PHPC | 688 | PHP C extension under PHPLIB. |
| PHP | 108 | Legacy PHP driver (pre-2014). Mostly out of window but a few tickets resolved late. |
| RUBY | 1195 | |
| CDRIVER | 1830 | libmongoc. |
| CXX | 619 | C++ driver, wraps libmongoc. |
| SWIFT | 322 | **Retired ~2022.** Window is 2015 → retirement. |
| PERL | 253 | **Retired ~2020.** Window is 2015 → retirement. |
| HHVM | 85 | HipHop VM driver, Facebook-only history. |
| SPEC | 0 | All resolved tickets are `Task` type; pull separately if we want spec-authoring history. |
| DRIVERSOLD | 4 | Tiny historical project; ignore unless needed. |

`HASKELL` and `ERLANG` had 0 resolved tickets in the window and are skipped.

## Open questions

- Should we expand to issuetype `Task` for `DRIVERS` and `SPEC`? That would add ~1,500 spec-authoring tickets and let us answer "how often did a per-driver bug trigger a spec amendment?" --- worth the extra ~$3 of classifier cost.
- Should we pull `New Feature` from per-driver projects? Probably not --- new spec rollouts there are noisy.
- Do we have access to GitHub PR data via the Jira dev-status panel? If yes, attribution of "caught by UTF" via CI logs becomes feasible. Tabled until classifier output is stable.

## Decisions log

- 2026-04-28: Excluded MONGOCRYPT and MONGOID per Jesse.
- 2026-04-28: Default issuetype filter is `Bug, Improvement`. Task can be added per project as needed.
- 2026-04-28: Classifier model is `claude-haiku-4-5`. Single-call per ticket, max 400 output tokens, JSON-only output. Description truncated to 4000 chars.
- 2026-04-28: Classification categories: `driver_spec_nonconformance`, `cross_driver_inconsistency`, `avoidable_by_spec_conformance`, `spec_ambiguity_or_gap`, `spec_authoring`, `test_infrastructure`, `not_relevant`. Plus `spec_area`, `mentions_other_driver`, `confidence`, `rationale`.

## Security notes

- The PAT was pasted into the chat session. Rotate at <https://jira.mongodb.org/tokens> after the analysis is complete.
- Token is stored at `~/.jira_pat` (chmod 600), never written to the repo or git-tracked.
- `data/tickets/` is gitignored to avoid checking in scraped Jira content (some descriptions may contain customer info or internal details).
