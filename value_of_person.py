"""Value of one more person: add one employee, available every day, and re-solve.

For each skill k, the new employee has only skill k; a last row gives them every skill (upper bound).
Each case is solved twice: with no workload/duration limit (best profit overall) and under the limits
of a chosen front point (default: P <= 6, D <= 8, the medium best plan).

Usage: python value_of_person.py INSTANCE.json [--caps P D] [--out NAME.json]
"""
import json
import sys
import time

import gurobipy as gp
from gurobipy import GRB

from staffing import build, load, take


def best_profit(data, pcap=None, dcap=None):
    """Max profit (ties broken towards small P, D), number of completed projects, and the number of
    days the added employee "New" actually works (0 if there is none)."""
    m, x, y, profit, Pmax, Dmax = build(*data)
    m.setObjective(profit - 1e-3 * (Pmax + Dmax), GRB.MAXIMIZE)
    if pcap is not None:
        m.addConstr(Pmax <= pcap)
        m.addConstr(Dmax <= dcap)
    m.optimize()
    assert m.Status == GRB.OPTIMAL, m.Status
    new_days = len({t for (i, j, k, t), v in x.items() if i == "New" and v.X > 0.5})
    return round(profit.getValue()), round(sum(v.X for v in y.values())), new_days


def with_new_person(data, skills):
    H, Q, S, QS, V, J, n, g, c, due = data
    QS2 = dict(QS, New=set(skills))
    V2 = dict(V, New=set())
    return H, Q, S + ["New"], QS2, V2, J, n, g, c, due


if __name__ == "__main__":
    args = sys.argv[1:]
    caps = take(args, "--caps", 2) or ["6", "8"]
    out = (take(args, "--out", 1) or [None])[0]
    path = args[0] if args else "medium_instance.json"
    pc, dc = map(int, caps)
    data = load(path)
    Q = data[1]
    t0 = time.time()
    base_free, done_free, _ = best_profit(data)
    base_caps, done_caps, _ = best_profit(data, pc, dc)
    print(f"baseline: profit {base_free} ({done_free} projects) without limits, "
          f"{base_caps} ({done_caps} projects) with P<={pc}, D<={dc}")
    rows = []
    for name, skills in [(k, [k]) for k in Q] + [("all skills", Q)]:
        p_free, n_free, d_free = best_profit(with_new_person(data, skills))
        p_caps, n_caps, _ = best_profit(with_new_person(data, skills), pc, dc)
        rows.append({"new_person": name, "profit_no_limit": p_free, "gain_no_limit": p_free - base_free,
                     "projects_no_limit": n_free, "days_worked": d_free,
                     "profit_caps": p_caps, "gain_caps": p_caps - base_caps, "projects_caps": n_caps})
        print(f"  + {name:<10} no limit: {p_free} (+{p_free - base_free}, {n_free} projects, "
              f"new person works {d_free} days)   "
              f"P<={pc}, D<={dc}: {p_caps} (+{p_caps - base_caps}, {n_caps} projects)", flush=True)
    print(f"{2 * len(rows) + 2} solves in {time.time() - t0:.1f}s")
    if out:
        with open(out, "w") as fh:
            json.dump({"instance": path, "caps": [pc, dc],
                       "baseline": {"profit_no_limit": base_free, "projects_no_limit": done_free,
                                    "profit_caps": base_caps, "projects_caps": done_caps},
                       "rows": rows}, fh, indent=1)
        print("wrote", out)
