"""Multi-methodology test of the YAML-tests-prevent-N-bugs hypothesis.

Reads data/panel.csv (per-driver, per-spec, per-month) and tries several
analyses, each producing a chart in data/plots/. Companion text report at
data/methodology_comparison.md describes which methods show the effect.

Methods:
  M1  Event study by months-relative-to-first-sync
  M2  Spike-then-decay near first-sync
  M3  Per-(driver,spec) before/after ratio distribution
  M4  Coverage dose-response (bins of file count)
  M5  Coverage dose-response (bins of non-comment line count)
  M6  Aggregate per-spec yearly N-bugs vs cumulative drivers-with-tests
  M7  Cumulative-vs-rate scatter
  M8  Within-driver per-spec sync/no-sync diff in difference (between specs
      that synced and specs that didn't)
"""
import csv
import math
from collections import defaultdict, Counter
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DATA = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data")
PLOT_DIR = DATA / "plots"
REPORT = DATA / "methodology_comparison.md"


# -------- shared utilities --------

def load_panel():
    """Returns dict (driver, spec, month) -> {n_bugs, n_files, n_lines}."""
    panel = {}
    with (DATA / "panel.csv").open() as f:
        for r in csv.DictReader(f):
            panel[(r["driver"], r["spec"], r["month"])] = {
                "n_bugs": int(r["n_bugs_created"]),
                "n_files": int(r["n_files"]),
                "n_lines": int(r["n_noncomment_lines"]),
            }
    return panel


def month_index(month):
    """YYYY-MM -> integer (months since 2000-01)."""
    y, m = int(month[:4]), int(month[5:7])
    return (y - 2000) * 12 + (m - 1)


def index_to_month(idx):
    y = idx // 12 + 2000
    m = idx % 12 + 1
    return f"{y:04d}-{m:02d}"


def by_driver_spec(panel):
    """Returns dict (driver, spec) -> [(month, data), ...] sorted by month."""
    out = defaultdict(list)
    for (d, s, m), v in panel.items():
        out[(d, s)].append((m, v))
    for k in out:
        out[k].sort(key=lambda x: x[0])
    return out


def first_sync_month(history, threshold=1):
    """Earliest month at which n_files >= threshold."""
    for m, v in history:
        if v["n_files"] >= threshold:
            return m
    return None


def driver_first_active_month(panel, driver):
    """Earliest month with any data (asset or bug) for this driver."""
    months = []
    for (d, s, m), v in panel.items():
        if d == driver:
            months.append(m)
    return min(months) if months else None


def driver_last_active_month(panel, driver):
    months = []
    for (d, s, m), v in panel.items():
        if d == driver:
            months.append(m)
    return max(months) if months else None


# -------- M1: Event study by months-relative-to-first-sync --------

def m1_event_study(panel, by_ds):
    """For each (driver, spec) with a first-sync, align to relative time and
    average N-bug counts at each relative offset."""
    rel_bugs = defaultdict(list)  # rel_month -> [n_bugs values]
    rel_cells = defaultdict(int)  # rel_month -> count of contributing cells
    skipped_no_sync = 0
    used_cells = 0
    for (driver, spec), hist in by_ds.items():
        first = first_sync_month(hist)
        if first is None:
            skipped_no_sync += 1
            continue
        used_cells += 1
        first_idx = month_index(first)
        # Build a quick lookup
        history_dict = {m: v for m, v in hist}
        # For each driver-active month, compute rel offset and add bugs
        d_first = driver_first_active_month(panel, driver)
        d_last = driver_last_active_month(panel, driver)
        if not d_first or not d_last:
            continue
        for idx in range(month_index(d_first), month_index(d_last) + 1):
            m = index_to_month(idx)
            v = history_dict.get(m)
            n_bugs = v["n_bugs"] if v else 0
            rel = idx - first_idx
            if -36 <= rel <= 60:
                rel_bugs[rel].append(n_bugs)
                rel_cells[rel] += 1

    # Average N-bugs per cell at each rel offset
    rels = sorted(rel_bugs.keys())
    means = [sum(rel_bugs[r]) / len(rel_bugs[r]) for r in rels]
    counts = [rel_cells[r] for r in rels]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 7), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1]})
    ax1.axvline(0, color="red", lw=1, alpha=0.6, label="first sync")
    ax1.plot(rels, means, lw=1.5, color="#1f77b4")
    # Smoothed
    smooth = []
    win = 6
    for i, r in enumerate(rels):
        lo = max(0, i - win)
        hi = min(len(means), i + win + 1)
        smooth.append(sum(means[lo:hi]) / (hi - lo))
    ax1.plot(rels, smooth, lw=2.5, color="#ff7f0e", label="smoothed (±6 mo)")
    ax1.set_ylabel("Mean N-bugs per (driver,spec) cell per month")
    ax1.set_title(f"M1: Event study --- N-bug rate aligned to first-sync month "
                  f"(n={used_cells} cells; skipped {skipped_no_sync} no-sync cells)")
    ax1.legend(loc="upper right")
    ax1.grid(True, alpha=0.3)

    ax2.bar(rels, counts, width=1, color="#888", alpha=0.6)
    ax2.set_xlabel("Months relative to first sync")
    ax2.set_ylabel("# cells")
    ax2.grid(True, alpha=0.3)
    ax2.axvline(0, color="red", lw=1, alpha=0.6)

    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m1_event_study.png", dpi=120)
    plt.close()

    # Compute pre vs post mean for summary
    pre = [m for r, m in zip(rels, means) if -36 <= r < 0]
    post = [m for r, m in zip(rels, means) if 0 < r <= 36]
    pre_mean = sum(pre) / len(pre) if pre else 0
    post_mean = sum(post) / len(post) if post else 0
    return {
        "name": "M1 event study",
        "n_cells": used_cells,
        "pre_mean_bugs_per_cell_month": round(pre_mean, 4),
        "post_mean_bugs_per_cell_month": round(post_mean, 4),
        "ratio_post_over_pre": round(post_mean / pre_mean, 3) if pre_mean else None,
    }


# -------- M2: Spike-then-decay near first-sync --------

def m2_spike_window(panel, by_ds):
    """Bin each cell's bugs into [-36..-13, -12..-1, 0..3, 4..15, 16..36] mo
    relative to first sync. Show distribution of bug counts per cell per
    window, with a spike around 0."""
    windows = [(-36, -13, "−36..−13"), (-12, -1, "−12..−1"),
               (0, 3, "0..+3"), (4, 15, "+4..+15"), (16, 36, "+16..+36")]
    win_totals = defaultdict(list)  # window_label -> [total bugs in window per cell]
    used = 0
    for (driver, spec), hist in by_ds.items():
        first = first_sync_month(hist)
        if first is None:
            continue
        first_idx = month_index(first)
        used += 1
        history_dict = {m: v for m, v in hist}
        d_first = driver_first_active_month(panel, driver)
        d_last = driver_last_active_month(panel, driver)
        if not d_first or not d_last:
            continue
        d_first_idx = month_index(d_first)
        d_last_idx = month_index(d_last)
        for lo, hi, label in windows:
            n = 0
            covered_months = 0
            for off in range(lo, hi + 1):
                idx = first_idx + off
                if idx < d_first_idx or idx > d_last_idx:
                    continue
                covered_months += 1
                m = index_to_month(idx)
                v = history_dict.get(m)
                if v:
                    n += v["n_bugs"]
            if covered_months > 0:
                win_totals[label].append(n / covered_months)  # per-month rate

    labels = [w[2] for w in windows]
    means = [sum(win_totals[l]) / len(win_totals[l]) if win_totals[l] else 0 for l in labels]
    counts = [len(win_totals[l]) for l in labels]

    fig, ax = plt.subplots(figsize=(9, 5))
    bars = ax.bar(labels, means, color=["#888", "#888", "#d62728", "#888", "#888"], alpha=0.85)
    for bar, n in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"n={n}", ha="center", va="bottom", fontsize=9)
    ax.set_ylabel("Mean N-bugs per cell per month")
    ax.set_xlabel("Window relative to first sync (months)")
    ax.set_title(f"M2: Bug rate per window around first-sync (n_cells={used})")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m2_spike_window.png", dpi=120)
    plt.close()

    return {"name": "M2 spike window",
            "n_cells": used,
            "rates_per_window": {l: round(m, 4) for l, m in zip(labels, means)}}


# -------- M3: per-(driver,spec) before/after ratio distribution --------

def m3_pre_post_ratio(panel, by_ds):
    """For each (driver, spec) with first-sync and at least 12 mo of pre and
    post data, compute (post_mean - pre_mean) / max(pre_mean, eps).
    Histogram of differences."""
    diffs = []
    pre_post_totals = []  # (pre_total, post_total) for raw before/after
    used = 0
    for (driver, spec), hist in by_ds.items():
        first = first_sync_month(hist)
        if first is None:
            continue
        first_idx = month_index(first)
        d_first = driver_first_active_month(panel, driver)
        d_last = driver_last_active_month(panel, driver)
        if not d_first or not d_last:
            continue
        df_idx, dl_idx = month_index(d_first), month_index(d_last)
        history_dict = {m: v for m, v in hist}

        pre_lo = max(df_idx, first_idx - 36)
        pre_hi = first_idx - 1
        post_lo = first_idx
        post_hi = min(dl_idx, first_idx + 36)
        if pre_hi - pre_lo < 11 or post_hi - post_lo < 11:
            continue
        used += 1
        pre_n = sum(history_dict.get(index_to_month(i), {"n_bugs": 0})["n_bugs"]
                    for i in range(pre_lo, pre_hi + 1))
        post_n = sum(history_dict.get(index_to_month(i), {"n_bugs": 0})["n_bugs"]
                     for i in range(post_lo, post_hi + 1))
        pre_months = pre_hi - pre_lo + 1
        post_months = post_hi - post_lo + 1
        pre_rate = pre_n / pre_months
        post_rate = post_n / post_months
        # log ratio (laplace smoothing)
        diff = math.log((post_rate + 0.05) / (pre_rate + 0.05))
        diffs.append(diff)
        pre_post_totals.append((pre_n, post_n, pre_rate, post_rate, driver, spec))

    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    # Histogram of log-ratios
    axes[0].axvline(0, color="red", lw=1.5, alpha=0.7, label="no change")
    axes[0].hist(diffs, bins=30, color="#1f77b4", alpha=0.7, edgecolor="white")
    axes[0].set_xlabel("log(post-rate + 0.05) − log(pre-rate + 0.05)")
    axes[0].set_ylabel("# (driver, spec) cells")
    axes[0].set_title(f"M3a: Distribution of log post/pre N-rate ratio (n={used})")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3)

    # Scatter of pre vs post rates
    pres = [p[2] for p in pre_post_totals]
    posts = [p[3] for p in pre_post_totals]
    mx = max(max(pres), max(posts), 0.1)
    axes[1].plot([0, mx], [0, mx], "k--", lw=1, alpha=0.5, label="post = pre")
    axes[1].scatter(pres, posts, alpha=0.4, s=18)
    axes[1].set_xlabel("Pre-sync N-bugs per month")
    axes[1].set_ylabel("Post-sync N-bugs per month")
    axes[1].set_title("M3b: Pre vs post-sync rates per (driver,spec)")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m3_pre_post.png", dpi=120)
    plt.close()

    n_decreased = sum(1 for d in diffs if d < 0)
    n_increased = sum(1 for d in diffs if d > 0)
    n_unchanged = len(diffs) - n_decreased - n_increased
    median_diff = sorted(diffs)[len(diffs)//2] if diffs else 0
    return {"name": "M3 pre/post ratio",
            "n_cells": used,
            "n_decreased": n_decreased,
            "n_unchanged": n_unchanged,
            "n_increased": n_increased,
            "median_log_ratio": round(median_diff, 3)}


# -------- M4 & M5: dose-response --------

def m45_dose_response(panel, metric, name, bins, label):
    """metric is 'n_files' or 'n_lines'. Bins into N quantile-ish buckets,
    compute mean N-bug rate per bucket."""
    rows = []
    for (d, s, m), v in panel.items():
        rows.append((v[metric], v["n_bugs"]))
    rows.sort(key=lambda x: x[0])
    # Custom bins
    by_bin = defaultdict(list)
    for cov, bugs in rows:
        for lo, hi, b_label in bins:
            if lo <= cov < hi:
                by_bin[b_label].append(bugs)
                break
    labels = [b[2] for b in bins]
    means = [sum(by_bin[l]) / len(by_bin[l]) if by_bin[l] else 0 for l in labels]
    counts = [len(by_bin[l]) for l in labels]

    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar(labels, means, color="#1f77b4", alpha=0.85)
    for bar, n in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"n={n}", ha="center", va="bottom", fontsize=8)
    ax.set_ylabel("Mean N-bugs per cell-month")
    ax.set_xlabel(label)
    ax.set_title(name)
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    out = PLOT_DIR / f"{name.split(':')[0].lower().replace(' ', '_')}.png"
    plt.savefig(out, dpi=120)
    plt.close()

    return {"name": name, "rates_per_bin": dict(zip(labels, [round(x, 4) for x in means])),
            "n_per_bin": dict(zip(labels, counts))}


# -------- M6: per-spec yearly aggregate --------

def m6_per_spec_aggregate(panel, by_ds):
    """For each spec area (canonical), aggregate yearly N-bugs across all
    drivers. Plot alongside cumulative test asset volume (max of files across
    drivers, summed). Pick top-9 specs by total N-bugs."""
    by_spec_year_bugs = defaultdict(lambda: defaultdict(int))
    by_spec_year_lines = defaultdict(lambda: defaultdict(int))
    by_spec_year_files = defaultdict(lambda: defaultdict(int))
    for (d, s, m), v in panel.items():
        year = m[:4]
        by_spec_year_bugs[s][year] += v["n_bugs"]
        # sum lines/files across drivers for this spec at the END of the year
        # actually we want max within year per driver, then sum. Simpler: total.
        by_spec_year_lines[s][year] += v["n_lines"]
        by_spec_year_files[s][year] += v["n_files"]

    # Top specs
    spec_totals = {s: sum(d.values()) for s, d in by_spec_year_bugs.items()}
    top_specs = [s for s, _ in sorted(spec_totals.items(), key=lambda x: -x[1])[:9]]

    fig, axes = plt.subplots(3, 3, figsize=(16, 12))
    for i, spec in enumerate(top_specs):
        ax = axes[i // 3][i % 3]
        years = sorted(set(by_spec_year_bugs[spec]) | set(by_spec_year_files[spec]))
        bugs = [by_spec_year_bugs[spec].get(y, 0) for y in years]
        files = [by_spec_year_files[spec].get(y, 0) for y in years]
        ax.bar(years, bugs, color="#d62728", alpha=0.7, label="N-bugs created")
        ax2 = ax.twinx()
        ax2.plot(years, files, color="#1f77b4", lw=2, label="cum file-count (sum across drivers)")
        ax.set_title(f"{spec}", fontsize=10)
        ax.tick_params(axis="x", rotation=45, labelsize=7)
        ax.set_ylabel("N-bugs", fontsize=9, color="#d62728")
        ax2.set_ylabel("file count", fontsize=9, color="#1f77b4")
        ax.grid(True, alpha=0.2)
    fig.suptitle("M6: Per-spec yearly N-bugs (red bars) vs total test files across drivers (blue line)",
                 fontsize=12)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m6_per_spec.png", dpi=120)
    plt.close()
    return {"name": "M6 per-spec aggregate", "top_specs": top_specs}


# -------- M7: cumulative coverage vs N-rate scatter --------

def m7_scatter(panel, metric):
    """Scatter: x=test asset volume in cell, y=bugs created in cell.
    Many cells have 0/0 so log scale tricky. Use month-level rates."""
    pairs = []
    for (d, s, m), v in panel.items():
        pairs.append((v[metric], v["n_bugs"]))

    # Bin into deciles for clarity
    pairs.sort(key=lambda x: x[0])
    n = len(pairs)
    n_deciles = 10
    decile_size = n // n_deciles
    deciles = []
    for i in range(n_deciles):
        chunk = pairs[i * decile_size:(i + 1) * decile_size]
        if not chunk:
            continue
        cov = sum(c for c, _ in chunk) / len(chunk)
        bugs = sum(b for _, b in chunk) / len(chunk)
        deciles.append((cov, bugs, len(chunk)))

    fig, ax = plt.subplots(figsize=(9, 5))
    ax.plot([d[0] for d in deciles], [d[1] for d in deciles], "o-",
            color="#1f77b4", markersize=8, lw=2)
    for d in deciles:
        ax.text(d[0], d[1], f" n={d[2]}", fontsize=7, alpha=0.6)
    ax.set_xlabel(f"Mean {metric} in decile (cell-months sorted by coverage)")
    ax.set_ylabel("Mean N-bugs per cell-month in decile")
    ax.set_title(f"M7: Coverage decile dose-response ({metric})")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / f"m7_decile_{metric}.png", dpi=120)
    plt.close()
    return {"name": f"M7 decile {metric}",
            "deciles": [{"mean_cov": round(d[0], 1), "mean_bugs": round(d[1], 4), "n": d[2]}
                        for d in deciles]}


# -------- M8: synced specs vs unsynced specs within same driver --------

def m8_within_driver_diff(panel, by_ds):
    """For each driver, separate (driver, spec) cells into 'ever-synced'
    and 'never-synced'. Compare mean N-bug rate per cell-month between groups.
    Within-driver comparison controls for per-driver dynamics."""
    driver_summary = []
    drivers = sorted(set(d for (d, s, m) in panel.keys()))
    for driver in drivers:
        synced_bugs = 0
        synced_months = 0
        unsynced_bugs = 0
        unsynced_months = 0
        n_synced_specs = 0
        n_unsynced_specs = 0
        for (d, s), hist in by_ds.items():
            if d != driver:
                continue
            first = first_sync_month(hist)
            total_bugs = sum(v["n_bugs"] for _, v in hist)
            total_months = len(hist)
            if first is not None:
                synced_bugs += total_bugs
                synced_months += total_months
                n_synced_specs += 1
            else:
                unsynced_bugs += total_bugs
                unsynced_months += total_months
                n_unsynced_specs += 1
        if synced_months and unsynced_months:
            driver_summary.append({
                "driver": driver,
                "synced_specs": n_synced_specs,
                "unsynced_specs": n_unsynced_specs,
                "synced_rate": synced_bugs / synced_months,
                "unsynced_rate": unsynced_bugs / unsynced_months,
            })

    fig, ax = plt.subplots(figsize=(11, 6))
    drivers_lbl = [d["driver"] for d in driver_summary]
    synced_rates = [d["synced_rate"] for d in driver_summary]
    unsynced_rates = [d["unsynced_rate"] for d in driver_summary]
    x = list(range(len(drivers_lbl)))
    w = 0.4
    ax.bar([xi - w/2 for xi in x], synced_rates, w, color="#1f77b4",
           alpha=0.85, label="synced specs")
    ax.bar([xi + w/2 for xi in x], unsynced_rates, w, color="#d62728",
           alpha=0.85, label="unsynced specs")
    ax.set_xticks(x)
    ax.set_xticklabels(drivers_lbl, rotation=45)
    ax.set_ylabel("Mean N-bugs per cell-month")
    ax.set_title("M8: Within-driver: synced specs vs unsynced specs N-bug rate "
                 "(higher rate in synced specs is the expected pattern under bug-discovery)")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m8_within_driver.png", dpi=120)
    plt.close()

    return {"name": "M8 within-driver", "summary": driver_summary}


# -------- main --------

def main():
    PLOT_DIR.mkdir(exist_ok=True)
    print("Loading panel...")
    panel = load_panel()
    by_ds = by_driver_spec(panel)
    print(f"  panel: {len(panel)} cells; (driver,spec) pairs: {len(by_ds)}")
    print(f"  pairs with at least one synced month: "
          f"{sum(1 for h in by_ds.values() if first_sync_month(h))}")

    results = []
    print("\nM1: Event study by months-relative-to-first-sync")
    results.append(m1_event_study(panel, by_ds))
    print(f"  {results[-1]}")

    print("\nM2: Spike-then-decay around first sync")
    results.append(m2_spike_window(panel, by_ds))
    print(f"  {results[-1]}")

    print("\nM3: Per-cell pre/post ratio distribution")
    results.append(m3_pre_post_ratio(panel, by_ds))
    print(f"  {results[-1]}")

    print("\nM4: Files dose-response")
    results.append(m45_dose_response(
        panel, "n_files",
        "M4 files dose-response",
        [(0, 1, "0"), (1, 5, "1-4"), (5, 20, "5-19"), (20, 50, "20-49"), (50, 99999, "50+")],
        "test files in cell",
    ))
    print(f"  {results[-1]}")

    print("\nM5: Lines dose-response")
    results.append(m45_dose_response(
        panel, "n_lines",
        "M5 lines dose-response",
        [(0, 1, "0"), (1, 1000, "1-999"), (1000, 5000, "1k-5k"),
         (5000, 20000, "5k-20k"), (20000, 99999999, "20k+")],
        "non-comment lines in cell",
    ))
    print(f"  {results[-1]}")

    print("\nM6: Per-spec yearly aggregate")
    results.append(m6_per_spec_aggregate(panel, by_ds))
    print(f"  {results[-1]['name']}")

    print("\nM7: Coverage decile scatter (files)")
    results.append(m7_scatter(panel, "n_files"))
    print(f"  {results[-1]['name']}")
    print("M7b: Coverage decile scatter (lines)")
    results.append(m7_scatter(panel, "n_lines"))
    print(f"  {results[-1]['name']}")

    print("\nM8: Within-driver synced vs unsynced spec rates")
    results.append(m8_within_driver_diff(panel, by_ds))
    print(f"  {results[-1]['name']}")

    # Save numeric summary
    import json
    (DATA / "methodology_results.json").write_text(json.dumps(results, indent=2))
    print(f"\nWrote {DATA / 'methodology_results.json'}")


if __name__ == "__main__":
    main()
