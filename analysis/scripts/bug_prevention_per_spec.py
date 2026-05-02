"""Per-spec event study: each subplot shows bug rate around first-sync for
ONE spec area, averaged across drivers. Lets us see which specs show the
effect cleanest.

Also: M14 = files-vs-lines as predictor (which is a stronger signal of
subsidence?); M15 = spec-detrended event study; M16 = ratio of new bugs
to test asset volume per year per spec.
"""
import csv
import math
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

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


# -------- M14: per-spec event study --------

def m14_per_spec_event(panel, by_ds):
    spec_data = defaultdict(lambda: defaultdict(list))  # spec -> rel -> [bugs]
    spec_n_drivers = defaultdict(int)
    for (d, s), hist in by_ds.items():
        first = first_sync_month(hist)
        if first is None:
            continue
        first_idx = month_index(first)
        spec_n_drivers[s] += 1
        for m, v in hist:
            rel = month_index(m) - first_idx
            if -36 <= rel <= 60:
                spec_data[s][rel].append(v["n_bugs"])

    # Pick top 12 specs by n_drivers
    top_specs = [s for s, _ in sorted(spec_n_drivers.items(), key=lambda x: -x[1])[:12]]
    fig, axes = plt.subplots(4, 3, figsize=(16, 14), sharex=True)
    axes = axes.flatten()
    for i, spec in enumerate(top_specs):
        ax = axes[i]
        rels = sorted(spec_data[spec].keys())
        means = [sum(spec_data[spec][r]) / len(spec_data[spec][r]) for r in rels]
        # Smooth
        smooth = []
        win = 4
        for j in range(len(rels)):
            lo = max(0, j - win)
            hi = min(len(means), j + win + 1)
            smooth.append(sum(means[lo:hi]) / (hi - lo))
        ax.axvline(0, color="red", lw=1, alpha=0.5)
        ax.plot(rels, means, lw=0.8, color="#1f77b4", alpha=0.4)
        ax.plot(rels, smooth, lw=2, color="#ff7f0e")
        ax.set_title(f"{spec} (n_drivers={spec_n_drivers[spec]})", fontsize=10)
        ax.grid(True, alpha=0.3)
        if i % 3 == 0:
            ax.set_ylabel("bugs/cell-month", fontsize=8)
        if i >= 9:
            ax.set_xlabel("months relative to first sync", fontsize=8)
    fig.suptitle("M14: Per-spec event study (one panel per top-12 spec; drivers averaged)",
                 fontsize=12)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m14_per_spec_event.png", dpi=120)
    plt.close()
    return {"name": "M14 per-spec event", "n_specs": len(top_specs)}


# -------- M15: spec-detrended event study --------

def m15_spec_detrended(panel, by_ds):
    """Compute residual = cell_bugs - mean of spec at calendar month."""
    spec_month_total = defaultdict(int)
    spec_month_cells = defaultdict(int)
    for (d, s, m), v in panel.items():
        spec_month_total[(s, m)] += v["n_bugs"]
        spec_month_cells[(s, m)] += 1
    spec_month_mean = {k: spec_month_total[k] / spec_month_cells[k]
                        for k in spec_month_total}

    rel_resid = defaultdict(list)
    for (d, s), hist in by_ds.items():
        first = first_sync_month(hist)
        if first is None:
            continue
        first_idx = month_index(first)
        for m, v in hist:
            baseline = spec_month_mean.get((s, m), 0)
            resid = v["n_bugs"] - baseline
            rel = month_index(m) - first_idx
            if -36 <= rel <= 60:
                rel_resid[rel].append(resid)

    rels = sorted(rel_resid.keys())
    means = [sum(rel_resid[r]) / len(rel_resid[r]) for r in rels]
    smooth = []
    win = 6
    for j in range(len(rels)):
        lo = max(0, j - win)
        hi = min(len(means), j + win + 1)
        smooth.append(sum(means[lo:hi]) / (hi - lo))

    fig, ax = plt.subplots(figsize=(12, 6))
    ax.axvline(0, color="red", lw=1, alpha=0.6, label="first sync")
    ax.axhline(0, color="black", lw=1, alpha=0.6)
    ax.plot(rels, means, lw=1, color="#1f77b4", alpha=0.5)
    ax.plot(rels, smooth, lw=2.5, color="#ff7f0e", label="smoothed")
    ax.set_xlabel("Months relative to first sync")
    ax.set_ylabel("Residual N-bugs per cell-month\n"
                  "(after subtracting spec's mean rate that calendar month)")
    ax.set_title("M15: Spec-detrended event study\n"
                 "(positive = above peer-driver rate for this spec at this time)")
    ax.legend()
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m15_spec_detrended.png", dpi=120)
    plt.close()

    pre = [m for r, m in zip(rels, means) if -36 <= r < 0]
    post_short = [m for r, m in zip(rels, means) if 0 < r <= 12]
    post_long = [m for r, m in zip(rels, means) if 24 <= r <= 60]
    return {"name": "M15 spec-detrended",
            "pre_mean": round(sum(pre)/len(pre), 4) if pre else 0,
            "post_short_mean": round(sum(post_short)/len(post_short), 4) if post_short else 0,
            "post_long_mean": round(sum(post_long)/len(post_long), 4) if post_long else 0}


# -------- M16: aggregate per-spec bugs vs coverage over time --------

def m16_per_spec_correlation(panel):
    """For each spec, build a yearly time series of:
    - total N-bugs across drivers
    - total file count across drivers (sum at end of year)
    Then compute correlation between bugs(t) and coverage(t).
    A negative correlation, especially after a lag, would support the
    'tests reduce bugs' hypothesis."""
    spec_year_bugs = defaultdict(lambda: defaultdict(int))
    spec_year_files = defaultdict(lambda: defaultdict(int))
    for (d, s, m), v in panel.items():
        y = m[:4]
        spec_year_bugs[s][y] += v["n_bugs"]
        if m.endswith("-12"):
            spec_year_files[s][y] += v["n_files"]
        else:
            # use latest entry for the year
            cur = spec_year_files[s].get(y, 0)
            spec_year_files[s][y] = max(cur, 0)
    # actually let me redo this properly: end-of-year file totals
    spec_year_files = defaultdict(lambda: defaultdict(int))
    for (d, s, m), v in panel.items():
        y, mn = m[:4], m[5:7]
        # take december or last available
        cur_month = spec_year_files[s].get(("month", y), "0000-00")
        if m > cur_month:
            spec_year_files[s][("month", y)] = m
            # don't add yet, we want the sum across drivers at the latest month per year
    # Simpler: sum file counts in december each year across drivers
    dec_files = defaultdict(lambda: defaultdict(int))
    for (d, s, m), v in panel.items():
        if m.endswith("-12"):
            y = m[:4]
            dec_files[s][y] += v["n_files"]

    fig, axes = plt.subplots(3, 4, figsize=(16, 11))
    axes = axes.flatten()
    spec_totals = {s: sum(d.values()) for s, d in spec_year_bugs.items()}
    top = [s for s, _ in sorted(spec_totals.items(), key=lambda x: -x[1])[:12]]
    for i, spec in enumerate(top):
        ax = axes[i]
        years = sorted(set(spec_year_bugs[spec]) | set(dec_files[spec]))
        bugs = [spec_year_bugs[spec].get(y, 0) for y in years]
        files = [dec_files[spec].get(y, 0) for y in years]
        ax2 = ax.twinx()
        ax.bar(years, bugs, color="#d62728", alpha=0.6, label="N-bugs/yr")
        ax2.plot(years, files, "o-", color="#1f77b4", lw=1.7, label="file count (Dec, summed)")
        ax.set_title(spec, fontsize=9)
        ax.tick_params(axis="x", rotation=45, labelsize=6)
        ax.set_ylabel("N-bugs", fontsize=7, color="#d62728")
        ax2.set_ylabel("# files", fontsize=7, color="#1f77b4")
        ax.grid(True, alpha=0.2)
    fig.suptitle("M16: Per-spec yearly bugs (red) vs total file-count across drivers at year-end (blue)",
                 fontsize=12)
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m16_per_spec_correlation.png", dpi=120)
    plt.close()
    return {"name": "M16 per-spec correlation"}


# -------- M17: same-calendar-month coverage comparison --------

def m17_within_spec_calendar(panel):
    """For each (spec, calendar_month), partition driver cells into
    'has tests' (n_files >= 1) and 'no tests'. Compare bug rates within
    the same calendar window. This controls for spec-specific calendar
    effects."""
    by_sm = defaultdict(lambda: {"with": [], "without": []})
    for (d, s, m), v in panel.items():
        bucket = "with" if v["n_files"] >= 1 else "without"
        by_sm[(s, m)][bucket].append(v["n_bugs"])

    # For each spec, sum across calendar months that have at least one
    # driver in each bucket (ensuring overlapping period)
    spec_compare = {}
    for spec in {k[0] for k in by_sm}:
        with_total = with_n = without_total = without_n = 0
        for (s, m), buckets in by_sm.items():
            if s != spec:
                continue
            if buckets["with"] and buckets["without"]:
                with_total += sum(buckets["with"])
                with_n += len(buckets["with"])
                without_total += sum(buckets["without"])
                without_n += len(buckets["without"])
        if with_n and without_n:
            spec_compare[spec] = {
                "with_rate": with_total / with_n,
                "without_rate": without_total / without_n,
                "with_n": with_n,
                "without_n": without_n,
                "with_bugs": with_total,
                "without_bugs": without_total,
            }

    # Plot
    specs = sorted(spec_compare.keys(),
                   key=lambda s: -(spec_compare[s]["with_bugs"] + spec_compare[s]["without_bugs"]))[:14]
    if not specs:
        return {"name": "M17 within-spec calendar", "details": "no overlap"}
    with_rates = [spec_compare[s]["with_rate"] for s in specs]
    without_rates = [spec_compare[s]["without_rate"] for s in specs]
    fig, ax = plt.subplots(figsize=(13, 6))
    x = list(range(len(specs)))
    w = 0.4
    ax.bar([xi - w/2 for xi in x], with_rates, w, color="#1f77b4",
           alpha=0.85, label="cells with tests (n_files ≥ 1)")
    ax.bar([xi + w/2 for xi in x], without_rates, w, color="#d62728",
           alpha=0.85, label="cells without tests (n_files = 0)")
    for i, s in enumerate(specs):
        ax.text(i, max(with_rates[i], without_rates[i]),
                f" {spec_compare[s]['with_bugs']}/{spec_compare[s]['without_bugs']}",
                ha="center", va="bottom", fontsize=7, alpha=0.7)
    ax.set_xticks(x)
    ax.set_xticklabels(specs, rotation=40, ha="right", fontsize=8)
    ax.set_ylabel("Mean N-bugs per cell-month")
    ax.set_title("M17: Within-spec, within-calendar-month: cells with tests vs cells without\n"
                 "(only months where the spec has both populations contribute; "
                 "labels: bugs in tested/untested cells)")
    ax.legend()
    ax.grid(True, alpha=0.3, axis="y")
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "m17_within_spec_cal.png", dpi=120)
    plt.close()

    # Aggregate
    agg_with = sum(spec_compare[s]["with_bugs"] for s in specs)
    agg_with_n = sum(spec_compare[s]["with_n"] for s in specs)
    agg_without = sum(spec_compare[s]["without_bugs"] for s in specs)
    agg_without_n = sum(spec_compare[s]["without_n"] for s in specs)
    return {"name": "M17 within-spec calendar",
            "agg_with_rate": round(agg_with / agg_with_n, 4) if agg_with_n else 0,
            "agg_without_rate": round(agg_without / agg_without_n, 4) if agg_without_n else 0,
            "n_specs": len(specs)}


def main():
    PLOT_DIR.mkdir(exist_ok=True)
    panel = load_panel()
    by_ds = by_driver_spec(panel)

    results = []
    print("M14: per-spec event study")
    results.append(m14_per_spec_event(panel, by_ds))
    print(f"  {results[-1]}")

    print("M15: spec-detrended event study")
    results.append(m15_spec_detrended(panel, by_ds))
    print(f"  {results[-1]}")

    print("M16: per-spec aggregated bugs vs coverage")
    results.append(m16_per_spec_correlation(panel))
    print(f"  {results[-1]}")

    print("M17: within-spec calendar comparison")
    results.append(m17_within_spec_calendar(panel))
    print(f"  {results[-1]}")

    import json
    out = DATA / "methodology_results_per_spec.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\nWrote {out}")


if __name__ == "__main__":
    main()
