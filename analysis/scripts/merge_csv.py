"""Merge per-chunk classifications with ticket metadata into a single CSV.

Reads:
- data/tickets/<KEY>.jsonl    (raw ticket data)
- data/chunks/chunk_*.results.jsonl  (Haiku classifications, one JSON per line)

Writes:
- data/classified.csv

Each CSV row is one ticket, joined on Jira key.
"""
import csv
import glob
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TICKETS = REPO / "data" / "tickets"
CHUNKS = REPO / "data" / "chunks"
OUT = REPO / "data" / "classified.csv"

COLUMNS = [
    "key", "project", "issuetype", "resolution", "priority",
    "created", "resolutiondate",
    "summary",
    "category", "spec_areas", "is_nonconformance",
    "mentions_other_driver", "preventable_by_yaml_test",
    "confidence", "rationale",
    "components", "labels", "fix_versions", "links",
    "url",
]


def jira_url(key: str) -> str:
    return f"https://jira.mongodb.org/browse/{key}"


def join_list(v) -> str:
    if not v: return ""
    if isinstance(v, list): return "|".join(str(x) for x in v)
    return str(v)


def main():
    # Load all classifications keyed by ticket key.
    classifications = {}
    for path in sorted(CHUNKS.glob("chunk_*.results.jsonl")):
        with open(path) as f:
            for line in f:
                line = line.strip()
                if not line: continue
                d = json.loads(line)
                # Some subagents wrote duplicate keys (rare); last wins.
                if d.get("key"):
                    classifications[d["key"]] = d

    print(f"loaded {len(classifications)} classifications")

    # Iterate tickets, join, write CSV.
    n_rows = 0
    n_unmatched = 0
    with OUT.open("w", newline="") as fout:
        w = csv.DictWriter(fout, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for path in sorted(TICKETS.glob("*.jsonl")):
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line: continue
                    t = json.loads(line)
                    c = classifications.get(t["key"], {})
                    if not c:
                        n_unmatched += 1
                    row = {
                        "key": t["key"],
                        "project": t.get("project", ""),
                        "issuetype": t.get("issuetype", ""),
                        "resolution": t.get("resolution", ""),
                        "priority": t.get("priority", ""),
                        "created": (t.get("created") or "")[:10],
                        "resolutiondate": (t.get("resolutiondate") or "")[:10],
                        "summary": t.get("summary", ""),
                        "category": c.get("category", ""),
                        "spec_areas": join_list(c.get("spec_areas", [])),
                        "is_nonconformance": c.get("is_nonconformance", ""),
                        "mentions_other_driver": c.get("mentions_other_driver", ""),
                        "preventable_by_yaml_test": c.get("preventable_by_yaml_test", ""),
                        "confidence": c.get("confidence", ""),
                        "rationale": c.get("rationale", ""),
                        "components": join_list(t.get("components", [])),
                        "labels": join_list(t.get("labels", [])),
                        "fix_versions": join_list(t.get("fixVersions", [])),
                        "links": "|".join(
                            f"{l['type']}:{l['key']}"
                            for l in t.get("links") or []
                        ),
                        "url": jira_url(t["key"]),
                    }
                    w.writerow(row)
                    n_rows += 1

    print(f"wrote {n_rows} rows to {OUT}")
    print(f"unmatched (no classification): {n_unmatched}")


if __name__ == "__main__":
    main()
