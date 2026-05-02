"""One chart per driver, with one line per spec area.
Y-axis: non-comment lines of YAML/JSON spec test code in the driver tree.

For copy-based drivers, sourced from data/drivers_timeline.csv.
For submodule-based drivers (JAVA, GODRIVER, PHPLIB), the effective view at
month M is max(local-copy lines, submodule lines), which smooths over the
copy→submodule transition.
"""
import csv
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

DATA = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data")
PLOT_DIR = DATA / "plots"
PLOT_DIR.mkdir(exist_ok=True)

SUBMODULE_DRIVERS = {"JAVA", "GODRIVER", "PHPLIB"}


def to_dt(month):
    return datetime.strptime(month + "-01", "%Y-%m-%d")


def main():
    # (driver, month, spec) -> n_lines
    copy = defaultdict(int)
    with (DATA / "drivers_timeline.csv").open() as f:
        for r in csv.DictReader(f):
            copy[(r["driver"], r["month"], r["spec"])] = int(r["n_lines"])

    sub = defaultdict(int)
    with (DATA / "drivers_submodule_timeline.csv").open() as f:
        for r in csv.DictReader(f):
            sub[(r["driver"], r["month"], r["spec"])] = int(r["n_lines"])

    # Combine: for submodule-based drivers, max(copy, sub); else copy only.
    combined = defaultdict(int)
    for key, v in copy.items():
        combined[key] = v
    for key, v in sub.items():
        if key[0] in SUBMODULE_DRIVERS:
            combined[key] = max(combined[key], v)

    # Group by driver
    by_driver = defaultdict(lambda: defaultdict(dict))  # driver -> spec -> {month -> lines}
    for (driver, month, spec), v in combined.items():
        by_driver[driver][spec][month] = v

    for driver in sorted(by_driver.keys()):
        spec_to_months = by_driver[driver]
        # Pick top 12 specs by peak value
        peaks = {s: max(m.values()) for s, m in spec_to_months.items()}
        top = [s for s, _ in sorted(peaks.items(), key=lambda x: -x[1])[:12]]
        all_months = sorted({m for s in top for m in spec_to_months[s]})
        if not all_months:
            continue
        xs = [to_dt(m) for m in all_months]

        fig, ax = plt.subplots(figsize=(13, 7))
        for spec in top:
            ys = [spec_to_months[spec].get(m, 0) for m in all_months]
            ax.plot(xs, ys, lw=1.7, label=spec, alpha=0.9)
        ax.set_title(f"{driver}: non-comment YAML/JSON spec-test lines per spec area")
        ax.set_xlabel("Month")
        ax.set_ylabel("Non-comment lines")
        ax.legend(loc="upper left", fontsize=8, ncol=2)
        ax.grid(True, alpha=0.3)
        ax.xaxis.set_major_locator(mdates.YearLocator())
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        plt.tight_layout()
        out = PLOT_DIR / f"per_driver_specs_{driver}.png"
        plt.savefig(out, dpi=120)
        plt.close()
        print(f"  wrote {out.name}")


if __name__ == "__main__":
    main()
