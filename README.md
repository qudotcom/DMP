# CompuOpti staffing: a multi-objective MILP

Decision Modelling project (CentraleSupélec), by Abdelouahed TAHRI, Lucien DESMOULINS and Eric KAMBIRÉ.  

Employees are assigned to (project, skill) pairs day by day. We compute all the non-dominated plans for
three criteria:

- **f1, profit:** gains of the completed projects minus the delay penalties (maximised);
- **f2, workload:** largest number of projects an employee works on (minimised);
- **f3, duration:** longest duration of a completed project (minimised).

The model is solved exactly with Gurobi, and the Pareto front is obtained with the epsilon-constraint method.

## Files

| File | Content |
|---|---|
| `staffing.py` | Model, Pareto sweep, plots, and the `--plan` option that shows any point of the front as a schedule |
| `generate_instance.py` | Random instance generator (same JSON format as the given instances) |
| `value_of_person.py`, `medium_value_of_person.json` | Profit gained by adding one employee with a given skill |
| `plot_cubes.py`, `pareto_cubes.png` | 3-D views of the fronts, drawn from the saved results |
| `figs.py` | Front charts used in the report and the slides |
| `toy_instance.json`, `medium_instance.json`, `large_instance.json` | Given instances |
| `generated/` | Generated instances `gen1` to `gen4`, with their fronts, figures and run logs |
| `*_front.txt`, `toy_front.json`, `*_pareto.png`, `*_schedule.png` | Results for the given instances |
| `medium_run.log`, `large_run.log` | Progress logs of the medium and large runs (one line per solve) |
| `staffing_report.pdf`, `build_report.py` | Report and the script that builds it |
| `slides.tex`, `slides.pdf` | Presentation slides |
| `bigM_vs_timewindow.tex`, `bigM_vs_timewindow.pdf` | One-page note (in French) comparing the big-M and time-window formulations |
| `centralesupelec_logo.png` | Logo used on the report cover (Wikimedia Commons, public domain) |

## Usage

Requires Python 3, `gurobipy` 13 with a licence that is not size-limited (an academic licence works),
`matplotlib`, and `reportlab` to rebuild the report.

```
git clone https://github.com/qudotcom/DMP.git && cd DMP
python staffing.py toy_instance.json --prefix toy_        # whole front: toy_front.json, toy_pareto.png, toy_schedule.png
python staffing.py toy_instance.json --plan 2 3           # plan with at most 2 projects per employee and 3-day projects
python staffing.py large_instance.json --resume old.log   # continue an interrupted run from its progress log
python generate_instance.py gen.json --staff 5 --jobs 12 --horizon 16 --quals 8 --seed 4
python value_of_person.py medium_instance.json --caps 6 8 --out medium_value_of_person.json
python plot_cubes.py
python figs.py
python build_report.py
```

## Results

| Instance | Staff / projects / days | Run time | Pareto points | Best (profit, P, D) |
|---|---|---|---|---|
| toy | 3 / 5 / 5 | 0.5 s | 9 | 65, 3, 2 |
| gen1 | 3 / 6 / 8 | 1.7 s | 9 | 76, 4, 3 |
| gen2 | 4 / 8 / 10 | 8.4 s | 17 | 103, 3, 5 |
| gen3 | 4 / 10 / 14 | 90 s | 31 | 180, 5, 5 |
| gen4 | 5 / 12 / 16 | 56 s | 28 | 222, 4, 8 |
| medium | 5 / 15 / 22 | 23 min | 46 | 413, 6, 8 |
| large | 6 / 25 / 36 | about 29 h (estimated, see below) | 92 | 817, 9, 8 |

P is the largest number of projects per employee and D the length of the longest project, in days. Times are for
the whole sweep on an idle machine with 8 cores. The large log adds up to 35 h of solver time, but its first 100
solves were made with our first (big-M) model. Solving 47 of them again with the time-window model was 5.7 times
faster, so the whole sweep with the final model is estimated at about 29 h.
