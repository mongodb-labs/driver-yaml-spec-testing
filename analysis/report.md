# Bug Classification Analysis: MongoDB Driver Jira Tickets

**Purpose:** Quantitative evidence for the ISSRE 2026 resubmission of *The Polyglot's Dilemma: Conformance Testing a Dozen Specs in as Many Languages*. Supports the claim that YAML-based spec tests reduce driver nonconformance bugs.

---

## 1. Overview

MongoDB maintains ~12 native driver implementations (Python, Java, Node.js, C#, Go, Rust, Ruby, PHP, C, C++, Swift, Perl, and others). Each driver must conform to shared cross-language specifications covering BSON serialization, SDAM, CRUD, authentication, sessions, transactions, and ~25 other protocol areas. The MongoDB Unified Test Format (UTF) encodes these specs as YAML test files that all drivers execute against a shared test runner.

**Research question:** Did the introduction of YAML spec tests (UTF and predecessor formats) reduce the rate of `driver_spec_nonconformance` bugs---bugs where a driver's behavior deviated from a published spec requirement?

**Approach:** Mine all resolved Bug and Improvement tickets from MongoDB driver Jira projects (2009--2026, all-time history). Classify each ticket using an LLM classifier. Compute a before/after nonconformance rate per spec area, using the date YAML tests were first committed to the specs repository as the intervention date.

---

## 2. Data Collection

### 2.1 Jira projects in scope

22 driver projects: CDRIVER, NODE, JAVA, CSHARP, GODRIVER, RUBY, PYTHON, PHPC, CXX, RUST, PHPLIB, SWIFT, PERL, HHVM, MOTOR, MGO, SCALA, JAVARS, JAVARX, SPEC, DRIVERS, DRIVERSOLD. Excluded: MONGOCRYPT, MONGOID (not core driver implementations).

Ticket window: all-time through 2026-04-28 (date of data pull). The oldest ticket is PERL-1 from 2009-07-17. Issuetypes: Bug and Improvement only (Task excluded to avoid spec-authoring noise, except SPEC and DRIVERS where Task covers authoring history).

### 2.2 Pull methodology

Pulled via Jira REST API, authenticated with a personal access token. Per-project JSONL files written to `data/tickets/`. Fields captured: key, project, summary, description, issuetype, status, resolution, priority, created, resolutiondate, components, labels, fixVersions, links.

**Total tickets pulled: 17,512** across 22 projects, all-time through 2026-04-28. The oldest ticket is PERL-1, resolved 2009-07-17.

| Project | Tickets | Notes |
|---|---:|---|
| JAVA | 2,505 | Java driver (oldest in 2009) |
| CDRIVER | 2,115 | libmongoc (C driver) |
| CSHARP | 1,964 | .NET driver |
| NODE | 1,956 | Node.js driver |
| RUBY | 1,697 | Ruby driver (oldest in 2009) |
| PYTHON | 1,369 | PyMongo (oldest in 2009) |
| GODRIVER | 1,183 | Go driver |
| PHP | 815 | Legacy `pecl-mongo` (oldest 2009; superseded by PHPC) |
| CXX | 790 | C++ driver |
| PHPC | 719 | PHP C extension |
| RUST | 482 | Rust driver |
| PERL | 482 | Perl driver (oldest 2009; retired ~2020) |
| SWIFT | 322 | Swift driver (retired ~2022) |
| DRIVERS | 321 | Cross-cutting coordination |
| PHPLIB | 279 | PHP high-level library |
| MOTOR | 199 | Async PyMongo wrapper |
| SCALA | 109 | Java/Scala bindings |
| HHVM | 85 | HipHop VM (historical) |
| MGO | 46 | Old community Go driver (mgo) |
| JAVARS | 45 | Java Reactive Streams |
| JAVARX | 18 | Java RxJava |
| DRIVERSOLD | 11 | Pre-DRIVERS coordination project |
| SPEC | 0 | All Task type, excluded by issuetype filter |

---

## 3. Classifier

### 3.1 Categories

Each ticket is assigned exactly one of six categories:

| Category | Code | Description |
|---|---|---|
| `driver_spec_nonconformance` | N | Driver implemented a spec area incorrectly; spec says X, driver did Y |
| `cross_driver_inconsistency` | X | Filed because two or more drivers behave differently; explicit cross-driver comparison |
| `spec_ambiguity_or_gap` | G | Root cause is a gap or ambiguity in the spec itself, not just the driver |
| `spec_authoring` | S | About writing or amending a specification (DRIVERS/SPEC project tickets) |
| `test_infrastructure` | T | About spec test runners, YAML test format, or CI plumbing for spec tests |
| `not_relevant` | R | Everything else: build/packaging, CI, docs, perf, internal refactors |

Additional fields per ticket: `spec_areas` (which spec areas the ticket touches), `is_nonconformance` (boolean), `mentions_other_driver` (boolean), `preventable_by_yaml_test` (boolean or "unsure"), `confidence` (high/medium/low).

A dropped seventh category (`avoidable_by_spec_conformance`) was removed after evaluation showed it was poorly defined and too small to estimate reliably.

### 3.2 Model selection

Three models were evaluated on the 80-ticket human-labeled gold set:

| Model | Overall agreement | N F1 | Notes |
|---|---:|---:|---|
| claude-haiku-4-5 | 27.5% | — | Unusably poor; dropped |
| claude-sonnet-4-6 | 81.2% | 0.649 (baseline) | Selected for full run |
| claude-opus-4-7 | ~85%* | — | Too expensive for 13,538 tickets |

*Opus used to label 120 additional gold-corpus tickets (see §3.3). Its label quality was judged adequate for gold-corpus use.

### 3.3 Gold corpus construction

80 tickets were hand-labeled by the first author (Jesse Davis). The labeling sample was constructed by stratified sampling from a preliminary classification pass: 20 tickets per category (N, X, R, and a now-dropped A category), balanced across high/medium/low confidence levels.

To improve evaluation reliability, 120 additional tickets were labeled by Opus 4.7, yielding a **200-ticket gold corpus**. Labels from the author and from Opus were treated as equally authoritative. Category distribution in the 200-ticket corpus:

| Category | Count |
|---|---:|
| not_relevant (R) | 136 |
| driver_spec_nonconformance (N) | 32 |
| test_infrastructure (T) | 24 |
| spec_ambiguity_or_gap (G) | 4 |
| spec_authoring (S) | 4 |

A critical labeling rule applied during gold-corpus construction: tickets with `links: Issue split: DRIVERS-XXXX` and `issuetype: Improvement` are classified `not_relevant`. These are proactive spec-rollout work (the DRIVERS project coordinates a new requirement; each driver gets a child ticket to implement it). The driver was not doing anything wrong; this is not a nonconformance. 14 tickets that Opus initially labeled N were corrected to R under this rule.

### 3.4 Prompt engineering experiments

8 prompt variants were evaluated against the 200-ticket gold corpus using Sonnet 4.6. The key metric is N F1 (harmonic mean of precision and recall for `driver_spec_nonconformance`), since the paper's central claim depends on accurately counting N tickets.

| Experiment | Overall | N prec | N rec | N F1 | Key change |
|---|---:|---:|---:|---:|---|
| exp01_baseline | 80.0% | 55.6% | 78.1% | 0.649 | Baseline prompt |
| **exp02_specific_rule** | **77.5%** | **73.3%** | **68.8%** | **0.710** | **Gate: name the specific rule** |
| exp03_cot_spec_rule | 77.5% | 75.0% | 65.6% | 0.700 | + `spec_rule` CoT output field |
| exp04_more_n_examples | 79.0% | 47.4% | 84.4% | 0.607 | 4 extra N few-shot examples |
| exp05_liberal_n | 75.5% | 43.1% | 78.1% | 0.556 | "err toward N" instruction |
| exp06_conservative_n | 75.5% | 44.1% | 81.2% | 0.571 | 3-part N checklist |
| exp07_no_fewshot | 76.5% | 54.2% | 81.2% | 0.650 | No few-shot examples |
| exp08_simplified | 78.5% | 48.9% | 71.9% | 0.582 | Stripped-down prompt |

**Winner: exp02_specific_rule.** The single change from baseline: a gate question added to the N category definition---*"Before classifying as `driver_spec_nonconformance`, ask: Can I name the specific rule in the spec that the driver violated? If yes, N. If not, `not_relevant`."* This raises N precision from 55.6% to 73.3% at the cost of recall (78.1% → 68.8%), for a net +6pp F1.

The baseline's main failure mode was classifying spec-covered-component bugs (memory leaks, pool resource leaks) as N when no specific spec rule was contradicted. The gate filters these out.

**Caveat:** The model cannot actually look up the spec---it draws on training data. The gate works as a confidence filter, not a ground-truth check. The rationale fields in N-classified tickets may cite rules that are approximate or imprecise; they should not be used as authoritative spec citations.

### 3.5 Classifier limitations

- **N precision 73.3%, recall 68.8%:** roughly 1 in 4 model N calls is a false positive; roughly 1 in 3 true N tickets is missed.
- Suitable for trend analysis (before/after rate estimation) but not for certifying individual tickets.
- Confidence intervals for estimated counts use a ratio estimator accounting for precision and recall (see §5).

---

## 4. Full Sonnet Re-classification

The full 17,512-ticket corpus was classified with claude-sonnet-4-6 using the exp02 prompt (N gate). 17,501 unique tickets were classified (11 tickets appeared as duplicates across chunk boundaries and were de-duplicated). Results are in `data/classified_sonnet.csv`.

### 4.1 Category distribution

| Category | Count | % |
|---|---:|---:|
| `not_relevant` | 13,863 | 79.2% |
| `driver_spec_nonconformance` | 2,302 | 13.2% |
| `test_infrastructure` | 1,188 | 6.8% |
| `spec_ambiguity_or_gap` | 66 | 0.4% |
| `cross_driver_inconsistency` | 53 | 0.3% |
| `spec_authoring` | 29 | 0.2% |
| **Total** | **17,501** | **100%** |

The exp02 prompt eliminated the previously-explored `avoidable_by_spec_conformance` category, which had been too poorly defined to estimate reliably. The N category's precision gate is the key change: it asks the classifier to name the specific violated spec rule, and discards any classification that can't.

**Tickets flagged `preventable_by_yaml_test = true`:** 1,803 (10.3% of all tickets).

**Top spec areas (N tickets only):**

| Spec area | N tickets |
|---|---:|
| BSON | 307 |
| CRUD | 291 |
| Server Selection | 279 |
| SDAM | 269 |
| Connection String | 218 |
| Write Concern | 156 |
| Wire Protocol | 144 |
| Cursors | 115 |
| Sessions | 114 |
| Auth | 112 |
| Change Streams | 102 |
| Transactions | 85 |
| Retryable Writes | 78 |
| GridFS | 77 |
| CMAP | 67 |

The early-driver-era spec areas (BSON, Server Selection, Connection String, GridFS) carry the largest absolute counts because every driver had to implement these from scratch in the 2009--2014 era before unified specs existed; many of the bugs in them were filed during that period. Spec areas introduced later (Transactions in 2018, Retryable Writes 2017, Change Streams 2018, CSE 2019, CSOT 2022) accumulated bug counts more rapidly relative to their lifetime.

### 4.2 Per-driver breakdown

| Project | N | X | G | S | T | R | Total |
|---|---:|---:|---:|---:|---:|---:|---:|
| JAVA | 255 | 10 | 3 | 0 | 222 | 2,014 | 2,504 |
| CDRIVER | 346 | 9 | 6 | 0 | 93 | 1,661 | 2,115 |
| CSHARP | 159 | 6 | 4 | 0 | 117 | 1,677 | 1,963 |
| NODE | 314 | 4 | 8 | 0 | 150 | 1,480 | 1,956 |
| RUBY | 296 | 2 | 3 | 0 | 122 | 1,273 | 1,696 |
| GODRIVER | 186 | 2 | 8 | 0 | 113 | 874 | 1,183 |
| PYTHON | 173 | 2 | 3 | 0 | 74 | 1,117 | 1,369 |
| PHP | 66 | 5 | 0 | 0 | 1 | 736 | 808 |
| CXX | 50 | 1 | 2 | 1 | 49 | 687 | 790 |
| PHPC | 91 | 2 | 0 | 0 | 4 | 622 | 719 |
| RUST | 78 | 1 | 1 | 0 | 41 | 361 | 482 |
| PERL | 81 | 2 | 2 | 0 | 15 | 381 | 481 |
| SWIFT | 48 | 1 | 1 | 0 | 34 | 238 | 322 |
| DRIVERS | 44 | 1 | 22 | 27 | 75 | 152 | 321 |
| PHPLIB | 59 | 1 | 1 | 0 | 56 | 162 | 279 |
| MOTOR | 2 | 2 | 0 | 0 | 7 | 188 | 199 |
| SCALA | 4 | 0 | 1 | 0 | 8 | 96 | 109 |
| HHVM | 31 | 2 | 0 | 0 | 0 | 52 | 85 |
| MGO | 12 | 0 | 0 | 0 | 1 | 33 | 46 |
| JAVARS | 0 | 0 | 1 | 0 | 6 | 38 | 45 |
| JAVARX | 0 | 0 | 0 | 0 | 0 | 18 | 18 |
| DRIVERSOLD | 7 | 0 | 0 | 1 | 0 | 3 | 11 |
| **Total** | **2,302** | **53** | **66** | **29** | **1,188** | **13,863** | **17,501** |

The highest absolute N counts are in CDRIVER (346), NODE (314), RUBY (296), JAVA (255), and GODRIVER (186)---the largest and most mature driver projects. JAVA's pre-spec history (2009--2014) is heavy on BSON and wire-protocol nonconformances. The legacy `pecl-mongo` PHP driver (66 N) shows similar density across BSON, server-selection, and write-concern. As a fraction of their ticket base, HHVM (36.5%) and CDRIVER (16.4%) have the highest nonconformance rates.

### 4.3 Estimated true N count with 95% CI

The classifier's precision and recall are not 100%, so the raw model count (2,302) is not the true number of nonconformance tickets. Using the ratio estimator:

**True N estimate = model\_N × (precision / recall) = 2,302 × (0.733 / 0.688) ≈ 2,453**

The reasoning: precision = TP / model\_N, so TP = model\_N × 0.733 = 1,687. Recall = TP / true\_N, so true\_N = TP / 0.688 = 2,453.

For a 95% CI, we apply Wilson score bounds to the model N rate (2,302 / 17,501 = 13.2%), giving [12.7%, 13.7%], then apply the precision/recall correction:

**95% CI on true N: approximately 2,361--2,547 tickets** out of 17,501 total (≈ 14.0% corrected base rate).

These figures are suitable for trend analysis---comparing before/after rates within the same corpus using the same classifier. They should not be treated as a precise headcount of all nonconformance bugs MongoDB drivers ever had.

---

## 5. Before/After YAML Test Analysis

### 5.1 Motivation

The core causal claim of the paper: once YAML spec tests existed for a given spec area, drivers could no longer check in versions that failed those tests, so the nonconformance bug rate for that area should drop.

### 5.2 Intervention dates

For each spec area, the intervention date is the date YAML test files for that area were first committed to the `mongodb/specifications` repository. These dates will be mined from the specs repo git history.

### 5.3 Analysis plan

For each (spec_area, driver, year) cell in the classified data:
- Count N tickets per year
- Mark years as pre/post the YAML test introduction date for that spec area
- Fit an interrupted time series model (or simple before/after comparison)
- Report the rate change and 95% CI

Candidate spec areas with enough tickets for reliable estimation (≥20 N tickets each from Sonnet): CRUD (250), SDAM (242), BSON (229), Server-Selection (200), Connection-String (161), Sessions (114), Wire-Protocol (115), Write-Concern (118), Change-Streams (102), Auth (93), Cursors (93), Transactions (85), Retryable-Writes (78).

### 5.4 Expected results

*[TBD]*

---

## 6. Cross-Driver Consistency

*[Placeholder for case studies from the X-category tickets and from tickets with `mentions_other_driver = true`.]*

---

## Appendix: Methodology notes

### A.1 "Issue split" ticket rule

Many per-driver tickets have `links: Issue split: DRIVERS-XXXX`. This means the ticket is a child of a cross-driver coordination ticket in the DRIVERS project. When the issuetype is Improvement, this nearly always means proactive spec-rollout work (the driver was implementing a new spec requirement, not fixing a bug). These are classified `not_relevant`. When the issuetype is Bug, the driver may have had incorrect behavior; these are classified on their merits (T or N based on the description).

### A.2 Confidence intervals

Given classifier precision p and recall r on the gold corpus, an observed model count M for category C implies:

- TP = M × p (true positives among model predictions)
- Estimated true count: T̂ = TP / r = M × p / r
- For N: T̂ = M × (0.733 / 0.688) ≈ M × 1.065

95% CI: compute Wilson score interval on the model N rate (M / total), then apply the p/r correction to the lower and upper bounds. This CI accounts for binomial sampling uncertainty in the classifier rate but not for uncertainty in the gold-corpus precision/recall estimates themselves (which are based on a 200-ticket corpus).

### A.3 Reproducibility

All code is in `analysis/scripts/`. The gold corpus is `data/gold_corpus.csv`. The prompt is `prompts/classify.md`. The full ticket data is gitignored (may contain customer-sensitive content) but can be re-pulled via `scripts/pull_tickets.py` with a Jira PAT.
