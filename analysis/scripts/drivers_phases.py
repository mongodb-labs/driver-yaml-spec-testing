"""Per-driver phase summary: when each spec area first appeared in each
driver's tree, and growth phases.

Reads data/drivers_timeline.csv and prints a per-driver report.
Also writes data/drivers_phases.csv.
"""
import csv
from collections import defaultdict
from pathlib import Path

IN_CSV = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data/drivers_timeline.csv")
OUT_CSV = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data/drivers_phases.csv")


def main():
    by_driver_dir = defaultdict(list)
    with IN_CSV.open() as f:
        for row in csv.DictReader(f):
            key = (row["driver"], row["spec"])
            by_driver_dir[key].append({
                "month": row["month"],
                "n_files": int(row["n_files"]),
                "n_lines": int(row["n_lines"]),
                "commit": row["commit"],
            })

    phases = []
    summary = []
    for (driver, d), hist in by_driver_dir.items():
        hist.sort(key=lambda r: r["month"])
        first = hist[0]
        last = hist[-1]
        peak = max(hist, key=lambda r: r["n_lines"])
        prev = None
        events = []
        for snap in hist:
            if prev is None:
                events.append({
                    "driver": driver, "spec": d, "month": snap["month"],
                    "kind": "intro", "n_files": snap["n_files"],
                    "n_lines": snap["n_lines"],
                    "delta_files": snap["n_files"], "delta_lines": snap["n_lines"],
                    "commit": snap["commit"],
                })
            else:
                df = snap["n_files"] - prev["n_files"]
                dl = snap["n_lines"] - prev["n_lines"]
                if (df >= 5 and prev["n_files"] > 0 and df / prev["n_files"] >= 0.5) or \
                   (dl >= 1000 and prev["n_lines"] > 0 and dl / prev["n_lines"] >= 0.5):
                    events.append({
                        "driver": driver, "spec": d, "month": snap["month"],
                        "kind": "phase", "n_files": snap["n_files"],
                        "n_lines": snap["n_lines"],
                        "delta_files": df, "delta_lines": dl,
                        "commit": snap["commit"],
                    })
            prev = snap
        phases.extend(events)
        summary.append({
            "driver": driver, "spec": d,
            "intro_month": first["month"],
            "intro_files": first["n_files"], "intro_lines": first["n_lines"],
            "peak_month": peak["month"], "peak_lines": peak["n_lines"],
            "final_month": last["month"],
            "final_files": last["n_files"], "final_lines": last["n_lines"],
            "n_phase_events": len([e for e in events if e["kind"] == "phase"]),
        })

    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["driver", "spec", "month", "kind", "n_files",
                                          "n_lines", "delta_files", "delta_lines", "commit"])
        w.writeheader()
        w.writerows(phases)

    # Print one section per driver
    summary.sort(key=lambda r: (r["driver"], r["intro_month"]))
    cur = None
    for s in summary:
        if s["driver"] != cur:
            cur = s["driver"]
            print(f"\n\n========== {cur} ==========")
            print(f"{'spec':<40} {'intro':<8} {'final':<8} {'files':>5} {'lines':>7} {'phases':>6}")
        print(f"{s['spec']:<40} {s['intro_month']:<8} {s['final_month']:<8} "
              f"{s['final_files']:>5} {s['final_lines']:>7} {s['n_phase_events']:>6}")

    # Print phase events grouped per driver
    by_driver_dir_events = defaultdict(list)
    for e in phases:
        by_driver_dir_events[(e["driver"], e["spec"])].append(e)
    cur = None
    for (driver, d), evs in sorted(by_driver_dir_events.items()):
        if driver != cur:
            cur = driver
            print(f"\n\n========== {driver}: PHASE EVENTS ==========")
        if any(ev["kind"] == "phase" for ev in evs):
            print(f"\n[{d}]")
            for ev in evs:
                kind = "intro " if ev["kind"] == "intro" else "phase "
                print(f"  {ev['month']}  {kind} files={ev['n_files']:>4}  "
                      f"lines={ev['n_lines']:>6}  Δfiles={ev['delta_files']:+d}  "
                      f"Δlines={ev['delta_lines']:+d}  ({ev['commit']})")


if __name__ == "__main__":
    main()
