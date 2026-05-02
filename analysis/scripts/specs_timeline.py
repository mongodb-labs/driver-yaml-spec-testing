"""Compute monthly snapshots of YAML test files and lines per spec area.

Uses git cat-file --batch for speed (single subprocess for all blob reads).
"""
import csv
import subprocess
import sys
from pathlib import Path
from collections import defaultdict

SPECS_REPO = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data/specifications")
OUT_CSV = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data/specs_timeline.csv")


def run(cmd, cwd=SPECS_REPO):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, check=False)


def month_iter(start_year, start_month, end_year, end_month):
    y, m = start_year, start_month
    while (y, m) <= (end_year, end_month):
        yield y, m
        m += 1
        if m > 12:
            m = 1
            y += 1


def last_commit_before(date_iso):
    r = run(["git", "log", "-1", f"--before={date_iso}", "--format=%H"])
    return r.stdout.strip() or None


def list_yaml_blobs(commit):
    """Return [(path, blob_sha), ...] of yaml files at this commit under source/."""
    r = run(["git", "ls-tree", "-r", commit, "source/"])
    out = []
    for line in r.stdout.splitlines():
        # mode\tsha\tpath  (actually space-separated then tab)
        # 100644 blob a1b2c3d4...\tpath/to/file
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        meta, path = parts
        meta_parts = meta.split()
        if len(meta_parts) < 3 or meta_parts[1] != "blob":
            continue
        sha = meta_parts[2]
        ll = path.lower()
        if ll.endswith(".yml") or ll.endswith(".yaml"):
            out.append((path, sha))
    return out


def batch_line_counts(commit_blobs, blob_cache):
    """For each (path, sha) pair, return line count. Cache by sha to avoid duplicates."""
    new_shas = [sha for _, sha in commit_blobs if sha not in blob_cache]
    if not new_shas:
        return
    p = subprocess.Popen(
        ["git", "cat-file", "--batch=%(objectsize)"],
        cwd=SPECS_REPO,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        text=True,
    )
    # We want line counts. We'll read content and count newlines.
    # --batch=%(objectsize) gives us just the size header; we still need content.
    # Use plain --batch which outputs: <sha> <type> <size>\n<content>\n
    p.kill()
    p = subprocess.Popen(
        ["git", "cat-file", "--batch"],
        cwd=SPECS_REPO,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        bufsize=0,
    )
    try:
        # Send all shas
        input_bytes = ("\n".join(new_shas) + "\n").encode()
        p.stdin.write(input_bytes)
        p.stdin.flush()
        p.stdin.close()
        out = p.stdout.read()
    finally:
        p.wait()

    # Parse: for each blob, header "<sha> blob <size>\n" then <size> bytes then "\n"
    pos = 0
    for sha in new_shas:
        # find newline
        nl = out.find(b"\n", pos)
        header = out[pos:nl].decode()
        parts = header.split()
        if len(parts) < 3 or parts[1] != "blob":
            blob_cache[sha] = 0
            pos = nl + 1
            continue
        size = int(parts[2])
        content = out[nl+1:nl+1+size]
        blob_cache[sha] = content.count(b"\n")
        pos = nl + 1 + size + 1  # +1 for trailing \n


def main():
    print("Computing monthly snapshots from 2014-04 to 2026-04...", file=sys.stderr)
    blob_cache = {}  # sha -> line count
    rows = []
    for year, month in month_iter(2014, 4, 2026, 5):
        if month == 12:
            cutoff = f"{year+1}-01-01"
        else:
            cutoff = f"{year}-{month+1:02d}-01"
        commit = last_commit_before(cutoff)
        if not commit:
            continue
        blobs = list_yaml_blobs(commit)
        batch_line_counts(blobs, blob_cache)
        by_spec = defaultdict(lambda: {"n_files": 0, "n_lines": 0})
        for path, sha in blobs:
            parts = path.split("/")
            if len(parts) < 2 or parts[0] != "source":
                continue
            spec = parts[1]
            by_spec[spec]["n_files"] += 1
            by_spec[spec]["n_lines"] += blob_cache.get(sha, 0)
        snapshot = f"{year}-{month:02d}"
        for spec, agg in sorted(by_spec.items()):
            rows.append({
                "month": snapshot,
                "spec": spec,
                "n_files": agg["n_files"],
                "n_lines": agg["n_lines"],
                "commit": commit[:8],
            })
        n_files_total = sum(s["n_files"] for s in by_spec.values())
        n_lines_total = sum(s["n_lines"] for s in by_spec.values())
        print(f"  {snapshot}  {commit[:8]}  files={n_files_total:>4}  lines={n_lines_total:>7}",
              file=sys.stderr, flush=True)

    OUT_CSV.parent.mkdir(parents=True, exist_ok=True)
    with OUT_CSV.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["month", "spec", "n_files", "n_lines", "commit"])
        w.writeheader()
        w.writerows(rows)
    print(f"\nWrote {len(rows)} rows to {OUT_CSV}", file=sys.stderr)


if __name__ == "__main__":
    main()
