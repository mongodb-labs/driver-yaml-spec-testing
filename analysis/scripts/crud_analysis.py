"""CRUD-focused analysis: do YAML spec tests catch nonconformance bugs,
and do fewer new bugs appear after a driver syncs CRUD tests?

Reads:
  - data/classified_sonnet.csv (LLM-classified tickets)
  - data/drivers_timeline.csv (per-driver monthly YAML/JSON file counts)
  - data/drivers_submodule_timeline.csv (for JAVA, GODRIVER, PHPLIB)

Outputs:
  - data/crud_panel.csv (driver × month panel, CRUD only)
  - data/plots/crud_*.png (charts)
  - prints summary to stdout
"""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

DATA = Path(__file__).resolve().parents[1] / "data"
PLOT_DIR = DATA / "plots"

DRIVERS = ["CDRIVER", "CSHARP", "CXX", "GODRIVER", "JAVA", "NODE",
           "PERL", "PHPLIB", "PYTHON", "RUBY", "RUST", "SWIFT"]
SUBMODULE_DRIVERS = {"JAVA", "GODRIVER", "PHPLIB"}

SPEC_ALIASES = {"bson": "bson-corpus", "sdam": "server-discovery-and-monitoring"}


def month_index(m):
    y, mo = int(m[:4]), int(m[5:7])
    return (y - 2000) * 12 + (mo - 1)


def index_to_month(idx):
    y = idx // 12 + 2000
    m = idx % 12 + 1
    return f"{y:04d}-{m:02d}"


def to_dt(month):
    return datetime.strptime(month + "-01", "%Y-%m-%d")


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


# ---- Charts ----

def chart_per_driver_timelines(panel_by_driver):
    """One chart per driver: CRUD file count and bug count over time."""
    fig, axes = plt.subplots(4, 3, figsize=(16, 16))
    for i, driver in enumerate(DRIVERS):
        ax = axes[i // 3][i % 3]
        rows = panel_by_driver[driver]
        months = [to_dt(r["month"]) for r in rows]
        bugs = [r["n_bugs"] for r in rows]
        files = [r["n_files"] for r in rows]
        sync = first_sync(panel_by_driver, driver)

        ax.bar(months, bugs, width=28, color="#d62728", alpha=0.7, label="CRUD N-bugs")
        ax2 = ax.twinx()
        ax2.plot(months, files, color="#1f77b4", lw=2, label="CRUD test files")
        ax2.set_ylabel("files", fontsize=8, color="#1f77b4")
        if sync:
            ax.axvline(to_dt(sync), color="green", lw=1.5, ls="--", alpha=0.7, label=f"first sync {sync}")
        ax.set_title(driver, fontsize=11)
        ax.set_ylabel("bugs/mo", fontsize=8, color="#d62728")
        ax.tick_params(axis="x", rotation=45, labelsize=7)
        ax.xaxis.set_major_locator(mdates.YearLocator(2))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.grid(True, alpha=0.2)
        if i == 0:
            lines1, labels1 = ax.get_legend_handles_labels()
            lines2, labels2 = ax2.get_legend_handles_labels()
            ax.legend(lines1 + lines2, labels1 + labels2, fontsize=7, loc="upper left")

    plt.suptitle("CRUD nonconformance bugs (red bars) vs synced test files (blue line) per driver",
                 fontsize=13)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "crud_per_driver.png", dpi=120)
    plt.close()


def chart_spike_decay(panel_by_driver):
    """Bug rate in 12-month windows aligned to each driver's first sync."""
    windows = [(-48, -37, "−48..−37"), (-36, -25, "−36..−25"), (-24, -13, "−24..−13"),
               (-12, -1, "−12..−1"), (0, 11, "0..+11"), (12, 23, "+12..+23"),
               (24, 35, "+24..+35"), (36, 47, "+36..+47"), (48, 59, "+48..+59"),
               (60, 71, "+60..+71")]
    win_bugs = defaultdict(int)
    win_months = defaultdict(int)

    for driver in DRIVERS:
        rows = panel_by_driver.get(driver, [])
        sync = first_sync(panel_by_driver, driver)
        if not sync:
            continue
        sync_idx = month_index(sync)
        d_first = month_index(rows[0]["month"])
        d_last = month_index(rows[-1]["month"])
        history = {r["month"]: r["n_bugs"] for r in rows}

        for lo, hi, label in windows:
            for off in range(lo, hi + 1):
                idx = sync_idx + off
                if idx < d_first or idx > d_last:
                    continue
                m = index_to_month(idx)
                win_bugs[label] += history.get(m, 0)
                win_months[label] += 1

    labels = [w[2] for w in windows]
    rates = [win_bugs[l] / win_months[l] * 12 if win_months[l] else 0 for l in labels]
    n_driver_years = [round(win_months[l] / 12, 1) for l in labels]

    fig, ax = plt.subplots(figsize=(9, 5))
    colors = ["#d62728" if lo < 0 else "#1f77b4" for lo, _, _ in windows]
    bars = ax.bar(labels, rates, color=colors, alpha=0.85)
    max_rate = max(rates)
    ax.set_ylim(0, max_rate * 1.25)
    for bar, n, rate in zip(bars, n_driver_years, rates):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"{rate:.1f}\nn={n}", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("CRUD N-bugs per driver-year")
    ax.set_xlabel("Window relative to first sync (months)")
    ax.set_title("CRUD: nonconformance bug rate before (red) and after (blue) test sync")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "crud_spike_decay.png", dpi=120)
    plt.close()
    return {l: round(r, 4) for l, r in zip(labels, rates)}


def chart_event_study(panel_by_driver):
    """Smoothed event study: mean bug rate vs months relative to first sync."""
    rel_bugs = defaultdict(list)

    for driver in DRIVERS:
        rows = panel_by_driver.get(driver, [])
        sync = first_sync(panel_by_driver, driver)
        if not sync:
            continue
        sync_idx = month_index(sync)
        history = {r["month"]: r["n_bugs"] for r in rows}
        d_first = month_index(rows[0]["month"])
        d_last = month_index(rows[-1]["month"])

        for idx in range(d_first, d_last + 1):
            rel = idx - sync_idx
            if -48 <= rel <= 72:
                m = index_to_month(idx)
                rel_bugs[rel].append(history.get(m, 0))

    rels = sorted(rel_bugs.keys())
    means = [sum(rel_bugs[r]) / len(rel_bugs[r]) for r in rels]
    # Smoothed (±6 month window)
    smooth = []
    win = 6
    for i in range(len(means)):
        lo = max(0, i - win)
        hi = min(len(means), i + win + 1)
        smooth.append(sum(means[lo:hi]) / (hi - lo))

    fig, ax = plt.subplots(figsize=(11, 5))
    ax.axvline(0, color="red", lw=1.5, alpha=0.6, label="first sync")
    ax.bar(rels, means, width=1, color="#1f77b4", alpha=0.3, label="monthly")
    ax.plot(rels, smooth, lw=2.5, color="#ff7f0e", label="smoothed (±6 mo)")
    ax.set_xlabel("Months relative to first CRUD test sync")
    ax.set_ylabel("Mean CRUD N-bugs per driver-month")
    ax.set_title(f"CRUD event study: bug rate aligned to first sync (n={sum(1 for d in DRIVERS if first_sync(panel_by_driver, d))} drivers)")
    ax.legend(loc="upper right")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "crud_event_study.png", dpi=120)
    plt.close()


def chart_pre_post_per_driver(panel_by_driver):
    """Per-driver pre vs post sync bug rates."""
    driver_data = []
    for driver in DRIVERS:
        rows = panel_by_driver.get(driver, [])
        sync = first_sync(panel_by_driver, driver)
        if not sync:
            continue
        pre_bugs = sum(r["n_bugs"] for r in rows if r["month"] < sync)
        pre_months = sum(1 for r in rows if r["month"] < sync)
        post_bugs = sum(r["n_bugs"] for r in rows if r["month"] >= sync)
        post_months = sum(1 for r in rows if r["month"] >= sync)
        driver_data.append({
            "driver": driver,
            "sync": sync,
            "pre_rate": pre_bugs / pre_months * 12 if pre_months else 0,
            "post_rate": post_bugs / post_months * 12 if post_months else 0,
            "pre_bugs": pre_bugs, "pre_months": pre_months,
            "post_bugs": post_bugs, "post_months": post_months,
        })

    fig, ax = plt.subplots(figsize=(11, 6))
    x = list(range(len(driver_data)))
    w = 0.4
    ax.bar([xi - w/2 for xi in x],
           [d["pre_rate"] for d in driver_data],
           w, color="#d62728", alpha=0.85, label="Pre-sync")
    ax.bar([xi + w/2 for xi in x],
           [d["post_rate"] for d in driver_data],
           w, color="#1f77b4", alpha=0.85, label="Post-sync")
    ax.set_xticks(x)
    ax.set_xticklabels([f"{d['driver']}\n({d['sync']})" for d in driver_data],
                       rotation=45, fontsize=8)
    ax.set_ylabel("CRUD N-bugs per year")
    ax.set_title("CRUD: pre-sync vs post-sync nonconformance bug rate per driver")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "crud_pre_post.png", dpi=120)
    plt.close()
    return driver_data


def chart_file_count_vs_bugs(panel_by_driver):
    """Scatter: each point is a driver-month. x = CRUD files, y = bugs that month."""
    all_rows = []
    for driver in DRIVERS:
        for r in panel_by_driver.get(driver, []):
            if r["n_files"] > 0 or r["n_bugs"] > 0:
                all_rows.append(r)

    # Bin by file-count ranges
    bins = [(0, 0, "0"), (1, 10, "1-10"), (11, 30, "11-30"),
            (31, 80, "31-80"), (81, 200, "81-200"), (201, 99999, "200+")]
    bin_bugs = defaultdict(int)
    bin_months = defaultdict(int)
    for r in all_rows:
        for lo, hi, label in bins:
            if lo <= r["n_files"] <= hi:
                bin_bugs[label] += r["n_bugs"]
                bin_months[label] += 1
                break

    # Include zero-file cells from full panel
    for driver in DRIVERS:
        for r in panel_by_driver.get(driver, []):
            if r["n_files"] == 0 and r["n_bugs"] == 0:
                bin_bugs["0"] += 0
                bin_months["0"] += 1

    labels = [b[2] for b in bins]
    rates = [bin_bugs[l] / bin_months[l] * 12 if bin_months[l] else 0 for l in labels]
    counts = [bin_months[l] for l in labels]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, rates, color="#1f77b4", alpha=0.85)
    for bar, n in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"n={n}", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("CRUD N-bugs per driver-year")
    ax.set_xlabel("CRUD test files synced to driver")
    ax.set_title("CRUD: bug rate by test file count")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "crud_dose_response.png", dpi=120)
    plt.close()


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


def chart_spike_decay_calendar(panel_by_driver):
    """Bug rate in calendar-year windows across all drivers."""
    year_bugs = defaultdict(int)
    year_drivers = defaultdict(set)

    for driver in DRIVERS:
        for r in panel_by_driver.get(driver, []):
            year = r["month"][:4]
            year_bugs[year] += r["n_bugs"]
            year_drivers[year].add(driver)

    years = sorted(year_bugs.keys())
    n_drivers = [len(year_drivers[y]) for y in years]
    rates = [year_bugs[y] / n_drivers[i] if n_drivers[i] else 0
             for i, y in enumerate(years)]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(years, rates, color="#1f77b4", alpha=0.85)
    max_rate = max(rates) if rates else 1
    ax.set_ylim(0, max_rate * 1.25)
    for bar, nd, rate in zip(bars, n_drivers, rates):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height() + max_rate * 0.01,
                f"{rate:.1f}\n{nd} drivers", ha="center", va="bottom", fontsize=7)
    ax.set_ylabel("CRUD N-bugs per driver-year")
    ax.set_xlabel("Year")
    ax.set_title("CRUD: nonconformance bug rate by calendar year")
    ax.grid(True, alpha=0.3, axis="y")
    ax.tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "crud_spike_decay_calendar.png", dpi=120)
    plt.close()


def chart_spike_decay_per_driver(panel_by_driver):
    """Per-driver small multiples of the spike-decay chart."""
    drivers_with_sync = []
    for driver in DRIVERS:
        sync = first_sync(panel_by_driver, driver)
        if sync:
            drivers_with_sync.append(driver)

    ncols = 3
    nrows = (len(drivers_with_sync) + ncols - 1) // ncols
    fig, axes = plt.subplots(nrows, ncols, figsize=(14, 3.2 * nrows),
                             sharex=True, sharey=True)
    axes = axes.flatten()

    for i, driver in enumerate(drivers_with_sync):
        ax = axes[i]
        rows = panel_by_driver[driver]
        sync = first_sync(panel_by_driver, driver)
        sync_idx = month_index(sync)
        d_first = month_index(rows[0]["month"])
        d_last = month_index(rows[-1]["month"])
        history = {r["month"]: r["n_bugs"] for r in rows}

        # Build windows this driver has data for.
        windows = []
        for lo in range(-48, 72, 12):
            hi = lo + 11
            # Check this driver covers at least half the window.
            covered = sum(1 for off in range(lo, hi + 1)
                          if d_first <= sync_idx + off <= d_last)
            if covered >= 6:
                label = f"{lo:+d}" if lo < 0 else f"+{lo}"
                windows.append((lo, hi, label))

        if not windows:
            ax.set_title(driver, fontsize=10)
            continue

        labels = [w[2] for w in windows]
        rates = []
        for lo, hi, label in windows:
            total_bugs = 0
            total_months = 0
            for off in range(lo, hi + 1):
                idx = sync_idx + off
                if d_first <= idx <= d_last:
                    m = index_to_month(idx)
                    total_bugs += history.get(m, 0)
                    total_months += 1
            rates.append(total_bugs / total_months * 12 if total_months else 0)

        colors = ["#d62728" if lo < 0 else "#1f77b4" for lo, _, _ in windows]
        ax.bar(labels, rates, color=colors, alpha=0.85)
        ax.set_title(f"{driver} (sync {sync})", fontsize=10)
        ax.tick_params(axis="x", labelsize=7, rotation=45)
        ax.grid(True, alpha=0.3, axis="y")

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.supylabel("CRUD N-bugs per driver-year", fontsize=11)
    fig.supxlabel("Window start (months relative to first sync)", fontsize=11)
    fig.suptitle("CRUD: nonconformance bug rate per driver, 12-month windows",
                 fontsize=13)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "crud_spike_decay_per_driver.png", dpi=120)
    plt.close()


def chart_aggregate_timeline(panel_by_driver, bugs):
    """Aggregate view: total CRUD bugs/year across all drivers, plus total files."""
    by_year_bugs = defaultdict(int)
    by_year_files = defaultdict(int)
    by_year_drivers_with_files = defaultdict(set)

    for driver in DRIVERS:
        for r in panel_by_driver.get(driver, []):
            year = r["month"][:4]
            by_year_bugs[year] += r["n_bugs"]
            if r["n_files"] > 0:
                by_year_files[year] = max(by_year_files[year], 0)
                by_year_drivers_with_files[year].add(driver)

    # For file count, use the max across all drivers at year-end
    for driver in DRIVERS:
        rows = panel_by_driver.get(driver, [])
        by_year = defaultdict(int)
        for r in rows:
            year = r["month"][:4]
            by_year[year] = max(by_year[year], r["n_files"])
        for year, n in by_year.items():
            by_year_files[year] += n

    years = sorted(set(by_year_bugs) | set(by_year_files))
    fig, ax = plt.subplots(figsize=(11, 5))
    ax.bar(years, [by_year_bugs[y] for y in years], color="#d62728", alpha=0.7,
           label="CRUD N-bugs filed")
    ax2 = ax.twinx()
    ax2.plot(years, [by_year_files[y] for y in years], "o-", color="#1f77b4",
             lw=2, label="Total CRUD test files (sum across drivers)")
    ax.set_ylabel("CRUD N-bugs", color="#d62728")
    ax2.set_ylabel("Test files", color="#1f77b4")
    ax.set_title("CRUD: yearly nonconformance bugs vs cumulative test files across all drivers")
    ax.tick_params(axis="x", rotation=45)
    ax.grid(True, alpha=0.2)
    lines1, labels1 = ax.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax.legend(lines1 + lines2, labels1 + labels2, loc="upper right")
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "crud_aggregate.png", dpi=120)
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

    # Generate charts
    print("\nGenerating charts...")
    chart_per_driver_timelines(panel_by_driver)
    print("  wrote crud_per_driver.png")

    window_rates = chart_spike_decay(panel_by_driver)
    print(f"  wrote crud_spike_decay.png  rates={window_rates}")

    chart_event_study(panel_by_driver)
    print("  wrote crud_event_study.png")

    driver_data = chart_pre_post_per_driver(panel_by_driver)
    print("  wrote crud_pre_post.png")

    chart_file_count_vs_bugs(panel_by_driver)
    print("  wrote crud_dose_response.png")

    chart_aggregate_timeline(panel_by_driver, bugs)
    print("  wrote crud_aggregate.png")

    chart_spike_decay_balanced(panel_by_driver)
    print("  wrote crud_spike_decay_balanced.png")

    chart_spike_decay_calendar(panel_by_driver)
    print("  wrote crud_spike_decay_calendar.png")

    chart_spike_decay_per_driver(panel_by_driver)
    print("  wrote crud_spike_decay_per_driver.png")

    print("\nDone.")


if __name__ == "__main__":
    main()
