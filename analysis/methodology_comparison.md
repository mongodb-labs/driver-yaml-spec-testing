# Do YAML spec tests reduce nonconformance bugs in drivers?

## Methodology comparison

A 17-method comparison of approaches to test the hypothesis that the
introduction of YAML spec tests in a (driver, spec) cell reduces
subsequent nonconformance bug filings.

---

## TL;DR

Three signals point clearly in the *predicted* direction:

1. **M2 spike-then-decay around first sync** — bug-filing rate jumps **2.5×**
   in the 4 months after a (driver, spec) first acquires test files
   (0.13 vs 0.05 pre-sync), then decays back toward baseline over ~3 years.
   This is unambiguous: tests reveal latent bugs at the moment they're
   synced.
2. **M9 pre/post coverage saturation** — for 11 of 14 spec areas with
   long histories, the per-(driver, month) bug rate is **substantially lower
   after** the spec's coverage saturated (≥80% of eventual file count) than
   before. The drop ranges from −9% (sessions) to −100% (CSE). This is the
   strongest single visual signal in the analysis.
3. **M16 per-spec yearly aggregate** — for the older specs (crud,
   server-selection, sdam, connection-string, read-write-concern, bson-
   corpus, gridfs), yearly bug counts peak in the year-or-two **before**
   coverage saturates and decline as coverage grows. This is the
   inverse-correlation we'd expect if tests work.

Three signals point in the *opposite* direction (tests correlate with more
bugs, not fewer):

4. **M4 / M5 dose-response** — cells with more test files do *not* have
   monotonically lower bug rates. Cells with 1-4 files actually have
   higher rates than cells with 0. The "0 files" bucket is dominated by
   (driver, spec, month) cells where the spec hasn't yet been
   implemented at all (e.g. RUST-2010 cells), which mechanically have 0
   bugs. Once we restrict to cells where the spec is being implemented,
   the dose-response is roughly flat.
5. **M17 within-spec, within-calendar-month** — for 9 of 14 spec areas,
   driver cells *with* tests in a given calendar month have **higher** bug
   rates than driver cells *without* tests in the same month. CRUD is the
   one striking exception: untested cells have **2.3× higher** rate than
   tested cells.
6. **M10 sync-lag scatter** — late-syncing drivers do not file
   measurably more bugs in their cells than early-syncing drivers
   (Pearson r = 0.01). Driver size dominates the y-axis here.

Two signals are ambiguous / weak:

7. **M1 event study (raw)**, **M12 driver-detrended event study**,
   **M13 long-run windows** — bug rate at +36..+59 months after sync is
   30% above pre-sync, not below. Slow decay, but no convincing dip below
   baseline.
8. **M3 pre/post ratio histogram** — across 263 (driver, spec) cells with
   sufficient pre/post coverage, 46 show a decline post-sync, 102 are
   roughly unchanged, 115 show an increase. Median log-ratio is ~0.

---

## What is the cleanest case for "tests prevent bugs"?

**M9 (saturation) and M16 (per-spec yearly).** Both look at the *spec
area* as the unit and compare bug rates before vs after the spec's test
coverage matured. The pattern is consistent across most specs: peak bug
filings precede or coincide with coverage growth, then drop sharply as
coverage saturates.

The chief confound for this story is **spec maturity confound**: every
spec passes through an implementation phase (high bugs) and a maintenance
phase (low bugs) regardless of whether tests are added; tests just happen
to land during the implementation phase. M9 / M16 cannot distinguish
"tests caused the decline" from "the decline would have happened anyway."

The next chart that would actually nail down causation is **M17**'s
within-spec, within-calendar-month comparison **but for matched
implementation phases**, e.g. comparing driver A (tests synced) and driver
B (tests not synced) at the *same point in driver A's and driver B's
implementation lifecycle*. We don't have a clean "implementation
lifecycle" measure per (driver, spec).

---

## Methods, in order of how strongly they support the hypothesis

### Strong support

#### M9 — Per-spec coverage-saturation pre/post
*Plot: data/plots/m9_saturation.png*

For each spec area, find the calendar month when the total file-count
across all drivers first reached ≥80% of its eventual peak ("saturation
date"). Compare mean N-bugs/(driver-month) cell before vs after.

Result: Across the 14 most-bug-heavy specs, **11 saw a post-saturation
decline**. The largest:
- crud: 0.173 → 0.027 (−84%, 241 vs 13 bugs)
- server-selection: 0.168 → 0.018 (−89%, 232 vs 9)
- sdam: 0.165 → 0.075 (−54%, 210 vs 45)
- read-write-concern: 0.124 → 0.036 (−71%, 142 vs 26)
- gridfs: 0.040 → 0.011 (−72%, 67 vs 2)
- CSE: 0.025 → 0.000 (−100%, 45 vs 0)

The 3 exceptions (post > pre) are auth, transactions, and retryable-writes
— all specs where coverage saturated relatively early (large initial test
drop) so the post-saturation period is also when many drivers were still
implementing the spec.

**Confound**: this is a calendar-time before-vs-after, with the same
calendar-time confound as M6 / M16. Drivers also matured over time.

#### M2 — Spike-then-decay window around first sync
*Plot: data/plots/m2_spike_window.png*

For each (driver, spec) cell with a first sync, bin the 73-month event
window around sync date into 5 chunks and compute the mean monthly bug rate
in each.

Result (n=315 cells):
| window | mean bugs/cell-month |
|---|---:|
| −36..−13 | 0.038 |
| −12..−1 | 0.051 |
| **0..+3** | **0.127** ← spike |
| +4..+15 | 0.077 |
| +16..+36 | 0.072 |

The spike is large (2.5× the immediate pre-sync rate) and well-localized.
After the spike, the rate stays elevated for ~3 years before approaching
the pre-sync level (M13 shows the +36..+59 window at 0.055 vs pre 0.042).

**Reading**: tests reveal latent bugs that would have stayed under the
radar otherwise, then the rate decays as the test-revealed backlog clears.
Whether the long-run rate would have been higher *without* tests is not
directly observable here.

#### M16 — Per-spec yearly bugs vs cumulative file-count
*Plot: data/plots/m16_per_spec_correlation.png*

12-panel grid; each panel is one spec; red bars = N-bugs per year, blue
line = total file-count across drivers at year-end. Inverse-correlation
visible for ~7 specs (crud, server-selection, sdam, read-write-concern,
bson-corpus, connection-string, sessions, transactions).

**Confound**: each spec has its own implementation lifecycle independent
of tests, so the inverse correlation is consistent with both the
"tests reduced bugs" hypothesis and the null "drivers matured" hypothesis.

### Mixed / inconclusive

#### M1 — Event study by months-relative-to-first-sync
*Plot: data/plots/m1_event_study.png*

Smoothed mean bugs/cell-month vs months relative to first sync (n=315
cells). Pre-sync: ~0.04; spike at 0..+5: ~0.13; gradual decline back to
~0.04 by month +60.

Long-run rate eventually returns to pre-sync, but the area under the curve
post-sync is well above pre-sync due to the spike. So "tests reveal bugs"
is supported, "tests prevent bugs in the long run" is not strongly
supported by the raw event study.

#### M11 — Synced vs unsynced cells, by year
*Plot: data/plots/m11_share.png*

Top panel: bug counts per year, stacked by whether (driver, spec, month)
cell had test files. Pre-2014, all bugs were in untested cells. The
tested-cell share grows alongside test adoption. From 2018 onward, most
bugs come from cells that had at least one test file.

Bottom panel: per-cell rate. Tested-cell rate spiked to 0.32 in 2015 then
declined steadily to 0.01 by 2025. Untested-cell rate stayed roughly flat
~0.03 throughout. Consistent with M9: as test coverage matures across the
ecosystem, the rate of new bug filings in tested areas drops.

#### M12 — Driver-detrended event study
*Plot: data/plots/m12_detrended.png*

Subtract each (driver, year)'s overall mean bug rate from each cell, then
align to first-sync. Removes driver-specific calendar effects.

Result: pre-sync residual is slightly negative (−0.003), post-sync stays
positive (+0.04), declining slowly to ~+0.01 by month +60. Even after
detrending, post-sync rate stays above the driver's typical rate for years.
Consistent with sustained bug-discovery effect, not sustained bug-
prevention.

#### M15 — Spec-detrended event study
*Plot: data/plots/m15_spec_detrended.png*

Like M12, but subtract the spec's mean bug rate that calendar month across
peer drivers. Isolates "this driver, in this spec, vs peers at the same
moment". Pre-sync residual ≈ 0; post short-term residual +0.010; post
long-term +0.007. Tested drivers do slightly worse than peer drivers in
the same spec at the same time — consistent with bug-discovery, not
prevention.

#### M14 — Per-spec event study, broken out
*Plot: data/plots/m14_per_spec_event.png*

12 panels, one per spec, each averaging bug rate across drivers around
that spec's first sync. CRUD shows a clean peak-then-decay from ~0.3 to
~0.05 over 60 months. read-write-concern and server-selection show
similar declines. Transactions shows a delayed peak around +20 months
then declines. Several smaller specs (max-staleness, command-monitoring)
have insufficient bug volume for a clean signal.

The per-spec view is more informative than the all-spec aggregate (M1)
because the relative magnitude of the spike vs the long-run rate varies
substantially across specs.

#### M13 — Long-run rate windows
*Plot: data/plots/m13_longrun.png*

Five windows pre/spike/early/mid/late around first sync. Late window
(+36..+59 months) is 0.055, only 30% above pre-sync (0.042). Slow decay,
but does not go below pre-sync.

### Weak or null

#### M4 / M5 — File-count and line-count dose-response
*Plots: data/plots/m4_files_dose-response.png, m5_lines_dose-response.png*

Bin (driver, spec, month) cells by test-asset volume; compute mean bug
rate per bin.

The rate at "0 files" is **lower** than at "1+", because the 0-file bin is
heavily populated by cells where the spec is not yet relevant to the
driver (e.g. RUST in 2010, NODE pre-2014 SDAM). These cells mechanically
have 0 bugs because no implementation exists.

**Within the non-zero coverage range**, the relationship is non-monotonic
and weak. So neither files nor lines is a strong predictor of low bug
rate. The user's hypothesis that "files might correlate better than lines"
isn't supported by this slice — both metrics produce similar (flat-ish)
dose-response curves.

#### M17 — Within-spec, within-calendar-month tested vs untested
*Plot: data/plots/m17_within_spec_cal.png*

For each (spec, calendar-month) where some drivers have tests and some
don't, compare bug rates. For 9 of 14 specs, tested cells have *higher*
rates than untested cells in the same month. CRUD is a striking
exception: untested 0.353, tested 0.155 (61 bugs in tested cells, 71 in
untested).

Reading: in most specs, having tests *correlates* with filing more bugs,
because the same drivers that sync tests are also the drivers actively
implementing & exercising the spec. Tests are filed *because* the
implementation activity surfaces issues, not as a pre-emptive measure.

CRUD's reverse pattern is interesting: it's the spec where tested-but-
buggy is rarer than untested-buggy in the same window. CRUD has the
largest test corpus by far (255 N-bugs, ~190 spec test files, 19,644 spec
YAML lines), so this is the spec with the most test coverage for the
longest time, and it's the one where the prevent-not-just-detect signal
shows up.

#### M10 — Sync-lag vs total bugs
*Plot: data/plots/m10_sync_lag.png*

For each (driver, spec) pair: x = lag between earliest first-sync (across
all drivers) and this driver's first sync; y = total bugs filed in that
cell. Pearson r = 0.01, slope 0.005. Late-syncers do not have measurably
more bugs than early-syncers.

This is the cross-driver test that should support the hypothesis if tests
were strongly causal. It doesn't. Plausible reasons:
- Driver size dominates (big drivers have more bugs and sync faster)
- Sync timing is endogenous (drivers sync when they need to, not when
  they should)
- The hypothesis is wrong at the cross-driver level

#### M3 — Pre/post log-ratio histogram per cell
*Plot: data/plots/m3_pre_post.png*

For each (driver, spec) cell with sufficient pre and post months, compute
log(post-rate + ε) − log(pre-rate + ε). Distribution of this log-ratio is
roughly symmetric around 0: 46 cells decreased, 102 unchanged, 115
increased.

A strong "tests prevent bugs" effect would shift this distribution
left; instead it's centered. The marginal cell shows no aggregate effect.

---

## What confounds the analysis most?

In rough order of severity:

1. **Spec maturity confound**. Specs naturally have an
   implementation-phase peak in bugs, then decline. Tests are added
   during implementation. So "tests added" and "spec matures" are
   collinear. Most of the visual signals (M9, M11, M16) are consistent
   with both "tests caused the decline" and "the decline would have
   happened anyway".

2. **Bug-discovery vs bug-creation**. The classifier sees ticket creation
   dates, but the underlying *bug introduction* date is unobserved. A
   bug filed in 2019 may have been latent since 2014. Tests synced in
   2019 don't prevent that bug; they discover it. Our M2 spike is the
   discovery signal. We can't distinguish "would have been filed
   anyway" from "would never have been noticed."

3. **Driver-size confound**. Bigger driver projects have more bugs and
   tend to sync tests earlier. Both axes are dominated by driver size,
   making M10 and M17 hard to interpret.

4. **JSON-vs-YAML inflation**. Drivers that store both formats have
   inflated line counts (2× the real test surface). This biases line-count
   dose-response (M5) and any cross-driver comparison using line counts.
   File-count is more layout-invariant.

5. **Submodule transition for JAVA / GODRIVER / PHPLIB**. These drivers
   show a sudden drop in local test asset counts when they switched to
   submodule-based syncing. Our combined max(copy, submodule) metric
   smooths this but doesn't eliminate the artifact entirely.

6. **Issue-split spec rollouts**. Many spec areas land in driver repos as
   coordinated DRIVERS-XXX issue splits. A bug filed against the same
   issue-split in driver D may technically be a "(spec_area, D, T)" event
   that coincides exactly with the sync date. Our N-gate prompt filters
   most issue-splits to `not_relevant`, but residual ambiguity is
   unavoidable.

---

## What would make the case airtight?

A direct test would require:
1. **A counterfactual sample**: drivers that *could* have synced tests but
   didn't. The closest natural experiment is HHVM (driver retired before
   spec tests were widespread) and MGO (older Go driver, no tests).
   Their bug rates are within the same order of magnitude as the bigger
   drivers, but the samples are too small to do anything quantitative.
2. **Bug-introduction dates**, not just bug-filing dates. Would let us
   distinguish "tests prevented this bug" from "tests revealed this
   pre-existing bug".
3. **Per-driver implementation-phase markers** independent of test
   sync. Hard to derive from public Jira metadata.

---

## Recommendation for the paper

Use **M9 (saturation) and M2 (spike-then-decay)** as the headline charts.
They tell a coherent story:
- Tests reveal latent bugs when first synced (the spike: tests as a
  bug-detection mechanism).
- Once test coverage saturates for a spec area, bug filings drop
  substantially (the decay: tests stabilize the spec).
- Caveat: maturity confound; some of the decline would have happened
  anyway as drivers matured.

Use **M14 per-spec breakouts** to show the effect varies by spec — CRUD,
server-selection, read-write-concern show the cleanest patterns; some
smaller specs are too noisy.

Use **M11** to show the ecosystem-level trend: in the 2010s most bugs
were in untested cells; by 2024 most bugs are in tested cells, and the
per-cell rate in tested cells dropped 30× over a decade.

Avoid overstating: M10 (sync-lag) and M17 (within-month tested vs
untested for non-CRUD specs) do *not* support the hypothesis cleanly.
The honest framing is "tests reveal bugs and reduce them over the long
run" rather than "tests prevent bugs from ever being filed".

---

## Files produced by this analysis

| File | Method | What it shows |
|---|---|---|
| `data/panel.csv` | (input) | 69,190 rows of (driver, spec, month) cells with bug counts and test asset counts |
| `data/plots/m1_event_study.png` | M1 | Event study by months relative to first sync |
| `data/plots/m2_spike_window.png` | M2 | 5-window spike-then-decay around first sync |
| `data/plots/m3_pre_post.png` | M3 | Per-cell pre/post log-ratio distribution |
| `data/plots/m4_files_dose-response.png` | M4 | Bug rate by file-count bin |
| `data/plots/m5_lines_dose-response.png` | M5 | Bug rate by line-count bin |
| `data/plots/m6_per_spec.png` | M6 | Per-spec yearly N-bugs vs file-count |
| `data/plots/m7_decile_n_files.png` | M7 | Decile scatter (files) |
| `data/plots/m7_decile_n_lines.png` | M7 | Decile scatter (lines) |
| `data/plots/m8_within_driver.png` | M8 | Within-driver synced vs unsynced |
| `data/plots/m9_saturation.png` | M9 | **Pre/post coverage saturation per spec** |
| `data/plots/m10_sync_lag.png` | M10 | Sync lag vs total bugs scatter |
| `data/plots/m11_share.png` | M11 | Yearly bug counts split by tested/untested |
| `data/plots/m12_detrended.png` | M12 | Driver-detrended event study |
| `data/plots/m13_longrun.png` | M13 | Long-run rate windows |
| `data/plots/m14_per_spec_event.png` | M14 | Per-spec event study (12 specs) |
| `data/plots/m15_spec_detrended.png` | M15 | Spec-detrended event study |
| `data/plots/m16_per_spec_correlation.png` | M16 | Per-spec yearly bugs vs file-count, 12 panels |
| `data/plots/m17_within_spec_cal.png` | M17 | Within-spec, within-calendar tested vs untested |
| `data/methodology_results.json` | M1–M8 | Raw numeric outputs |
| `data/methodology_results_extra.json` | M9–M13 | Raw numeric outputs |
| `data/methodology_results_per_spec.json` | M14–M17 | Raw numeric outputs |
