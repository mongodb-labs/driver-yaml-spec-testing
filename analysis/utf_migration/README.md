# UTF Migration LOC Analysis

How much test code did each MongoDB driver delete when it migrated from many
format-specific YAML test runners to the Unified Test Format (UTF)?

## Files

- `commits.json` --- manually curated list of UTF-migration commits per driver,
  with test-file path patterns for each language.
- `results.csv` --- computed per-commit LOC stats (regenerable; tracked for
  convenience).
- `../scripts/utf_migration_loc.py` --- script that reads `commits.json` and
  writes `results.csv`.

## Methodology

For each driver we manually identified commits that are part of the UTF
migration:

1. **`runner_creation`** --- the commit(s) that first introduced the unified
   runner. This is an *investment* (adds LOC) rather than a saving.
2. **`conversion`** --- commits that converted old format-specific test runners
   (and their YAML files) to the unified format, deleting legacy code.
3. **`runner_evolution`** --- later housekeeping of the unified runner itself
   (e.g. JUnit 4→5 migration); labeled separately.

For each commit the script runs `git show --unified=0` against the bare driver
repo and counts `-` (deleted) and `+` (added) lines in test files, filtered by
per-driver path patterns and file extensions.

**What counts as a test file:**

| Driver | Extensions | Path patterns |
|--------|-----------|---------------|
| CDRIVER | `.c`, `.h` | `src/libmongoc/tests/`, `_test.c` |
| CSHARP | `.cs` | `tests/` |
| CXX | `.cpp`, `.hh`, `.hpp` | `/test/spec/`, `/test/spec/unified` |
| GODRIVER | `.go` | `_test.go`, `/integration/unified/` |
| JAVA | `.java`, `.scala` | `/src/test/`, `/src/it/` |
| NODE | `.ts`, `.js` | `test/` |
| PHPLIB | `.php` | `tests/` |
| PYTHON | `.py` | `test/` |
| RUBY | `.rb` | `spec/spec_tests/`, `spec/runners/` |
| RUST | `.rs` | `/test/`, `test.rs`, `_test.rs` |
| SWIFT | `.swift` | `Tests/MongoSwiftSyncTests/`, `Tests/MongoSwiftTests/` |
| PERL | `.t`, `.pm` | `t/`, `t/lib/` |

## Results summary

All figures are lines of test code in the driver's native language.
"Conversion net" = deleted minus added across conversion commits only (excludes runner_creation cost).
"Runner cost" = net lines added to write the unified runner.
"Net overall" = conversion net minus runner cost.

| Driver | Conv deleted | Conv added | Conv net | Runner cost | Net overall | Migration status |
|--------|-------------|-----------|----------|-------------|-------------|-----------------|
| CSHARP | 8,928 | 4,231 | +4,697 | 5,392 | −695 | Largely complete |
| JAVA | 7,780 | 1,742 | +6,038 | 2,000 | +4,038 | Largely complete |
| RUST | 5,138 | 638 | +4,500 | 2,320 | +2,180 | Complete |
| GODRIVER | 2,903 | 1,609 | +1,294 | 5,111 | −3,817 | Largely complete |
| PHPLIB | 2,570 | 198 | +2,372 | 3,806 | −1,434 | Complete |
| PYTHON | 1,957 | 237 | +1,720 | 1,160 | +560 | Complete |
| NODE | 1,759 | 358 | +1,401 | 2,736 | −1,335 | Largely complete |
| SWIFT | 740 | 202 | +538 | 473 | +65 | Partial (CRUD/txn/retry legacy remain) |
| CXX | 510 | 355 | +155 | 2,495 | −2,340 | Partial (most legacy runners remain) |
| CDRIVER | 535 | 777 | −242 | 8,424 | −8,666 | Partial (only change streams fully migrated) |
| RUBY | 203 | 317 | −114 | 1,244 | −1,358 | Partial (many legacy runners remain) |
| PERL | 0 | 0 | 0 | 0 | 0 | **No migration** — EOL Aug 2019, retired before UTF existed. Left with 16 legacy runners (~5,448 LOC). |

## Key findings

**JAVA savings are much larger than previously reported.** The prior figure of ~2,000 was the
size of the unified runner itself (`fa758caace`). The actual legacy code deleted across 19 commits
(2021--2026) is **7,780 lines**, with a conversion net of **6,038 lines**. Jeff Yemin's intuition
was correct.

**RUST savings are slightly higher than previously reported.** The prior claim of 4,066 was from an
incomplete commit set, missing `91a91e2f` (deleted the entire `crud_v1` runner, 1,606 lines) and
`5000d323` (deleted orphaned command-monitoring files, 418 lines). Corrected figure: **5,138 lines
deleted**, conversion net **4,500**.

**CSHARP deleted the most code** among all drivers: 8,928 lines across 13 conversion commits.

**Net overall is often negative** (runner investment not yet recovered) for CSHARP, GODRIVER, NODE,
PHPLIB, RUBY, CXX, and CDRIVER. This is expected: the unified runner is more capable and covers
more specs than the sum of the runners it replaced. The payback comes as new specs are added without
requiring new runners.

**PERL is a useful contrast case.** It was retired in 2020 before it could migrate, leaving 16
fragmented legacy runners (~5,448 LOC) --- illustrating the maintenance burden that UTF eliminates.

**PHPLIB figures verified.** The 10 per-spec deletion figures cited in the paper match git history
exactly. CLAUDE.md had a typo ("~2,751") --- the correct sum is **2,551**.

## Regenerating results.csv

```
cd /path/to/driver-yaml-spec-testing
analysis/.venv/bin/python analysis/scripts/utf_migration_loc.py
```

To process only specific drivers:
```
analysis/.venv/bin/python analysis/scripts/utf_migration_loc.py RUST JAVA
```
