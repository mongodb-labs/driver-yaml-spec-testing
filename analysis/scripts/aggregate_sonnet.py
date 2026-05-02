"""Aggregate all chunk_NNNN.results.jsonl files into summary statistics.

Reads data/sonnet_results/chunk_*.results.jsonl, deduplicates by key,
then prints:
  - Overall category distribution
  - Per-project category distribution
  - N count with 95% CI using gold-corpus precision/recall
  - preventable_by_yaml_test true counts
Outputs data/classified_sonnet.csv (one row per ticket).
"""
import csv
import json
import math
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
RESULTS_DIR = REPO / "data" / "sonnet_results"
TICKET_DIR = REPO / "data" / "tickets"
OUT_CSV = REPO / "data" / "classified_sonnet.csv"

# Gold-corpus metrics from exp02 (200-ticket corpus)
N_PRECISION = 0.733
N_RECALL = 0.688

CATEGORIES = [
    "driver_spec_nonconformance",
    "cross_driver_inconsistency",
    "spec_ambiguity_or_gap",
    "spec_authoring",
    "test_infrastructure",
    "not_relevant",
]

# Load ticket metadata (created date, project) for each key
def load_ticket_meta():
    meta = {}
    for path in sorted(TICKET_DIR.glob("*.jsonl")):
        with path.open() as f:
            for line in f:
                t = json.loads(line)
                meta[t["key"]] = {
                    "project": t["project"],
                    "issuetype": t.get("issuetype"),
                    "created": (t.get("created") or "")[:10],
                    "resolutiondate": (t.get("resolutiondate") or "")[:10],
                    "resolution": t.get("resolution"),
                    "priority": t.get("priority"),
                    "summary": t.get("summary", ""),
                    "components": "|".join(t.get("components") or []),
                    "labels": "|".join(t.get("labels") or []),
                    "fix_versions": "|".join(t.get("fixVersions") or []),
                    "links": "|".join(
                        f"{lnk['type']}:{lnk['key']}" for lnk in (t.get("links") or [])
                    ),
                    "url": f"https://jira.mongodb.org/browse/{t['key']}",
                }
    return meta


def load_results():
    seen = {}
    for path in sorted(RESULTS_DIR.glob("chunk_*.results.jsonl")):
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    d = json.loads(line)
                except json.JSONDecodeError:
                    continue
                key = d.get("key")
                if not key:
                    continue
                if key not in seen:
                    seen[key] = d
    return seen


def ci_95(n, N):
    """Wilson score interval for a proportion p=n/N."""
    if N == 0:
        return (0.0, 0.0)
    z = 1.96
    p = n / N
    denom = 1 + z**2 / N
    center = (p + z**2 / (2 * N)) / denom
    margin = z * math.sqrt(p * (1 - p) / N + z**2 / (4 * N**2)) / denom
    return (max(0, center - margin), min(1, center + margin))


def true_n_estimate(model_n, total):
    """Estimate true N count from model count using precision/recall."""
    # true_N ≈ model_N / precision * recall ... actually:
    # model_N = true_N * precision ... no wait:
    # precision = TP / (TP + FP) = TP / model_N
    # recall    = TP / (TP + FN) = TP / true_N
    # So TP = model_N * precision
    # And true_N = TP / recall = model_N * precision / recall
    tp = model_n * N_PRECISION
    true_n = tp / N_RECALL
    return round(true_n)


def main():
    print("Loading ticket metadata...")
    meta = load_ticket_meta()
    print(f"  {len(meta)} tickets in metadata")

    print("Loading Sonnet results...")
    results = load_results()
    print(f"  {len(results)} unique classified tickets")

    # Write CSV
    columns = [
        "key", "project", "issuetype", "resolution", "priority",
        "created", "resolutiondate", "summary",
        "category", "spec_areas", "is_nonconformance", "mentions_other_driver",
        "preventable_by_yaml_test", "confidence", "rationale",
        "components", "labels", "fix_versions", "links", "url",
    ]
    with OUT_CSV.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=columns)
        writer.writeheader()
        for key, r in sorted(results.items()):
            m = meta.get(key, {})
            spec_areas = r.get("spec_areas") or []
            if isinstance(spec_areas, list):
                spec_areas = "|".join(spec_areas)
            row = {
                "key": key,
                "project": m.get("project", r.get("project", "")),
                "issuetype": m.get("issuetype", ""),
                "resolution": m.get("resolution", ""),
                "priority": m.get("priority", ""),
                "created": m.get("created", ""),
                "resolutiondate": m.get("resolutiondate", ""),
                "summary": m.get("summary", ""),
                "category": r.get("category", ""),
                "spec_areas": spec_areas,
                "is_nonconformance": r.get("is_nonconformance", ""),
                "mentions_other_driver": r.get("mentions_other_driver", ""),
                "preventable_by_yaml_test": r.get("preventable_by_yaml_test", ""),
                "confidence": r.get("confidence", ""),
                "rationale": r.get("rationale", ""),
                "components": m.get("components", ""),
                "labels": m.get("labels", ""),
                "fix_versions": m.get("fix_versions", ""),
                "links": m.get("links", ""),
                "url": m.get("url", f"https://jira.mongodb.org/browse/{key}"),
            }
            writer.writerow(row)
    print(f"  Wrote {len(results)} rows to {OUT_CSV}")

    # --- Overall category distribution ---
    cat_counts = defaultdict(int)
    for r in results.values():
        cat_counts[r.get("category", "unknown")] += 1

    total = len(results)
    print(f"\n=== Category Distribution (N={total}) ===")
    for cat in CATEGORIES:
        n = cat_counts[cat]
        print(f"  {cat:<35} {n:>5}  ({100*n/total:.1f}%)")
    other = total - sum(cat_counts[c] for c in CATEGORIES)
    if other:
        print(f"  {'other/unknown':<35} {other:>5}  ({100*other/total:.1f}%)")

    # --- Estimated true N ---
    model_n = cat_counts["driver_spec_nonconformance"]
    true_n = true_n_estimate(model_n, total)
    print(f"\n=== N Estimate ===")
    print(f"  Model N count:     {model_n}")
    print(f"  Estimated true N:  {true_n}  (model_N × precision/recall = {model_n} × {N_PRECISION}/{N_RECALL:.3f})")
    lo, hi = ci_95(model_n, total)
    print(f"  95% CI on model N rate: [{lo:.3f}, {hi:.3f}]  →  [{round(lo*total*N_PRECISION/N_RECALL)}, {round(hi*total*N_PRECISION/N_RECALL)}] tickets")

    # --- preventable_by_yaml_test ---
    preventable = sum(1 for r in results.values()
                      if str(r.get("preventable_by_yaml_test", "")).lower() == "true")
    print(f"\n=== Preventable by YAML Test ===")
    print(f"  preventable_by_yaml_test=true:  {preventable}  ({100*preventable/total:.1f}%)")

    # --- Per-project breakdown ---
    proj_cats = defaultdict(lambda: defaultdict(int))
    for key, r in results.items():
        proj = meta.get(key, {}).get("project") or r.get("project") or key.split("-")[0]
        proj_cats[proj][r.get("category", "unknown")] += 1

    print(f"\n=== Per-Project Breakdown ===")
    header = f"{'project':<12}" + "".join(f"{'N':>5}{'X':>4}{'G':>4}{'S':>4}{'T':>4}{'R':>6}{'tot':>6}")
    print(header)
    short = {"driver_spec_nonconformance":"N","cross_driver_inconsistency":"X",
             "spec_ambiguity_or_gap":"G","spec_authoring":"S",
             "test_infrastructure":"T","not_relevant":"R"}
    for proj in sorted(proj_cats.keys()):
        pc = proj_cats[proj]
        tot = sum(pc.values())
        row = f"{proj:<12}" + "".join(f"{pc.get(cat,0):>5}" if i==0 else f"{pc.get(cat,0):>4}"
                                      for i, cat in enumerate(CATEGORIES))
        row += f"{tot:>6}"
        print(row)

    # --- Top spec areas (among N tickets) ---
    area_counts = defaultdict(int)
    for r in results.values():
        if r.get("category") == "driver_spec_nonconformance":
            areas = r.get("spec_areas") or []
            if isinstance(areas, str):
                areas = [a for a in areas.split("|") if a]
            for a in areas:
                area_counts[a] += 1

    print(f"\n=== Top Spec Areas (N tickets only) ===")
    for area, cnt in sorted(area_counts.items(), key=lambda x: -x[1])[:15]:
        print(f"  {area:<30} {cnt:>4}")


if __name__ == "__main__":
    main()
