"""
CompuOpti staffing - multi-objective MILP with Gurobi.
Objectives:
  f1 = max  profit  = sum g_j y_j - sum c_j l_j
  f2 = min  max number of projects per employee
  f3 = min  max duration of a completed project
Pareto front via epsilon-constraint on (f2, f3).
Usage: python staffing.py toy_instance.json [--prefix toy_] [--resume previous_progress.log]
       python staffing.py toy_instance.json --plan 2 3      (one chosen point of the front)
"""
import json, sys, itertools, time, re
import gurobipy as gp
from gurobipy import GRB
import matplotlib.pyplot as plt


def load(path):
    with open(path) as f:
        d = json.load(f)
    H = list(range(1, d["horizon"] + 1))
    Q = d["qualifications"]
    S = [s["name"] for s in d["staff"]]
    QS = {s["name"]: set(s["qualifications"]) for s in d["staff"]}
    V = {s["name"]: set(s["vacations"]) for s in d["staff"]}
    J = [j["name"] for j in d["jobs"]]
    n = {j["name"]: j["working_days_per_qualification"] for j in d["jobs"]}
    g = {j["name"]: j["gain"] for j in d["jobs"]}
    c = {j["name"]: j["daily_penalty"] for j in d["jobs"]}
    due = {j["name"]: j["due_date"] for j in d["jobs"]}
    return H, Q, S, QS, V, J, n, g, c, due


def build(H, Q, S, QS, V, J, n, g, c, due):
    m = gp.Model("staffing")
    m.Params.OutputFlag = 0
    # x only created where feasible -> constraints (1),(3) and k in Q_j^J built in
    idx = [(i, j, k, t) for i in S for j in J for k in n[j]
           for t in H if k in QS[i] and t not in V[i]]
    x = m.addVars(idx, vtype=GRB.BINARY, name="x")
    y = m.addVars(J, vtype=GRB.BINARY, name="y")             # project completed
    # Time window of each project, without big-M constraints:
    #   b[j,t] = 1 if project j starts on day t, f[j,t] = 1 if it ends on day t,
    #   a[j,t] = 1 if day t lies in [start, end]  (a = #starts up to t - #ends before t)
    b = m.addVars(J, H, vtype=GRB.BINARY, name="b")
    f = m.addVars(J, H, vtype=GRB.BINARY, name="f")
    a = m.addVars(J, H, lb=0, ub=1, name="a")
    z = m.addVars(S, J, vtype=GRB.BINARY, name="z")          # i works on j
    Pmax = m.addVar(lb=0, name="Pmax")
    Dmax = m.addVar(lb=0, name="Dmax")

    # (2) one assignment per employee per day
    for i in S:
        for t in H:
            m.addConstr(x.sum(i, "*", "*", t) <= 1)
    # (4)+(5) coverage: exactly n_jk days if completed, 0 otherwise
    for j in J:
        for k, njk in n[j].items():
            m.addConstr(x.sum("*", j, k, "*") == njk * y[j])
    # one start and one end day per completed project; a >= 0 forces end >= start
    for j in J:
        m.addConstr(b.sum(j, "*") == y[j])
        m.addConstr(f.sum(j, "*") == y[j])
        for t in H:
            m.addConstr(a[j, t] == gp.quicksum(b[j, u] for u in H if u <= t)
                        - gp.quicksum(f[j, u] for u in H if u < t))
        m.addConstr(Dmax >= a.sum(j, "*"))                   # duration = active days
    # work only inside the window; z[i,j] = 1 if i ever works on j
    ijt = {(i, j, t) for (i, j, _, t) in idx}
    for (i, j, t) in ijt:
        w = x.sum(i, j, "*", t)
        m.addConstr(w <= a[j, t])
        m.addConstr(w <= z[i, j])
    for i in S:
        m.addConstr(Pmax >= z.sum(i, "*"))

    # days late = max(0, end - due), read off the end-day indicator
    late = {j: gp.quicksum((t - due[j]) * f[j, t] for t in H if t > due[j]) for j in J}
    profit = gp.quicksum(g[j] * y[j] - c[j] * late[j] for j in J)
    return m, x, y, profit, Pmax, Dmax


LOG_RE = re.compile(r"\[(\d+)/\d+\] Pmax<=(\d+) Dmax<=(\d+) status=(\d+) .*?elapsed=(\d+)s"
                    r"(?: -> profit=(-?\d+) P=(\d+) D=(\d+))?")


def read_log(path):
    """Pairs solved in a previous run's progress log -> ({(a, b): pt or None}, elapsed).
    pt is None when that solve was not optimal (infeasible)."""
    done, elapsed = {}, 0
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            mt = LOG_RE.search(line)
            if not mt:
                continue
            pt = (int(mt[6]), int(mt[7]), int(mt[8])) if mt[6] is not None else None
            done[int(mt[2]), int(mt[3])] = pt
            elapsed = int(mt[5])
    return done, elapsed


def pareto(path, resume=None):
    data = load(path)
    H, J = data[0], data[5]
    m, x, y, profit, Pmax, Dmax = build(*data)
    eps = 1e-3  # tie-break so solutions are non-dominated
    m.setObjective(profit - eps * (Pmax + Dmax), GRB.MAXIMIZE)
    cP = m.addConstr(Pmax <= len(J))
    cD = m.addConstr(Dmax <= len(H))
    done, prev = read_log(resume) if resume else ({}, 0)
    nH, total = len(H), len(J) * len(H)
    if resume:
        print(f"Resuming from {resume}: {len(done)} of {total} pairs already solved", flush=True)
    sols = [(pt, None) for pt in done.values() if pt is not None]  # plans are not logged
    t0 = time.time() - prev
    # For each Pmax cap a, sweep the Dmax cap b downward. If the optimum at (a, b) has
    # Dmax = d <= b, it stays optimal for every cap in [d, b] (smaller feasible set, same
    # solution still feasible), so jump straight to b = d - 1. Infeasible -> all smaller
    # caps are infeasible too. Gives the same front as trying every (a, b) pair.
    for a in range(1, len(J) + 1):
        b = nH
        while b >= 1:
            if (a, b) in done:
                pt = done[a, b]
            else:
                cP.RHS, cD.RHS = a, b
                m.optimize()
                msg = (f"[{(a - 1) * nH + b}/{total}] Pmax<={a} Dmax<={b} status={m.Status} "
                       f"solve={m.Runtime:.1f}s elapsed={time.time() - t0:.0f}s")
                if m.Status != GRB.OPTIMAL:
                    print(msg, flush=True)
                    pt = None
                else:
                    pt = (round(profit.getValue()), round(Pmax.X), round(Dmax.X))
                    print(f"{msg} -> profit={pt[0]} P={pt[1]} D={pt[2]}", flush=True)
                    sols.append((pt, [k for k, v in x.items() if v.X > 0.5]))
            if pt is None:
                break
            b = min(pt[2], b) - 1
    # keep non-dominated (max f1, min f2, min f3)
    dom = lambda p, q: p[0] >= q[0] and p[1] <= q[1] and p[2] <= q[2] and p != q
    front = {}
    for p, plan in sols:
        if not any(dom(q, p) for q, _ in sols):
            front[p] = plan
    best = max(front)
    if front[best] is None:  # best point came from the resume log: re-solve it for its plan
        cP.RHS, cD.RHS = best[1], best[2]
        m.optimize()
        front[best] = [k for k, v in x.items() if v.X > 0.5]
    return front, data


def solve_point(path, pcap, dcap):
    """One solve with Pmax <= pcap and Dmax <= dcap: the plan behind one point of the front."""
    data = load(path)
    m, x, y, profit, Pmax, Dmax = build(*data)
    m.setObjective(profit - 1e-3 * (Pmax + Dmax), GRB.MAXIMIZE)
    m.addConstr(Pmax <= pcap)
    m.addConstr(Dmax <= dcap)
    m.optimize()
    if m.Status != GRB.OPTIMAL:
        return None, None, data
    pt = (round(profit.getValue()), round(Pmax.X), round(Dmax.X))
    return pt, [k for k, v in x.items() if v.X > 0.5], data


def describe(plan, data):
    """Print, for each completed project, who works on it, its start/end day and days late."""
    H, Q, S, QS, V, J, n, g, c, due = data
    for j in J:
        days = sorted({t for (_, jj, _, t) in plan if jj == j})
        if not days:
            print(f"  {j:<6} not done")
            continue
        who = sorted({i for (i, jj, _, _) in plan if jj == j})
        late = max(0, days[-1] - due[j])
        print(f"  {j:<6} days {days[0]:>2}-{days[-1]:<2} ({days[-1] - days[0] + 1} d)  gain {g[j]:>3}"
              f"  late {late} d (-{c[j] * late})  staff: {', '.join(who)}")


def plot_front(front, fname="pareto.png"):
    pts = list(front)
    ax = plt.figure().add_subplot(projection="3d")
    ax.scatter([p[1] for p in pts], [p[2] for p in pts], [p[0] for p in pts], c="#8C1515")
    ax.set_xlabel("max projects / employee"); ax.set_ylabel("max duration"); ax.set_zlabel("profit")
    plt.title("Non-dominated solutions"); plt.savefig(fname, dpi=200); plt.close()


def plot_schedule(plan, data, fname="schedule.png", title=None):
    H, S = data[0], data[2]
    fig, ax = plt.subplots(figsize=(1 + len(H) * 0.6, 1 + len(S) * 0.5))
    cmap = plt.get_cmap("tab20")
    jobs = sorted({j for _, j, _, _ in plan})
    for (i, j, k, t) in plan:
        r = S.index(i)
        ax.barh(r, 1, left=t - 0.5, color=cmap(jobs.index(j) % 20), edgecolor="white")
        ax.text(t, r, f"{j},{k}", ha="center", va="center", fontsize=6)
    ax.set_yticks(range(len(S))); ax.set_yticklabels(S); ax.set_xticks(H)
    if title:
        ax.set_title(title, loc="left", fontsize=9)
    ax.set_xlabel("day"); plt.tight_layout(); plt.savefig(fname, dpi=200); plt.close()


def take(args, flag, n):
    """Remove `flag` and its n values from args; return the values (or None)."""
    if flag not in args:
        return None
    i = args.index(flag)
    vals = args[i + 1:i + 1 + n]
    del args[i:i + 1 + n]
    return vals


USAGE = """usage:
  python staffing.py INSTANCE.json [--prefix NAME_] [--resume LOG]
      whole Pareto front: prints it, writes NAME_front.json, NAME_pareto.png, NAME_schedule.png
  python staffing.py INSTANCE.json --plan P D [--prefix NAME_]
      the solution behind one front point (max P projects/employee, longest project D days):
      prints it project by project and writes NAME_schedule_P{P}_D{D}.png"""

if __name__ == "__main__":
    args = sys.argv[1:]
    if "-h" in args or "--help" in args:
        sys.exit(USAGE)
    resume = (take(args, "--resume", 1) or [None])[0]
    prefix = (take(args, "--prefix", 1) or [""])[0]
    plan_caps = take(args, "--plan", 2)
    path = args[0] if args else "toy_instance.json"

    if plan_caps:  # decision space: one chosen solution
        pc, dc = map(int, plan_caps)
        pt, plan, data = solve_point(path, pc, dc)
        if pt is None:
            sys.exit(f"no feasible plan with at most {pc} projects/employee and {dc}-day projects")
        print(f"profit={pt[0]}  maxProj/emp={pt[1]}  maxDuration={pt[2]}")
        describe(plan, data)
        fname = f"{prefix}schedule_P{pc}_D{dc}.png"
        plot_schedule(plan, data, fname, f"profit {pt[0]}, max {pt[1]} projects/employee, "
                                         f"longest project {pt[2]} days")
        print("wrote", fname)
        sys.exit()

    t0 = time.time()
    front, data = pareto(path, resume)
    print(f"front: {len(front)} points in {time.time() - t0:.1f}s")
    for p in sorted(front, reverse=True):
        print(f"profit={p[0]:>5}  maxProj/emp={p[1]}  maxDuration={p[2]}")
    with open(f"{prefix}front.json", "w") as fh:
        json.dump([{"profit": p[0], "max_projects_per_employee": p[1], "max_duration": p[2]}
                   for p in sorted(front, reverse=True)], fh, indent=1)
    plot_front(front, f"{prefix}pareto.png")
    best = max(front)
    plot_schedule(front[best], data, f"{prefix}schedule.png",
                  f"profit {best[0]}, max {best[1]} projects/employee, longest project {best[2]} days")
    print(f"wrote {prefix}front.json, {prefix}pareto.png, {prefix}schedule.png")
