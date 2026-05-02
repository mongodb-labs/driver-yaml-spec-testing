# Proposal A execution status

Live status of the Jira ticket mining for the ISSRE 2026 resubmission. Updated as work progresses. The full plan lives in `../plan-proposal-a.md`; this file is the running log.

## Current phase

**Phase 4 of 7: full classification COMPLETE.** All 13,538 tickets classified by Haiku subagents. Output is `data/classified.csv` (committed). Aggregation, hand-validation, and case studies are next.

### Phase 4 results

- **13,538 / 13,538 classified** (100%, zero JSON errors after retries)
- **4,941 (36.5%) relevant** to the paper (any non-`not_relevant` category)
- **8,596 (63.5%) `not_relevant`** --- the conservative classifier correctly buckets most build/packaging/perf/refactor noise
- **2,505 (18.5%) `driver_spec_nonconformance`**
- **974 (7.2%) `avoidable_by_spec_conformance`**
- **635 (4.7%) `cross_driver_inconsistency`**
- **45 (0.3%) `spec_ambiguity_or_gap`** --- thin; classifier may be conservative here
- **151 (1.1%) `spec_authoring`**
- **631 (4.7%) `test_infrastructure`**
- **2,908 (21.5%) flagged `preventable_by_yaml_test = True`**
- **1,594 tickets** with `mentions_other_driver = True` AND a spec-relevant category --- prime candidates for cross-driver consistency case studies

Top spec areas across the 4,941 relevant tickets: CRUD 929, BSON 869, SDAM 405, Auth 286, CMAP 276, Cursors 276, Connection-String 266, Sessions 193, Wire-Protocol 190, Server-Selection 175, Change-Streams 154, Transactions 152, CSFLE 126, GridFS 119, Index-Management 111, Write-Concern 110, Retryable-Writes 101.

### Per-driver breakdown (relevant categories)

| project | total | relevant | nonconf | x-driver | avoidable |
|---|---:|---:|---:|---:|---:|
| CDRIVER | 1830 | 587 | 225 | 146 | 125 |
| NODE | 1779 | 598 | 314 | 74 | 117 |
| JAVA | 1705 | 661 | 331 | 52 | 146 |
| CSHARP | 1396 | 485 | 213 | 136 | 100 |
| RUBY | 1195 | 554 | 333 | 29 | 106 |
| GODRIVER | 1183 | 506 | 268 | 62 | 113 |
| PYTHON | 924 | 207 | 56 | 54 | 73 |
| PHPC | 688 | 202 | 94 | 21 | 69 |
| CXX | 619 | 203 | 110 | 38 | 20 |
| RUST | 482 | 250 | 171 | 6 | 32 |
| SWIFT | 322 | 126 | 66 | 0 | 19 |
| DRIVERS | 321 | 107 | 26 | 2 | 5 |
| PHPLIB | 272 | 151 | 97 | 1 | 17 |
| PERL | 253 | 119 | 92 | 1 | 14 |
| ... | | | | | |

## Phases

- [x] **0. Setup.** PAT saved at `~/.jira_pat`, smoke-tested. venv at `analysis/.venv`. Project list pulled to `data/projects.json` (372 total Jira projects).
- [x] **1. Volume planning.** `scripts/count_volume.py` ran. Bug+Improvement totals: **17,512 tickets** all-time through 2026-04-28. (An earlier run with a 2015-01-01 floor returned only 13,538; the floor was removed and the pull re-run.)
- [x] **2. Bulk pull.** `scripts/pull_tickets.py` wrote `data/tickets/<PROJECT>.jsonl` for 22 driver projects.
- [x] **3. Chunk + smoke test.** Split into 271 chunks of 50 tickets. Smoke-tested chunk_0001 (CDRIVER): 50/50 valid, sensible distribution.
- [x] **4. Full classification.** All 271 chunks dispatched to Haiku subagents in parallel batches (typically 12--30 per dispatch). Initial 30-batch attempt at chunks 162--191 hit a wave of stream-idle timeouts; recovered by dropping to 12 per batch. Five chunks needed retry for missing files / short outputs / one bare-`unsure` JSON glitch. Final state: **13,538 / 13,538 classified, zero errors.**
- [ ] **5. Aggregation.** Per-driver-per-year, per-spec-area, before-vs-after-UTF rates. Compute fan-out from DRIVERS to per-driver tickets via the `links` column.
- [ ] **6. Hand-validate sample.** Two-rater check on stratified sample of ~250 tickets (Jesse + Jeff) to estimate Cohen's kappa. Spot-check: smoke-test (50 CDRIVER tickets) showed minor over-tagging of auth sub-areas; main category labels looked correct.
- [ ] **7. Case studies.** Pick 2--3 vivid tickets from the 1,594 cross-driver-flagged set and the 974 avoidable bucket for narrative paragraphs in the paper.

## Open issues from the run

- **Spec-area sub-tag noise.** The classifier sometimes tags `auth-oidc` or `auth-aws` when the ticket only says "auth" or describes X.509. Aggregate by parent-area (`auth`) when this matters. Down-tag in post-process if needed.
- **Bare-`unsure` JSON glitch.** Two lines in the original chunk_0166 emitted `unsure` without quotes (invalid JSON). Caught by validator, retried successfully. No remaining occurrences in the final CSV.
- **Subagent self-reported success but no file written.** Five chunks (0202, 0247, 0208, 0249, 0256) reported "done: N classifications written" but the file either didn't exist or was short by 2--3 lines. Likely a Write tool path mismatch or partial write under load. Retried successfully. **Always verify on disk, not in chat.**
- **`preventable_by_yaml_test` casing.** 31 rows have lowercased `false` and 19 have `true`. Cosmetic; normalize in the aggregation step.
- **One row with empty category.** A single row from the 13,538 has blank classification fields. Find and reclassify in the aggregation pass.

## Phases

- [x] **0. Setup.** PAT saved at `~/.jira_pat`, smoke-tested. venv at `analysis/.venv`. Project list pulled to `data/projects.json` (372 total Jira projects).
- [x] **1. Volume planning.** `scripts/count_volume.py` ran across 25 candidate projects. Bug+Improvement totals: **17,512 tickets** all-time through 2026-04-28 (an earlier run with a 2015-01-01 floor returned only 13,538). Per-project counts are in `data/pull.log` once the pull finishes.
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
| SWIFT | 322 | **Retired ~2022.** Window: project inception → retirement. |
| PERL | 482 | **Retired ~2020.** Window: 2009 → retirement. |
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
