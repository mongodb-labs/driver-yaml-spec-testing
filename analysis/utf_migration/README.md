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

1. **`runner_creation`** --- the commit that first introduced the unified
   runner. This is an *investment* (adds LOC) rather than a saving.
2. **`conversion`** --- commits that converted old format-specific test runners
   (and their YAML files) to the unified format, deleting legacy code.
3. **`runner_evolution`** --- later housekeeping of the unified runner itself
   (e.g. JUnit 4→5 migration); included for completeness, separately labeled.

For each commit the script runs `git show --unified=0` against the bare driver
repo and counts lines starting with `-` (deleted) and `+` (added) in test-only
files, as determined by per-driver path patterns and file extensions.

**What counts as a test file:**

| Driver | Extensions | Path patterns |
|--------|-----------|---------------|
| RUST | `.rs` | `/test/`, `test.rs`, `_test.rs` |
| JAVA | `.java`, `.scala` | `/src/test/`, `/src/it/` |
| (others TBD as analysis completes) | | |

## Key results (RUST and JAVA)

All figures are net lines removed (deleted minus added) in test files only.

| Driver | Gross legacy deleted | New wrappers added | Net removed | Runner cost | Net incl. runner |
|--------|--------------------|--------------------|-------------|-------------|-----------------|
| RUST | 5,138 | 638 | **4,500** | 2,320 | 2,180 |
| JAVA | 7,780 | 1,742 | **6,038** | 2,000 | 4,038 |

The previously reported figure of **4,066** for RUST was from an incomplete
commit set (missing `91a91e2f` which deleted the entire `crud_v1` runner, and
`5000d323` which cleaned up orphaned command-monitoring files). The corrected
gross figure is **4,500**.

The previously reported figure of **~2,000** for JAVA was the size of the UTF
runner itself (`fa758caace`), not the savings. Jeff Yemin's intuition that Java
saved far more is confirmed: **6,038** lines of legacy runner code deleted.

## Regenerating results.csv

```
cd /path/to/driver-yaml-spec-testing
analysis/.venv/bin/python analysis/scripts/utf_migration_loc.py
```

To process only specific drivers:
```
analysis/.venv/bin/python analysis/scripts/utf_migration_loc.py RUST JAVA
```
