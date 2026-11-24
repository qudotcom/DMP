"""
Random instance generator for the CompuOpti staffing problem.
Writes a JSON file in the same format as toy/medium/large_instance.json.

Usage:
  python generate_instance.py OUT.json [--horizon 15] [--staff 4] [--jobs 10]
                              [--quals 5] [--load 1.3] [--vacation 0.08] [--seed 0]

  --load      total person-days demanded / total person-days available
              (> 1 means not every project can be done, as in the given instances)
  --vacation  share of each employee's days that are leave days
The generator is reproducible: the same arguments and seed give the same file.
"""
import argparse, json, random, string

NAMES = ["Olivia", "Liam", "Emma", "Noah", "Amelia", "Oliver", "Ava", "Elijah", "Sophia",
         "Lucas", "Mia", "Mateo", "Isla", "Leo", "Zoe", "Hugo", "Lina", "Adam", "Nora", "Sami"]


def generate(horizon, n_staff, n_jobs, n_quals, load, vacation, seed):
    rng = random.Random(seed)
    quals = list(string.ascii_uppercase[:n_quals])

    # staff: 1 to min(5, Q) skills each; make sure every skill is held by someone
    staff = []
    for s in range(n_staff):
        k = rng.randint(1, min(5, n_quals))
        staff.append({"name": NAMES[s] if s < len(NAMES) else f"Staff{s + 1}",
                      "qualifications": sorted(rng.sample(quals, k)),
                      "vacations": sorted(rng.sample(range(1, horizon + 1),
                                                     round(vacation * horizon * rng.uniform(0.5, 1.5))))})
    for q in quals:
        if not any(q in s["qualifications"] for s in staff):
            s = rng.choice(staff)
            s["qualifications"] = sorted(s["qualifications"] + [q])

    # jobs: 1-4 skills each, random person-days, then scaled to hit the target load
    capacity = sum(horizon - len(s["vacations"]) for s in staff)
    raw = []
    for _ in range(n_jobs):
        ks = rng.sample(quals, rng.randint(1, min(4, n_quals)))
        raw.append({k: rng.uniform(1, 6) for k in ks})
    scale = load * capacity / sum(sum(r.values()) for r in raw)
    jobs = []
    for j, r in enumerate(raw):
        days = {k: max(1, round(v * scale)) for k, v in sorted(r.items())}
        work = sum(days.values())
        # gain about 3.75 per person-day (as in the given instances), rounded to 5
        gain = max(5, 5 * round(work * 3.75 * rng.uniform(0.7, 1.3) / 5))
        # due date: at least enough calendar days for the longest skill, at most the horizon
        earliest = min(horizon, max(days.values()) + 1)
        due = rng.randint(max(earliest, horizon // 3), horizon)
        jobs.append({"name": f"Job{j + 1}", "gain": gain, "due_date": due, "daily_penalty": 3,
                     "working_days_per_qualification": days})

    return {"horizon": horizon, "qualifications": quals, "staff": staff, "jobs": jobs}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("out")
    ap.add_argument("--horizon", type=int, default=15)
    ap.add_argument("--staff", type=int, default=4)
    ap.add_argument("--jobs", type=int, default=10)
    ap.add_argument("--quals", type=int, default=5)
    ap.add_argument("--load", type=float, default=1.3)
    ap.add_argument("--vacation", type=float, default=0.08)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    inst = generate(a.horizon, a.staff, a.jobs, a.quals, a.load, a.vacation, a.seed)
    with open(a.out, "w") as f:
        json.dump(inst, f, indent=4)
    demand = sum(sum(j["working_days_per_qualification"].values()) for j in inst["jobs"])
    cap = sum(a.horizon - len(s["vacations"]) for s in inst["staff"])
    print(f"wrote {a.out}: {a.staff} staff, {a.jobs} jobs, {a.horizon} days, {a.quals} skills, "
          f"demand {demand} / capacity {cap} person-days")
