"""Evaluate classifier against the 80-ticket hand-labeled gold set.

Reads data/labeling_sample.csv for human labels, loads full ticket content
from data/tickets/*.jsonl, classifies with the current prompt, and prints
agreement stats and a confusion matrix.

Usage:
    python scripts/eval_gold_set.py [--model MODEL] [--workers N]
"""
import argparse
import json
import os
import sys
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import csv

import anthropic

REPO = Path(__file__).resolve().parents[1]
GOLD_CSV = REPO / "data" / "labeling_sample.csv"
TICKETS_DIR = REPO / "data" / "tickets"
PROMPT_PATH = REPO / "prompts" / "classify.md"

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_DESC_CHARS = 4000

CATEGORIES = [
    "driver_spec_nonconformance",
    "cross_driver_inconsistency",
    "avoidable_by_spec_conformance",
    "spec_ambiguity_or_gap",
    "spec_authoring",
    "test_infrastructure",
    "not_relevant",
]
SHORT = {
    "driver_spec_nonconformance": "N",
    "cross_driver_inconsistency": "X",
    "avoidable_by_spec_conformance": "A",
    "spec_ambiguity_or_gap": "G",
    "spec_authoring": "S",
    "test_infrastructure": "T",
    "not_relevant": "R",
}


def load_gold() -> dict[str, str]:
    with GOLD_CSV.open() as f:
        return {r["key"]: r["your_label"] for r in csv.DictReader(f) if r["your_label"]}


def load_tickets(keys: set) -> dict[str, dict]:
    tickets = {}
    for path in TICKETS_DIR.glob("*.jsonl"):
        with path.open() as f:
            for line in f:
                t = json.loads(line)
                if t["key"] in keys:
                    tickets[t["key"]] = t
    return tickets


def truncate(s: str, n: int) -> str:
    if not s:
        return ""
    return s if len(s) <= n else s[:n] + f"\n[... truncated {len(s)-n} chars]"


def ticket_to_user_msg(t: dict) -> str:
    parts = [
        f"key: {t['key']}",
        f"project: {t['project']}",
        f"issuetype: {t['issuetype']}",
        f"resolution: {t.get('resolution')}",
        f"priority: {t.get('priority')}",
        f"created: {(t.get('created') or '')[:10]}",
        f"resolved: {(t.get('resolutiondate') or '')[:10]}",
        f"components: {', '.join(t.get('components') or []) or '(none)'}",
        f"labels: {', '.join(t.get('labels') or []) or '(none)'}",
        f"fix_versions: {', '.join(t.get('fixVersions') or []) or '(none)'}",
    ]
    links = t.get("links") or []
    if links:
        parts.append("links:")
        for lnk in links[:20]:
            parts.append(f"  - {lnk['type']} {lnk['direction']}: {lnk['key']}")
    parts.append(f"summary: {t['summary']}")
    parts.append("description:")
    parts.append(truncate(t.get("description") or "(empty)", MAX_DESC_CHARS))
    return "\n".join(parts)


def parse_response(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        if text.endswith("```"):
            text = text.rsplit("```", 1)[0]
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < 0:
        raise ValueError(f"no JSON in response: {text[:200]}")
    return json.loads(text[start:end+1])


def classify_one(client, system, ticket):
    resp = client.messages.create(
        model=client._model,
        max_tokens=500,
        system=system,
        messages=[{"role": "user", "content": ticket_to_user_msg(ticket)}],
    )
    text = "".join(b.text for b in resp.content if b.type == "text")
    return parse_response(text)


def confusion_matrix(results: list[tuple[str, str]]) -> None:
    """Print confusion matrix and per-category metrics."""
    cats = sorted({h for h, _ in results} | {m for _, m in results})
    # Only include categories that appear
    cats = [c for c in CATEGORIES if c in cats]

    # Matrix: rows=human, cols=model
    matrix = defaultdict(lambda: defaultdict(int))
    for human, model in results:
        matrix[human][model] += 1

    col_w = max(len(SHORT.get(c, c[:4])) for c in cats)
    row_label_w = max(len(c) for c in cats)

    header = " " * (row_label_w + 1) + "  ".join(f"{SHORT.get(c,c[:4]):>{col_w}}" for c in cats) + "  total"
    print(header)
    for human in cats:
        row_total = sum(matrix[human].values())
        row = f"{human:<{row_label_w}} " + "  ".join(
            f"{matrix[human][model]:>{col_w}}" for model in cats
        ) + f"  {row_total}"
        print(row)

    print()
    print(f"{'category':<35} {'prec':>6} {'recall':>7} {'human_n':>7} {'model_n':>7}")
    total_agree = 0
    total = len(results)
    for cat in cats:
        tp = matrix[cat][cat]
        fp = sum(matrix[h][cat] for h in cats if h != cat)
        fn = sum(matrix[cat][m] for m in cats if m != cat)
        prec = tp / (tp + fp) if (tp + fp) else float("nan")
        rec = tp / (tp + fn) if (tp + fn) else float("nan")
        human_n = sum(matrix[cat].values())
        model_n = sum(matrix[h][cat] for h in cats)
        total_agree += tp
        print(f"{cat:<35} {prec:>6.0%} {rec:>7.0%} {human_n:>7} {model_n:>7}")

    print()
    print(f"overall agreement: {total_agree}/{total} = {total_agree/total:.1%}")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", default=DEFAULT_MODEL)
    p.add_argument("--workers", type=int, default=6)
    p.add_argument("--out", default=None, help="Write model outputs to this CSV")
    args = p.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        sys.exit("error: ANTHROPIC_API_KEY not set")

    gold = load_gold()
    print(f"gold set: {len(gold)} tickets", file=sys.stderr)

    tickets = load_tickets(set(gold))
    missing = set(gold) - set(tickets)
    if missing:
        print(f"warning: {len(missing)} gold tickets not found in JSONL: {missing}", file=sys.stderr)

    system = PROMPT_PATH.read_text()
    client = anthropic.Anthropic()
    client._model = args.model  # stash for classify_one

    print(f"classifying {len(tickets)} tickets with {args.model} ...", file=sys.stderr)

    results = []
    errors = []
    out_rows = []

    with ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = {ex.submit(classify_one, client, system, t): (key, gold[key])
                for key, t in tickets.items()}
        done = 0
        for fut in as_completed(futs):
            key, human_label = futs[fut]
            done += 1
            try:
                result = fut.result()
            except Exception as e:
                errors.append((key, str(e)))
                print(f"[err] {key}: {e}", file=sys.stderr)
                continue
            model_cat = result.get("category", "")
            results.append((human_label, model_cat))
            out_rows.append({"key": key, "human": human_label, "model": model_cat,
                             "spec_areas": "|".join(result.get("spec_areas") or []),
                             "confidence": result.get("confidence", ""),
                             "rationale": result.get("rationale", "")})
            agree = "OK" if human_label == model_cat else "DIFF"
            print(f"  {done:>3}/{len(tickets)} {key:<18} human={SHORT.get(human_label,'?')} "
                  f"model={SHORT.get(model_cat,'?')} {agree}", file=sys.stderr)

    print(f"\n{len(errors)} errors\n", file=sys.stderr)

    if args.out:
        with open(args.out, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=["key", "human", "model", "spec_areas", "confidence", "rationale"])
            w.writeheader()
            w.writerows(sorted(out_rows, key=lambda r: r["key"]))
        print(f"wrote {len(out_rows)} rows to {args.out}", file=sys.stderr)

    print("\n--- confusion matrix (rows=human, cols=model) ---\n")
    confusion_matrix(results)


if __name__ == "__main__":
    main()
