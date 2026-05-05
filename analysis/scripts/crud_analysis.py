"""CRUD-focused analysis: do YAML spec tests catch nonconformance bugs,
and do fewer new bugs appear after a driver syncs CRUD tests?

Reads:
  - data/classified_sonnet.csv (LLM-classified tickets)
  - data/drivers_timeline.csv (per-driver monthly YAML/JSON file counts)
  - data/drivers_submodule_timeline.csv (for JAVA, GODRIVER, PHPLIB)

Outputs:
  - data/crud_panel.csv (driver × month panel, CRUD only)
  - data/plots/crud_spike_decay_balanced.png (balanced-panel bug chart)
  - prints summary to stdout
"""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path(__file__).resolve().parents[1] / "data"
PLOT_DIR = DATA / "plots"

DRIVERS = ["CDRIVER", "CSHARP", "CXX", "GODRIVER", "JAVA", "NODE",
           "PERL", "PHPLIB", "PYTHON", "RUBY", "RUST", "SWIFT"]
SUBMODULE_DRIVERS = {"JAVA", "GODRIVER", "PHPLIB"}

SPEC_ALIASES = {"bson": "bson-corpus", "sdam": "server-discovery-and-monitoring"}


def month_index(m):
    y, mo = int(m[:4]), int(m[5:7])
    return (y - 2000) * 12 + (mo - 1)


def load_crud_bugs():
    """Returns {(driver, month): n_bugs}."""
    counts = defaultdict(int)
    with (DATA / "classified_sonnet.csv").open() as f:
        for r in csv.DictReader(f):
            if r["category"] != "driver_spec_nonconformance":
                continue
            specs = [SPEC_ALIASES.get(s, s) for s in (r.get("spec_areas") or "").split("|") if s]
            if "crud" not in specs:
                continue
            created = r.get("created", "")
            if not created or len(created) < 7:
                continue
            project = r["project"]
            if project not in DRIVERS:
                continue
            counts[(project, created[:7])] += 1
    return counts


def load_crud_assets():
    """Returns {(driver, month): (n_files, n_lines)}."""
    assets = {}
    with (DATA / "drivers_timeline.csv").open() as f:
        for r in csv.DictReader(f):
            if r["spec"] != "crud" or r["driver"] not in DRIVERS:
                continue
            key = (r["driver"], r["month"])
            assets[key] = (int(r["n_files"]), int(r["n_lines"]))
    with (DATA / "drivers_submodule_timeline.csv").open() as f:
        for r in csv.DictReader(f):
            if r["spec"] != "crud" or r["driver"] not in SUBMODULE_DRIVERS:
                continue
            key = (r["driver"], r["month"])
            sub_f, sub_l = int(r["n_files"]), int(r["n_lines"])
            existing = assets.get(key, (0, 0))
            assets[key] = (max(existing[0], sub_f), max(existing[1], sub_l))
    return assets


def load_driver_active_range():
    months = defaultdict(list)
    with (DATA / "classified_sonnet.csv").open() as f:
        for r in csv.DictReader(f):
            created = r.get("created", "")
            if created and len(created) >= 7 and r["project"] in DRIVERS:
                months[r["project"]].append(created[:7])
    return {d: (min(ms), max(ms)) for d, ms in months.items()}


def month_iter(start, end):
    sy, sm = int(start[:4]), int(start[5:7])
    ey, em = int(end[:4]), int(end[5:7])
    y, m = sy, sm
    while (y, m) <= (ey, em):
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m > 12:
            m = 1
            y += 1


def build_panel(bugs, assets, ranges):
    """Build rectangular (driver, month) panel for CRUD."""
    rows = []
    for driver in DRIVERS:
        if driver not in ranges:
            continue
        first, last = ranges[driver]
        for month in month_iter(first, last):
            n_files, n_lines = assets.get((driver, month), (0, 0))
            n_bugs = bugs.get((driver, month), 0)
            rows.append({
                "driver": driver, "month": month,
                "n_bugs": n_bugs, "n_files": n_files, "n_lines": n_lines,
            })
    return rows


def first_sync(panel_by_driver, driver):
    for r in panel_by_driver[driver]:
        if r["n_files"] > 0:
            return r["month"]
    return None


def chart_spike_decay_balanced(panel_by_driver):
    """Calendar-year bug rate using only the 9 drivers with ≥36 months
    pre-sync history, so the driver pool is constant."""
    MIN_PRE = 36

    qualified = set()
    for driver in DRIVERS:
        rows = panel_by_driver.get(driver, [])
        sync = first_sync(panel_by_driver, driver)
        if not sync:
            continue
        sync_idx = month_index(sync)
        d_first = month_index(rows[0]["month"])
        if sync_idx - d_first >= MIN_PRE:
            qualified.add(driver)

    if not qualified:
        return

    year_bugs = defaultdict(int)
    year_drivers = defaultdict(set)
    for driver in qualified:
        for r in panel_by_driver[driver]:
            year = r["month"][:4]
            year_bugs[year] += r["n_bugs"]
            year_drivers[year].add(driver)

    # Only show years where all qualified drivers are present.
    n_drivers = len(qualified)
    years = sorted(y for y in year_bugs if len(year_drivers[y]) == n_drivers)
    counts = [year_bugs[y] for y in years]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(years, counts, color="#1f77b4", alpha=0.85)
    max_count = max(counts) if counts else 1
    ax.set_ylim(0, max_count * 1.25)
    for bar, count in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max_count * 0.01,
                f"{count}", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("")
    ax.set_xlabel("Year")
    ax.set_title("CRUD spec nonconformance bugs per year")
    ax.grid(True, alpha=0.3, axis="y")
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "crud_spike_decay_balanced.png", dpi=120)
    plt.close()


def main():
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    print("Loading CRUD bugs from classified_sonnet.csv...")
    bugs = load_crud_bugs()
    total_bugs = sum(bugs.values())
    print(f"  {total_bugs} CRUD nonconformance bugs across {len(set(d for d, m in bugs))} drivers")

    print("Loading CRUD test assets...")
    assets = load_crud_assets()
    print(f"  {len(assets)} (driver, month) cells with CRUD test files")

    print("Loading driver active ranges...")
    ranges = load_driver_active_range()

    print("Building CRUD panel...")
    panel = build_panel(bugs, assets, ranges)
    print(f"  {len(panel)} total (driver, month) cells")

    # Write panel CSV
    out = DATA / "crud_panel.csv"
    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["driver", "month", "n_bugs", "n_files", "n_lines"])
        w.writeheader()
        w.writerows(panel)
    print(f"  wrote {out}")

    # Organize by driver
    panel_by_driver = defaultdict(list)
    for r in panel:
        panel_by_driver[r["driver"]].append(r)
    for d in panel_by_driver:
        panel_by_driver[d].sort(key=lambda r: r["month"])

    # Per-driver summary
    print("\n=== Per-driver summary ===\n")
    print(f"{'Driver':10s} {'Sync':8s} {'Pre bugs':>8s} {'Pre mo':>6s} {'Pre rate':>8s}"
          f" {'Post bugs':>9s} {'Post mo':>7s} {'Post rate':>9s} {'Change':>8s}")
    for driver in DRIVERS:
        sync = first_sync(panel_by_driver, driver)
        rows = panel_by_driver[driver]
        if not sync:
            print(f"{driver:10s} {'never':8s}")
            continue
        pre_bugs = sum(r["n_bugs"] for r in rows if r["month"] < sync)
        pre_months = sum(1 for r in rows if r["month"] < sync)
        post_bugs = sum(r["n_bugs"] for r in rows if r["month"] >= sync)
        post_months = sum(1 for r in rows if r["month"] >= sync)
        pre_rate = pre_bugs / pre_months * 12 if pre_months else 0
        post_rate = post_bugs / post_months * 12 if post_months else 0
        change = (post_rate - pre_rate) / pre_rate * 100 if pre_rate else float('inf')
        print(f"{driver:10s} {sync:8s} {pre_bugs:8d} {pre_months:6d} {pre_rate:8.3f}"
              f" {post_bugs:9d} {post_months:7d} {post_rate:9.3f} {change:+7.0f}%")

    # Aggregate pre/post/spike/longrun
    print("\n=== Aggregate rates ===\n")
    pre_b, pre_m, post_b, post_m = 0, 0, 0, 0
    spike_b, spike_m, longrun_b, longrun_m = 0, 0, 0, 0
    for driver in DRIVERS:
        sync = first_sync(panel_by_driver, driver)
        if not sync:
            continue
        sync_idx = month_index(sync)
        for r in panel_by_driver[driver]:
            idx = month_index(r["month"])
            rel = idx - sync_idx
            if rel < 0:
                pre_b += r["n_bugs"]
                pre_m += 1
            else:
                post_b += r["n_bugs"]
                post_m += 1
                if 0 <= rel <= 5:
                    spike_b += r["n_bugs"]
                    spike_m += 1
                elif rel > 24:
                    longrun_b += r["n_bugs"]
                    longrun_m += 1

    print(f"Pre-sync:       {pre_b:3d} bugs / {pre_m/12:.1f} driver-years = {pre_b/pre_m*12:.2f}/yr")
    print(f"Post-sync:      {post_b:3d} bugs / {post_m/12:.1f} driver-years = {post_b/post_m*12:.2f}/yr")
    print(f"Spike (0..+5):  {spike_b:3d} bugs / {spike_m/12:.1f} driver-years = {spike_b/spike_m*12:.2f}/yr")
    print(f"Long-run (>24): {longrun_b:3d} bugs / {longrun_m/12:.1f} driver-years = {longrun_b/longrun_m*12:.2f}/yr")
    print(f"\nSpike / pre:    {(spike_b/spike_m)/(pre_b/pre_m):.1f}x")
    print(f"Long-run / pre: {(longrun_b/longrun_m)/(pre_b/pre_m):.2f}x")

    # Generate chart
    print("\nGenerating chart...")
    chart_spike_decay_balanced(panel_by_driver)
    print("  wrote crud_spike_decay_balanced.png")

    print("\nDone.")


if __name__ == "__main__":
    main()
