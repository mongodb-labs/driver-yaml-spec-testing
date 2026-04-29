"""Build a stratified labeling sample from data/classified.csv.

20 tickets per category for the four main spec-relevant categories (or
not_relevant), with a mix of confidence levels within each. Joined with
the original ticket descriptions so we can show them while labeling.

Output: data/labeling_sample.csv with an empty `your_label` column.
"""
import csv
import json
import random
from collections import defaultdict
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CSV_IN = REPO / "data" / "classified.csv"
TICKETS_DIR = REPO / "data" / "tickets"
OUT = REPO / "data" / "labeling_sample.csv"

CATEGORIES = [
    "driver_spec_nonconformance",
    "cross_driver_inconsistency",
    "avoidable_by_spec_conformance",
    "not_relevant",
]
N_PER_CAT = 20
# Within each category, take this many at each confidence level if available.
CONF_TARGETS = {"high": 6, "medium": 8, "low": 6}
SEED = 17


def main():
    # Group classifications by (category, confidence).
    rows_by_cat_conf = defaultdict(list)
    with CSV_IN.open() as f:
        for r in csv.DictReader(f):
            if r["category"] in CATEGORIES:
                rows_by_cat_conf[(r["category"], r["confidence"])].append(r)

    rng = random.Random(SEED)
    sample = []
    for cat in CATEGORIES:
        picked = []
        for conf, target in CONF_TARGETS.items():
            pool = rows_by_cat_conf[(cat, conf)]
            n = min(target, len(pool))
            picked.extend(rng.sample(pool, n))
        # If we didn't reach N_PER_CAT (rare), top up from any conf.
        remaining = [
            r for c in CONF_TARGETS for r in rows_by_cat_conf[(cat, c)]
            if r not in picked
        ]
        while len(picked) < N_PER_CAT and remaining:
            picked.append(rng.choice(remaining))
            remaining.remove(picked[-1])
        # Shuffle within category so confidence isn't grouped.
        rng.shuffle(picked)
        sample.extend(picked[:N_PER_CAT])

    # Final shuffle of full sample so categories are interleaved.
    rng.shuffle(sample)

    # Load full ticket text for each sampled key.
    needed = {r["key"] for r in sample}
    tickets = {}
    for path in TICKETS_DIR.glob("*.jsonl"):
        with path.open() as f:
            for line in f:
                t = json.loads(line)
                if t["key"] in needed:
                    tickets[t["key"]] = t

    # Write the labeling CSV.
    cols = [
        "n", "key", "url", "model_category", "model_spec_areas",
        "model_confidence", "model_rationale",
        "your_label", "notes",
        "summary", "description",
        "issuetype", "components", "labels", "links",
    ]
    with OUT.open("w", newline="") as fout:
        w = csv.DictWriter(fout, fieldnames=cols)
        w.writeheader()
        for i, r in enumerate(sample, 1):
            t = tickets.get(r["key"], {})
            w.writerow({
                "n": i,
                "key": r["key"],
                "url": r["url"],
                "model_category": r["category"],
                "model_spec_areas": r["spec_areas"],
                "model_confidence": r["confidence"],
                "model_rationale": r["rationale"],
                "your_label": "",
                "notes": "",
                "summary": t.get("summary", ""),
                "description": t.get("description", ""),
                "issuetype": t.get("issuetype", ""),
                "components": "|".join(t.get("components") or []),
                "labels": "|".join(t.get("labels") or []),
                "links": "|".join(
                    f"{l['type']}:{l['key']}" for l in t.get("links") or []
                ),
            })

    print(f"wrote {len(sample)} sampled tickets to {OUT}")
    by_cat = defaultdict(int)
    for r in sample:
        by_cat[r["category"]] += 1
    for cat in CATEGORIES:
        print(f"  {cat}: {by_cat[cat]}")


if __name__ == "__main__":
    main()
