# Plan: Proposal A --- Bug-class Taxonomy from Jira Ticket Mining

Source: see `CLAUDE.md` § "Proposed quantitative measurements" → A.

**Goal:** produce headline numbers and 2--3 case studies showing what classes of bugs UTF caught, what it missed, and how UTF correlates with cross-driver consistency. This is the highest-payoff response to the unanimous reviewer complaint that the FSE submission lacks defect-level evidence.

## 1. Driver Jira project inventory

MongoDB drivers each have their own Jira project on `jira.mongodb.org` (Server/Data Center, not Cloud). The `DRIVERS` project holds cross-cutting tickets; per-driver tickets typically link to a DRIVERS parent via "is part of" / "depends on" / "implements".

The list below is a working inventory based on Glean search hits and our own knowledge. **It needs to be confirmed exhaustively by hitting `GET /rest/api/2/project`** once a PAT is in hand (see § 2). Treat the lifetime dates as approximate until verified from project creation timestamps and the first/last public release.

| Key | Driver / library | Language | Status | Notes |
|---|---|---|---|---|
| DRIVERS | Cross-cutting specs and platform | --- | Active | Specs, UTF schema, cross-driver issues. **The hub for our analysis.** |
| PYTHON | PyMongo | Python | Active | |
| MOTOR | Motor (async Python) | Python | Wind-down | Superseded by PyMongo's async API; treat as a sub-project of PYTHON for spec coverage. |
| JAVA | Java driver (sync + reactive) | Java / Scala | Active | Scala driver lives in this project. |
| NODE | Node.js driver | JavaScript / TypeScript | Active | |
| CSHARP | C# / .NET driver | C# | Active | |
| GODRIVER | Go driver | Go | Active | |
| RUST | Rust driver | Rust | Active | |
| PHPLIB | PHP library (high-level) | PHP | Active | The user-facing PHP driver. |
| PHPC | PHP C extension | C / PHP | Active | Lower-level PHP extension; ticket may not have shown up in the Glean sample but the project exists. **Verify.** |
| RUBY | Ruby driver | Ruby | Active | |
| MONGOID | Mongoid ODM | Ruby | Active | Built on the Ruby driver; relevant for spec coverage cross-checks. |
| CDRIVER | libmongoc | C | Active | |
| CXX | C++ driver | C++ | Active | Wraps libmongoc. |
| SWIFT | Swift driver | Swift | **Retired** (~2022) | Include in the "before retirement" window only. |
| PERL | Perl driver | Perl | **Retired** (~2020) | **Verify project key still exists.** Did not appear in Glean sample. |
| MONGOCRYPT | libmongocrypt | C | Active | Used by all drivers for CSFLE; spec area. |

**Driver lifetime matters for the analysis.** Bug-rate denominators must be normalized by years of active maintenance, not calendar years. UTF-coverage windows must be intersected with each driver's active window:
- Pre-UTF era: 2015 (CRUD v1) through 2020 (UTF debut).
- UTF era: 2020 → present.
- For SWIFT and PERL: only count tickets up to their EOL.
- For drivers that adopted UTF *gradually* per spec area, the relevant window per driver per spec is when that driver's test runner gained a `schemaVersion` capable of running that spec's UTF tests (data we will also produce in Proposal E).

Also missing from the table but worth checking via the REST API:
- A KAFKA / MongoDB Connector for Kafka project (built on Java driver, may surface UTF-derived tests).
- Any community drivers that MongoDB has internalized.
- The SPECIFICATIONS or SPEC project (if separate from DRIVERS).

## 2. Jira access setup

Confirmed from Glean / corp wiki:

- **Endpoint:** `https://jira.mongodb.org/rest/api/2/`
- **Auth:** Personal Access Token (PAT). Generate at <https://jira.mongodb.org/tokens>. Header: `Authorization: Bearer <token>`.
- **JQL is supported.** Standard Jira Server JQL (not Cloud).
- **Rate limit:** standard `X-RateLimit-*` headers. Bot best-practices doc lives on the corp wiki.
- **Library:** the Python `jira` package works against Jira Server with PAT auth.
- **Compliance gate:** "Internally developed applications or scripts must be reviewed by Security via a Jira ticket before being enabled." For an ad-hoc research script run by a single engineer reading public-to-MongoDB-employees ticket data, this is almost certainly fine, but **verify with #ask-security if we plan to run anything resembling a recurring scrape**.

**Setup steps:**
1. Jesse generates a PAT (read-only scope is enough --- we only `GET`).
2. Store in `~/.jira_pat` or env var; never commit.
3. Smoke-test: `GET /rest/api/2/myself` → confirms auth.
4. Enumerate all projects: `GET /rest/api/2/project` → ground-truth project list with creation dates and lead. Save to `data/projects.json`. **This replaces the table in § 1.**
5. For each project key, confirm via `GET /rest/api/2/project/{key}` that issuetype/component metadata is what we expect.

## 3. Cross-driver linkage via the DRIVERS project

This is the structural feature of MongoDB's Jira layout we need to exploit. The DRIVERS project tracks specifications and cross-cutting initiatives; per-driver work to implement a spec is filed in the per-driver project and linked to a DRIVERS ticket by "is part of" / "implements" / "blocks".

Two ways to use this:
1. **Spec → bug fan-out.** For each DRIVERS ticket representing a spec or behavioral fix, find all linked per-driver tickets. This gives us the *scope* of a cross-driver consistency issue and lets us count "number of drivers that needed the same fix".
2. **Bug → spec attribution.** For each per-driver bug ticket, walk up to the DRIVERS parent (if any) to attribute it to a spec area. Tickets without a DRIVERS link are likely driver-local concerns (build/CI, language ecosystem, performance, packaging) --- we want to **exclude** those from the conformance-bug count.

JQL pattern: `project = JAVA AND issueLinkType in ("is part of", "implements", "depends on") AND issueLink.project = DRIVERS`. Verify exact link-type names against `/rest/api/2/issueLinkType`.

## 4. Sampling strategy

Exhaustive analysis of every closed ticket across ~14 projects over ~10 years is too expensive and most tickets are noise (build infra, duplicate, won't-fix). Two-stage approach:

**Stage 1: bulk pull, machine-classifiable.** For each driver project:
- Fetch all tickets with `issuetype = Bug AND status = Closed AND resolution in (Fixed, Done)` resolved between 2015-01-01 and 2026-04-01.
- Per ticket: key, summary, description, components, labels, fix versions, resolved date, linked tickets, linked PRs (the GitHub-Jira integration leaves PR refs in the development panel, retrievable via `/rest/dev-status/latest/issue/detail?issueId=...`).
- Estimated volume: rough guess 500--3000 bug tickets per major driver, scaling with age and adoption. PYTHON, JAVA, NODE will be the bulk; CDRIVER, GODRIVER, CSHARP medium; RUST, SWIFT, PERL small.

Save raw JSON to `data/tickets/<PROJECT>.json`. This is a one-time pull; refresh before the deadline.

**Stage 2: hand-classify a stratified sample.** Random sample ~25 tickets per active driver, stratified by year, total ~250 tickets. For each, label:
- **Spec area** (CRUD, transactions, retryable r/w, sessions, change streams, CSFLE, BSON, SDAM, conn-string parsing, GridFS, auth, monitoring, other).
- **UTF coverage at the time** (was UTF or a predecessor DSTL covering this spec area on this driver when the bug was introduced and when it was caught?).
- **How was the bug caught?** UTF spec test, driver-local test, internal user, external user, fuzzing, code review.
- **Was it a cross-driver consistency bug?** I.e. did the same issue manifest in ≥2 drivers, or did UTF surface a divergence?
- **Could UTF have caught it in principle?** (Y/N + one-line reason. This is the "structural limit" data Reviewer C asked for.)

Two raters cross-label ~10% to compute Cohen's kappa; if kappa < 0.7 we revise the codebook.

## 5. Headline metrics we expect to produce

From the bulk pull (cheap, exhaustive):
- Total closed bug count per driver per year. Plot to show denominator.
- Fraction of closed bugs linked to a DRIVERS ticket (proxy for "spec-adjacent" vs "driver-local").
- Ratio of (bugs in UTF-covered spec areas) / (bugs in non-UTF areas), per driver, before vs after UTF adoption for that area.
- For each DRIVERS spec ticket: fan-out count = number of per-driver bug tickets linked to it. Distribution: how often is a single spec issue followed by many drivers fixing the same thing?

From the labeled sample (hand-coded, with confidence intervals):
- Of bugs in UTF-covered areas, what fraction was caught by UTF spec tests vs slipped past?
- Bug-rate-per-active-year, UTF-covered areas vs non-covered areas. Hypothesis: lower in UTF-covered.
- Cross-driver consistency bugs: rate before vs after UTF.
- "UTF could have caught it" rate for slipped bugs: bounds the structural limit.

## 6. Case studies (qualitative, picked from the sample)

Pick 2--3 high-signal cases:
1. A bug where UTF caught a divergence: same YAML failed in driver X *because* it had passed in driver Y first, exposing X's nonconformance. Tell the story: which spec, which YAML, which assertion, which driver-side bug.
2. A bug class UTF cannot catch (likely BSON serialization edge case, or SDAM state-machine race) --- explain why. Reinforces the "we cannot unify everything" lesson.
3. A common-mode failure --- bug present in all drivers because the spec was ambiguous, fixed by spec amendment + new UTF tests. This shows the *spec authoring + UTF* loop, not just the test-runner side.

## 7. Risks and mitigations

- **PR-Jira linkage may be sparse for older tickets.** Some pre-2018 tickets won't have GitHub PR refs because the integration was added later. Mitigation: use ticket fix-version + git-blame fallback to find the actual fix commit.
- **"UTF caught it" attribution is hard.** A bug fixed alongside a YAML change tells us the test was *added*, not necessarily that it *initially failed*. Mitigation: filter to PRs where CI logs show a YAML test failure on the pre-fix commit. This requires CI history; Evergreen retains task logs but with retention limits. Skip this filter if data is unavailable and acknowledge the limitation.
- **Sampling bias.** Rare-but-important spec areas (CSFLE, transactions) may be undersampled by uniform sampling. Mitigation: stratify by spec area as well as by year, oversampling the small categories.
- **Compliance.** A research-purpose read-only scrape of internal Jira is low-risk but not zero. Confirm with #ask-security before kicking off the bulk pull, especially if rate exceeds ~1 req/s.
- **Project key drift.** Verify against `/rest/api/2/project` --- our § 1 table is informed-guess-plus-Glean, not authoritative.
- **Scope creep.** The labeling task is the bottleneck. **Cap at 250 sampled tickets across 10 active drivers (25 per driver).** Resist the urge to grow it.

## 8. Effort and timeline

Working backwards from full-paper deadline 2026-07-05:

- **2026-04-29 → 2026-05-05:** Jesse PAT + project enumeration. Confirm § 1 inventory. Get security sign-off if needed. Build the bulk-pull script.
- **2026-05-06 → 2026-05-15:** Bulk pull all driver projects. Land raw data in repo (probably `data/tickets/*.json.gz`, gitignored). Compute the cheap exhaustive metrics (counts, fan-out, link rates).
- **2026-05-16 → 2026-06-05:** Hand-label the stratified sample. Two raters (Jesse + Jeff). Compute kappa, refine codebook if needed.
- **2026-06-06 → 2026-06-15:** Aggregate, generate plots. Write the methodology and results subsections.
- **2026-06-15 → 2026-06-28:** Pick the 2--3 case studies, write narrative paragraphs. Abstract due 2026-06-28.
- **Buffer to 2026-07-05** for revisions and integration with the rest of the paper.

This is roughly **6 person-weeks** (one engineer half-time). If that's too much, the cheapest acceptable cut is: keep the bulk-pull metrics, drop the hand-labeled sample to ~100 tickets across ~5 drivers, and use that to support 1 case study instead of 3.

## 9. Concrete next steps

- [ ] Jesse: generate Jira PAT, set up auth, run `/rest/api/2/project` and replace § 1 table with ground-truth output.
- [ ] Jesse: post in #ask-security with a one-paragraph description of the bulk-pull plan to confirm no review needed.
- [ ] Decide whether to also pull from each driver's GitHub Issues (some drivers, especially RUST and GODRIVER, accept community bug reports on GitHub before they are mirrored to Jira). Cheap to add to the pipeline; valuable for "external user-reported bug" classification.
- [ ] Write `scripts/pull_tickets.py` --- single script, paged JQL, gzip output.
- [ ] Draft the labeling codebook before any hand-labeling begins; circulate to Jeff for review.
