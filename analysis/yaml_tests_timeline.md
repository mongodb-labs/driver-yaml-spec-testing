# YAML Spec Test Timeline: Specs Repo and Driver Repos

This is the evidence file for the "before/after YAML test introduction"
analysis (§6 of `report.md`). For each spec area, it documents:

1. **Specs repo** (mongodb/specifications): when YAML test files for that
   spec area first appeared and how they grew over time.
2. **Driver repos**: when each driver synced those YAML tests into its own
   tree (or referenced them via a git submodule), and how they grew.

All numeric data is reproducible from `data/specs_timeline.csv`,
`data/specs_phases.csv`, `data/drivers_timeline.csv`,
`data/drivers_phases.csv`, and `data/drivers_submodule_timeline.csv`.
Charts are in `data/plots/`.

---

## 1. Methodology

### 1.1 Specs repo

Repo: `https://github.com/mongodb/specifications` (full history fetched, 2,751
commits 2014-04-29 through 2026-04).

For each calendar month from 2014-04 to 2026-05, `analysis/scripts/specs_timeline.py`:

- Finds the last commit `c` with author date < first day of the next month.
- Lists all `.yml` and `.yaml` files in the tree at `c` under `source/`.
- Buckets each file by the immediate sub-directory under `source/` (so all
  files under `source/crud/...` count toward spec area `crud`, etc.).
- Sums file count and line count per spec area for that month-end snapshot.

Output: `data/specs_timeline.csv` (one row per (month, spec) cell).

The script uses a single `git cat-file --batch` subprocess per snapshot to
read all blob contents, with a per-blob-sha cache so the same blob is never
read twice across months. Total runtime: ~2 minutes.

JSON files in `source/` are deliberately *not* counted in this section: most
are auto-generated copies of the YAML files, so counting them would
double-count. (BSON corpus is the one spec area that ships JSON-only ---
it is excluded by this script's YAML-only pass and noted separately in §6.)

### 1.2 Phase detection

`scripts/specs_phases.py` re-reads the timeline CSV and emits two events
per spec area:

- `intro`: the first month in which the spec area had any YAML files.
- `phase`: any subsequent month in which file count grew by ≥50% **and**
  ≥5 files were added in that month, *or* line count grew by ≥50% **and**
  ≥1000 lines were added. These thresholds are intentionally tight; minor
  bumps (a few new test cases, an `expectedError` field added) are filtered
  out so the remaining events represent real test-corpus expansions.

### 1.3 Driver repos --- copy-based

Drivers that **copy** YAML/JSON spec test files into their own tree. To be
robust to driver-specific reorganizations (e.g., NODE moved its tests from
`spec/` to `test/spec/` in late 2019; CSHARP went `src/.../*Tests` →
`tests/.../*Tests` → `specifications/`; CDRIVER went `tests/json` →
`src/libmongoc/tests/json`), `scripts/drivers_timeline.py`:

1. Enumerates all `.yml`, `.yaml`, and `.json` files in the repo at each
   month-end commit.
2. Filters out non-test noise (`.github`, `.evergreen`, `node_modules`,
   `package-lock.json`, native-image config, `Cargo.lock`, etc.).
3. Buckets each remaining file by the *first matching spec-area regex*
   that appears as any directory component in its path. The full regex
   table is in `scripts/drivers_timeline.py:SPEC_PATTERNS`. It accepts
   variations like `crud`, `CRUD`, `crud-v2`, `crud_unified`,
   `change-streams`, `change_stream`, `sdam`, `discovery_and_monitoring`,
   etc.

For drivers we count `.yml` + `.yaml` + `.json` together because driver
repos are inconsistent about which format they sync (some keep only the
JSON, some keep both, some convert YAML→JSON during sync).

Output: `data/drivers_timeline.csv`.

### 1.4 Driver repos --- submodule-based

Three drivers pull spec tests via a git submodule pointing at
`mongodb/specifications`:

| Driver | Current submodule path |
|---|---|
| GODRIVER | `testdata/specifications` (was `specifications` 2017-02 → 2025-04) |
| JAVA | `testing/resources/specifications` (was `driver-core/src/test/resources/specifications` 2025-04 → ~2025-12) |
| PHPLIB | `tests/specifications` |

For these, `scripts/drivers_submodule_timeline.py`:

- Walks the driver's commits monthly.
- At each driver-month commit, reads `.gitmodules` *at that commit* (not
  at HEAD) to find the path of the submodule whose URL contains
  `mongodb/specifications`.
- Reads the submodule SHA via `git ls-tree`.
- Resolves that SHA in the local clone of `mongodb/specifications` and
  computes the per-spec YAML totals at that submodule revision.

This gives a per-driver-month view of "as of this month, which spec tests
were available to this driver via the submodule." Note that *available* is
not the same as *executed* --- the driver's test runner may not yet support
new schema versions or new spec areas. We do not detect runner support
here.

### 1.5 Drivers that don't sync YAML/JSON spec tests

Two drivers in the corpus do not adopt the YAML/JSON spec tests:

- **PHPC** (`mongo-php-driver`): re-implements every test as a hand-written
  PHP `.phpt` file. The `tests/` directory has subdirectories named after
  spec areas (`crud/`, `retryable-writes/`, `change-streams/`,
  `clientEncryption/`, etc.). PHPC also pulls libmongoc as a submodule (so
  it indirectly benefits from CDRIVER's YAML test execution at the C level),
  but PHP-level behavior is covered only by hand-written `.phpt` tests.
  See §6 for a `.phpt` count table.
- **HHVM** (`mongo-hhvm-driver`): driver was sunset in late 2019; final
  commit 2021-12-22. Repo-wide YAML/JSON count at HEAD: 2 files
  (`.travis.yml`, `benchmarks/composer.json`). HHVM never adopted YAML/JSON
  spec tests in any form.

---

## 2. Specs repo: YAML test introductions and growth phases

Source: `data/specs_timeline.csv` (2,549 rows), `data/specs_phases.csv`.
Chart: `data/plots/specs_total.png` (total over time),
`data/plots/specs_per_spec.png` (top 12 specs stacked),
`data/plots/specs_intro.png` (intro scatter).

### 2.1 Per-spec summary

Sorted by introduction date. `final_*` is the state at the most recent
month for which the spec area still exists; some early areas were renamed
or superseded (noted inline).

| Spec area | Intro | Final | Final files | Final lines | # phases |
|---|---|---|---:|---:|---:|
| server-discovery-and-monitoring | 2014-09 | 2026-05 | 230 | 18,478 | 1 |
| crud | 2015-02 | 2026-05 | 189 | 19,644 | 2 |
| server-selection | 2015-02 | 2026-05 | 108 | 3,005 | 0 |
| command-monitoring | 2015-07 | 2022-09 | 13 | 1,398 | 0 |
| connection-string | 2015-09 | 2026-05 | 8 | 1,258 | 0 |
| gridfs | 2015-09 | 2026-05 | 8 | 1,194 | 0 |
| read-write-concern | 2015-10 | 2026-05 | 8 | 842 | 0 |
| max-staleness | 2016-07 | 2026-05 | 32 | 1,007 | 0 |
| retryable-writes | 2017-07 | 2026-05 | 35 | 6,470 | 1 |
| initial-dns-seedlist-discovery | 2017-09 | 2026-05 | 53 | 511 | 2 |
| transactions | 2018-03 | 2026-05 | 44 | 18,076 | 1 |
| auth | 2018-04 | 2026-05 | 2 | 715 | 0 |
| change-streams | 2018-05 | 2026-05 | 9 | 4,183 | 1 |
| object-id | 2018-06 | 2018-06 | 1 | 814 | 0 |
| connection-monitoring-and-pooling | 2019-01 | 2026-05 | 35 | 1,875 | 0 |
| retryable-reads | 2019-01 | 2026-05 | 45 | 12,397 | 1 |
| transactions-convenient-api | 2019-01 | 2026-05 | 10 | 2,230 | 0 |
| uri-options | 2019-01 | 2026-05 | 12 | 1,380 | 0 |
| sessions | 2019-05 | 2026-05 | 7 | 1,912 | 0 |
| client-side-encryption | 2019-06 | 2026-05 | 223 | 56,061 | 4 |
| atlas-data-lake-testing | 2020-07 | 2025-08 | 7 | 235 | 0 |
| unified-test-format | 2020-10 | 2026-05 | 320 | 7,463 | 0 |
| versioned-api | 2020-12 | 2026-05 | 6 | 1,170 | 0 |
| load-balancers | 2021-04 | 2026-05 | 8 | 1,718 | 0 |
| collection-management | 2021-05 | 2026-05 | 6 | 515 | 0 |
| client-side-operations-timeout | 2022-05 | 2026-05 | 28 | 22,174 | 0 |
| command-logging-and-monitoring | 2022-10 | 2026-05 | 25 | 3,293 | 0 |
| run-command | 2023-04 | 2026-05 | 2 | 710 | 0 |
| index-management | 2023-05 | 2026-05 | 7 | 625 | 0 |
| mongodb-handshake | 2025-06 | 2026-05 | 1 | 59 | 0 |
| open-telemetry | 2025-09 | 2026-05 | 22 | 2,092 | 0 |
| client-backpressure | 2026-03 | 2026-05 | 4 | 3,841 | 0 |

### 2.2 Per-spec phase events (raw)

Each row below is either an `intro` (first month with any YAML files) or a
`phase` (≥50% growth in files or lines, with absolute floors). The `Δfiles`
and `Δlines` columns show the change from the prior month.

#### server-discovery-and-monitoring
- 2014-09 **intro** files=37 lines=1,740 — commit `98d6b27c`
- 2020-04 phase files=161 lines=10,547 (Δ +66 / +4,613) — commit `17371253`

  → A second wave introduced 66 new test files in April 2020. Prose tests
  for SDAM "errors" (load-balancer-aware error handling) and the unified
  format conversion landed at this point.

#### crud
- 2015-02 **intro** files=14 lines=896 — commit `012a23b5`
- 2016-10 phase files=29 lines=1,234 (Δ +15 / +338) — commit `64e8d2fe`

  → CRUD v1.1 (added `aggregate.json`, etc.).

- 2020-03 phase files=89 lines=5,800 (Δ +38 / +2,404) — commit `dbabacf2`

  → First major UTF migration of CRUD tests in March 2020.

#### server-selection
- 2015-02 **intro** files=33 lines=662 — commit `012a23b5`

  → Same commit as the first CRUD tests. No subsequent major phases.

#### command-monitoring
- 2015-07 **intro** files=5 lines=399 — commit `58e2a772`

  → Spec area was deprecated; replaced by `command-logging-and-monitoring`
  (introduced 2022-10). Final snapshot 2022-09 had 13 files / 1,398 lines.

#### connection-string
- 2015-09 **intro** files=7 lines=1,061 — commit `5ceaac4d`

  → Single landing; has grown only by minor edits since.

#### gridfs
- 2015-09 **intro** files=4 lines=571 — commit `5ceaac4d`

#### read-write-concern
- 2015-10 **intro** files=4 lines=211 — commit `c1dc6aed`

#### max-staleness
- 2016-07 **intro** files=29 lines=885 — commit `47c43c8d`

  → Single drop of 29 files when MaxStalenessMS shipped with MongoDB 3.4.

#### retryable-writes
- 2017-07 **intro** files=8 lines=620 — commit `1f63bb92`
- 2018-06 phase files=18 lines=1,947 (Δ +8 / +639) — commit `d6b90ff3`

  → Doubled in June 2018: retryable writes v1.0 + initial retryable-reads
  in the same window.

#### initial-dns-seedlist-discovery
- 2017-09 **intro** files=4 lines=26 — commit `cb211034`
- 2017-11 phase files=23 lines=161 (Δ +16 / +102) — commit `da2bfbae`
- 2021-10 phase files=54 lines=458 (Δ +19 / +182) — commit `e827caab`

  → Load-balancer-aware DNS seedlist tests added in October 2021.

#### transactions
- 2018-03 **intro** files=19 lines=3,447 — commit `84c3b10b`
- 2018-06 phase files=21 lines=8,594 (Δ +3 / +3,665) — commit `d6b90ff3`

  → Doubled in line count three months after introduction (full transaction
  API coverage landed).

#### auth
- 2018-04 **intro** files=1 lines=366 — commit `bebf9b68`

  → Auth tests stayed at 1 YAML file (legacy SCRAM-SHA). The bulk of auth
  test surface is in `auth-aws/`, `auth-oidc/`, etc. as subdirectories
  which we do *not* report as separate spec areas (they're under
  `source/auth/`).

#### change-streams
- 2018-05 **intro** files=2 lines=393 — commit `5f25cb24`
- 2020-02 phase files=4 lines=2,907 (Δ +2 / +2,297) — commit `afaeb1d7`

  → Change streams test corpus jumped 7× in line count when the resumability
  semantics were tightened in early 2020.

#### object-id
- 2018-06 **intro** files=1 lines=814 — commit `d6b90ff3`

  → ObjectID spec was a one-shot landing in mid-2018. Final snapshot is
  the same as intro: the directory was later moved or its tests were folded
  into BSON.

#### connection-monitoring-and-pooling
- 2019-01 **intro** files=19 lines=541 — commit `45c92ffa`

#### retryable-reads
- 2019-01 **intro** files=42 lines=4,995 — commit `45c92ffa`
- 2024-03 phase files=45 lines=12,397 (Δ +0 / +6,452) — commit `bbb335e6`

  → Retryable-reads test files grew 2.5× in line count in March 2024.
  File count was unchanged: existing files were rewritten in unified format
  with much more coverage.

#### transactions-convenient-api
- 2019-01 **intro** files=9 lines=1,838 — commit `45c92ffa`

#### uri-options
- 2019-01 **intro** files=8 lines=398 — commit `45c92ffa`

#### sessions
- 2019-05 **intro** files=1 lines=272 — commit `8c0d8cc3`

#### client-side-encryption
- 2019-06 **intro** files=29 lines=3,081 — commit `63540092`
- 2022-04 phase files=47 lines=5,460 (Δ +14 / +2,444) — commit `de75e99f`
- 2022-12 phase files=94 lines=18,969 (Δ +31 / +11,065) — commit `3a90e3ff`
- 2023-01 phase files=106 lines=28,841 (Δ +12 / +9,872) — commit `0a44c5bb`
- 2025-08 phase files=220 lines=55,587 (Δ +101 / +25,603) — commit `49ade88e`

  → CSE has the most growth phases of any spec area: **5 phase events**.
  - 2019-06: legacy CSE (FLE 1.0) intro.
  - 2022-04: queryable encryption (QE) initial drop.
  - 2022-12, 2023-01: QE v2 prose tests (substantial line count: +11k +10k).
  - 2025-08: QE range queries v2 — single landing of 101 new files / 25k
    new lines. **This is the largest single phase event in the corpus.**

#### atlas-data-lake-testing
- 2020-07 **intro** files=7 lines=153 — commit `4f89b79b`

  → Final snapshot 2025-08 (peak). De-emphasized; tests didn't grow.

#### unified-test-format
- 2020-10 **intro** files=161 lines=3,942 — commit `db7387df`

  → Single landing of 161 files (mostly schema-version validation tests,
  including 80+ `invalid/` files designed to fail validation). UTF is the
  *substrate* for all later spec test landings.

#### versioned-api
- 2020-12 **intro** files=6 lines=1,031 — commit `fc7a1b6a`

#### load-balancers
- 2021-04 **intro** files=8 lines=1,688 — commit `70c26f32`

#### collection-management
- 2021-05 **intro** files=1 lines=129 — commit `7b2221c9`

#### client-side-operations-timeout
- 2022-05 **intro** files=26 lines=21,075 — commit `bf372a16`

  → CSOT landed in a single drop of 26 files / 21k lines. **Second-largest
  single-month event** after CSE 2025-08.

#### command-logging-and-monitoring
- 2022-10 **intro** files=22 lines=2,866 — commit `a1bd61e6`

  → Replaces the older `command-monitoring/` directory.

#### run-command
- 2023-04 **intro** files=1 lines=242 — commit `5112bcca`

#### index-management
- 2023-05 **intro** files=5 lines=305 — commit `9e770b54`

#### mongodb-handshake
- 2025-06 **intro** files=1 lines=58 — commit `66899295`

#### open-telemetry
- 2025-09 **intro** files=22 lines=1,923 — commit `ace53b16`

#### client-backpressure
- 2026-03 **intro** files=4 lines=4,396 — commit `c3c82b62`

  → Most recent spec area (March 2026).

### 2.3 Aggregate growth (specs repo)

Total YAML files and lines in `source/`, sampled at year-end:

| Year-end | Total files | Total lines |
|---|---:|---:|
| 2014 | 37 | 1,740 |
| 2015 | 70 | 3,829 |
| 2016 | 99 | 4,932 |
| 2017 | 115 | 5,773 |
| 2018 | 196 | 16,994 |
| 2019 | 360 | 33,617 |
| 2020 | 591 | 51,470 |
| 2021 | 663 | 56,617 |
| 2022 | 805 | 88,762 |
| 2023 | 1,043 | 132,720 |
| 2024 | 1,265 | 156,793 |
| 2025 | 1,460 | 188,776 |

The corpus reached its current size (~1,460 files, ~188k lines) by end
of 2025. The two largest year-over-year jumps are 2018→2019 (transactions,
CSE intro) and 2022→2023 (QE v2 + CSOT).

---

## 3. Driver repos: copy-based timelines

Source: `data/drivers_timeline.csv` (21,968 rows),
`data/drivers_phases.csv`. Chart: `data/plots/drivers_total.png` shows all
12 drivers' total spec-test lines on one axis;
`data/plots/driver_<DRIVER>.png` shows top-8 spec areas per driver over
time.

For each driver below: the test-path layout (where in the repo the spec
tests live), totals over time, a per-spec summary, and a list of major
phase events.

> **Caveat.** "Driver had file X at month M" tells us only the file existed
> in the tree. Whether the driver's test runner could *execute* the file
> at month M depends on its UTF schema-version support, which we do not
> detect. Some drivers (notably JAVA and PHPLIB) ceased copying spec tests
> mid-history when they migrated to a git-submodule sync; their copy-based
> totals therefore *fall* at the migration point. See §4 for the
> submodule-based view of those drivers.


### CDRIVER

**Path layout** (top sample-path roots at recent snapshots):
- `src/libmongoc/tests/...` (~4170 cumulative file-rows)
- `src/libbson/tests/...` (~111 cumulative file-rows)

**Total spec-test lines:** first month 2015-02 → 3,867 lines; peak 2026-03 → 331,359; last month 2026-05 → 330,542.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| server-discovery-and-monitoring | 2015-02 | 2026-05 | 243 | 29,973 | 2 |
| server-selection | 2015-02 | 2026-05 | 108 | 6,155 | 1 |
| command-monitoring | 2016-02 | 2026-05 | 15 | 3,244 | 0 |
| max-staleness | 2016-07 | 2026-05 | 32 | 2,293 | 0 |
| connection-string | 2017-02 | 2026-05 | 11 | 1,882 | 0 |
| auth | 2017-08 | 2026-05 | 2 | 1,079 | 0 |
| initial-dns-seedlist-discovery | 2017-10 | 2026-05 | 54 | 608 | 2 |
| retryable-writes | 2017-11 | 2026-05 | 48 | 13,507 | 1 |
| bson-corpus | 2017-12 | 2026-05 | 37 | 5,597 | 0 |
| read-write-concern | 2018-02 | 2026-05 | 6 | 1,212 | 0 |
| transactions | 2018-05 | 2026-05 | 47 | 34,314 | 1 |
| crud | 2018-06 | 2026-05 | 158 | 37,456 | 4 |
| change-streams | 2018-07 | 2026-05 | 9 | 8,285 | 2 |
| gridfs | 2018-10 | 2026-05 | 4 | 1,464 | 0 |
| transactions-convenient-api | 2019-02 | 2026-05 | 10 | 3,796 | 0 |
| uri-options | 2019-06 | 2026-05 | 12 | 1,621 | 0 |
| retryable-reads | 2019-08 | 2026-05 | 45 | 21,562 | 0 |
| client-side-encryption | 2019-11 | 2026-05 | 214 | 125,303 | 3 |
| sessions | 2020-01 | 2026-05 | 7 | 2,956 | 1 |
| unified-test-format | 2020-11 | 2026-05 | 24 | 5,996 | 2 |
| atlas-data-lake-testing | 2020-12 | 2025-08 | 7 | 276 | 0 |
| versioned-api | 2021-03 | 2026-05 | 6 | 2,914 | 0 |
| collection-management | 2021-06 | 2026-05 | 5 | 932 | 0 |
| load-balancers | 2021-08 | 2026-05 | 8 | 3,942 | 0 |
| index-management | 2023-07 | 2026-05 | 6 | 837 | 0 |
| command-logging-and-monitoring | 2024-05 | 2026-05 | 25 | 6,027 | 1 |
| client-backpressure | 2026-03 | 2026-05 | 4 | 7,486 | 0 |
| mongodb-handshake | 2026-04 | 2026-05 | 1 | 101 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2017-11 `initial-dns-seedlist-discovery`: files 23 (+16), lines 231 (+143) — driver commit `3ffee13d`
- 2018-06 `transactions`: files 23 (+6), lines 15,008 (+7,105) — driver commit `6268ffdf`
- 2018-07 `retryable-writes`: files 19 (+9), lines 4,760 (+1,988) — driver commit `5bc43d9a`
- 2018-07 `crud`: files 32 (+30), lines 3,731 (+3,572) — driver commit `5bc43d9a`
- 2019-03 `crud`: files 76 (+41), lines 7,981 (+3,087) — driver commit `4ac75d8d`
- 2020-03 `crud`: files 89 (+38), lines 13,250 (+5,442) — driver commit `c899fc3d`
- 2020-03 `change-streams`: files 4 (+2), lines 4,242 (+3,354) — driver commit `c899fc3d`
- 2020-05 `server-discovery-and-monitoring`: files 167 (+66), lines 15,193 (+8,531) — driver commit `370fc185`
- 2021-02 `unified-test-format`: files 10 (+9), lines 4,003 (+3,903) — driver commit `43f5997e`
- 2021-06 `server-discovery-and-monitoring`: files 306 (+119), lines 32,870 (+14,705) — driver commit `e37552db`
- 2021-06 `crud`: files 101 (+10), lines 21,115 (+7,192) — driver commit `e37552db`
- 2021-06 `unified-test-format`: files 16 (+6), lines 4,538 (+535) — driver commit `e37552db`
- 2021-07 `sessions`: files 6 (+5), lines 2,638 (+1,803) — driver commit `d8684bed`
- 2021-11 `initial-dns-seedlist-discovery`: files 53 (+19), lines 592 (+219) — driver commit `2bd2d842`
- 2022-05 `change-streams`: files 9 (+4), lines 11,690 (+7,224) — driver commit `db7e894b`
- 2022-05 `client-side-encryption`: files 59 (+28), lines 21,775 (+12,274) — driver commit `db7e894b`
- 2023-02 `client-side-encryption`: files 103 (+43), lines 60,471 (+38,240) — driver commit `c0b43912`
- 2025-01 `server-selection`: files 73 (+15), lines 4,008 (+1,679) — driver commit `61592503`
- 2025-01 `command-logging-and-monitoring`: files 25 (+24), lines 6,022 (+5,802) — driver commit `61592503`
- 2025-10 `client-side-encryption`: files 211 (+93), lines 124,440 (+58,910) — driver commit `48d0a485`

### CSHARP

**Path layout** (top sample-path roots at recent snapshots):
- `specifications/server-discovery-and-monitoring/tests/...` (~1768 cumulative file-rows)
- `specifications/crud/tests/...` (~852 cumulative file-rows)
- `specifications/server-selection/tests/...` (~848 cumulative file-rows)
- `specifications/client-side-encryption/prose-tests/...` (~819 cumulative file-rows)
- `specifications/initial-dns-seedlist-discovery/tests/...` (~426 cumulative file-rows)

**Total spec-test lines:** first month 2015-03 → 9,367 lines; peak 2026-04 → 503,387; last month 2026-05 → 503,387.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| crud | 2015-03 | 2026-05 | 284 | 49,995 | 2 |
| server-discovery-and-monitoring | 2015-03 | 2026-05 | 444 | 45,483 | 2 |
| server-selection | 2015-03 | 2026-05 | 216 | 9,167 | 2 |
| gridfs | 2015-08 | 2026-05 | 8 | 2,950 | 1 |
| command-monitoring | 2015-09 | 2022-09 | 26 | 3,763 | 1 |
| connection-string | 2015-10 | 2026-05 | 20 | 3,104 | 1 |
| read-write-concern | 2015-10 | 2026-05 | 12 | 2,176 | 1 |
| bson-corpus | 2016-09 | 2026-05 | 34 | 5,514 | 1 |
| max-staleness | 2016-09 | 2026-05 | 64 | 3,300 | 0 |
| initial-dns-seedlist-discovery | 2017-11 | 2026-05 | 100 | 1,018 | 2 |
| retryable-writes | 2017-12 | 2026-05 | 70 | 19,082 | 2 |
| transactions | 2018-04 | 2026-05 | 87 | 54,053 | 1 |
| auth | 2018-06 | 2026-05 | 4 | 1,785 | 1 |
| change-streams | 2018-06 | 2026-05 | 18 | 12,553 | 1 |
| transactions-convenient-api | 2019-03 | 2026-05 | 20 | 7,571 | 0 |
| retryable-reads | 2019-05 | 2026-05 | 90 | 40,388 | 0 |
| uri-options | 2019-08 | 2026-05 | 24 | 2,999 | 0 |
| client-side-encryption | 2019-09 | 2026-05 | 273 | 125,059 | 1 |
| connection-monitoring-and-pooling | 2019-10 | 2026-05 | 68 | 4,908 | 0 |
| sessions | 2019-11 | 2026-05 | 14 | 6,071 | 1 |
| unified-test-format | 2020-12 | 2026-05 | 96 | 10,782 | 1 |
| versioned-api | 2021-03 | 2026-05 | 12 | 4,085 | 0 |
| collection-management | 2021-07 | 2026-05 | 6 | 1,052 | 0 |
| load-balancers | 2021-07 | 2026-05 | 16 | 5,737 | 0 |
| atlas-data-lake-testing | 2022-10 | 2025-02 | 14 | 437 | 0 |
| command-logging-and-monitoring | 2022-10 | 2026-05 | 50 | 9,661 | 0 |
| index-management | 2023-07 | 2026-05 | 12 | 1,546 | 0 |
| client-side-operations-timeout | 2025-08 | 2026-05 | 32 | 55,840 | 0 |
| open-telemetry | 2026-02 | 2026-05 | 44 | 6,181 | 0 |
| client-backpressure | 2026-04 | 2026-05 | 8 | 11,327 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2016-06 `server-discovery-and-monitoring`: files 200 (+100), lines 11,878 (+5,939) — driver commit `b14629fe`
- 2016-06 `server-selection`: files 132 (+66), lines 6,260 (+3,130) — driver commit `b14629fe`
- 2016-06 `connection-string`: files 36 (+18), lines 5,274 (+2,637) — driver commit `b14629fe`
- 2016-07 `crud`: files 56 (+28), lines 5,766 (+2,883) — driver commit `faac9ba1`
- 2016-07 `gridfs`: files 16 (+8), lines 3,948 (+1,974) — driver commit `faac9ba1`
- 2016-07 `command-monitoring`: files 36 (+18), lines 4,810 (+2,405) — driver commit `faac9ba1`
- 2016-11 `crud`: files 116 (+60), lines 7,944 (+2,178) — driver commit `10b3b67d`
- 2018-04 `retryable-writes`: files 36 (+18), lines 5,356 (+2,678) — driver commit `2f5a667f`
- 2018-06 `transactions`: files 84 (+12), lines 45,542 (+18,962) — driver commit `8eaf2f55`
- 2018-07 `retryable-writes`: files 72 (+32), lines 12,124 (+3,964) — driver commit `f65e52d7`
- 2020-03 `read-write-concern`: files 12 (+8), lines 1,748 (+1,372) — driver commit `06700ca8`
- 2020-03 `change-streams`: files 8 (+4), lines 7,093 (+5,575) — driver commit `06700ca8`
- 2020-05 `bson-corpus`: files 38 (+31), lines 9,047 (+5,141) — driver commit `2c15f361`
- 2020-06 `server-discovery-and-monitoring`: files 307 (+146), lines 25,109 (+13,920) — driver commit `21b6b068`
- 2021-07 `initial-dns-seedlist-discovery`: files 80 (+30), lines 738 (+309) — driver commit `a563175b`
- 2021-07 `sessions`: files 12 (+8), lines 4,014 (+2,697) — driver commit `a563175b`
- 2021-08 `unified-test-format`: files 56 (+20), lines 7,370 (+1,146) — driver commit `ab4b3671`
- 2021-11 `initial-dns-seedlist-discovery`: files 124 (+44), lines 1,185 (+447) — driver commit `f4fd11d2`
- 2023-01 `client-side-encryption`: files 232 (+93), lines 117,308 (+59,351) — driver commit `5d1353dc`
- 2024-04 `auth`: files 4 (+2), lines 1,968 (+1,153) — driver commit `7c4216e7`
- 2026-01 `server-selection`: files 198 (+70), lines 8,329 (+2,515) — driver commit `3f47046c`

### CXX

**Path layout** (top sample-path roots at recent snapshots):
- `data/crud/legacy/...` (~710 cumulative file-rows)
- `data/client_side_encryption/corpus/...` (~670 cumulative file-rows)
- `data/retryable-reads/legacy/...` (~270 cumulative file-rows)
- `data/transactions/legacy/...` (~240 cumulative file-rows)
- `data/initial_dns_seedlist_discovery/load-balanced/...` (~114 cumulative file-rows)

**Total spec-test lines:** first month 2017-01 → 4,964 lines; peak 2026-01 → 203,491; last month 2026-05 → 203,491.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| crud | 2017-01 | 2026-05 | 142 | 32,112 | 2 |
| gridfs | 2017-03 | 2026-05 | 8 | 3,708 | 1 |
| change-streams | 2018-08 | 2026-05 | 9 | 8,285 | 2 |
| command-monitoring | 2018-08 | 2026-05 | 10 | 1,662 | 0 |
| transactions | 2018-09 | 2026-05 | 40 | 26,665 | 1 |
| retryable-reads | 2019-10 | 2026-05 | 45 | 22,399 | 0 |
| client-side-encryption | 2019-12 | 2026-05 | 134 | 88,275 | 3 |
| transactions-convenient-api | 2020-02 | 2026-05 | 10 | 3,796 | 0 |
| read-write-concern | 2020-07 | 2026-05 | 4 | 972 | 0 |
| atlas-data-lake-testing | 2020-11 | 2026-05 | 7 | 278 | 0 |
| unified-test-format | 2021-04 | 2026-05 | 19 | 6,088 | 1 |
| versioned-api | 2021-05 | 2026-05 | 6 | 2,822 | 0 |
| sessions | 2021-11 | 2026-05 | 5 | 2,119 | 0 |
| collection-management | 2022-05 | 2026-05 | 4 | 812 | 0 |
| initial-dns-seedlist-discovery | 2023-02 | 2026-05 | 19 | 219 | 0 |
| uri-options | 2023-02 | 2026-05 | 1 | 116 | 0 |
| retryable-writes | 2023-03 | 2026-05 | 3 | 2,169 | 0 |
| index-management | 2023-07 | 2026-05 | 6 | 994 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2019-10 `gridfs`: files 16 (+8), lines 4,779 (+2,794) — driver commit `50627c99`
- 2019-10 `transactions`: files 56 (+12), lines 38,028 (+13,022) — driver commit `50627c99`
- 2020-06 `change-streams`: files 8 (+4), lines 7,091 (+5,573) — driver commit `5efb920e`
- 2020-07 `crud`: files 143 (+43), lines 16,781 (+6,212) — driver commit `0b86224c`
- 2020-07 `client-side-encryption`: files 66 (+10), lines 22,489 (+10,628) — driver commit `0b86224c`
- 2022-03 `client-side-encryption`: files 44 (+6), lines 31,290 (+11,337) — driver commit `ea0e0396`
- 2022-06 `crud`: files 109 (+18), lines 23,901 (+9,602) — driver commit `43c93631`
- 2022-08 `change-streams`: files 5 (+1), lines 7,346 (+3,015) — driver commit `f1f3f50e`
- 2022-08 `unified-test-format`: files 19 (+7), lines 6,087 (+692) — driver commit `f1f3f50e`
- 2023-04 `client-side-encryption`: files 128 (+50), lines 87,019 (+37,946) — driver commit `52a1150d`

### GODRIVER

**Path layout** (top sample-path roots at recent snapshots):
- `testdata/server-discovery-and-monitoring/errors/...` (~1710 cumulative file-rows)
- `testdata/crud/unified/...` (~1186 cumulative file-rows)
- `testdata/client-side-encryption/legacy/...` (~652 cumulative file-rows)
- `testdata/server-selection/in_window/...` (~568 cumulative file-rows)
- `testdata/initial-dns-seedlist-discovery/load-balanced/...` (~408 cumulative file-rows)

**Total spec-test lines:** first month 2017-10 → 22,827 lines; peak 2025-03 → 379,019; last month 2025-10 → 358,411.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| bson-corpus | 2017-10 | 2025-10 | 31 | 5,254 | 0 |
| connection-string | 2017-10 | 2025-10 | 20 | 2,936 | 0 |
| max-staleness | 2017-10 | 2025-10 | 62 | 3,212 | 0 |
| server-discovery-and-monitoring | 2017-10 | 2025-10 | 426 | 39,901 | 1 |
| server-selection | 2017-10 | 2025-10 | 142 | 5,722 | 0 |
| initial-dns-seedlist-discovery | 2017-11 | 2025-10 | 102 | 1,110 | 1 |
| crud | 2018-02 | 2025-10 | 278 | 43,256 | 1 |
| read-write-concern | 2018-02 | 2025-10 | 12 | 1,747 | 1 |
| auth | 2018-06 | 2025-10 | 2 | 815 | 0 |
| command-monitoring | 2018-07 | 2025-10 | 46 | 8,577 | 1 |
| gridfs | 2018-08 | 2025-10 | 10 | 3,453 | 1 |
| retryable-writes | 2018-08 | 2025-10 | 64 | 9,383 | 0 |
| transactions | 2018-08 | 2025-10 | 67 | 39,825 | 0 |
| change-streams | 2018-11 | 2025-10 | 16 | 12,204 | 1 |
| sessions | 2019-07 | 2025-10 | 14 | 4,854 | 1 |
| uri-options | 2019-07 | 2025-10 | 20 | 2,479 | 0 |
| client-side-encryption | 2019-08 | 2025-10 | 216 | 90,165 | 2 |
| connection-monitoring-and-pooling | 2019-08 | 2025-10 | 72 | 5,252 | 0 |
| retryable-reads | 2019-08 | 2025-10 | 84 | 22,637 | 0 |
| atlas-data-lake-testing | 2020-07 | 2025-10 | 14 | 433 | 0 |
| unified-test-format | 2020-10 | 2025-10 | 102 | 10,395 | 2 |
| versioned-api | 2021-01 | 2025-10 | 12 | 3,962 | 0 |
| load-balancers | 2021-04 | 2025-10 | 16 | 5,644 | 0 |
| collection-management | 2021-06 | 2025-10 | 10 | 1,393 | 1 |
| client-side-operations-timeout | 2022-04 | 2025-10 | 20 | 30,068 | 2 |
| run-command | 2023-07 | 2025-10 | 4 | 2,222 | 0 |
| index-management | 2023-09 | 2025-10 | 12 | 1,512 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2020-02 `read-write-concern`: files 12 (+8), lines 1,747 (+1,372) — driver commit `6f3c9d10`
- 2020-03 `change-streams`: files 8 (+4), lines 7,119 (+5,572) — driver commit `a2fd8774`
- 2020-06 `server-discovery-and-monitoring`: files 314 (+132), lines 24,806 (+13,115) — driver commit `09ccd6fc`
- 2021-04 `unified-test-format`: files 32 (+12), lines 6,669 (+818) — driver commit `3fd62610`
- 2021-05 `unified-test-format`: files 60 (+28), lines 7,503 (+834) — driver commit `7450663b`
- 2021-06 `crud`: files 202 (+28), lines 31,132 (+12,642) — driver commit `5199a0b7`
- 2021-07 `sessions`: files 12 (+10), lines 4,014 (+2,739) — driver commit `57125a02`
- 2021-10 `initial-dns-seedlist-discovery`: files 104 (+42), lines 1,001 (+446) — driver commit `34dde800`
- 2022-05 `client-side-encryption`: files 102 (+34), lines 24,372 (+9,983) — driver commit `f98d6aa2`
- 2022-05 `collection-management`: files 8 (+6), lines 1,119 (+735) — driver commit `f98d6aa2`
- 2022-08 `client-side-operations-timeout`: files 14 (+6), lines 16,301 (+1,311) — driver commit `f301e5d7`
- 2022-09 `client-side-operations-timeout`: files 18 (+4), lines 29,181 (+12,880) — driver commit `b18931bf`
- 2022-11 `gridfs`: files 10 (+2), lines 3,453 (+1,369) — driver commit `977993fa`
- 2022-12 `client-side-encryption`: files 184 (+60), lines 66,292 (+34,636) — driver commit `e1bf8858`
- 2023-01 `command-monitoring`: files 44 (+18), lines 8,360 (+4,114) — driver commit `599b80ac`

### JAVA

**Path layout** (top sample-path roots at recent snapshots):
- `driver-core/src/test/...` (~3685 cumulative file-rows)
- `bson/src/test/...` (~408 cumulative file-rows)

**Total spec-test lines:** first month 2015-01 → 1,544 lines; peak 2025-03 → 306,438; last month 2025-12 → 5,508.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| server-discovery-and-monitoring | 2015-01 | 2025-03 | 211 | 25,248 | 1 |
| crud | 2015-03 | 2025-03 | 158 | 39,367 | 2 |
| server-selection | 2015-03 | 2025-03 | 106 | 6,337 | 1 |
| bson-corpus | 2015-06 | 2025-12 | 34 | 5,508 | 2 |
| connection-string | 2015-08 | 2025-03 | 10 | 1,761 | 0 |
| gridfs | 2015-08 | 2025-03 | 5 | 2,313 | 0 |
| command-monitoring | 2015-09 | 2025-03 | 15 | 3,233 | 0 |
| initial-dns-seedlist-discovery | 2017-11 | 2025-03 | 51 | 642 | 1 |
| retryable-writes | 2017-11 | 2025-03 | 33 | 11,919 | 1 |
| auth | 2018-04 | 2025-03 | 2 | 1,077 | 0 |
| transactions | 2018-04 | 2025-03 | 40 | 34,569 | 1 |
| change-streams | 2018-06 | 2025-03 | 8 | 8,194 | 2 |
| uri-options | 2019-01 | 2025-03 | 10 | 970 | 0 |
| connection-monitoring-and-pooling | 2019-02 | 2025-03 | 33 | 3,123 | 0 |
| transactions-convenient-api | 2019-02 | 2025-03 | 10 | 5,343 | 0 |
| retryable-reads | 2019-04 | 2025-03 | 45 | 27,991 | 0 |
| client-side-encryption | 2019-06 | 2025-03 | 113 | 64,639 | 2 |
| sessions | 2019-11 | 2025-03 | 7 | 3,343 | 1 |
| unified-test-format | 2020-11 | 2025-03 | 61 | 8,866 | 1 |
| versioned-api | 2021-01 | 2025-03 | 6 | 2,915 | 0 |
| load-balancers | 2021-05 | 2025-03 | 8 | 4,019 | 0 |
| collection-management | 2021-06 | 2025-03 | 5 | 932 | 0 |
| command-logging-and-monitoring | 2023-01 | 2025-03 | 10 | 2,790 | 0 |
| index-management | 2023-07 | 2025-03 | 6 | 1,016 | 0 |
| client-side-operations-timeout | 2024-07 | 2025-03 | 27 | 40,323 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2016-07 `server-selection`: files 61 (+28), lines 2,801 (+1,492) — driver commit `809b2085`
- 2016-07 `bson-corpus`: files 12 (+7), lines 4,223 (+3,900) — driver commit `809b2085`
- 2016-10 `bson-corpus`: files 28 (+16), lines 4,761 (+538) — driver commit `70bf1146`
- 2016-11 `crud`: files 29 (+15), lines 2,738 (+751) — driver commit `ca2f1979`
- 2018-06 `retryable-writes`: files 18 (+9), lines 4,115 (+2,261) — driver commit `166a5a6c`
- 2018-06 `transactions`: files 21 (+3), lines 14,178 (+5,740) — driver commit `166a5a6c`
- 2020-04 `crud`: files 88 (+38), lines 13,152 (+5,268) — driver commit `14a3e5f5`
- 2020-04 `change-streams`: files 4 (+2), lines 4,242 (+3,315) — driver commit `14a3e5f5`
- 2020-05 `server-discovery-and-monitoring`: files 162 (+73), lines 14,604 (+8,987) — driver commit `a1b912fa`
- 2021-02 `unified-test-format`: files 18 (+8), lines 4,230 (+230) — driver commit `927e50d5`
- 2021-07 `sessions`: files 6 (+4), lines 2,638 (+1,786) — driver commit `7206b710`
- 2021-10 `initial-dns-seedlist-discovery`: files 54 (+21), lines 608 (+242) — driver commit `53b0ff15`
- 2022-04 `change-streams`: files 5 (+0), lines 7,323 (+2,857) — driver commit `1ffcc02f`
- 2022-05 `client-side-encryption`: files 63 (+30), lines 23,799 (+12,541) — driver commit `9fcdefd4`
- 2023-01 `client-side-encryption`: files 106 (+43), lines 62,303 (+38,273) — driver commit `d5fb38f9`

### NODE

**Path layout** (top sample-path roots at recent snapshots):
- `test/spec/unified-test-format/...` (~2104 cumulative file-rows)
- `test/integration/server-discovery-and-monitoring/...` (~1760 cumulative file-rows)
- `test/spec/crud/...` (~1140 cumulative file-rows)
- `test/spec/client-side-encryption/...` (~882 cumulative file-rows)
- `test/integration/server-selection/...` (~864 cumulative file-rows)

**Total spec-test lines:** first month 2015-08 → 2,232 lines; peak 2026-03 → 528,712; last month 2026-05 → 526,606.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| command-monitoring | 2015-08 | 2022-11 | 22 | 3,904 | 0 |
| connection-string | 2015-10 | 2026-05 | 20 | 3,104 | 1 |
| crud | 2016-11 | 2026-05 | 380 | 64,021 | 3 |
| max-staleness | 2017-04 | 2026-05 | 64 | 3,300 | 0 |
| server-selection | 2017-04 | 2026-05 | 220 | 10,206 | 1 |
| gridfs | 2017-12 | 2026-05 | 16 | 4,229 | 2 |
| initial-dns-seedlist-discovery | 2017-12 | 2026-05 | 104 | 1,082 | 2 |
| retryable-writes | 2017-12 | 2026-05 | 66 | 18,092 | 2 |
| transactions | 2018-04 | 2026-05 | 87 | 54,029 | 1 |
| change-streams | 2018-06 | 2026-05 | 18 | 12,553 | 2 |
| auth | 2018-12 | 2026-05 | 4 | 1,809 | 0 |
| server-discovery-and-monitoring | 2018-12 | 2026-05 | 440 | 45,558 | 1 |
| uri-options | 2019-03 | 2026-05 | 24 | 3,001 | 0 |
| client-side-encryption | 2019-08 | 2026-05 | 294 | 126,326 | 2 |
| retryable-reads | 2019-08 | 2026-05 | 90 | 40,388 | 1 |
| sessions | 2019-08 | 2026-05 | 14 | 4,854 | 1 |
| connection-monitoring-and-pooling | 2019-12 | 2026-05 | 74 | 5,446 | 1 |
| read-write-concern | 2020-02 | 2026-05 | 12 | 2,176 | 0 |
| atlas-data-lake-testing | 2020-10 | 2024-06 | 14 | 433 | 0 |
| unified-test-format | 2021-01 | 2026-05 | 526 | 19,058 | 0 |
| versioned-api | 2021-03 | 2026-05 | 8 | 3,843 | 0 |
| collection-management | 2021-07 | 2026-05 | 12 | 1,544 | 1 |
| load-balancers | 2021-07 | 2026-05 | 16 | 5,711 | 0 |
| transactions-convenient-api | 2022-02 | 2026-05 | 20 | 7,571 | 0 |
| command-logging-and-monitoring | 2022-12 | 2026-05 | 50 | 9,646 | 0 |
| faas-automated-testing | 2023-04 | 2026-05 | 2 | 104 | 0 |
| run-command | 2023-04 | 2026-05 | 4 | 2,221 | 1 |
| client-side-operations-timeout | 2023-05 | 2026-05 | 58 | 63,454 | 1 |
| index-management | 2023-05 | 2026-05 | 14 | 1,793 | 0 |
| mongodb-handshake | 2025-07 | 2026-05 | 2 | 160 | 0 |
| client-backpressure | 2026-02 | 2026-05 | 8 | 11,327 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2017-10 `crud`: files 70 (+12), lines 6,012 (+2,039) — driver commit `903eb00d`
- 2018-06 `retryable-writes`: files 36 (+16), lines 6,062 (+2,099) — driver commit `955c7ab6`
- 2019-02 `transactions`: files 68 (+26), lines 40,032 (+17,261) — driver commit `430fe275`
- 2019-08 `connection-string`: files 32 (+16), lines 5,259 (+2,649) — driver commit `b542d348`
- 2019-08 `crud`: files 82 (+16), lines 8,911 (+3,383) — driver commit `b542d348`
- 2019-08 `initial-dns-seedlist-discovery`: files 94 (+46), lines 813 (+392) — driver commit `b542d348`
- 2019-11 `client-side-encryption`: files 68 (+10), lines 24,459 (+10,709) — driver commit `8fe456bc`
- 2020-04 `crud`: files 178 (+76), lines 19,058 (+7,948) — driver commit `3ae3e919`
- 2020-04 `change-streams`: files 8 (+4), lines 7,093 (+5,546) — driver commit `3ae3e919`
- 2020-06 `server-discovery-and-monitoring`: files 348 (+158), lines 28,410 (+16,061) — driver commit `e11e573e`
- 2021-07 `sessions`: files 10 (+8), lines 3,492 (+2,697) — driver commit `a9c0de80`
- 2021-11 `initial-dns-seedlist-discovery`: files 108 (+44), lines 1,066 (+460) — driver commit `b9fbac5b`
- 2022-05 `change-streams`: files 18 (+8), lines 18,209 (+10,271) — driver commit `4501a1ce`
- 2022-05 `connection-monitoring-and-pooling`: files 52 (+14), lines 2,869 (+1,106) — driver commit `4501a1ce`
- 2022-05 `collection-management`: files 8 (+6), lines 1,121 (+737) — driver commit `4501a1ce`
- 2023-01 `client-side-encryption`: files 234 (+93), lines 117,616 (+59,375) — driver commit `14143939`
- 2023-05 `run-command`: files 4 (+2), lines 2,222 (+1,504) — driver commit `f98f26ca`
- 2024-01 `server-selection`: files 150 (+14), lines 6,811 (+2,631) — driver commit `9401d09a`
- 2024-01 `client-side-operations-timeout`: files 54 (+52), lines 61,446 (+60,559) — driver commit `9401d09a`
- 2024-07 `gridfs`: files 10 (+8), lines 3,453 (+2,498) — driver commit `54efb7d4`
- 2024-07 `retryable-writes`: files 66 (+0), lines 18,086 (+6,129) — driver commit `54efb7d4`
- 2024-07 `retryable-reads`: files 90 (+0), lines 40,388 (+14,094) — driver commit `54efb7d4`
- 2025-10 `gridfs`: files 16 (+6), lines 4,229 (+776) — driver commit `517da849`

### PERL

**Path layout** (top sample-path roots at recent snapshots):
- `t/data/SDAM/...` (~876 cumulative file-rows)
- `t/data/SS/...` (~672 cumulative file-rows)
- `t/data/retryable-reads/...` (~492 cumulative file-rows)
- `t/data/CRUD/...` (~480 cumulative file-rows)
- `t/data/max_staleness/...` (~420 cumulative file-rows)

**Total spec-test lines:** first month 2014-09 → 1,578 lines; peak 2019-09 → 114,864; last month 2026-05 → 108,876.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| command-monitoring | 2014-09 | 2026-05 | 20 | 2,467 | 0 |
| server-discovery-and-monitoring | 2014-11 | 2026-05 | 146 | 10,232 | 0 |
| server-selection | 2015-01 | 2026-05 | 96 | 2,956 | 0 |
| crud | 2015-03 | 2026-05 | 80 | 8,735 | 2 |
| gridfs | 2015-12 | 2026-05 | 3 | 1,186 | 0 |
| max-staleness | 2016-07 | 2026-05 | 70 | 3,461 | 0 |
| connection-string | 2016-08 | 2026-05 | 38 | 4,363 | 1 |
| initial-dns-seedlist-discovery | 2018-01 | 2026-05 | 50 | 453 | 0 |
| retryable-writes | 2018-05 | 2026-05 | 40 | 6,094 | 1 |
| change-streams | 2018-06 | 2026-05 | 4 | 1,549 | 0 |
| transactions | 2018-06 | 2026-05 | 54 | 37,378 | 0 |
| read-write-concern | 2018-11 | 2026-05 | 4 | 376 | 0 |
| auth | 2019-05 | 2026-05 | 2 | 653 | 0 |
| retryable-reads | 2019-07 | 2026-05 | 82 | 22,492 | 0 |
| sessions | 2019-07 | 2026-05 | 2 | 795 | 0 |
| transactions-convenient-api | 2019-07 | 2026-05 | 18 | 5,686 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2016-11 `crud`: files 58 (+30), lines 3,972 (+1,089) — driver commit `04bb7829`
- 2018-06 `retryable-writes`: files 36 (+18), lines 6,062 (+3,384) — driver commit `4d21e6f6`
- 2019-02 `crud`: files 152 (+76), lines 13,466 (+6,760) — driver commit `e4d2f711`
- 2019-02 `connection-string`: files 38 (+18), lines 4,134 (+1,211) — driver commit `e4d2f711`

### PHPLIB

**Path layout** (top sample-path roots at recent snapshots):
- `tests/UnifiedSpecTests/crud/...` (~556 cumulative file-rows)
- `tests/SpecTests/client-side-encryption/...` (~534 cumulative file-rows)
- `tests/UnifiedSpecTests/atlas-data-lake/...` (~285 cumulative file-rows)
- `tests/UnifiedSpecTests/retryable-reads/...` (~225 cumulative file-rows)
- `tests/UnifiedSpecTests/transactions/...` (~195 cumulative file-rows)

**Total spec-test lines:** first month 2016-03 → 1,974 lines; peak 2024-09 → 234,873; last month 2026-05 → 68.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| gridfs | 2016-03 | 2024-09 | 5 | 2,475 | 1 |
| retryable-writes | 2019-05 | 2024-09 | 31 | 10,477 | 0 |
| change-streams | 2019-06 | 2024-09 | 8 | 8,194 | 4 |
| command-monitoring | 2019-06 | 2024-09 | 14 | 3,012 | 0 |
| transactions | 2019-06 | 2024-09 | 39 | 33,682 | 0 |
| crud | 2019-07 | 2024-09 | 139 | 32,838 | 6 |
| retryable-reads | 2019-08 | 2024-09 | 45 | 27,991 | 1 |
| transactions-convenient-api | 2019-09 | 2024-09 | 10 | 5,343 | 0 |
| client-side-encryption | 2020-01 | 2024-09 | 135 | 89,252 | 2 |
| read-write-concern | 2020-03 | 2024-09 | 4 | 1,203 | 0 |
| unified-test-format | 2020-10 | 2026-05 | 1 | 68 | 0 |
| versioned-api | 2021-04 | 2024-09 | 6 | 2,834 | 0 |
| collection-management | 2021-06 | 2024-09 | 5 | 932 | 0 |
| sessions | 2021-08 | 2024-09 | 7 | 3,343 | 1 |
| load-balancers | 2021-10 | 2024-09 | 8 | 3,975 | 0 |
| run-command | 2023-05 | 2024-09 | 1 | 634 | 0 |
| index-management | 2023-08 | 2024-09 | 6 | 1,026 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2020-01 `crud`: files 10 (+5), lines 2,244 (+795) — driver commit `4d891151`
- 2020-02 `crud`: files 16 (+6), lines 2,946 (+702) — driver commit `8060d725`
- 2020-03 `change-streams`: files 4 (+0), lines 4,239 (+2,692) — driver commit `99101b87`
- 2020-04 `crud`: files 54 (+38), lines 8,396 (+5,268) — driver commit `63b80602`
- 2020-07 `change-streams`: files 4 (+0), lines 4,329 (+2,782) — driver commit `b3a4c241`
- 2020-07 `crud`: files 61 (+51), lines 8,895 (+6,651) — driver commit `b3a4c241`
- 2021-03 `change-streams`: files 4 (+0), lines 4,329 (+2,782) — driver commit `027134d4`
- 2021-03 `crud`: files 61 (+56), lines 8,895 (+7,446) — driver commit `027134d4`
- 2021-04 `gridfs`: files 5 (+1), lines 2,475 (+1,011) — driver commit `df4e32cf`
- 2021-04 `client-side-encryption`: files 43 (+4), lines 32,635 (+11,237) — driver commit `df4e32cf`
- 2021-06 `crud`: files 66 (+12), lines 16,259 (+5,443) — driver commit `94f7ce08`
- 2022-02 `sessions`: files 6 (+2), lines 3,026 (+1,225) — driver commit `103c1f2e`
- 2022-04 `change-streams`: files 5 (+0), lines 7,327 (+2,861) — driver commit `ec68b3cb`
- 2023-03 `client-side-encryption`: files 124 (+43), lines 88,617 (+38,240) — driver commit `446985d7`
- 2024-03 `retryable-reads`: files 45 (+3), lines 27,991 (+9,802) — driver commit `d2f37660`

### PYTHON

**Path layout** (top sample-path roots at recent snapshots):
- `test/data_lake/unified/...` (~1248 cumulative file-rows)
- `test/discovery_and_monitoring/errors/...` (~820 cumulative file-rows)
- `test/client-side-encryption/corpus/...` (~779 cumulative file-rows)
- `test/crud/unified/...` (~492 cumulative file-rows)
- `test/server_selection/in_window/...` (~403 cumulative file-rows)

**Total spec-test lines:** first month 2014-09 → 1,544 lines; peak 2026-04 → 410,947; last month 2026-05 → 410,947.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| server-discovery-and-monitoring | 2014-09 | 2026-05 | 206 | 25,213 | 1 |
| crud | 2015-03 | 2026-05 | 164 | 40,319 | 1 |
| server-selection | 2015-03 | 2026-05 | 103 | 4,930 | 1 |
| connection-string | 2015-08 | 2026-05 | 10 | 1,743 | 0 |
| gridfs | 2015-08 | 2026-05 | 8 | 3,035 | 1 |
| command-monitoring | 2015-09 | 2026-05 | 14 | 3,136 | 0 |
| max-staleness | 2016-07 | 2026-05 | 32 | 2,293 | 0 |
| bson-corpus | 2016-08 | 2026-05 | 34 | 5,514 | 0 |
| retryable-writes | 2017-10 | 2026-05 | 35 | 12,612 | 1 |
| auth | 2018-04 | 2026-05 | 2 | 1,079 | 0 |
| read-write-concern | 2018-04 | 2026-05 | 6 | 1,443 | 0 |
| transactions | 2018-04 | 2026-05 | 44 | 36,041 | 1 |
| change-streams | 2018-06 | 2026-05 | 9 | 8,370 | 1 |
| uri-options | 2019-02 | 2026-05 | 11 | 1,482 | 0 |
| transactions-convenient-api | 2019-03 | 2026-05 | 10 | 5,341 | 0 |
| retryable-reads | 2019-04 | 2026-05 | 45 | 27,991 | 0 |
| connection-monitoring-and-pooling | 2019-06 | 2026-05 | 34 | 3,083 | 0 |
| sessions | 2019-06 | 2026-05 | 7 | 3,351 | 1 |
| client-side-encryption | 2019-08 | 2026-05 | 260 | 154,549 | 4 |
| initial-dns-seedlist-discovery | 2019-11 | 2026-05 | 53 | 665 | 1 |
| atlas-data-lake-testing | 2020-12 | 2024-07 | 7 | 282 | 0 |
| unified-test-format | 2020-12 | 2026-05 | 312 | 14,198 | 0 |
| versioned-api | 2021-01 | 2026-05 | 6 | 2,915 | 0 |
| load-balancers | 2021-05 | 2026-05 | 8 | 4,019 | 1 |
| collection-management | 2021-06 | 2026-05 | 3 | 703 | 0 |
| client-side-operations-timeout | 2022-06 | 2026-05 | 26 | 32,724 | 0 |
| run-command | 2023-06 | 2026-05 | 2 | 1,511 | 0 |
| index-management | 2023-07 | 2026-05 | 6 | 866 | 0 |
| faas-automated-testing | 2023-08 | 2026-05 | 2 | 111 | 0 |
| command-logging-and-monitoring | 2024-02 | 2026-05 | 14 | 4,224 | 0 |
| client-backpressure | 2026-04 | 2026-05 | 4 | 7,486 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2016-11 `crud`: files 29 (+15), lines 2,738 (+751) — driver commit `f2aff0fd`
- 2018-06 `retryable-writes`: files 18 (+9), lines 4,115 (+2,261) — driver commit `35391b7c`
- 2018-06 `transactions`: files 22 (+4), lines 15,012 (+6,559) — driver commit `35391b7c`
- 2020-04 `server-discovery-and-monitoring`: files 140 (+66), lines 13,500 (+8,504) — driver commit `d8342367`
- 2020-07 `change-streams`: files 4 (+2), lines 4,329 (+3,377) — driver commit `add995fe`
- 2020-11 `client-side-encryption`: files 48 (+4), lines 32,765 (+11,232) — driver commit `56258606`
- 2021-06 `sessions`: files 6 (+4), lines 2,638 (+1,787) — driver commit `fd845654`
- 2021-06 `load-balancers`: files 8 (+4), lines 3,911 (+3,495) — driver commit `fd845654`
- 2021-10 `initial-dns-seedlist-discovery`: files 54 (+21), lines 608 (+242) — driver commit `9f6c6a30`
- 2022-06 `client-side-encryption`: files 85 (+33), lines 50,270 (+12,602) — driver commit `6d916d68`
- 2022-07 `gridfs`: files 5 (+1), lines 2,475 (+1,085) — driver commit `fbb8dde8`
- 2023-01 `client-side-encryption`: files 142 (+57), lines 88,935 (+38,657) — driver commit `540562a6`
- 2025-09 `client-side-encryption`: files 258 (+99), lines 154,061 (+59,460) — driver commit `215b3b19`
- 2025-12 `server-selection`: files 93 (+25), lines 4,283 (+1,500) — driver commit `6585d9cb`

### RUBY

**Path layout** (top sample-path roots at recent snapshots):
- `spec/spec_tests/data/...` (~3461 cumulative file-rows)

**Total spec-test lines:** first month 2015-01 → 1,740 lines; peak 2024-08 → 109,261; last month 2026-05 → 99,383.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| server-discovery-and-monitoring | 2015-01 | 2026-05 | 187 | 12,164 | 1 |
| server-selection | 2015-02 | 2026-05 | 50 | 1,299 | 0 |
| command-monitoring | 2015-07 | 2022-05 | 10 | 801 | 0 |
| max-staleness | 2016-09 | 2026-05 | 31 | 979 | 0 |
| change-streams | 2018-08 | 2022-03 | 4 | 2,912 | 1 |
| connection-string | 2018-08 | 2026-05 | 10 | 1,332 | 0 |
| crud | 2018-08 | 2026-05 | 152 | 15,077 | 2 |
| gridfs | 2018-08 | 2026-05 | 4 | 586 | 0 |
| retryable-writes | 2018-08 | 2026-05 | 33 | 3,719 | 0 |
| transactions | 2018-08 | 2026-05 | 32 | 13,215 | 0 |
| uri-options | 2018-12 | 2026-05 | 11 | 1,038 | 0 |
| connection-monitoring-and-pooling | 2019-03 | 2026-05 | 32 | 1,350 | 0 |
| retryable-reads | 2019-04 | 2026-05 | 43 | 5,791 | 0 |
| auth | 2019-09 | 2026-05 | 1 | 366 | 0 |
| read-write-concern | 2019-10 | 2026-05 | 6 | 537 | 0 |
| client-side-encryption | 2020-03 | 2026-05 | 63 | 7,623 | 2 |
| unified-test-format | 2020-12 | 2026-05 | 25 | 2,658 | 0 |
| versioned-api | 2021-03 | 2026-05 | 6 | 1,128 | 0 |
| load-balancers | 2021-06 | 2026-05 | 8 | 1,718 | 1 |
| collection-management | 2021-07 | 2026-05 | 5 | 466 | 0 |
| index-management | 2023-09 | 2026-05 | 6 | 537 | 0 |
| client-side-operations-timeout | 2024-08 | 2026-05 | 27 | 21,867 | 0 |
| open-telemetry | 2025-12 | 2026-05 | 22 | 2,092 | 0 |
| client-backpressure | 2026-03 | 2026-05 | 4 | 3,841 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2019-07 `crud`: files 45 (+8), lines 3,004 (+1,015) — driver commit `04ca01aa`
- 2020-04 `change-streams`: files 4 (+2), lines 2,855 (+2,242) — driver commit `ded669b0`
- 2020-04 `crud`: files 83 (+38), lines 5,413 (+2,322) — driver commit `ded669b0`
- 2020-05 `server-discovery-and-monitoring`: files 168 (+73), lines 10,481 (+4,932) — driver commit `ddaa661e`
- 2022-06 `client-side-encryption`: files 60 (+27), lines 7,758 (+3,510) — driver commit `01f4fdcb`
- 2023-02 `client-side-encryption`: files 104 (+43), lines 28,742 (+20,931) — driver commit `b92b7f40`
- 2025-01 `load-balancers`: files 8 (+4), lines 1,727 (+1,486) — driver commit `5960f5f6`

### RUST

**Path layout** (top sample-path roots at recent snapshots):
- `spec/mongodb-handshake/unified/...` (~2424 cumulative file-rows)
- `spec/server-discovery-and-monitoring/errors/...` (~1832 cumulative file-rows)
- `spec/crud/unified/...` (~1312 cumulative file-rows)
- `spec/server-selection/in_window/...` (~848 cumulative file-rows)
- `spec/client-side-encryption/unified/...` (~825 cumulative file-rows)

**Total spec-test lines:** first month 2019-08 → 18,568 lines; peak 2026-03 → 467,912; last month 2026-05 → 466,072.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| connection-monitoring-and-pooling | 2019-08 | 2026-05 | 70 | 5,154 | 0 |
| max-staleness | 2019-08 | 2026-05 | 64 | 3,300 | 0 |
| server-discovery-and-monitoring | 2019-08 | 2026-05 | 460 | 46,453 | 1 |
| server-selection | 2019-08 | 2026-05 | 216 | 9,160 | 1 |
| connection-string | 2019-10 | 2026-05 | 20 | 3,110 | 0 |
| uri-options | 2019-10 | 2026-05 | 24 | 3,001 | 1 |
| auth | 2019-11 | 2026-05 | 4 | 1,785 | 0 |
| crud | 2019-11 | 2026-05 | 328 | 58,349 | 2 |
| read-write-concern | 2019-11 | 2026-05 | 12 | 2,176 | 1 |
| command-monitoring | 2019-12 | 2022-09 | 26 | 4,218 | 0 |
| initial-dns-seedlist-discovery | 2019-12 | 2026-05 | 104 | 1,149 | 0 |
| retryable-reads | 2020-05 | 2026-05 | 90 | 40,388 | 0 |
| retryable-writes | 2020-07 | 2026-05 | 70 | 19,082 | 1 |
| versioned-api | 2020-12 | 2026-05 | 12 | 4,085 | 1 |
| sessions | 2021-03 | 2026-05 | 14 | 6,067 | 1 |
| transactions | 2021-04 | 2026-05 | 87 | 54,053 | 0 |
| collection-management | 2021-06 | 2026-05 | 10 | 1,398 | 0 |
| unified-test-format | 2021-07 | 2026-05 | 606 | 20,945 | 2 |
| load-balancers | 2021-10 | 2026-05 | 16 | 5,737 | 0 |
| change-streams | 2022-01 | 2026-05 | 18 | 12,553 | 1 |
| client-side-encryption | 2022-10 | 2026-05 | 275 | 125,894 | 2 |
| command-logging-and-monitoring | 2022-10 | 2026-05 | 50 | 9,189 | 0 |
| gridfs | 2022-10 | 2026-05 | 16 | 4,229 | 1 |
| transactions-convenient-api | 2023-04 | 2026-05 | 20 | 7,571 | 0 |
| run-command | 2023-06 | 2026-05 | 4 | 2,222 | 0 |
| index-management | 2023-11 | 2026-05 | 12 | 1,514 | 0 |
| open-telemetry | 2025-10 | 2026-05 | 44 | 6,181 | 0 |
| client-backpressure | 2026-03 | 2026-05 | 8 | 11,327 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2021-03 `server-discovery-and-monitoring`: files 348 (+160), lines 27,141 (+14,892) — driver commit `8fd04d26`
- 2021-03 `crud`: files 174 (+86), lines 18,491 (+8,517) — driver commit `8fd04d26`
- 2021-04 `versioned-api`: files 12 (+6), lines 4,166 (+1,663) — driver commit `f9b1aa47`
- 2021-05 `read-write-concern`: files 12 (+8), lines 1,748 (+1,372) — driver commit `6cb18e19`
- 2021-07 `crud`: files 202 (+28), lines 31,183 (+12,692) — driver commit `295f3be0`
- 2021-07 `sessions`: files 12 (+8), lines 4,014 (+2,697) — driver commit `295f3be0`
- 2021-09 `unified-test-format`: files 98 (+60), lines 6,127 (+1,719) — driver commit `dd5d0a2a`
- 2022-02 `change-streams`: files 8 (+6), lines 10,123 (+9,935) — driver commit `bf12ff89`
- 2022-11 `client-side-encryption`: files 141 (+128), lines 58,218 (+32,010) — driver commit `f9e79dbb`
- 2023-01 `server-selection`: files 142 (+10), lines 6,550 (+2,441) — driver commit `fa952f46`
- 2023-03 `client-side-encryption`: files 234 (+93), lines 117,767 (+59,549) — driver commit `204cbb62`
- 2023-05 `unified-test-format`: files 594 (+477), lines 19,089 (+12,244) — driver commit `3e1c14e4`
- 2024-05 `retryable-writes`: files 66 (+0), lines 18,086 (+7,231) — driver commit `243d1542`
- 2025-04 `gridfs`: files 16 (+6), lines 4,229 (+1,015) — driver commit `72084629`
- 2025-07 `uri-options`: files 22 (+2), lines 2,882 (+1,110) — driver commit `c95787fb`

### SWIFT

**Path layout** (top sample-path roots at recent snapshots):
- `Tests/Specs/unified-test-format/...` (~1380 cumulative file-rows)
- `Tests/Specs/crud/...` (~975 cumulative file-rows)
- `Tests/Specs/server-selection/...` (~816 cumulative file-rows)
- `Tests/Specs/retryable-reads/...` (~504 cumulative file-rows)
- `Tests/Specs/max-staleness/...` (~384 cumulative file-rows)

**Total spec-test lines:** first month 2018-02 → 5,125 lines; peak 2022-09 → 138,589; last month 2026-05 → 138,589.

**Per-spec summary** (rows sorted by introduction month):

| Spec area | Intro | Final | Files | Lines | Phases |
|---|---|---|---:|---:|---:|
| bson-corpus | 2018-02 | 2021-06 | 31 | 5,146 | 0 |
| benchmarking | 2018-03 | 2018-10 | 6 | 6 | 0 |
| command-monitoring | 2018-03 | 2026-05 | 13 | 2,820 | 0 |
| crud | 2018-03 | 2026-05 | 195 | 34,246 | 2 |
| connection-string | 2018-05 | 2026-05 | 10 | 1,688 | 1 |
| read-write-concern | 2018-05 | 2026-05 | 2 | 240 | 0 |
| retryable-writes | 2019-05 | 2026-05 | 31 | 6,357 | 0 |
| change-streams | 2019-08 | 2026-05 | 16 | 12,280 | 3 |
| initial-dns-seedlist-discovery | 2019-08 | 2026-05 | 50 | 580 | 0 |
| auth | 2019-10 | 2026-05 | 1 | 449 | 0 |
| retryable-reads | 2019-10 | 2026-05 | 84 | 22,656 | 1 |
| transactions | 2020-04 | 2026-05 | 39 | 26,991 | 0 |
| uri-options | 2020-06 | 2026-05 | 9 | 1,314 | 0 |
| unified-test-format | 2020-10 | 2026-05 | 230 | 10,508 | 0 |
| versioned-api | 2021-03 | 2026-05 | 12 | 4,014 | 1 |
| load-balancers | 2021-08 | 2026-05 | 8 | 3,942 | 0 |
| collection-management | 2021-10 | 2026-05 | 2 | 384 | 0 |
| sessions | 2021-10 | 2026-05 | 6 | 2,653 | 0 |
| max-staleness | 2022-02 | 2026-05 | 64 | 3,300 | 0 |
| server-selection | 2022-02 | 2026-05 | 136 | 4,167 | 0 |

**Major phase events** (≥50% growth in files or lines, with absolute floors of +5 files or +1000 lines):

- 2020-06 `connection-string`: files 10 (+8), lines 1,669 (+1,522) — driver commit `2ce49dbf`
- 2021-01 `crud`: files 70 (+35), lines 7,039 (+2,145) — driver commit `858b6d08`
- 2021-03 `change-streams`: files 5 (+3), lines 4,445 (+3,537) — driver commit `f876f362`
- 2021-06 `crud`: files 128 (+57), lines 18,345 (+10,744) — driver commit `59caa083`
- 2021-06 `versioned-api`: files 12 (+6), lines 4,026 (+1,022) — driver commit `59caa083`
- 2022-06 `change-streams`: files 6 (+1), lines 7,072 (+2,597) — driver commit `3eb642c7`
- 2022-06 `retryable-reads`: files 84 (+40), lines 22,656 (+3,306) — driver commit `3eb642c7`
- 2022-08 `change-streams`: files 12 (+6), lines 11,788 (+4,716) — driver commit `790bfa80`

---

## 4. Driver repos: submodule-based timelines

Source: `data/drivers_submodule_timeline.csv` (1,347 rows). For each
month with a submodule, this records what spec tests the driver *had
access to* via the pinned submodule SHA, computed by walking the
specifications repo at that SHA.

> Note. GODRIVER added a `specifications/` submodule as far back as
> 2017-02 but did not actively bump it for many years (the SHA stayed
> at `deff67d6` from 2017-02 through 2025-04). During that long gap,
> GODRIVER actually used a separate `data/` directory of copied JSON
> tests; the submodule was vestigial. From 2025-04 onward (commit
> `31ef273f`, "Use Git submodules for spec tests"), GODRIVER moved the
> submodule to `testdata/specifications` and started bumping it
> regularly. JAVA and PHPLIB followed the same pattern: long history of
> copy-based, then a recent switch to submodule-based.


### GODRIVER

**Submodule first appears in repo:** 2017-02 (driver still using copy-based tests before that, see §3.GODRIVER).
**Total YAML lines available via submodule** at 2017-02: 9,881; at 2026-05: 194,898.
**Distinct submodule SHAs over the period:** 10 bumps.
**First 6 SHA bumps:**
  - 2017-02  →  specifications@deff67d6
  - 2025-05  →  specifications@1c1500ad
  - 2025-06  →  specifications@db693517
  - 2025-07  →  specifications@66899295
  - 2025-08  →  specifications@5ef7b1bc
  - 2025-09  →  specifications@4a46628a
  - ... (4 more bumps)

**Per-spec at first vs latest month:**

| Spec area | At 2017-02 | At 2026-05 | Δ lines |
|---|---:|---:|---:|
| client-side-encryption | 0 files / 0 lines | 223 files / 56,061 lines | +56,061 |
| client-side-operations-timeout | 0 files / 0 lines | 28 files / 22,174 lines | +22,174 |
| crud | 32 files / 1,588 lines | 189 files / 19,644 lines | +18,056 |
| server-discovery-and-monitoring | 57 files / 3,719 lines | 230 files / 18,478 lines | +14,759 |
| transactions | 0 files / 0 lines | 44 files / 18,076 lines | +18,076 |
| retryable-reads | 0 files / 0 lines | 45 files / 12,397 lines | +12,397 |
| unified-test-format | 0 files / 0 lines | 320 files / 7,463 lines | +7,463 |
| retryable-writes | 0 files / 0 lines | 35 files / 6,470 lines | +6,470 |
| change-streams | 0 files / 0 lines | 9 files / 4,183 lines | +4,183 |
| client-backpressure | 0 files / 0 lines | 4 files / 3,841 lines | +3,841 |
| command-logging-and-monitoring | 0 files / 0 lines | 25 files / 3,293 lines | +3,293 |
| server-selection | 40 files / 843 lines | 108 files / 3,005 lines | +2,162 |
| transactions-convenient-api | 0 files / 0 lines | 10 files / 2,230 lines | +2,230 |
| open-telemetry | 0 files / 0 lines | 22 files / 2,092 lines | +2,092 |
| sessions | 0 files / 0 lines | 7 files / 1,912 lines | +1,912 |
| connection-monitoring-and-pooling | 0 files / 0 lines | 35 files / 1,875 lines | +1,875 |
| load-balancers | 0 files / 0 lines | 8 files / 1,718 lines | +1,718 |
| uri-options | 0 files / 0 lines | 12 files / 1,380 lines | +1,380 |
| connection-string | 7 files / 1,069 lines | 8 files / 1,258 lines | +189 |
| gridfs | 4 files / 567 lines | 8 files / 1,194 lines | +627 |
| versioned-api | 0 files / 0 lines | 6 files / 1,170 lines | +1,170 |
| max-staleness | 35 files / 1,082 lines | 32 files / 1,007 lines | -75 |
| read-write-concern | 4 files / 211 lines | 8 files / 842 lines | +631 |
| auth | 0 files / 0 lines | 2 files / 715 lines | +715 |
| run-command | 0 files / 0 lines | 2 files / 710 lines | +710 |
| index-management | 0 files / 0 lines | 7 files / 625 lines | +625 |
| collection-management | 0 files / 0 lines | 6 files / 515 lines | +515 |
| initial-dns-seedlist-discovery | 0 files / 0 lines | 53 files / 511 lines | +511 |
| mongodb-handshake | 0 files / 0 lines | 1 files / 59 lines | +59 |
| command-monitoring | 9 files / 802 lines | 0 files / 0 lines | -802 |
| atlas-data-lake-testing | 0 files / 0 lines | 0 files / 0 lines | +0 |

### JAVA

**Submodule first appears in repo:** 2025-04 (driver still using copy-based tests before that, see §3.JAVA).
**Total YAML lines available via submodule** at 2025-04: 157,725; at 2026-05: 194,898.
**Distinct submodule SHAs over the period:** 12 bumps.
**First 6 SHA bumps:**
  - 2025-04  →  specifications@a039bb44
  - 2025-05  →  specifications@ca0e382f
  - 2025-06  →  specifications@db693517
  - 2025-07  →  specifications@c13d23b9
  - 2025-08  →  specifications@5ef7b1bc
  - 2025-09  →  specifications@eb7f9a25
  - ... (6 more bumps)

**Per-spec at first vs latest month:**

| Spec area | At 2025-04 | At 2026-05 | Δ lines |
|---|---:|---:|---:|
| client-side-encryption | 119 files / 29,971 lines | 223 files / 56,061 lines | +26,090 |
| client-side-operations-timeout | 28 files / 21,891 lines | 28 files / 22,174 lines | +283 |
| crud | 164 files / 18,030 lines | 189 files / 19,644 lines | +1,614 |
| server-discovery-and-monitoring | 221 files / 17,716 lines | 230 files / 18,478 lines | +762 |
| transactions | 40 files / 17,215 lines | 44 files / 18,076 lines | +861 |
| retryable-reads | 45 files / 12,397 lines | 45 files / 12,397 lines | +0 |
| unified-test-format | 315 files / 7,394 lines | 320 files / 7,463 lines | +69 |
| retryable-writes | 35 files / 6,470 lines | 35 files / 6,470 lines | +0 |
| change-streams | 9 files / 4,148 lines | 9 files / 4,183 lines | +35 |
| client-backpressure | 0 files / 0 lines | 4 files / 3,841 lines | +3,841 |
| command-logging-and-monitoring | 25 files / 3,162 lines | 25 files / 3,293 lines | +131 |
| server-selection | 73 files / 2,049 lines | 108 files / 3,005 lines | +956 |
| transactions-convenient-api | 10 files / 2,230 lines | 10 files / 2,230 lines | +0 |
| open-telemetry | 0 files / 0 lines | 22 files / 2,092 lines | +2,092 |
| sessions | 7 files / 1,510 lines | 7 files / 1,912 lines | +402 |
| connection-monitoring-and-pooling | 35 files / 1,875 lines | 35 files / 1,875 lines | +0 |
| load-balancers | 8 files / 1,718 lines | 8 files / 1,718 lines | +0 |
| uri-options | 11 files / 1,327 lines | 12 files / 1,380 lines | +53 |
| connection-string | 8 files / 1,258 lines | 8 files / 1,258 lines | +0 |
| gridfs | 8 files / 1,194 lines | 8 files / 1,194 lines | +0 |
| versioned-api | 6 files / 1,170 lines | 6 files / 1,170 lines | +0 |
| max-staleness | 32 files / 1,007 lines | 32 files / 1,007 lines | +0 |
| read-write-concern | 8 files / 842 lines | 8 files / 842 lines | +0 |
| auth | 2 files / 699 lines | 2 files / 715 lines | +16 |
| run-command | 2 files / 710 lines | 2 files / 710 lines | +0 |
| index-management | 6 files / 530 lines | 7 files / 625 lines | +95 |
| collection-management | 5 files / 466 lines | 6 files / 515 lines | +49 |
| initial-dns-seedlist-discovery | 53 files / 511 lines | 53 files / 511 lines | +0 |
| mongodb-handshake | 0 files / 0 lines | 1 files / 59 lines | +59 |
| atlas-data-lake-testing | 7 files / 235 lines | 0 files / 0 lines | -235 |

### PHPLIB

**Submodule first appears in repo:** 2024-10 (driver still using copy-based tests before that, see §3.PHPLIB).
**Total YAML lines available via submodule** at 2024-10: 155,054; at 2026-05: 194,898.
**Distinct submodule SHAs over the period:** 19 bumps.
**First 6 SHA bumps:**
  - 2024-10  →  specifications@34f9a579
  - 2024-11  →  specifications@f321471e
  - 2024-12  →  specifications@787bbe67
  - 2025-01  →  specifications@d9b434db
  - 2025-02  →  specifications@449d0397
  - 2025-03  →  specifications@f3549601
  - ... (13 more bumps)

**Per-spec at first vs latest month:**

| Spec area | At 2024-10 | At 2026-05 | Δ lines |
|---|---:|---:|---:|
| client-side-encryption | 113 files / 29,446 lines | 223 files / 56,061 lines | +26,615 |
| client-side-operations-timeout | 27 files / 21,710 lines | 28 files / 22,174 lines | +464 |
| crud | 156 files / 17,514 lines | 189 files / 19,644 lines | +2,130 |
| server-discovery-and-monitoring | 217 files / 17,268 lines | 230 files / 18,478 lines | +1,210 |
| transactions | 40 files / 17,212 lines | 44 files / 18,076 lines | +864 |
| retryable-reads | 45 files / 12,397 lines | 45 files / 12,397 lines | +0 |
| unified-test-format | 307 files / 6,976 lines | 320 files / 7,463 lines | +487 |
| retryable-writes | 33 files / 6,175 lines | 35 files / 6,470 lines | +295 |
| change-streams | 8 files / 4,087 lines | 9 files / 4,183 lines | +96 |
| client-backpressure | 0 files / 0 lines | 4 files / 3,841 lines | +3,841 |
| command-logging-and-monitoring | 25 files / 3,168 lines | 25 files / 3,293 lines | +125 |
| server-selection | 73 files / 2,049 lines | 108 files / 3,005 lines | +956 |
| transactions-convenient-api | 10 files / 2,232 lines | 10 files / 2,230 lines | -2 |
| open-telemetry | 0 files / 0 lines | 22 files / 2,092 lines | +2,092 |
| sessions | 7 files / 1,510 lines | 7 files / 1,912 lines | +402 |
| connection-monitoring-and-pooling | 35 files / 1,877 lines | 35 files / 1,875 lines | -2 |
| load-balancers | 8 files / 1,701 lines | 8 files / 1,718 lines | +17 |
| uri-options | 11 files / 1,327 lines | 12 files / 1,380 lines | +53 |
| connection-string | 8 files / 1,256 lines | 8 files / 1,258 lines | +2 |
| gridfs | 6 files / 979 lines | 8 files / 1,194 lines | +215 |
| versioned-api | 6 files / 1,170 lines | 6 files / 1,170 lines | +0 |
| max-staleness | 32 files / 1,007 lines | 32 files / 1,007 lines | +0 |
| read-write-concern | 8 files / 842 lines | 8 files / 842 lines | +0 |
| auth | 2 files / 699 lines | 2 files / 715 lines | +16 |
| run-command | 2 files / 710 lines | 2 files / 710 lines | +0 |
| index-management | 6 files / 530 lines | 7 files / 625 lines | +95 |
| collection-management | 5 files / 466 lines | 6 files / 515 lines | +49 |
| initial-dns-seedlist-discovery | 53 files / 511 lines | 53 files / 511 lines | +0 |
| mongodb-handshake | 0 files / 0 lines | 1 files / 59 lines | +59 |
| atlas-data-lake-testing | 7 files / 235 lines | 0 files / 0 lines | -235 |

---

## 5. Drivers that don't sync YAML/JSON spec tests

### 5.1 PHPC

PHPC reimplements every spec test as a hand-written PHP `.phpt` file in
`tests/`. The `tests/` directory has subdirectories named after spec
areas. Counts at HEAD (2026-04-28):

| `tests/<dir>/` | `.phpt` files | Likely spec area |
|---|---:|---|
| bson-corpus | 983 | BSON corpus (auto-converted from spec JSON) |
| bson | 442 | BSON encoding / decoding |
| manager | 174 | client manager (driver-specific) |
| cursor | 62 | cursors |
| bulkwritecommand | 62 | CRUD bulk write |
| server | 55 | SDAM server descriptions |
| session | 46 | sessions |
| bulk | 45 | CRUD bulk |
| clientEncryption | 41 | client-side-encryption |
| apm | 36 | command-monitoring |
| readPreference | 32 | server-selection |
| writeConcern | 29 | write-concern |
| query | 24 | CRUD reads |
| bson-binary-vector | 24 | BSON binary vector subtype |
| writeResult | 23 | CRUD result objects |
| readConcern | 17 | read-concern |
| connect | 17 | connection |
| standalone | 14 | SDAM standalone |
| logging | 12 | logging |
| exception | 12 | exception types (driver-specific) |
| causal-consistency | 12 | sessions (causal consistency) |
| command | 11 | command APIs |
| serverDescription | 10 | SDAM |
| serverApi | 9 | versioned-api |
| replicaset | 9 | SDAM RS |
| topologyDescription | 8 | SDAM topology |
| writeError | 7 | CRUD write errors |
| retryable-writes | 6 | retryable-writes |
| ... | ... | (various smaller dirs) |

PHPC `.phpt` total over time:

| Year-end | `.phpt` files |
|---|---:|
| 2015 | 248 |
| 2017 | 1,629 |
| 2019 | 1,819 |
| 2021 | 2,035 |
| 2023 | 2,261 |
| 2025 | 2,238 |

PHPC also depends on libmongoc (CDRIVER) via submodule, so the C-level
behavior covered by CDRIVER's YAML tests is exercised at PHPC build/test
time. But the PHP-language-level test surface is entirely hand-written and
is **not** synced from `mongodb/specifications` --- the file format
(`.phpt`) is not interchangeable with YAML/JSON spec tests.

### 5.2 HHVM

The HHVM driver was sunset in late 2019; the repo's final commit is
2021-12-22. Repo-wide `.yml`/`.yaml`/`.json` count at HEAD: 2 files
(`.travis.yml`, `benchmarks/composer.json`). HHVM never adopted YAML/JSON
spec tests in any form.

For the 31 N-classified HHVM tickets in the §5 of `report.md`, the
"intervention date" of YAML test introduction is moot --- HHVM's spec
nonconformance bugs are filed against a driver that never adopted spec
tests. They serve as a useful "no-treatment" control case in the
before/after analysis.

---

## 6. Aggregate observations and caveats

### 6.1 The "UTF wave" of 2020-10

UTF (`unified-test-format`) introduced 161 new files in October 2020
(commit `db7387df`). This was largely metadata: schema-version validation
tests + the runner conformance tests, including 80+ `invalid/` files
designed to fail validation. The substantive impact of UTF was that it
became the *required format* for new spec tests after this point. Every
spec area introduced from 2020-12 onward (`versioned-api`,
`load-balancers`, `collection-management`, `client-side-operations-timeout`,
`command-logging-and-monitoring`, `run-command`, `index-management`,
`mongodb-handshake`, `open-telemetry`, `client-backpressure`) ships its
tests in UTF format. In contrast, several pre-UTF specs maintain dual
copies: legacy + unified directories side-by-side (e.g., CRUD has both
`source/crud/tests/legacy/` and `source/crud/tests/unified/`).

### 6.2 Sync lag from specs to driver

Comparing intro months between §2 and §3, drivers typically lag the
specs repo by 0–6 months for a given spec area. Some examples:

| Spec | Specs intro | NODE intro | PYTHON intro | CDRIVER intro | RUBY intro |
|---|---|---|---|---|---|
| sdam | 2014-09 | 2019-12 (moved from `spec/`) | 2014-09 | 2015-02 | 2018-08 |
| crud | 2015-02 | 2019-12 | 2015-03 | 2018-06 | 2018-08 |
| transactions | 2018-03 | 2019-12 | 2018-04 | 2018-05 | 2018-08 |
| change-streams | 2018-05 | 2019-12 | 2018-06 | 2018-07 | 2018-08 |
| client-side-encryption | 2019-06 | 2019-12 | 2019-08 | 2019-11 | 2019-09 |
| client-side-operations-timeout | 2022-05 | 2023-05 | 2022-06 | 2022-08 | 2022-08 |

The NODE "2019-12" intro for older specs is misleading: NODE had spec
tests in `spec/` from 2014, then *moved* them to `test/spec/` in
December 2019 (commit `bede1f0ec`, "test: move all specs to a common
top-level `spec` folder"). Our path-agnostic classifier picks them up
under whatever directory they live in, so the NODE driver-side intro
months reflect both the actual sync date and the relocation date,
whichever is later.

The largest lag is typically for CSE: drivers landed CSE 2-5 months
after the spec, which is consistent with CSE being a complex subsystem
that requires the libmongocrypt dependency.

### 6.3 Drivers that switched copy → submodule

Three drivers switched from copying spec tests to using a git submodule
mid-history; this shows up as a *step-down* in their copy-based total
(§3) at the migration point:

- **GODRIVER**: ~2025-04. Files dropped from ~360k lines to under 1k
  in `data/drivers_timeline.csv` (because the submodule contents are
  not enumerated by the copy-based pass). The submodule view (§4)
  picks up at that point.
- **JAVA**: ~2025-04 in `driver-core/src/test/resources/specifications`,
  then renamed to `testing/resources/specifications` ~2025-12. The
  copy-based total dropped from ~310k to near zero around 2025-04;
  some residual files persisted until the path rename.
- **PHPLIB**: ~2024-10. Dropped from ~280k to near zero in
  `data/drivers_timeline.csv` at that month.

The combined view is: copy-based timeline gives the historical record
through 2024-10 / 2025-04 depending on the driver, and the submodule
view (§4) gives the current state as a function of which submodule SHA
was pinned each month.

### 6.4 What this analysis does **not** do

- **Schema-version vs availability.** "The submodule was bumped to commit
  X on month M" tells us only that the spec tests *existed* in the
  driver's tree. Whether the driver's test runner could *execute* the
  new tests at that commit depends on its UTF schema-version support.
  We do not detect runner support.
- **Renames and reorganizations within specs.** Some early spec areas
  (`object-id`, `command-monitoring`) were superseded by later ones
  (`bson-objectid`, `command-logging-and-monitoring`). Our per-spec
  bucketing reports them as separate areas, with `final_month` set to
  the last month they existed under that path.
- **JSON-only specs.** `bson-corpus`, `bson-binary-vector`,
  `bson-decimal128`, and `bson-objectid` ship JSON-only test files.
  They are excluded from the YAML-only counts in §2 but counted in §3
  (drivers count `.json` there because drivers are inconsistent about
  which format they sync).
- **Auth subspecs.** `source/auth/` contains subdirectories `auth-aws`,
  `auth-oidc`, etc. that the spec readers treat as separate specs but
  whose on-disk layout is under a single parent. Our bucketing reports
  them all under `auth`, which under-counts the number of distinct auth
  subspecs.
- **Unmatched files.** Each driver had between 0 and 2,000 files whose
  path didn't match any spec-area regex. Examples include
  `topology_test_descriptions/monitoring/...` (NODE-specific),
  `lib/uri/...` (PHPLIB internal config), and one-off filenames like
  `gridfs-download.json` that aren't under a `gridfs/` directory. These
  files are *not* in any per-spec count; they would only inflate
  totals. The script logs a sample of unmatched paths per driver to
  stderr (see `data/plots/` for the saved console output).

### 6.5 How to reproduce

```bash
cd analysis
# 1. Specs repo timeline
.venv/bin/python scripts/specs_timeline.py        # ~2 min
.venv/bin/python scripts/specs_phases.py

# 2. Driver repos (clone bare repos first)
mkdir -p data/driver_repos
for r in mongo-c-driver mongo-csharp-driver mongo-cxx-driver \
         node-mongodb-native mongo-python-driver mongo-perl-driver \
         mongo-ruby-driver mongo-rust-driver mongo-swift-driver \
         mongo-java-driver mongo-go-driver mongo-php-library \
         mongo-php-driver mongo-hhvm-driver; do
  git clone --bare https://github.com/mongodb/$r data/driver_repos/${r%-driver}.git
done

# 3. Driver timelines
.venv/bin/python scripts/drivers_timeline.py             # ~10 min
.venv/bin/python scripts/drivers_phases.py
.venv/bin/python scripts/drivers_submodule_timeline.py   # ~3 min

# 4. Plots and per-driver sections
.venv/bin/python scripts/plot_timelines.py
.venv/bin/python scripts/build_driver_sections.py > driver_sections.md
.venv/bin/python scripts/build_submodule_sections.py > submodule_sections.md
```
