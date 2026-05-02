"""Emit per-driver markdown sections for yaml_tests_timeline.md.

For each driver, prints:
- Path layout (most populated test root at last snapshot)
- Per-spec summary table (intro / final / files / lines / phases)
- Major phase events list

Reads data/drivers_timeline.csv and data/drivers_phases.csv.
"""
import csv
from collections import defaultdict
from pathlib import Path

DATA = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data")


def load(path):
    with (DATA / path).open() as f:
        return list(csv.DictReader(f))


def main():
    timeline = load("drivers_timeline.csv")
    phases = load("drivers_phases.csv")

    by_driver = defaultdict(list)
    for r in timeline:
        by_driver[r["driver"]].append(r)
    phases_by_driver = defaultdict(list)
    for r in phases:
        phases_by_driver[r["driver"]].append(r)

    for driver in sorted(by_driver.keys()):
        rows = by_driver[driver]
        # Per-spec stats
        by_spec = defaultdict(list)
        for r in rows:
            by_spec[r["spec"]].append(r)
        summary = []
        for spec, hist in by_spec.items():
            hist.sort(key=lambda r: r["month"])
            first = hist[0]
            last = hist[-1]
            phase_count = sum(1 for p in phases_by_driver[driver]
                              if p["spec"] == spec and p["kind"] == "phase")
            summary.append({
                "spec": spec,
                "intro_month": first["month"],
                "final_month": last["month"],
                "final_files": int(last["n_files"]),
                "final_lines": int(last["n_lines"]),
                "n_phases": phase_count,
                "sample": first["sample_path"],
            })
        summary.sort(key=lambda x: x["intro_month"])

        # Find most-populated test root path
        root_counts = defaultdict(int)
        for r in rows[-100:]:  # sample latest snapshots
            sp = r.get("sample_path") or ""
            if "/" in sp:
                root = "/".join(sp.split("/")[:3])  # top-3 components
                root_counts[root] += int(r["n_files"])
        top_roots = sorted(root_counts.items(), key=lambda x: -x[1])[:5]

        # Get driver totals over time
        by_month = defaultdict(int)
        for r in rows:
            by_month[r["month"]] += int(r["n_lines"])
        all_months = sorted(by_month.keys())
        first_lines = by_month[all_months[0]]
        last_lines = by_month[all_months[-1]]
        peak_month = max(all_months, key=lambda m: by_month[m])
        peak_lines = by_month[peak_month]

        print(f"\n### {driver}\n")
        print(f"**Path layout** (top sample-path roots at recent snapshots):")
        for root, count in top_roots:
            print(f"- `{root}/...` (~{count} cumulative file-rows)")
        print()
        print(f"**Total spec-test lines:** first month {all_months[0]} → "
              f"{first_lines:,} lines; peak {peak_month} → {peak_lines:,}; "
              f"last month {all_months[-1]} → {last_lines:,}.")
        print()
        print(f"**Per-spec summary** (rows sorted by introduction month):\n")
        print(f"| Spec area | Intro | Final | Files | Lines | Phases |")
        print(f"|---|---|---|---:|---:|---:|")
        for s in summary:
            print(f"| {s['spec']} | {s['intro_month']} | {s['final_month']} | "
                  f"{s['final_files']} | {s['final_lines']:,} | {s['n_phases']} |")

        # Phase events list
        relevant_events = [p for p in phases_by_driver[driver]
                           if p["kind"] == "phase"]
        if relevant_events:
            print(f"\n**Major phase events** (≥50% growth in files or lines, "
                  f"with absolute floors of +5 files or +1000 lines):\n")
            relevant_events.sort(key=lambda p: p["month"])
            for ev in relevant_events:
                df = int(ev["delta_files"])
                dl = int(ev["delta_lines"])
                print(f"- {ev['month']} `{ev['spec']}`: files {ev['n_files']}"
                      f" (+{df}), lines {int(ev['n_lines']):,} (+{dl:,})"
                      f" — driver commit `{ev['commit']}`")


if __name__ == "__main__":
    main()
