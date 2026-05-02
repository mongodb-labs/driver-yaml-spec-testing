"""Identify YAML test introduction and growth phases per spec area.

For each spec, detect:
- First month with any YAML files (introduction)
- Major growth phases: months where n_files or n_lines grew by >=30% vs prior month
- Final state

Output: data/specs_phases.csv (per-spec phase events)
        prints a markdown-friendly summary table to stdout
"""
import csv
from collections import defaultdict
from pathlib import Path

IN_CSV = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data/specs_timeline.csv")
OUT_CSV = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data/specs_phases.csv")


def main():
    by_spec = defaultdict(list)  # spec -> [(month, n_files, n_lines), ...]
    with IN_CSV.open() as f:
        for row in csv.DictReader(f):
            by_spec[row["spec"]].append({
                "month": row["month"],
                "n_files": int(row["n_files"]),
                "n_lines": int(row["n_lines"]),
                "commit": row["commit"],
            })

    phases = []
    summary = []
    for spec, hist in sorted(by_spec.items()):
        hist.sort(key=lambda r: r["month"])
        first = hist[0]
        last = hist[-1]
        peak = max(hist, key=lambda r: r["n_lines"])
        # Identify major growth events (+30% lines vs prior month, with min jump >= 200 lines)
        prev = None
        events = []
        for snap in hist:
            if prev is None:
                # First month with any files = introduction
                events.append({
                    "spec": spec,
                    "month": snap["month"],
                    "kind": "intro",
                    "n_files": snap["n_files"],
                    "n_lines": snap["n_lines"],
                    "delta_files": snap["n_files"],
                    "delta_lines": snap["n_lines"],
                    "commit": snap["commit"],
                })
            else:
                df = snap["n_files"] - prev["n_files"]
                dl = snap["n_lines"] - prev["n_lines"]
                # Major phase: file count grew by >= 50% AND added >= 5 files,
                # OR line count grew by >= 50% AND added >= 1000 lines
                if (df >= 5 and prev["n_files"] > 0 and df / prev["n_files"] >= 0.5) or \
                   (dl >= 1000 and prev["n_lines"] > 0 and dl / prev["n_lines"] >= 0.5):
                    events.append({
                        "spec": spec,
                        "month": snap["month"],
                        "kind": "phase",
                        "n_files": snap["n_files"],
                        "n_lines": snap["n_lines"],
                        "delta_files": df,
                        "delta_lines": dl,
                        "commit": snap["commit"],
                    })
            prev = snap
        phases.extend(events)

        # Build summary row
        summary.append({
            "spec": spec,
            "intro_month": first["month"],
            "intro_files": first["n_files"],
            "intro_lines": first["n_lines"],
            "peak_month": peak["month"],
            "peak_lines": peak["n_lines"],
            "final_month": last["month"],
            "final_files": last["n_files"],
            "final_lines": last["n_lines"],
            "n_phase_events": len([e for e in events if e["kind"] == "phase"]),
        })

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["spec", "month", "kind", "n_files", "n_lines",
                                          "delta_files", "delta_lines", "commit"])
        w.writeheader()
        w.writerows(phases)

    # Print summary table
    print("\n=== Per-spec timeline summary ===\n")
    print(f"{'spec':<40} {'intro':<8} {'final':<8} {'files':>6} {'lines':>8} {'phases':>7}")
    for s in sorted(summary, key=lambda x: x["intro_month"]):
        print(f"{s['spec']:<40} {s['intro_month']:<8} {s['final_month']:<8} "
              f"{s['final_files']:>6} {s['final_lines']:>8} {s['n_phase_events']:>7}")

    # Print phase events per spec
    print("\n=== Major phase events per spec ===\n")
    by_spec_events = defaultdict(list)
    for e in phases:
        by_spec_events[e["spec"]].append(e)
    for spec in sorted(by_spec_events, key=lambda s: by_spec_events[s][0]["month"]):
        evs = by_spec_events[spec]
        print(f"\n## {spec}")
        for e in evs:
            kind = "intro" if e["kind"] == "intro" else "phase"
            print(f"  {e['month']}  {kind:<6}  files={e['n_files']:>4}  lines={e['n_lines']:>6}"
                  f"  Δfiles={e['delta_files']:+d}  Δlines={e['delta_lines']:+d}  ({e['commit']})")


if __name__ == "__main__":
    main()
