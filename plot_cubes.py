"""Draw the 3-D Pareto 'cubes' from saved fronts (no solving).

Writes toy_pareto.png, medium_pareto.png, large_pareto.png and pareto_cubes.png (the three side by side),
plus generated/gen*_pareto.png for the generated instances.
Usage: python plot_cubes.py
"""
import glob
import json
import os
import re

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from staffing import draw_cube, plot_front


def read_front(path):
    """Front points (profit, P, D) from a *_front.json or *_front.txt file."""
    if path.endswith(".json"):
        return [(p["profit"], p["max_projects_per_employee"], p["max_duration"]) for p in json.load(open(path))]
    pts = []
    for line in open(path):
        m = re.match(r"profit=\s*(-?\d+)\s+maxProj/emp=(\d+)\s+maxDuration=(\d+)", line)
        if m:
            pts.append(tuple(map(int, m.groups())))
    return pts


if __name__ == "__main__":
    given = [("toy", "toy_front.json"), ("medium", "medium_front.txt"), ("large", "large_front.txt")]
    fronts = {name: read_front(f) for name, f in given}
    for name, pts in fronts.items():
        plot_front(pts, f"{name}_pareto.png", f"{name} instance: {len(pts)} Pareto points")
    for f in sorted(glob.glob(os.path.join("generated", "gen*_front.json"))):
        name = os.path.basename(f)[:-len("_front.json")]
        pts = read_front(f)
        plot_front(pts, os.path.join("generated", f"{name}_pareto.png"), f"{name}: {len(pts)} Pareto points")
    fig = plt.figure(figsize=(13, 4.8))
    for k, (name, pts) in enumerate(fronts.items(), 1):
        draw_cube(fig.add_subplot(1, 3, k, projection="3d"), pts, f"{name} ({len(pts)} points)", fs=1.5)
    fig.subplots_adjust(left=0.04, right=0.98, bottom=0.05, top=0.92, wspace=0.12)
    plt.savefig("pareto_cubes.png", dpi=200)
    plt.close()
    print("wrote toy/medium/large_pareto.png, generated/gen*_pareto.png, pareto_cubes.png")
