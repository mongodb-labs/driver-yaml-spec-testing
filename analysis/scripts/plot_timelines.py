"""Generate matplotlib charts for the YAML test timeline report.

Outputs (PNG files in data/plots/):
- specs_total.png         total YAML lines across all spec areas, over time
- specs_per_spec.png      stacked area chart of YAML lines per top-12 spec
- specs_intro.png         scatter showing introduction month for each spec
- driver_<DRIVER>.png     per-driver line chart of total spec-test lines over time
"""
import csv
import sys
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import datetime

DATA = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data")
PLOT_DIR = DATA / "plots"
PLOT_DIR.mkdir(exist_ok=True)


def to_dt(month):
    return datetime.strptime(month + "-01", "%Y-%m-%d")


def load_specs_timeline():
    rows = []
    with (DATA / "specs_timeline.csv").open() as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def load_drivers_timeline():
    rows = []
    p = DATA / "drivers_timeline.csv"
    if not p.exists():
        return rows
    with p.open() as f:
        for r in csv.DictReader(f):
            rows.append(r)
    return rows


def specs_total():
    rows = load_specs_timeline()
    by_month = defaultdict(int)
    for r in rows:
        by_month[r["month"]] += int(r["n_lines"])
    months = sorted(by_month.keys())
    xs = [to_dt(m) for m in months]
    ys = [by_month[m] for m in months]
    fig, ax = plt.subplots(figsize=(10, 5))
    ax.plot(xs, ys, lw=2, color="#1f77b4")
    ax.fill_between(xs, ys, alpha=0.2)
    ax.set_title("mongodb/specifications: total YAML test lines over time")
    ax.set_xlabel("Month")
    ax.set_ylabel("Total YAML lines (all spec areas)")
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "specs_total.png", dpi=120)
    plt.close()
    print(f"  wrote specs_total.png ({len(months)} months)")


def specs_per_spec_stacked():
    rows = load_specs_timeline()
    spec_max = defaultdict(int)
    for r in rows:
        spec_max[r["spec"]] = max(spec_max[r["spec"]], int(r["n_lines"]))
    top = [s for s, _ in sorted(spec_max.items(), key=lambda x: -x[1])[:12]]
    months = sorted({r["month"] for r in rows})
    by_month_spec = defaultdict(lambda: defaultdict(int))
    for r in rows:
        by_month_spec[r["month"]][r["spec"]] = int(r["n_lines"])
    xs = [to_dt(m) for m in months]
    series = []
    for spec in top:
        series.append([by_month_spec[m].get(spec, 0) for m in months])
    fig, ax = plt.subplots(figsize=(12, 6))
    ax.stackplot(xs, series, labels=top, alpha=0.85)
    ax.set_title("mongodb/specifications: YAML test lines per spec area (top 12)")
    ax.set_xlabel("Month")
    ax.set_ylabel("YAML lines")
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", fontsize=8)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "specs_per_spec.png", dpi=120)
    plt.close()
    print(f"  wrote specs_per_spec.png (top {len(top)} specs)")


def specs_intro_scatter():
    rows = load_specs_timeline()
    by_spec = defaultdict(list)
    for r in rows:
        by_spec[r["spec"]].append(r)
    points = []
    for spec, hist in by_spec.items():
        hist.sort(key=lambda r: r["month"])
        first_with_files = next((h for h in hist if int(h["n_files"]) > 0), None)
        if first_with_files is None:
            continue
        peak_lines = max(int(h["n_lines"]) for h in hist)
        points.append((to_dt(first_with_files["month"]), peak_lines, spec))
    points.sort(key=lambda p: p[0])
    fig, ax = plt.subplots(figsize=(12, 6))
    xs = [p[0] for p in points]
    ys = [p[1] for p in points]
    sizes = [max(40, p[1] / 100) for p in points]
    ax.scatter(xs, ys, s=sizes, alpha=0.6, color="#d62728")
    for x, y, label in points:
        ax.annotate(label, (x, y), fontsize=7, alpha=0.8,
                    xytext=(4, 4), textcoords="offset points")
    ax.set_title("Spec area introductions in mongodb/specifications")
    ax.set_xlabel("Month of first YAML test commit")
    ax.set_ylabel("Peak YAML lines")
    ax.set_yscale("symlog", linthresh=100)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "specs_intro.png", dpi=120)
    plt.close()
    print(f"  wrote specs_intro.png ({len(points)} specs)")


def driver_total_chart():
    rows = load_drivers_timeline()
    if not rows:
        print("  drivers_timeline.csv missing or empty; skipping driver charts")
        return
    by_driver_month = defaultdict(lambda: defaultdict(int))
    for r in rows:
        by_driver_month[r["driver"]][r["month"]] += int(r["n_lines"])
    drivers = sorted(by_driver_month.keys())
    fig, ax = plt.subplots(figsize=(12, 7))
    for d in drivers:
        months = sorted(by_driver_month[d].keys())
        xs = [to_dt(m) for m in months]
        ys = [by_driver_month[d][m] for m in months]
        ax.plot(xs, ys, lw=1.5, label=d, alpha=0.85)
    ax.set_title("Per-driver: total spec-test YAML/JSON lines over time")
    ax.set_xlabel("Month")
    ax.set_ylabel("Total spec-test lines")
    ax.legend(loc="upper left", fontsize=8, ncol=2)
    ax.grid(True, alpha=0.3)
    ax.xaxis.set_major_locator(mdates.YearLocator())
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    plt.tight_layout()
    plt.savefig(PLOT_DIR / "drivers_total.png", dpi=120)
    plt.close()
    print(f"  wrote drivers_total.png ({len(drivers)} drivers)")


def driver_per_spec_charts():
    """One chart per driver showing top-8 specs over time."""
    rows = load_drivers_timeline()
    if not rows:
        return
    by_driver = defaultdict(list)
    for r in rows:
        by_driver[r["driver"]].append(r)
    for driver, drows in sorted(by_driver.items()):
        spec_max = defaultdict(int)
        for r in drows:
            spec_max[r["spec"]] = max(spec_max[r["spec"]], int(r["n_lines"]))
        top = [s for s, _ in sorted(spec_max.items(), key=lambda x: -x[1])[:8]]
        months = sorted({r["month"] for r in drows})
        by_month_spec = defaultdict(lambda: defaultdict(int))
        for r in drows:
            by_month_spec[r["month"]][r["spec"]] = int(r["n_lines"])
        xs = [to_dt(m) for m in months]
        fig, ax = plt.subplots(figsize=(12, 6))
        for s in top:
            ys = [by_month_spec[m].get(s, 0) for m in months]
            ax.plot(xs, ys, lw=1.5, label=s, alpha=0.9)
        ax.set_title(f"{driver}: spec-test lines over time (top 8 spec areas)")
        ax.set_xlabel("Month")
        ax.set_ylabel("Spec-test lines (yml + json)")
        ax.legend(loc="upper left", fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        plt.tight_layout()
        plt.savefig(PLOT_DIR / f"driver_{driver}.png", dpi=120)
        plt.close()
        print(f"  wrote driver_{driver}.png")


if __name__ == "__main__":
    print("Generating plots...")
    specs_total()
    specs_per_spec_stacked()
    specs_intro_scatter()
    driver_total_chart()
    driver_per_spec_charts()
    print("Done")
