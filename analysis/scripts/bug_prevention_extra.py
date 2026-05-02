"""Additional bug-prevention methodologies (M9-M13).

These build on data/panel.csv and try harder to isolate the
YAML-tests-reduce-bugs effect from confounds:

  M9   Per-spec coverage-saturation: bug rate before vs after the spec's
       coverage saturates (≥80% of eventual peak coverage reached).
  M10  Sync-lag scatter: (driver, spec) cells, x = months between spec's
       first appearance in specs repo and driver's first sync; y = total N
       bugs filed in that (driver, spec). Late-sync should mean more bugs.
  M11  Synced-vs-unsynced share over calendar time: as YAML adoption grows,
       does the share of bugs in synced-spec areas drop?
  M12  Driver-detrended event study: residual N-bug rate after subtracting
       driver's own all-spec monthly rate. Removes driver-specific calendar
       effects.
  M13  Long-run rate: pre-sync rate vs rate at +12-24, +24-36, +36-60.
       Looking for sustained reduction below pre-sync after the spike.
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data")
PLOT_DIR = DATA / "plots"


def load_panel():
    panel = {}
    with (DATA / "panel.csv").open() as f:
        for r in csv.DictReader(f):
            panel[(r["driver"], r["spec"], r["month"])] = {
                "n_bugs": int(r["n_bugs_created"]),
                "n_files": int(r["n_files"]),
                "n_lines": int(r["n_noncomment_lines"]),
            }
    return panel


def month_index(m):
    return (int(m[:4]) - 2000) * 12 + (int(m[5:7]) - 1)


def index_to_month(i):
    y = i // 12 + 2000
    m = i % 12 + 1
    return f"{y:04d}-{m:02d}"


def by_driver_spec(panel):
    out = defaultdict(list)
    for k, v in panel.items():
        out[(k[0], k[1])].append((k[2], v))
    for k in out:
        out[k].sort(key=lambda x: x[0])
    return out


def first_sync_month(history, threshold=1):
    for m, v in history:
        if v["n_files"] >= threshold:
            return m
    return None


# -------- M9: Coverage saturation analysis --------

def m9_saturation(panel):
    """For each spec, find the calendar month when total coverage (sum of
    file counts across drivers) reaches 80% of its eventual peak. Compare
    bug rate before vs after."""
    # Build (spec, month) -> total file count across drivers
    spec_month_total = defaultdict(lambda: defaultdict(int))
    spec_months = defaultdict(set)
    for (d, s, m), v in panel.items():
        spec_month_total[s][m] += v["n_files"]
        spec_months[s].add(m)

    # Compute saturation date per spec
    sat_date = {}
    for spec, by_m in spec_month_total.items():
        if not by_m:
            continue
        peak = max(by_m.values())
        if peak < 5:
            continue
        thr = 0.8 * peak
        for m in sorted(spec_months[spec]):
            if by_m[m] >= thr:
                sat_date[spec] = m
                break

    # Bugs before vs after sat_date per spec
    pre_post = {}
    for spec, sd in sat_date.items():
        pre_bugs = post_bugs = 0
        pre_cell_months = post_cell_months = 0
        for (d, s, m), v in panel.items():
            if s != spec:
                continue
            if m < sd:
                pre_bugs += v["n_bugs"]
                pre_cell_months += 1
            else:
                post_bugs += v["n_bugs"]
                post_cell_months += 1
        if pre_cell_months and post_cell_months:
            pre_post[spec] = {
                "sat_date": sd,
                "pre_rate": pre_bugs / pre_cell_months,
                "post_rate": post_bugs / post_cell_months,
                "pre_bugs": pre_bugs, "post_bugs": post_bugs,
            }

    # Plot: for each spec, show pre and post rate
    specs = sorted(pre_post.keys(), key=lambda s: -pre_post[s]["pre_bugs"])[:14]
    pre_rates = [pre_post[s]["pre_rate"] for s in specs]
    post_rates = [pre_post[s]["post_rate"] for s in specs]
    pre_n = [pre_post[s]["pre_bugs"] for s in specs]
    post_n = [pre_post[s]["post_bugs"] for s in specs]

    fig, ax = plt.subplots(figsize=(13, 6))
    x = list(range(len(specs)))
    w = 0.4
    ax.bar([xi - w/2 for xi in x], pre_rates, w, color="#d62728",
           alpha=0.85, label="pre-saturation")
    ax.bar([xi + w/2 for xi in x], post_rates, w, color="#1f77b4",
           alpha=0.85, label="post-saturation")
    for i, s in enumerate(specs):
        ax.text(i, max(pre_rates[i], post_rates[i]),
                f" {pre_n[i]}/{post_n[i]}", ha="center", va="bottom",
                fontsize=7, alpha=0.6)
    ax.set_xticks(x)
    ax.set_xticklabels(specs, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("Mean N-bugs per (driver, month) cell")
    ax.set_title("M9: Bug rate before vs after spec coverage saturation\n"
                 "(saturation = month total file-count first ≥80% of eventual peak; "
                 "labels: pre/post bug counts)")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m9_saturation.png", dpi=120)
    plt.close()
    return {"name": "M9 saturation",
            "n_specs": len(pre_post),
            "details": {s: {**pre_post[s], "pre_rate": round(pre_post[s]["pre_rate"], 4),
                            "post_rate": round(pre_post[s]["post_rate"], 4)} for s in specs}}


# -------- M10: Sync lag scatter --------

def m10_sync_lag(panel, by_ds):
    """For each (driver, spec) pair: x = months between earliest spec test
    in any driver and this driver's first sync; y = total N bugs in that
    (driver, spec)."""
    # Earliest sync month per spec across all drivers
    earliest_per_spec = {}
    for (d, s), hist in by_ds.items():
        first = first_sync_month(hist)
        if first is None:
            continue
        if s not in earliest_per_spec or first < earliest_per_spec[s]:
            earliest_per_spec[s] = first

    points = []  # (spec, lag_months, total_bugs, driver)
    for (d, s), hist in by_ds.items():
        first = first_sync_month(hist)
        if first is None or s not in earliest_per_spec:
            continue
        lag = month_index(first) - month_index(earliest_per_spec[s])
        bugs = sum(v["n_bugs"] for _, v in hist)
        points.append((s, lag, bugs, d))

    fig, ax = plt.subplots(figsize=(10, 6))
    spec_color = {}
    palette = plt.get_cmap("tab20").colors
    for i, sp in enumerate(sorted({p[0] for p in points})):
        spec_color[sp] = palette[i % len(palette)]
    xs = [p[1] for p in points]
    ys = [p[2] for p in points]
    cs = [spec_color[p[0]] for p in points]
    ax.scatter(xs, ys, c=cs, alpha=0.7, s=24)
    # Linear fit
    if len(xs) > 1:
        n = len(xs)
        mx = sum(xs) / n
        my = sum(ys) / n
        num = sum((x - mx) * (y - my) for x, y in zip(xs, ys))
        den = sum((x - mx) ** 2 for x in xs)
        slope = num / den if den else 0
        intercept = my - slope * mx
        # Pearson r
        sd_x = math.sqrt(den / n)
        sd_y = math.sqrt(sum((y - my) ** 2 for y in ys) / n)
        r = num / (n * sd_x * sd_y) if (sd_x * sd_y) else 0
        x_min, x_max = min(xs), max(xs)
        ax.plot([x_min, x_max], [slope * x_min + intercept, slope * x_max + intercept],
                "k--", lw=1.5, alpha=0.6, label=f"OLS slope={slope:.3f}, r={r:.3f}")
        ax.legend()
    ax.set_xlabel("Sync lag: this driver's first-sync − earliest first-sync across drivers (months)")
    ax.set_ylabel("Total N-bugs filed in this (driver, spec) cell")
    ax.set_title(f"M10: Sync lag vs total bug count (each point = (driver, spec); n={len(points)})")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m10_sync_lag.png", dpi=120)
    plt.close()
    return {"name": "M10 sync lag",
            "n_points": len(points),
            "slope": round(slope, 4) if len(xs) > 1 else None,
            "pearson_r": round(r, 3) if len(xs) > 1 else None}


# -------- M11: Synced vs unsynced share over calendar time --------

def m11_share(panel):
    """For each calendar year, compute the fraction of N-bugs filed in
    (driver, spec, month) cells that had test files at that moment vs
    cells that didn't."""
    yearly = defaultdict(lambda: {"with_tests": 0, "without_tests": 0,
                                   "cells_with": 0, "cells_without": 0})
    for (d, s, m), v in panel.items():
        year = m[:4]
        if v["n_files"] > 0:
            yearly[year]["with_tests"] += v["n_bugs"]
            yearly[year]["cells_with"] += 1
        else:
            yearly[year]["without_tests"] += v["n_bugs"]
            yearly[year]["cells_without"] += 1
    years = sorted(yearly.keys())
    if not years:
        return {"name": "M11 share", "details": "no data"}
    fig, axes = plt.subplots(2, 1, figsize=(12, 8), sharex=True)

    # Top: total bug counts stacked
    with_t = [yearly[y]["with_tests"] for y in years]
    without_t = [yearly[y]["without_tests"] for y in years]
    axes[0].bar(years, without_t, color="#d62728", alpha=0.85, label="cells without tests")
    axes[0].bar(years, with_t, bottom=without_t, color="#1f77b4", alpha=0.85,
                label="cells with ≥1 test file")
    axes[0].set_ylabel("Total N-bugs created")
    axes[0].set_title("M11: N-bugs by year, split by whether the (driver, spec) cell had test files")
    axes[0].legend()
    axes[0].grid(True, alpha=0.3, axis="y")

    # Bottom: per-cell rates, divided
    with_rate = [yearly[y]["with_tests"] / max(1, yearly[y]["cells_with"]) for y in years]
    without_rate = [yearly[y]["without_tests"] / max(1, yearly[y]["cells_without"]) for y in years]
    axes[1].plot(years, with_rate, "o-", color="#1f77b4", lw=2, label="cells with tests")
    axes[1].plot(years, without_rate, "o-", color="#d62728", lw=2, label="cells without tests")
    axes[1].set_ylabel("Mean N-bugs per cell-month")
    axes[1].set_xlabel("Year")
    axes[1].legend()
    axes[1].grid(True, alpha=0.3)
    axes[1].tick_params(axis="x", rotation=45)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m11_share.png", dpi=120)
    plt.close()
    return {"name": "M11 share",
            "yearly": {y: {"with_tests": yearly[y]["with_tests"],
                           "without_tests": yearly[y]["without_tests"]}
                       for y in years[-5:]}}


# -------- M12: Driver-detrended event study --------

def m12_detrended(panel, by_ds):
    """For each (driver, spec, month), compute residual = cell_bugs −
    driver's average monthly bug rate that year (across all specs).
    Then do an event study around first sync. The detrending removes
    driver-year-specific calendar effects."""
    # Compute driver-year monthly bug rate (across all specs)
    driver_year_total = defaultdict(int)
    driver_year_cells = defaultdict(int)
    for (d, s, m), v in panel.items():
        y = m[:4]
        driver_year_total[(d, y)] += v["n_bugs"]
        driver_year_cells[(d, y)] += 1
    driver_year_rate = {k: driver_year_total[k] / driver_year_cells[k]
                         for k in driver_year_total}

    # Event study with detrending
    rel_resid = defaultdict(list)
    for (d, s), hist in by_ds.items():
        first = first_sync_month(hist)
        if first is None:
            continue
        first_idx = month_index(first)
        for m, v in hist:
            y = m[:4]
            baseline = driver_year_rate.get((d, y), 0)
            resid = v["n_bugs"] - baseline
            rel = month_index(m) - first_idx
            if -36 <= rel <= 60:
                rel_resid[rel].append(resid)

    rels = sorted(rel_resid.keys())
    means = [sum(rel_resid[r]) / len(rel_resid[r]) for r in rels]
    smooth = []
    win = 6
    for i in range(len(rels)):
        lo = max(0, i - win)
        hi = min(len(means), i + win + 1)
        smooth.append(sum(means[lo:hi]) / (hi - lo))

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axvline(0, color="red", lw=1, alpha=0.6, label="first sync")
    ax.axhline(0, color="black", lw=1, alpha=0.6)
    ax.plot(rels, means, lw=1, color="#1f77b4", alpha=0.5, label="raw residual")
    ax.plot(rels, smooth, lw=2.5, color="#ff7f0e", label="smoothed (±6 mo)")
    ax.set_xlabel("Months relative to first sync")
    ax.set_ylabel("Residual N-bugs per cell-month\n(after subtracting driver-year mean)")
    ax.set_title("M12: Driver-detrended event study\n"
                 "(positive = above driver's typical rate that year; spike at sync should show, "
                 "long-run residual ≤ 0 would mean post-sync rate is below driver baseline)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m12_detrended.png", dpi=120)
    plt.close()

    # Mean residual in pre/post windows
    pre_resid = [m for r, m in zip(rels, means) if -36 <= r < 0]
    post_resid = [m for r, m in zip(rels, means) if 0 < r <= 36]
    pre_mean = sum(pre_resid) / len(pre_resid) if pre_resid else 0
    post_mean = sum(post_resid) / len(post_resid) if post_resid else 0
    return {"name": "M12 detrended",
            "pre_mean_residual": round(pre_mean, 4),
            "post_mean_residual": round(post_mean, 4),
            "diff": round(post_mean - pre_mean, 4)}


# -------- M13: Long-run rate breakdown --------

def m13_longrun(panel, by_ds):
    """For each (driver, spec) with a sync, compute bug rate in five windows:
    pre[-36..-1], spike[0..3], early[4..15], mid[16..35], late[36..59]."""
    windows = [(-36, -1, "pre"), (0, 3, "spike"),
               (4, 15, "early"), (16, 35, "mid"), (36, 59, "late")]
    win_rates = defaultdict(list)
    used = 0
    for (d, s), hist in by_ds.items():
        first = first_sync_month(hist)
        if first is None:
            continue
        first_idx = month_index(first)
        history = {m: v for m, v in hist}
        for lo, hi, label in windows:
            n_bugs = 0
            n_months = 0
            for off in range(lo, hi + 1):
                m = index_to_month(first_idx + off)
                if m in history:
                    n_bugs += history[m]["n_bugs"]
                    n_months += 1
            if n_months > 0:
                win_rates[label].append(n_bugs / n_months)
        used += 1

    labels = [w[2] for w in windows]
    means = [sum(win_rates[l]) / len(win_rates[l]) if win_rates[l] else 0 for l in labels]
    counts = [len(win_rates[l]) for l in labels]

    fig, ax = plt.subplots(figsize=(10, 5))
    colors = ["#888", "#d62728", "#ff7f0e", "#2ca02c", "#1f77b4"]
    bars = ax.bar(labels, means, color=colors, alpha=0.85)
    for bar, n in zip(bars, counts):
        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                f"n={n}", ha="center", va="bottom", fontsize=9)
    pre_mean = means[0]
    if pre_mean:
        ax.axhline(pre_mean, color="black", linestyle="--", lw=1, alpha=0.5,
                   label=f"pre rate = {pre_mean:.3f}")
        ax.legend()
    ax.set_ylabel("Mean N-bugs per cell-month")
    ax.set_xlabel("Window relative to first sync (months)")
    ax.set_title(f"M13: Long-run rate breakdown around first sync (n_cells={used})\n"
                 f"Question: does any post-sync window go below the pre-sync baseline?")
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m13_longrun.png", dpi=120)
    plt.close()
    return {"name": "M13 long-run",
            "n_cells": used,
            "windows": dict(zip(labels, [round(x, 4) for x in means]))}


# -------- main --------

def main():
    PLOT_DIR.mkdir(exist_ok=True)
    panel = load_panel()
    by_ds = by_driver_spec(panel)

    results = []
    print("M9: spec coverage saturation")
    results.append(m9_saturation(panel))
    print(f"  {results[-1]['name']}: {results[-1].get('n_specs', '?')} specs")

    print("M10: sync lag scatter")
    results.append(m10_sync_lag(panel, by_ds))
    print(f"  {results[-1]}")

    print("M11: synced vs unsynced share")
    results.append(m11_share(panel))
    print(f"  {results[-1]['name']}")

    print("M12: driver-detrended event study")
    results.append(m12_detrended(panel, by_ds))
    print(f"  {results[-1]}")

    print("M13: long-run rate windows")
    results.append(m13_longrun(panel, by_ds))
    print(f"  {results[-1]}")

    import json
    out = DATA / "methodology_results_extra.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
