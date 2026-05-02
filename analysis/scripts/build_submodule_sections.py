"""Emit per-driver markdown for the submodule-based drivers.

For each (driver, spec), shows total YAML lines available via the submodule
at the first month they used it, and at the latest month.
"""
import csv
from collections import defaultdict
from pathlib import Path

DATA = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data")


def main():
    rows = list(csv.DictReader((DATA / "drivers_submodule_timeline.csv").open()))
    by_driver = defaultdict(list)
    for r in rows:
        by_driver[r["driver"]].append(r)

    for driver in sorted(by_driver.keys()):
        drows = by_driver[driver]
        # Submodule first/last month
        all_months = sorted({r["month"] for r in drows})
        first = all_months[0]
        last = all_months[-1]

        # Per spec at first vs last
        by_spec = defaultdict(dict)
        for r in drows:
            by_spec[r["spec"]][r["month"]] = (int(r["n_files"]), int(r["n_lines"]))

        # Find the unique submodule SHAs over time, with first appearance month
        shas = []
        last_sha = None
        for m in all_months:
            sha_for_m = next((r["submodule_sha"] for r in drows if r["month"] == m), None)
            if sha_for_m and sha_for_m != last_sha:
                shas.append((m, sha_for_m))
                last_sha = sha_for_m

        # Total lines at first/last month
        first_total = sum(by_spec[s].get(first, (0, 0))[1] for s in by_spec)
        last_total = sum(by_spec[s].get(last, (0, 0))[1] for s in by_spec)

        print(f"\n### {driver}\n")
        print(f"**Submodule first appears in repo:** {first} (driver still using "
              f"copy-based tests before that, see §3.{driver}).")
        print(f"**Total YAML lines available via submodule** at {first}: "
              f"{first_total:,}; at {last}: {last_total:,}.")
        print(f"**Distinct submodule SHAs over the period:** {len(shas)} bumps.")
        print(f"**First 6 SHA bumps:**")
        for m, sha in shas[:6]:
            print(f"  - {m}  →  specifications@{sha}")
        if len(shas) > 6:
            print(f"  - ... ({len(shas) - 6} more bumps)")

        # Per-spec at first and last
        print(f"\n**Per-spec at first vs latest month:**\n")
        print(f"| Spec area | At {first} | At {last} | Δ lines |")
        print(f"|---|---:|---:|---:|")
        # Sort by latest line count desc
        specs = sorted(by_spec.keys(),
                       key=lambda s: -by_spec[s].get(last, (0, 0))[1])
        for spec in specs:
            f_files, f_lines = by_spec[spec].get(first, (0, 0))
            l_files, l_lines = by_spec[spec].get(last, (0, 0))
            d_lines = l_lines - f_lines
            print(f"| {spec} | {f_files} files / {f_lines:,} lines | "
                  f"{l_files} files / {l_lines:,} lines | "
                  f"{d_lines:+,} |")


if __name__ == "__main__":
    main()
