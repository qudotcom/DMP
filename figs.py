"""Make the front charts for the report (profit vs max duration, one line per
max-projects-per-employee value). Usage: python figs.py <project_dir> <out_dir>"""
import re, sys, os
from collections import defaultdict
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

proj, out = sys.argv[1], sys.argv[2]
# ordinal blue ramp (light -> dark), starting no lighter than step 250
RAMP = ["#86b6ef", "#6da7ec", "#5598e7", "#3987e5", "#2a78d6", "#256abf", "#1c5cab", "#184f95",
        "#104281", "#0d366b"]
INK, MUTED, GRID = "#2b2b29", "#6b6b66", "#e6e5e1"


def front_from_log(path):
    pts = set()
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.search(r"profit=(-?\d+) P=(\d+) D=(\d+)", line)
        if m:
            pts.add(tuple(map(int, m.groups())))
    dom = lambda p, q: p[0] >= q[0] and p[1] <= q[1] and p[2] <= q[2] and p != q
    return {p for p in pts if not any(dom(q, p) for q in pts)}


def front_from_txt(path):
    pts = set()
    for line in open(path):
        m = re.match(r"profit=\s*(-?\d+)\s+maxProj/emp=(\d+)\s+maxDuration=(\d+)", line)
        if m:
            pts.add(tuple(map(int, m.groups())))
    return pts


def chart(pts, title, fname):
    by = defaultdict(list)
    for p, P, D in pts:
        if P > 0:
            by[P].append((D, p))
    Ps = sorted(by)
    if len(Ps) <= len(RAMP):
        cols = RAMP[-len(Ps):]
    else:  # interpolate the ramp to get one shade per line
        from matplotlib.colors import LinearSegmentedColormap
        cm_ = LinearSegmentedColormap.from_list("r", RAMP)
        cols = [cm_(i / (len(Ps) - 1)) for i in range(len(Ps))]
    fig, ax = plt.subplots(figsize=(7.2, 3.9), dpi=200)
    for P, col in zip(Ps, cols):
        xs, ys = zip(*sorted(by[P]))
        ax.plot(xs, ys, color=col, lw=2, marker="o", ms=4.5, mec="white", mew=1,
                label=f"{P}", solid_capstyle="round")
    ax.set_xlabel("longest project (days)", color=MUTED, fontsize=9)
    ax.set_ylabel("profit", color=MUTED, fontsize=9)
    ax.set_title(title, loc="left", color=INK, fontsize=10.5, pad=10)
    ax.grid(True, color=GRID, lw=0.8); ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color("#c9c8c3")
    ax.tick_params(colors=MUTED, labelsize=8)
    leg = ax.legend(title="max projects\nper employee", fontsize=8, title_fontsize=8,
                    frameon=False, loc="center left", bbox_to_anchor=(1.01, 0.5))
    plt.setp(leg.get_title(), color=MUTED)
    fig.tight_layout()
    fig.savefig(os.path.join(out, fname), facecolor="white")
    plt.close(fig)


chart(front_from_txt(os.path.join(proj, "medium_front.txt")),
      "Medium instance: best profit for each trade-off (Pareto front)", "medium_front.png")
lf = os.path.join(proj, "large_front.txt")
if os.path.exists(lf):
    chart(front_from_txt(lf), "Large instance: best profit for each trade-off (Pareto front)", "large_front.png")
else:
    chart(front_from_log(os.path.join(proj, "large_run.log")),
          "Large instance: Pareto front found so far (run in progress)", "large_front.png")
import json
for n in (3, 4):
    fj = os.path.join(proj, "generated", f"gen{n}_front.json")
    if os.path.exists(fj):
        pts = {(p["profit"], p["max_projects_per_employee"], p["max_duration"]) for p in json.load(open(fj))}
        chart(pts, f"Generated instance gen{n}: Pareto front", f"gen{n}_front.png")
print("ok")
