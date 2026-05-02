"""A single 2-panel headline chart combining the two strongest signals:
- top: M2 spike-then-decay (tests reveal bugs)
- bottom: M9 pre/post coverage saturation (bug rate drops once coverage
  matures)

Outputs data/plots/headline.png
"""
import csv
from collections import defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

DATA = Path("/Users/emptysquare/co/driver-yaml-spec-testing/analysis/data")
PLOT_DIR = DATA / "plots"


def load_panel():
    panel = {}
    with (DATA / "panel.csv").open() as f:
        for r in csv.DictReader(f):
            panel[(r["driver"], r["spec"], r["month"])] = {
                "n_bugs": int(r["n_bugs_created"]),
                "n_files": int(r["n_files"]),
                "n_lines": int(r["n_noncomment_lines"]),
            }
    return panel


def month_index(m):
    return (int(m[:4]) - 2000) * 12 + (int(m[5:7]) - 1)


def by_driver_spec(panel):
    out = defaultdict(list)
    for k, v in panel.items():
        out[(k[0], k[1])].append((k[2], v))
    for k in out:
        out[k].sort(key=lambda x: x[0])
    return out


def first_sync_month(history, threshold=1):
    for m, v in history:
        if v["n_files"] >= threshold:
            return m
    return None


def main():
    panel = load_panel()
    by_ds = by_driver_spec(panel)

    # Top panel: M2 spike-then-decay windows
    windows = [(-36, -13, "−36..−13"), (-12, -1, "−12..−1"),
               (0, 3, "0..+3"), (4, 15, "+4..+15"),
               (16, 35, "+16..+35"), (36, 59, "+36..+59")]
    win_rates = defaultdict(list)
    for (d, s), hist in by_ds.items():
        first = first_sync_month(hist)
        if first is None:
            continue
        first_idx = month_index(first)
        history = {m: v for m, v in hist}
        for lo, hi, label in windows:
            n_bugs = 0
            n_months = 0
            for off in range(lo, hi + 1):
                idx = first_idx + off
                y = idx // 12 + 2000
                m_ = idx % 12 + 1
                m_str = f"{y:04d}-{m_:02d}"
                if m_str in history:
                    n_bugs += history[m_str]["n_bugs"]
                    n_months += 1
            if n_months > 0:
                win_rates[label].append(n_bugs / n_months)
    win_labels = [w[2] for w in windows]
    win_means = [sum(win_rates[l]) / len(win_rates[l]) if win_rates[l] else 0 for l in win_labels]

    # Bottom panel: M9 saturation — top 8 specs by pre+post bug volume
    spec_month_total = defaultdict(lambda: defaultdict(int))
    for (d, s, m), v in panel.items():
        spec_month_total[s][m] += v["n_files"]
    sat_date = {}
    for spec, by_m in spec_month_total.items():
        if not by_m:
            continue
        peak = max(by_m.values())
        if peak < 5:
            continue
        thr = 0.8 * peak
        for m in sorted(by_m.keys()):
            if by_m[m] >= thr:
                sat_date[spec] = m
                break

    pre_post = {}
    for spec, sd in sat_date.items():
        pre_bugs = post_bugs = 0
        pre_n = post_n = 0
        for (d, s, m), v in panel.items():
            if s != spec:
                continue
            if m < sd:
                pre_bugs += v["n_bugs"]
                pre_n += 1
            else:
                post_bugs += v["n_bugs"]
                post_n += 1
        if pre_n and post_n:
            pre_post[spec] = (pre_bugs / pre_n, post_bugs / post_n,
                              pre_bugs, post_bugs)

    specs_top = sorted(pre_post.keys(),
                       key=lambda s: -pre_post[s][2])[:10]

    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(13, 10))

    # Top: spike-then-decay
    colors_top = ["#888", "#888", "#d62728", "#f49a3c", "#5fa55a", "#1f77b4"]
    bars = ax1.bar(win_labels, win_means, color=colors_top, alpha=0.9)
    pre_baseline = (win_means[0] + win_means[1]) / 2
    ax1.axhline(pre_baseline, color="black", linestyle="--", lw=1, alpha=0.6,
                label=f"pre-sync baseline = {pre_baseline:.3f}")
    for bar, m in zip(bars, win_means):
        ax1.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 0.003,
                 f"{m:.3f}", ha="center", va="bottom", fontsize=9)
    ax1.set_ylabel("Mean N-bugs per (driver,spec) cell-month",
                   fontsize=11)
    ax1.set_xlabel("Months relative to a (driver,spec)'s first test sync",
                   fontsize=11)
    ax1.set_title("(a) Bug-filing rate spikes 2.5× when tests are first synced, then decays\n"
                  f"n={len(win_rates['0..+3'])} (driver, spec) cells averaged",
                  fontsize=12)
    ax1.legend(fontsize=10)
    ax1.grid(True, alpha=0.3, axis="y")

    # Bottom: saturation per-spec
    pre_rates = [pre_post[s][0] for s in specs_top]
    post_rates = [pre_post[s][1] for s in specs_top]
    pre_n = [pre_post[s][2] for s in specs_top]
    post_n = [pre_post[s][3] for s in specs_top]
    x = list(range(len(specs_top)))
    w = 0.4
    ax2.bar([xi - w/2 for xi in x], pre_rates, w,
            color="#d62728", alpha=0.85, label="pre-saturation")
    ax2.bar([xi + w/2 for xi in x], post_rates, w,
            color="#1f77b4", alpha=0.85, label="post-saturation")
    for i, s in enumerate(specs_top):
        pct = (post_rates[i] - pre_rates[i]) / pre_rates[i] * 100 if pre_rates[i] else 0
        ax2.text(i, max(pre_rates[i], post_rates[i]) + 0.005,
                 f"{pct:+.0f}%\n({pre_n[i]}→{post_n[i]})",
                 ha="center", va="bottom", fontsize=8)
    ax2.set_xticks(x)
    ax2.set_xticklabels(specs_top, rotation=30, ha="right", fontsize=9)
    ax2.set_ylabel("Mean N-bugs per (driver,month) cell", fontsize=11)
    ax2.set_title("(b) Once a spec's test coverage saturates (≥80% of peak), "
                  "per-driver bug rate drops in 8 of 10 high-volume specs\n"
                  "labels: % change in rate; (pre-bug-count → post-bug-count)",
                  fontsize=12)
    ax2.legend(fontsize=10)
    ax2.grid(True, alpha=0.3, axis="y")

    plt.tight_layout()
    plt.savefig(PLOT_DIR / "headline.png", dpi=140)
    plt.close()
    print(f"Wrote {PLOT_DIR / 'headline.png'}")


if __name__ == "__main__":
    main()
