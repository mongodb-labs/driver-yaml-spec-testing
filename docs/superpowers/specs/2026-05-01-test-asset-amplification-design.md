---
title: Test-Asset Amplification Factor --- Design Spec
date: 2026-05-01
status: draft
---

# Test-Asset Amplification Factor

## Context

This is Proposal C from `CLAUDE.md`: a "cheap, vivid" quantitative measurement for the ISSRE 2026
resubmission of *The Polyglot's Dilemma*. The goal is a punchy leverage number for the abstract and
a short paper section making two related claims:

1. **Amplification claim**: a single YAML test file, written once, is exercised by all 12 drivers.
   The cost model for YAML-based testing (runner + data corpus) compares favorably to the
   per-driver cost of idiomatic native tests.
2. **Maintenance burden claim**: the pre-YAML native operation tests are fragile imperative code
   that churns when driver internals change. Post-YAML runners test the stable public API and churn
   only with spec evolution. This is measurable via git log.

## Baseline: the Java driver

Focus on the Java driver (`mongo-java-driver`) because:

- It is old enough to predate any YAML-based testing, making the counterfactual concrete.
- The `com.mongodb.internal.operation` test suite (`driver-core`) was the main integration testing
  strategy pre-YAML: it tested operations at the internal layer so that both sync and async front-ends
  were covered without duplication at the public API layer.
- That suite became largely redundant after YAML-based testing arrived but was not removed, because
  determining which assertions were still load-bearing was too costly. It therefore serves as a
  preserved artifact of "what one driver needed before the shared corpus existed."

**YAML adoption date for Java driver**: 2015-03-06 (commit `7b96881e60`, "Implemented CRUD Spec
tests"). This is the pre/post split for churn analysis.

## Cost model

Three layers, each measured separately:

| Layer | Java LOC (current) | Nature |
|---|---|---|
| Operation tests (`*/internal/operation*`) | ~15,400 (58 files) | Imperative; Groovy/Spock; breaks on internal refactoring |
| Unified test runner (`driver-sync/.../unified/` + reactive-streams adapter) | ~9,400 (8,610 + 812) | Imperative; tests stable public API; changes track spec evolution |
| YAML corpus (specs repo, all drivers) | ~124,000 | Declarative data; no logic; shared across all 12 drivers |

Key distinction: YAML is *data*, not code. Comparing raw YAML LOC to native LOC is misleading.
The runner is the real per-driver infrastructure cost; YAML lines are a shared data cost amortized
across 12 drivers.

**Marginal cost per new test:**
- Pre-YAML: write N lines of imperative test code per driver. 12 drivers = 12N lines.
- Post-YAML: write N lines of YAML data once. Runner delta ≈ 0 for most new tests.

**Lower-bound amplification estimate**: the Java operation suite (~15k LOC) represents one driver's
pre-YAML integration test burden. Across 12 drivers that would be ~180k LOC of fragile imperative
code. The post-YAML arrangement replaces that with some LOC of runners (one per driver; Java's is ~9,400
across driver-sync and reactive-streams, Python's is ~1,600, Go's is ~10,000) plus 124k LOC of
shared YAML data --- and the YAML data is qualitatively different: no logic, no logic bugs, no
internal-API coupling.

The vivid abstract number: "one line of YAML exercises 12 drivers."

## Claim 1 --- Amplification factor

### Data to collect

1. **Operation test LOC**: already measured. 58 files, ~15,400 LOC under
   `driver-core/src/test/*/com/mongodb/internal/operation/`.
2. **Unified runner LOC**: ~9,400 LOC total. driver-sync `unified/` package: 8,610 LOC across all
   `.java` files (not just `Unified*.java` --- includes `Entities.java`, `EventMatcher.java`,
   `ContextElement.java`, etc.). Reactive-streams adapter: 812 LOC. The driver-sync package is the
   substantive runner; reactive-streams contains thin wiring to the sync adapter.
3. **YAML corpus LOC**: already known from the paper. ~124,000 lines, 606 files in the specs repo.
   Verify current count via `find` + `wc -l` on the specs repo.
4. **Pre-UTF old-format spec runner LOC** (optional, for historical depth): find any JSON-driven
   runners that predate the unified runner in `driver-core/src/test/functional/com/mongodb/client/`.
   `CrudTestHelper.java` is ~102 LOC; enumerate others.

### Narrative structure

- State the three-layer cost model as a table (runner + YAML data + per-driver historic test suites).
- Present the Java operation suite as the counterfactual.
- Give the "12 drivers × 15k LOC = 180k LOC avoided" number with an explicit caveat: the operation
  tests cover the pre-YAML era specs; post-YAML spec areas have no operation-test counterpart, so
  180k understates the true saving.
- State the marginal-cost argument: runner is amortized; each new spec test costs YAML data only.

## Claim 2 --- Maintenance burden

### Data to collect

Mine the Java driver git log (`mongo-java-driver`) for:

1. **Monthly commit count touching operation test files** (pre- and post-2015-03-06):
   ```
   git log --oneline --after="YYYY-MM-DD" --before="YYYY-MM-DD" \
     -- "*/internal/operation*Specification*" "*/internal/operation*Test*"
   ```
   Aggregate by month. Plot as a time series with 2015-03-06 marked.

2. **Monthly commit count touching the unified runner** (post-runner-introduction):
   ```
   git log --oneline -- "*/client/unified/Unified*.java"
   ```
   Aggregate by month.

3. **Monthly commit count touching YAML corpus** (in the specs repo):
   Count commits to `source/` touching `*.json` or `*.yaml` files, by month.

### Hypothesis

- Operation test churn is high and variable pre-2015 and remains non-zero post-2015, driven by
  internal refactoring (Spock mock updates, sync/async duplication maintenance).
- Unified runner churn is lower and follows a step-function pattern tied to spec evolution, not
  driver internals.
- YAML corpus churn reflects feature additions and spec corrections --- meaningful signal, not noise.

### Qualitative supplement

One paragraph explaining *why* the operation tests are fragile, using concrete examples:

- They test the internal operation layer (pre-4.0 this was the public API; post-4.0 it is purely
  internal), so any internal refactoring forces test updates.
- Groovy/Spock mocks of internal collaborators break whenever those collaborators' interfaces change.
- Sync and async paths are tested separately, creating duplication (partially hidden by Spock's
  `where:` tables but still real maintenance surface).
- Correctness is asserted via server-side effects rather than command monitoring, so wire-protocol
  conformance is not directly verified.

YAML-based tests avoid all four: they target the stable public client API, carry no mock logic,
run once against both sync and async via an adapter, and express expected commands declaratively.

## Concrete examples (graduated complexity)

Use three operation test files as a graduated illustration, showing that complexity scales with
the operation --- and that the YAML equivalent is comparably expressive at every level.

| Complexity | Java file | Java LOC | Role |
|---|---|---|---|
| Simple | `FindOperationSpecification.groovy` | 713 | Basic query; single return path |
| Medium | `AggregateOperationSpecification.groovy` | 495 | Pipeline; cursor handling |
| Complex | `MixedBulkWriteOperationSpecification.groovy` | 1,253 | Multiple write models; error aggregation; ordering |

For each:
- Show a short excerpt illustrating the Groovy/Spock pattern (mock setup, `where:` table, or
  server-side-effect assertion).
- Show the equivalent YAML test (from the CRUD or aggregation spec) and its LOC.
- One sentence annotating what boilerplate the YAML eliminates.

The bulk write example is particularly useful: `MixedBulkWriteOperationSpecification.groovy` at
1,253 LOC is the largest single file in the suite, and bulk write has meaningful YAML coverage in
the specs repo, making the side-by-side concrete.

## Rust driver comparison (positive control)

The Rust driver (`mongo-rust-driver`) started in January 2018 --- three years after the YAML corpus
existed --- and was designed from the start to rely on it. This makes it a natural "positive
control" for the Java counterfactual.

### What Rust has

| Layer | LOC | Nature |
|---|---|---|
| Native integration tests (public API) | ~7,600 | Idiomatic Rust (`#[tokio::test]`); targets gaps not in YAML |
| Spec runner (unified + legacy runners) | ~13,100 | Runs YAML/JSON corpus; more complete than Java's |
| CRUD unified test data (local copy from specs) | 164 JSON files | Synced from specs repo; run via unified runner |

### What Rust does not have

No internal-operation-layer test suite analogous to `com.mongodb.internal.operation`. Rust tests
CRUD comprehensively through the unified test runner against 164 JSON files synced from the shared
specs corpus (`spec/crud/unified/`).

Its native tests (`coll.rs` at 1,319 LOC / 38 tests, `bulk_write.rs` at 544 LOC / 8 tests,
`cursor.rs` at 291 LOC / 7 tests) deliberately target behaviors the shared corpus does not cover:

- **Batching and wire-protocol limits**: `large_insert_*`, `max_write_batch_size_batching`,
  `max_message_size_bytes_batching`, `namespace_batch_splitting`, `insert_many_document_sequences`
- **Error-detail structure**: `insert_err_details`, `write_error_batches`, `too_large_client_error`,
  `unsupported_server_client_error`
- **Rust-specific type/serde behavior**: `invalid_utf8_response`,
  `configure_human_readable_serialization`, `aggregate_with_generics`
- **Async cursor lifecycle**: `kill_cursors_on_drop`, `no_kill_cursors_on_exhausted`,
  `batch_exhaustion`, `cursor_final_batch`
- **Option propagation smoke tests**: `find_allow_disk_use_*`, `delete_hint_*`
- **Basic operation smoke tests**: `count`, `find`, `update`, `delete`, `aggregate_out`

The last two categories are the only ones that overlap with what the YAML corpus tests, and they are
shallow single-case checks, not comprehensive option/behavior coverage. The YAML corpus carries that
weight entirely.

Also notable: Rust has no old-format pre-UTF spec runner. Its CRUD tests skip the intermediate
stage that Java went through (JSON-powered per-spec runners) and land directly in the unified
runner. This is the clearest illustration of what "building post-YAML" looks like.

### The comparison

| | Java | Rust |
|---|---|---|
| Driver era | Pre-YAML (history from ~2011) | Post-YAML (started Jan 2018) |
| Internal operation tests | 15,400 LOC | None |
| Native public-API tests | Included above | ~7,600 LOC (edge cases only) |
| Spec runner | ~9,400 LOC (sync + reactive adapter) | ~13,100 LOC |
| CRUD test strategy | Old-format JSON runner + UTF unified runner | UTF unified runner only (164 JSON files from shared corpus) |

The contrast is the core argument: Java had to build comprehensive integration tests from scratch
because no shared corpus existed; it now carries that test suite as technical debt. Rust inherited
the corpus on day one and spent its testing budget on gaps --- error paths, Rust-specific async
behavior, batching edge cases --- rather than reimplementing what the corpus already verifies.

**On runner LOC disparity**: Rust's runner (13,100 LOC) is larger than Java's (9,400 LOC) despite
covering the same spec surface area. This is attributable to Rust's language verbosity relative to
Java --- explicit lifetimes, async machinery, match exhaustiveness --- not to a broader
implementation. The paper should note this to preempt the reader inferring that post-YAML runners
are inherently more expensive.

### What to investigate

Whether Rust's corpus-only CRUD approach left any coverage gaps that affected users:
- Check Rust Jira (RUST project) for CRUD conformance bugs not caught by the YAML corpus --- this
  would be evidence the corpus is insufficient, not that it is amplifying.
- Rust's local CRUD data (164 files) is a synced copy from the specs repo, not bespoke tests, so
  any gap in the shared corpus is also a gap for Rust. This is the same gap Java's operation tests
  partially fill --- making the comparison sharper.

## Scope and caveats to state in the paper

- The Java driver is the pre-YAML representative; other pre-YAML drivers (C, C++, Ruby, Python)
  likely have analogous native test suites, but are not measured here.
- The operation tests and YAML corpus do not cover identical spec areas: operation tests are denser
  for older CRUD options; YAML tests cover post-2015 specs with no operation-test counterpart.
  This means 15k LOC is a lower bound on the per-driver native test burden.
- LOC is an imperfect proxy; the qualitative distinction (imperative vs. declarative data) matters
  as much as the count.
- The Rust runner (13,100 LOC) is larger than Java's (5,400 LOC) partly because Rust implements
  more of the spec runner surface; this should be noted to avoid the misleading implication that
  post-YAML drivers have smaller runners.

## Output artifacts

- A short paper section (400--600 words + two tables + one figure) covering both claims and the
  Rust comparison.
- Table 1: three-layer cost model (Java).
- Table 2: Java vs. Rust side-by-side.
- The figure: monthly commit churn time series for Java operation tests vs. unified runner,
  2012--2025, with 2015-03-06 annotated.
- The concrete examples: three inline excerpts (Find / Aggregate / BulkWrite), ≤ one column total.
