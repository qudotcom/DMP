"""Front charts used in the report and the slides: best profit against the longest project,
one line per bound on the number of projects per employee.

Usage: python figs.py [project_dir]
"""
import json
import os
import re
import sys
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

proj = sys.argv[1] if len(sys.argv) > 1 else "."
# blue shades from light to dark, one per line
RAMP = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95",
        "#104281", "#0d366b"]
INK, MUTED, GRID = "#2b2b29", "#6b6b66", "#e6e5e1"


def front_from_txt(path):
    pts = set()
    for line in open(path):
        m = re.match(r"profit=\s*(-?\d+)\s+maxProj/emp=(\d+)\s+maxDuration=(\d+)", line)
        if m:
            pts.add(tuple(map(int, m.groups())))
    return pts


def front_from_json(path):
    return {(p["profit"], p["max_projects_per_employee"], p["max_duration"]) for p in json.load(open(path))}


def chart(pts, title, fname):
    by = defaultdict(list)
    for p, P, D in pts:
        if P > 0:
            by[P].append((D, p))
    Ps = sorted(by)
    if len(Ps) <= len(RAMP):
        cols = RAMP[-len(Ps):]
    else:
        cmap = LinearSegmentedColormap.from_list("ramp", RAMP)
        cols = [cmap(i / (len(Ps) - 1)) for i in range(len(Ps))]
    fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=200)
    for P, col in zip(Ps, cols):
        xs, ys = zip(*sorted(by[P]))
        ax.plot(xs, ys, color=col, lw=2, marker="o", ms=4.5, mec="white", mew=1, label=f"{P}",
                solid_capstyle="round")
    ax.set_xlabel("longest project (days)", color=MUTED, fontsize=9)
    ax.set_ylabel("profit", color=MUTED, fontsize=9)
    ax.set_title(title, loc="left", color=INK, fontsize=10.5, pad=10)
    ax.grid(True, color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c9c8c3")
    ax.tick_params(colors=MUTED, labelsize=8)
    leg = ax.legend(title="max projects\nper employee", fontsize=8, title_fontsize=8, frameon=False,
                    loc="center left", bbox_to_anchor=(1.01, 0.5))
    plt.setp(leg.get_title(), color=MUTED)
    fig.tight_layout()
    fig.savefig(fname, facecolor="white")
    plt.close(fig)


if __name__ == "__main__":
    chart(front_from_txt(os.path.join(proj, "medium_front.txt")),
          "Medium instance: best profit for each trade-off (Pareto front)", os.path.join(proj, "medium_front.png"))
    chart(front_from_txt(os.path.join(proj, "large_front.txt")),
          "Large instance: best profit for each trade-off (Pareto front)", os.path.join(proj, "large_front.png"))
    chart(front_from_json(os.path.join(proj, "generated", "gen4_front.json")),
          "Generated instance gen4: Pareto front", os.path.join(proj, "generated", "gen4_front.png"))
    print("wrote medium_front.png, large_front.png, generated/gen4_front.png")
