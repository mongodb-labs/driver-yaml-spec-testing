"""Build a (driver, spec, year-month) panel that joins:
- Per-month N-bug counts from classified_sonnet.csv (using `created` date)
- Per-month YAML/JSON test asset counts from drivers_timeline.csv +
  drivers_submodule_timeline.csv

Output: data/panel.csv with columns:
  driver, spec, month, n_bugs_created, n_files, n_noncomment_lines

The panel is rectangular: every (driver, spec, month) triple in the cross
product of (driver-active months) × (canonical spec areas) gets a row, with
zeros where there's no data. Driver-active range is from the driver's first
to last classified ticket. This is essential for unbiased rate estimation;
without it, the only way a row can have n_files = 0 is if there's a bug
without test assets, which makes "0 files" cells look like 100% bug-cells.

A spec_area in the classifier output may use a short alias (sdam, csfle,
write-concern); we normalize to the canonical names used in the test-asset
data (server-discovery-and-monitoring, client-side-encryption, read-write-
concern). Multi-spec tickets attribute one count to each spec_area.
"""
import csv
from collections import defaultdict
from pathlib import Path

DATA = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data")

# Map classifier spec_area aliases to canonical names used in drivers_timeline.
SPEC_ALIASES = {
    "sdam":                 "server-discovery-and-monitoring",
    "bson":                 "bson-corpus",
    "dns-seedlist":         "initial-dns-seedlist-discovery",
    "srv":                  "initial-dns-seedlist-discovery",
    "csfle":                "client-side-encryption",
    "cmap":                 "connection-monitoring-and-pooling",
    "read-concern":         "read-write-concern",
    "write-concern":        "read-write-concern",
    "load-balancer":        "load-balancers",
    "stable-api":           "versioned-api",
    "csot":                 "client-side-operations-timeout",
    "auth-scram":           "auth",
    "auth-aws":             "auth",
    "auth-oidc":            "auth",
    "auth-x509":            "auth",
    "causal-consistency":   "sessions",
}

# Canonical specs we'll build the panel over. These are the spec areas with
# meaningful test-asset coverage and/or substantial bug counts.
CANONICAL_SPECS = [
    "server-discovery-and-monitoring",
    "crud", "server-selection", "command-monitoring", "connection-string",
    "gridfs", "read-write-concern", "max-staleness", "retryable-writes",
    "initial-dns-seedlist-discovery", "transactions", "auth", "change-streams",
    "connection-monitoring-and-pooling", "retryable-reads",
    "transactions-convenient-api", "uri-options", "sessions",
    "client-side-encryption", "atlas-data-lake-testing", "unified-test-format",
    "versioned-api", "load-balancers", "collection-management",
    "client-side-operations-timeout", "command-logging-and-monitoring",
    "run-command", "index-management", "mongodb-handshake", "open-telemetry",
    "client-backpressure", "bson-corpus",
    # Specs that the classifier names but have no canonical test directory:
    "wire-protocol", "cursors", "compression", "logging", "ocsp",
]

# Drivers in scope. PHPC, HHVM, JAVARS, JAVARX, SCALA, MOTOR, SPEC,
# DRIVERSOLD, MGO are excluded from the active panel either because they
# never sync YAML (PHPC, HHVM) or are too small / niche.
DRIVERS = ["CDRIVER", "CSHARP", "CXX", "GODRIVER", "JAVA", "NODE",
           "PERL", "PHPLIB", "PYTHON", "RUBY", "RUST", "SWIFT"]

SUBMODULE_DRIVERS = {"JAVA", "GODRIVER", "PHPLIB"}


def canon(spec):
    return SPEC_ALIASES.get(spec, spec)


def load_test_assets():
    """Returns (driver, spec, month) -> (n_files, n_lines)."""
    assets = {}
    with (DATA / "drivers_timeline.csv").open() as f:
        for r in csv.DictReader(f):
            key = (r["driver"], r["spec"], r["month"])
            assets[key] = (int(r["n_files"]), int(r["n_lines"]))
    with (DATA / "drivers_submodule_timeline.csv").open() as f:
        for r in csv.DictReader(f):
            if r["driver"] not in SUBMODULE_DRIVERS:
                continue
            key = (r["driver"], r["spec"], r["month"])
            sub_f, sub_l = int(r["n_files"]), int(r["n_lines"])
            existing = assets.get(key, (0, 0))
            assets[key] = (max(existing[0], sub_f), max(existing[1], sub_l))
    return assets


def load_bug_counts():
    """Returns (driver, spec, month) -> n_bugs_created."""
    counts = defaultdict(int)
    with (DATA / "classified_sonnet.csv").open() as f:
        for r in csv.DictReader(f):
            if r["category"] != "driver_spec_nonconformance":
                continue
            created = r.get("created", "")
            if not created or len(created) < 7:
                continue
            month = created[:7]
            project = r["project"]
            specs_raw = r.get("spec_areas", "") or ""
            specs = [canon(s) for s in specs_raw.split("|") if s]
            if not specs:
                specs = ["(unspecified)"]
            for s in specs:
                counts[(project, s, month)] += 1
    return counts


def load_driver_active_range():
    """Earliest and latest month with any classified ticket per driver."""
    months = defaultdict(list)
    with (DATA / "classified_sonnet.csv").open() as f:
        for r in csv.DictReader(f):
            created = r.get("created", "")
            if created and len(created) >= 7:
                months[r["project"]].append(created[:7])
    out = {}
    for driver, ms in months.items():
        out[driver] = (min(ms), max(ms))
    return out


def month_iter(start, end):
    """Yield YYYY-MM strings from start (inclusive) to end (inclusive)."""
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def main():
    print("Loading test assets...")
    assets = load_test_assets()
    print(f"  {len(assets)} (driver, spec, month) cells in test-asset data")

    print("Loading bug counts...")
    bugs = load_bug_counts()
    print(f"  {len(bugs)} (driver, spec, month) cells with bugs")

    print("Loading driver active ranges...")
    ranges = load_driver_active_range()
    for d in sorted(ranges):
        print(f"  {d}: {ranges[d][0]} → {ranges[d][1]}")

    # Build rectangular panel
    rows = []
    n_zero_zero = 0
    for driver in DRIVERS:
        if driver not in ranges:
            continue
        first, last = ranges[driver]
        for month in month_iter(first, last):
            for spec in CANONICAL_SPECS:
                key = (driver, spec, month)
                n_files, n_lines = assets.get(key, (0, 0))
                n_bugs = bugs.get(key, 0)
                if n_files == 0 and n_lines == 0 and n_bugs == 0:
                    n_zero_zero += 1
                rows.append({
                    "driver": driver, "spec": spec, "month": month,
                    "n_bugs_created": n_bugs,
                    "n_files": n_files,
                    "n_noncomment_lines": n_lines,
                })

    out = DATA / "panel.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["driver", "spec", "month",
                                          "n_bugs_created", "n_files", "n_noncomment_lines"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {out}")
    print(f"  zero/zero cells: {n_zero_zero} ({100*n_zero_zero/len(rows):.1f}%)")
    print(f"  bug-bearing cells: {sum(1 for r in rows if r['n_bugs_created'] > 0)}")
    print(f"  asset-bearing cells: {sum(1 for r in rows if r['n_files'] > 0)}")
    n_bugs_total = sum(r['n_bugs_created'] for r in rows)
    print(f"  total N-bugs in panel: {n_bugs_total}")


if __name__ == "__main__":
    main()
