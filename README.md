# CompuOpti staffing — multi-objective MILP

Decision Modelling project (CentraleSupélec), by Abdelouahed TAHRI, Lucien DESMOULINS and Eric KAMBIRÉ.

The project assigns employees to (project, skill) pairs, day by day, and computes the full set of
non-dominated plans for three objectives:

- **f1: profit.** Gains of the completed projects minus late penalties. Maximised.
- **f2: workload.** The largest number of projects any one employee works on. Minimised.
- **f3: project length.** The longest duration of a completed project. Minimised.

The model is solved exactly with Gurobi. The Pareto front comes from the epsilon-constraint method.

## Files

| File | Content |
|---|---|
| `staffing.py` | Model, Pareto sweep, plots, and the `--plan` option that shows any point of the front as a schedule |
| `generate_instance.py` | Random instance generator in the same JSON format |
| `toy/medium/large_instance.json` | Given instances |
| `generated/` | Generated instances `gen1`–`gen4`, with their fronts, plots and run logs |
| `*_front.txt`, `*_pareto.png`, `*_schedule.png` | Results for the given instances |
| `large_run.log` | Progress log of the large run (one line per solve) |
| `slides.tex` / `slides.pdf` | Defense slides |
| `staffing_report.pdf`, `build_report.py`, `figs.py` | Written report and the scripts that build it |

## Usage

Requires Python 3, `gurobipy` 13 with a licence that is not size-limited (an academic licence works), and `matplotlib`.

```
python staffing.py toy_instance.json --prefix toy_        # whole front -> toy_front.json, toy_pareto.png, toy_schedule.png
python staffing.py toy_instance.json --plan 2 3           # schedule of the point with <= 2 projects/employee and <= 3-day projects
python staffing.py large_instance.json --resume old.log   # continue an interrupted run from its progress log
python generate_instance.py gen.json --staff 5 --jobs 12 --horizon 16 --quals 8 --seed 4
```

## Results

| Instance | Staff / projects / days | Run time | Pareto points | Best (profit, P, D) |
|---|---|---|---|---|
| toy | 3 / 5 / 5 | 0.5 s | 9 | 65, 3, 2 |
| gen1 | 3 / 6 / 8 | 1.7 s | 9 | 76, 4, 3 |
| gen2 | 4 / 8 / 10 | 8.4 s | 17 | 103, 3, 5 |
| gen3 | 4 / 10 / 14 | 90 s | 31 | 180, 5, 5 |
| gen4 | 5 / 12 / 16 | 56 s | 28 | 222, 4, 8 |
| medium | 5 / 15 / 22 | 72 min | 46 | 413, 6, 8 |
| large | 6 / 25 / 36 | ≈ 35 h of solver time | 92 | 817, 9, 8 |

In the last column, P is the largest number of projects per employee and D the length of the longest project, in days.
