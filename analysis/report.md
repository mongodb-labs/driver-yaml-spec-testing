# Bug Classification Analysis: MongoDB Driver Jira Tickets

**Purpose:** Quantitative evidence for the ISSRE 2026 resubmission of *The Polyglot's Dilemma: Conformance Testing a Dozen Specs in as Many Languages*. Supports the claim that YAML-based spec tests reduce driver nonconformance bugs.

---

## 1. Overview

MongoDB maintains ~12 native driver implementations (Python, Java, Node.js, C#, Go, Rust, Ruby, PHP, C, C++, Swift, Perl, and others). Each driver must conform to shared cross-language specifications covering BSON serialization, SDAM, CRUD, authentication, sessions, transactions, and ~25 other protocol areas. The MongoDB Unified Test Format (UTF) encodes these specs as YAML test files that all drivers execute against a shared test runner.

**Research question:** Did the introduction of YAML spec tests (UTF and predecessor formats) reduce the rate of `driver_spec_nonconformance` bugs---bugs where a driver's behavior deviated from a published spec requirement?

**Approach:** Mine all resolved Bug and Improvement tickets from MongoDB driver Jira projects (2015--2026). Classify each ticket using an LLM classifier. Compute a before/after nonconformance rate per spec area, using the date YAML tests were first committed to the specs repository as the intervention date.

---

## 2. Data Collection

### 2.1 Jira projects in scope

22 driver projects: CDRIVER, NODE, JAVA, CSHARP, GODRIVER, RUBY, PYTHON, PHPC, CXX, RUST, PHPLIB, SWIFT, PERL, HHVM, MOTOR, MGO, SCALA, JAVARS, JAVARX, SPEC, DRIVERS, DRIVERSOLD. Excluded: MONGOCRYPT, MONGOID (not core driver implementations).

Ticket window: 2015-01-01 through 2026-04-28 (date of data pull). Issuetypes: Bug and Improvement only (Task excluded to avoid spec-authoring noise, except SPEC and DRIVERS where Task covers authoring history).

### 2.2 Pull methodology

Pulled via Jira REST API, authenticated with a personal access token. Per-project JSONL files written to `data/tickets/`. Fields captured: key, project, summary, description, issuetype, status, resolution, priority, created, resolutiondate, components, labels, fixVersions, links.

**Total tickets pulled: 13,538** across 22 projects.

| Project | Tickets | Notes |
|---|---:|---|
| NODE | 1,779 | Node.js driver |
| CDRIVER | 1,830 | libmongoc (C driver) |
| JAVA | 1,705 | Java driver |
| CSHARP | 1,396 | .NET driver |
| GODRIVER | 1,183 | Go driver |
| RUBY | 1,195 | Ruby driver |
| PYTHON | 924 | PyMongo |
| PHPC | 688 | PHP C extension |
| CXX | 619 | C++ driver |
| RUST | 482 | Rust driver |
| SWIFT | 322 | Swift driver (retired ~2022) |
| DRIVERS | 321 | Cross-cutting coordination |
| PHPLIB | 272 | PHP high-level library |
| PERL | 253 | Perl driver (retired ~2020) |
| HHVM | 85 | HipHop VM (historical) |
| *others* | ~484 | MOTOR, MGO, SCALA, JAVARS, JAVARX, etc. |

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

80 tickets were hand-labeled by the first author (Jesse Davis). The labeling sample was constructed by stratified sampling from the Haiku-classified dataset: 20 tickets per category (N, X, R, and a now-dropped A category), balanced across high/medium/low Haiku confidence levels.

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

## 4. Preliminary Results (Haiku classification)

The initial full-corpus classification used Haiku (cheap, fast, but lower quality) to produce `data/classified.csv`. These results should be treated as directional only; the Sonnet re-classification is the authoritative dataset.

Haiku category distribution (13,538 tickets):

| Category | Count | % |
|---|---:|---:|
| not_relevant | 8,596 | 63.5% |
| driver_spec_nonconformance | 2,505 | 18.5% |
| avoidable_by_spec_conformance* | 974 | 7.2% |
| test_infrastructure | 631 | 4.7% |
| cross_driver_inconsistency | 635 | 4.7% |
| spec_authoring | 151 | 1.1% |
| spec_ambiguity_or_gap | 45 | 0.3% |

*This category was dropped from the Sonnet re-run.

Top spec areas across relevant tickets (Haiku): CRUD 929, BSON 869, SDAM 405, Auth 286, CMAP 276, Cursors 276, Connection-String 266, Sessions 193, Wire-Protocol 190, Server-Selection 175.

**Tickets flagged `preventable_by_yaml_test = true`:** 2,908 (21.5% of all tickets).

---

## 5. Full Sonnet Re-classification

*[Results pending --- classification in progress.]*

The full 13,538-ticket corpus is being re-classified with claude-sonnet-4-6 using the exp02 prompt (N gate). Results will be written to `data/classified_sonnet.csv`.

### 5.1 Category distribution

*[TBD]*

### 5.2 Per-driver breakdown

*[TBD]*

### 5.3 Estimated true N count with 95% CI

Using a ratio estimator with the gold-corpus precision (73.3%) and recall (68.8%), the 95% confidence interval on the true N count is:

*[TBD --- formula: true_N ≈ model_N_count × (recall / precision), CI from bootstrap on gold set]*

---

## 6. Before/After YAML Test Analysis

### 6.1 Motivation

The core causal claim of the paper: once YAML spec tests existed for a given spec area, drivers could no longer check in versions that failed those tests, so the nonconformance bug rate for that area should drop.

### 6.2 Intervention dates

For each spec area, the intervention date is the date YAML test files for that area were first committed to the `mongodb/specifications` repository. These dates will be mined from the specs repo git history.

### 6.3 Analysis plan

For each (spec_area, driver, year) cell in the classified data:
- Count N tickets per year
- Mark years as pre/post the YAML test introduction date for that spec area
- Fit an interrupted time series model (or simple before/after comparison)
- Report the rate change and 95% CI

Candidate spec areas with enough tickets for reliable estimation (≥20 N tickets each from Haiku): CRUD, BSON, SDAM, Auth, CMAP, Cursors, Connection-String, Sessions, Wire-Protocol.

### 6.4 Expected results

*[TBD]*

---

## 7. Cross-Driver Consistency

*[Placeholder for case studies from the X-category tickets and from tickets with `mentions_other_driver = true`.]*

---

## Appendix: Methodology notes

### A.1 "Issue split" ticket rule

Many per-driver tickets have `links: Issue split: DRIVERS-XXXX`. This means the ticket is a child of a cross-driver coordination ticket in the DRIVERS project. When the issuetype is Improvement, this nearly always means proactive spec-rollout work (the driver was implementing a new spec requirement, not fixing a bug). These are classified `not_relevant`. When the issuetype is Bug, the driver may have had incorrect behavior; these are classified on their merits (T or N based on the description).

### A.2 Confidence intervals

Given classifier precision p and recall r on the gold corpus, an observed model count M for category C implies:
- Estimated true count: T̂ = M × (r / p) ... *[actually needs derivation, TBD]*
- Standard approach: use the ratio estimator; bootstrap CI from gold corpus

### A.3 Reproducibility

All code is in `analysis/scripts/`. The gold corpus is `data/gold_corpus.csv`. The prompt is `prompts/classify.md`. The full ticket data is gitignored (may contain customer-sensitive content) but can be re-pulled via `scripts/pull_tickets.py` with a Jira PAT.
