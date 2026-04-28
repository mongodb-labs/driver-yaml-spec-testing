"""Split data/tickets/*.jsonl into fixed-size chunks for parallel
classification by Haiku subagents.

Each chunk file contains up to N tickets. A subagent reads
data/chunks/chunk_NNNN.jsonl and writes data/chunks/chunk_NNNN.results.jsonl
with one classification JSON object per line.
"""
import argparse
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
TICKET_DIR = REPO / "data" / "tickets"
CHUNK_DIR = REPO / "data" / "chunks"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--size", type=int, default=50, help="tickets per chunk")
    p.add_argument("--projects", nargs="*", default=None,
                   help="restrict to these projects (default: all)")
    args = p.parse_args()

    CHUNK_DIR.mkdir(parents=True, exist_ok=True)
    # Wipe any prior chunks so the numbering is deterministic.
    for f in CHUNK_DIR.glob("chunk_*.jsonl"):
        f.unlink()

    files = sorted(TICKET_DIR.glob("*.jsonl"))
    if args.projects:
        wanted = set(args.projects)
        files = [f for f in files if f.stem in wanted]

    tickets = []
    for f in files:
        with f.open() as fh:
            for line in fh:
                line = line.strip()
                if line:
                    tickets.append(line)

    n_chunks = 0
    for i in range(0, len(tickets), args.size):
        chunk = tickets[i:i + args.size]
        n_chunks += 1
        out = CHUNK_DIR / f"chunk_{n_chunks:04d}.jsonl"
        with out.open("w") as fh:
            for line in chunk:
                fh.write(line + "\n")

    print(f"wrote {n_chunks} chunks of up to {args.size} tickets each "
          f"(total {len(tickets)} tickets) to {CHUNK_DIR}")


if __name__ == "__main__":
    main()
