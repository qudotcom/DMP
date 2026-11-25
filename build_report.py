"""Build the staffing report PDF. Usage: python build_report.py <project_dir> <fig_dir> <out_pdf>"""
import os, re, sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                Image, PageBreak, Preformatted, KeepTogether)
from reportlab.lib.utils import ImageReader

proj, figs, out = sys.argv[1], sys.argv[2], sys.argv[3]
AUTHORS = "Abdelouahed TAHRI, Lucien DESMOULINS, Eric KAMBIRÉ"

INK = colors.HexColor("#2b2b29")
MUTED = colors.HexColor("#6b6b66")
ACCENT = colors.HexColor("#1c5cab")
RULE = colors.HexColor("#d9d8d3")
BAND = colors.HexColor("#f3f2ef")
NOTE = colors.HexColor("#eef4fc")

ss = getSampleStyleSheet()
base = dict(fontName="Helvetica", textColor=INK)
S = {
    "title": ParagraphStyle("t", parent=ss["Title"], fontName="Helvetica-Bold", fontSize=22,
                            leading=27, alignment=TA_LEFT, textColor=INK, spaceAfter=4),
    "authors": ParagraphStyle("au", fontName="Helvetica", fontSize=10.5, leading=14.5, textColor=INK,
                              spaceBefore=2, spaceAfter=8),
    "sub": ParagraphStyle("s", fontName="Helvetica", fontSize=10.5, leading=14, textColor=MUTED, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=19,
                         textColor=ACCENT, spaceBefore=14, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=15,
                         textColor=INK, spaceBefore=10, spaceAfter=4),
    "body": ParagraphStyle("b", **base, fontSize=10, leading=14.2, spaceAfter=6),
    "bullet": ParagraphStyle("bl", **base, fontSize=10, leading=14, leftIndent=14,
                             bulletIndent=4, spaceAfter=2.5),
    "cap": ParagraphStyle("c", fontName="Helvetica", fontSize=8.5, leading=11, textColor=MUTED, spaceAfter=10),
    "cell": ParagraphStyle("cell", **base, fontSize=8.8, leading=11.2),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=8.8, leading=11.2, textColor=INK),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=8, leading=10.2, textColor=INK,
                           backColor=BAND, borderPadding=(6, 6, 6, 6), leftIndent=6, rightIndent=6,
                           spaceBefore=4, spaceAfter=10),
    "math": ParagraphStyle("m", **base, fontSize=10, leading=15, leftIndent=18, spaceAfter=3),
    "note": ParagraphStyle("n", **base, fontSize=9.5, leading=13.5, backColor=NOTE,
                           borderPadding=(7, 8, 7, 8), leftIndent=8, rightIndent=8,
                           spaceBefore=6, spaceAfter=12),
}

P = lambda t, s="body": KeepTogether([Paragraph(t, S[s])]) if s == "note" else Paragraph(t, S[s])
B = lambda t: Paragraph(t, S["bullet"], bulletText="•")
M = lambda t: Paragraph(t, S["math"])
code = lambda t: Preformatted(t, S["code"])


def table(rows, widths, header=True, align_right_from=None):
    data = [[Paragraph(str(c), S["cellb" if (header and r == 0) else "cell"]) for c in row]
            for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1 if header else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("LINEBELOW", (0, 0), (-1, 0), 0.8, INK if header else RULE),
          ("LINEBELOW", (0, 1), (-1, -1), 0.4, RULE),
          ("TOPPADDING", (0, 0), (-1, -1), 3.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
          ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    if header:
        st.append(("BACKGROUND", (0, 0), (-1, 0), BAND))
    t.setStyle(TableStyle(st))
    return t


def img(path, width):
    w, h = ImageReader(path).getSize()
    return Image(path, width=width, height=width * h / w)


# ---------- data ----------
def read_front_txt(path):
    pts = []
    for line in open(path):
        m = re.match(r"profit=\s*(-?\d+)\s+maxProj/emp=(\d+)\s+maxDuration=(\d+)", line)
        if m:
            pts.append(tuple(map(int, m.groups())))
    return sorted(pts, reverse=True)


def large_status(path):
    done = {}
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.search(r"Pmax<=(\d+) Dmax<=(\d+) status=\d+ solve=([\d.]+)s.*?"
                      r"(?:-> profit=(-?\d+) P=(\d+) D=(\d+))?$", line)
        if m:
            pt = (int(m[4]), int(m[5]), int(m[6])) if m[4] else None
            done[int(m[1]), int(m[2])] = (float(m[3]), pt)
    pts = {v[1] for v in done.values() if v[1]}
    dom = lambda p, q: p[0] >= q[0] and p[1] <= q[1] and p[2] <= q[2] and p != q
    front = sorted([p for p in pts if not any(dom(q, p) for q in pts)], reverse=True)
    cap = max(a for a, _ in done)
    hours = sum(t for t, _ in done.values()) / 3600
    return done, front, cap, hours


toy_front = [(65, 3, 2), (65, 2, 3), (59, 4, 1), (55, 2, 2), (49, 3, 1),
             (42, 1, 3), (37, 2, 1), (30, 1, 2), (20, 1, 1)]
med_front = read_front_txt(os.path.join(proj, "medium_front.txt"))
done, lfront, lcap, lhours = large_status(os.path.join(proj, "large_run.log"))
lfront = read_front_txt(os.path.join(proj, "large_front.txt"))
lbest = lfront[0]

# ---------- page decoration ----------
def on_page(c, doc):
    c.saveState()
    c.setFont("Helvetica", 8)
    c.setFillColor(MUTED)
    c.drawString(2 * cm, 1.2 * cm, "CompuOpti staffing — model, code and results")
    c.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"{doc.page}")
    c.restoreState()


doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                        topMargin=1.8 * cm, bottomMargin=2 * cm,
                        title="CompuOpti staffing report", author=AUTHORS)
W = A4[0] - 4 * cm
st = []

# ---------- title + summary ----------
st += [P("CompuOpti staffing: model, code and results", "title"),
       P(f"<b>{AUTHORS}</b><br/>CentraleSupélec — Decision Modelling", "authors"),
       P("Who works on which project, on which day — and what are the best trade-offs "
         "between profit, workload spread and project length. All three instances solved (23 November 2026).", "sub")]

st.append(P("Summary", "h1"))
st += [
    B("<b>The problem.</b> A company has employees with skills and holidays, and projects that each need "
      "a number of working days per skill. Finishing a project earns money; finishing late costs a daily "
      "penalty. We want a schedule that is good on three goals at once: <b>high profit</b>, "
      "<b>few projects per employee</b>, and <b>short projects</b>."),
    B("<b>The method.</b> A mixed-integer linear program (MILP) solved with Gurobi. Because the three goals "
      "conflict, we do not compute one answer but the full list of best compromises (the <i>Pareto "
      "front</i>), using the epsilon-constraint method."),
    B("<b>What we changed along the way.</b> (1) a smarter sweep that skips redundant solves, "
      "(2) a <i>resume</i> option so the long run survives a reboot, and (3) a tighter way of modelling "
      "project start/end dates, which made hard solves up to <b>28× faster</b> with identical answers."),
]
st.append(Spacer(1, 6))
st.append(table([
    ["Instance", "Size", "Status", "Best profit found", "Pareto points"],
    ["Toy", "3 staff, 5 projects, 5 days", "Done (0.5 s)", "65 (≤ 3 projects/employee, longest project 2 days)", "9"],
    ["Medium", "5 staff, 15 projects, 22 days", "Done (72 min with new model)", "413 (≤ 6 projects/employee, longest 8 days)", "46"],
    ["Large", "6 staff, 25 projects, 36 days", f"Done ({len(done)} solves, about {lhours:.0f} h of solver time)",
     f"{lbest[0]} (≤ {lbest[1]} projects/employee, longest {lbest[2]} days)",
     f"{len(lfront)}"],
], [1.7 * cm, 3.6 * cm, 3.2 * cm, 5.0 * cm, 3.5 * cm]))

# ---------- 1. problem ----------
st.append(P("1. The problem in plain words", "h1"))
st.append(P("Each instance file (JSON) describes:"))
st += [
    B("<b>A planning horizon</b> of <i>h</i> working days (5, 22 or 36)."),
    B("<b>Employees</b>, each with a set of qualifications (skills A, B, C, …) and vacation days."),
    B("<b>Projects</b>, each needing a number of working days per skill (e.g. Job2 needs 1 day of A "
      "and 2 days of B), a <b>gain</b> earned if it is fully completed, a <b>due date</b>, and a "
      "<b>daily penalty</b> for each day it finishes late."),
]
st.append(P("The rules of the game:"))
st += [
    B("An employee can only work on a skill they have, and never on a vacation day."),
    B("An employee does at most one thing per day (one project, one skill)."),
    B("A project counts only if <b>all</b> its required days are done; a half-done project earns "
      "nothing, so partial work is never scheduled."),
    B("Projects may be skipped entirely if they are not worth it."),
]
st.append(P("The three goals:"))
st.append(table([
    ["Goal", "Meaning", "Direction"],
    ["f1 — profit", "gains of completed projects minus lateness penalties", "maximise"],
    ["f2 — workload spread", "largest number of different projects any one employee works on", "minimise"],
    ["f3 — project length", "longest duration (first day to last day) of any completed project", "minimise"],
], [3.6 * cm, 10.2 * cm, 2.6 * cm]))
st.append(P("These goals pull against each other: the most profitable plans make people juggle many "
            "projects and stretch projects over many days. There is no single “best” plan, "
            "only trade-offs — which is why we compute the Pareto front.", "note"))

# ---------- 2. model ----------
st.append(P("2. The mathematical model", "h1"))
st.append(P("2.1 Decision variables (what the solver chooses)", "h2"))
st.append(table([
    ["Variable", "Type", "Meaning"],
    ["x<sub>i,j,k,t</sub>", "0/1", "employee <i>i</i> works on project <i>j</i>, using skill <i>k</i>, on day <i>t</i>. "
     "Only created when <i>i</i> has skill <i>k</i>, project <i>j</i> needs <i>k</i>, and <i>t</i> is not a vacation day "
     "— so the skill and vacation rules are built in."],
    ["y<sub>j</sub>", "0/1", "project <i>j</i> is completed"],
    ["z<sub>i,j</sub>", "0/1", "employee <i>i</i> works on project <i>j</i> at least once"],
    ["b<sub>j,t</sub>, f<sub>j,t</sub>", "0/1", "project <i>j</i> <b>b</b>egins on day <i>t</i> / <b>f</b>inishes on day <i>t</i>"],
    ["a<sub>j,t</sub>", "0..1", "project <i>j</i> is <b>a</b>ctive on day <i>t</i> (between its start and end)"],
    ["P<sub>max</sub>, D<sub>max</sub>", "number", "largest projects-per-employee (f2) and longest project duration (f3)"],
], [2.6 * cm, 1.5 * cm, 12.3 * cm]))

st.append(P("2.2 Constraints (the rules, written as equations)", "h2"))
rules = [
    ("One task per day", "for every employee <i>i</i> and day <i>t</i>:",
     "Σ<sub>j,k</sub> x<sub>i,j,k,t</sub> ≤ 1"),
    ("All or nothing", "for every project <i>j</i> and skill <i>k</i> it needs (n<sub>j,k</sub> days):",
     "Σ<sub>i,t</sub> x<sub>i,j,k,t</sub> = n<sub>j,k</sub> · y<sub>j</sub>"),
    ("One start, one end", "a completed project has exactly one start day and one end day:",
     "Σ<sub>t</sub> b<sub>j,t</sub> = y<sub>j</sub>, &nbsp;&nbsp; Σ<sub>t</sub> f<sub>j,t</sub> = y<sub>j</sub>"),
    ("Active window", "a project is active from its start day until its end day (a counter: +1 at the start, −1 after the end; "
     "since a ≥ 0, the end cannot come before the start):",
     "a<sub>j,t</sub> = Σ<sub>u≤t</sub> b<sub>j,u</sub> − Σ<sub>u&lt;t</sub> f<sub>j,u</sub>, &nbsp;&nbsp; 0 ≤ a<sub>j,t</sub> ≤ 1"),
    ("Work only inside the window", "for every employee, project and day:",
     "Σ<sub>k</sub> x<sub>i,j,k,t</sub> ≤ a<sub>j,t</sub>"),
    ("Who works on what", "if <i>i</i> works on <i>j</i> on any day, z<sub>i,j</sub> = 1; then count them:",
     "Σ<sub>k</sub> x<sub>i,j,k,t</sub> ≤ z<sub>i,j</sub>, &nbsp;&nbsp; P<sub>max</sub> ≥ Σ<sub>j</sub> z<sub>i,j</sub>"),
    ("Project length", "the duration of a project is its number of active days:",
     "D<sub>max</sub> ≥ Σ<sub>t</sub> a<sub>j,t</sub>"),
]
for name, txt, eq in rules:
    st.append(KeepTogether([P(f"<b>{name}</b> — {txt}"), M(eq)]))

st.append(P("2.3 Profit", "h2"))
st.append(P("Days late are read directly from the end day: finishing on day <i>t</i> after the due date "
            "<i>d<sub>j</sub></i> means <i>t − d<sub>j</sub></i> days late. So"))
st.append(M("late<sub>j</sub> = Σ<sub>t &gt; d<sub>j</sub></sub> (t − d<sub>j</sub>) · f<sub>j,t</sub>, "
            "&nbsp;&nbsp;&nbsp; profit = Σ<sub>j</sub> ( g<sub>j</sub> · y<sub>j</sub> − c<sub>j</sub> · late<sub>j</sub> )"))

st.append(P("2.4 Getting all the trade-offs: the epsilon-constraint method", "h2"))
st.append(P("We turn goals f2 and f3 into <b>limits</b> and maximise profit under those limits. For every pair "
            "of limits (α, β):"))
st.append(M("maximise &nbsp; profit − ε (P<sub>max</sub> + D<sub>max</sub>) &nbsp;&nbsp; subject to "
            "&nbsp; P<sub>max</sub> ≤ α, &nbsp; D<sub>max</sub> ≤ β, &nbsp; and all rules above"))
st.append(P("The tiny term ε = 0.001 is a tie-breaker: between two plans with the same profit, prefer the one "
            "with fewer projects per employee and shorter projects. Each solve gives one candidate point "
            "(profit, P, D). At the end we keep only the points that no other point beats on all three goals "
            "at once — that list is the <b>Pareto front</b>."))
st.append(P("<b>The shortcut (“jump”).</b> For a fixed α, we try β from the loosest value (the whole "
            "horizon) downwards. If the best plan under limit β has its longest project at only D days, then the "
            "same plan is also best for every limit between D and β (it is still allowed, and nothing better "
            "was allowed). So we jump straight to β = D − 1. This gives exactly the same front with far "
            "fewer solves (toy: 12 instead of 25; medium: 144 instead of 330).", "note"))

st.append(P("2.5 Why the start/end modelling matters (big-M vs time window)", "h2"))
st.append(P("The first version of the model described start and end days with integer variables "
            "s<sub>j</sub>, e<sub>j</sub> and so-called <b>big-M</b> constraints, one set per x variable:"))
st.append(M("e<sub>j</sub> ≥ t · x<sub>i,j,k,t</sub>, &nbsp;&nbsp; s<sub>j</sub> ≤ t + h (1 − x<sub>i,j,k,t</sub>), "
            "&nbsp;&nbsp; D<sub>max</sub> ≥ e<sub>j</sub> − s<sub>j</sub> + 1 − h (1 − y<sub>j</sub>)"))
st.append(P("This is correct, but weak. A MILP solver first solves a relaxed version where 0/1 variables may take "
            "fractional values (like 0.1). With x = 0.1, the term h(1 − x) is almost h, so these constraints "
            "say almost nothing: the relaxed problem believes projects can be very short and very profitable. "
            "The solver's upper bound is then far from reality, and it must explore a huge search tree to "
            "close the gap. That is why some solves took <b>2 hours</b> and more."))
st.append(P("The new version uses the start/end/active indicators b, f, a described above. There is no large "
            "constant h multiplying anything: duration is simply a count of active days, lateness a sum over "
            "the end-day indicator. The relaxed problem is much closer to the real one, so the solver proves "
            "optimality much sooner. It also has about half as many constraints."))
st.append(table([
    ["Instance", "Old model (big-M): vars / constraints", "New model (time window): vars / constraints"],
    ["Toy", "127 / 308", "187 / 182"],
    ["Medium", "1,435 / 4,073", "2,380 / 2,248"],
    ["Large", "4,191 / 12,149", "6,816 / 6,973"],
], [2.4 * cm, 7 * cm, 7 * cm]))
st.append(Spacer(1, 8))
st.append(P("Measured on the same problems, same answers:"))
st.append(table([
    ["Test", "Old model", "New model", "Result (identical)"],
    ["Large, α=4, β=13 (one solve)", "644 s", "227 s (2.8× faster)", "profit 726, P=4, D=13"],
    ["Large, α=4, β=9 (one solve)", "7,071 s (1 h 58)", "251 s (28× faster)", "profit 670, P=4, D=9"],
    ["Medium, whole front", "3 h 37 (all cores, 330 solves)", "72 min (2 cores, 144 solves)", "same 46-point front"],
    ["Toy, whole front", "about 5 s", "0.5 s", "same 9-point front"],
], [4.6 * cm, 3.8 * cm, 3.8 * cm, 4.2 * cm]))

# ---------- 3. code ----------
st.append(PageBreak())
st.append(P("3. The code (staffing.py)", "h1"))
st.append(P("One Python file, about 260 lines, built on <b>gurobipy</b> (Gurobi's Python interface) and "
            "<b>matplotlib</b> for the plots. Its parts, in order:"))
st.append(table([
    ["Function", "What it does"],
    ["load(path)", "Reads the JSON instance into simple Python lists and dictionaries: days, skills, staff, "
                   "their skills and vacations, projects with their required days, gains, penalties, due dates."],
    ["build(...)", "Creates the Gurobi model: the variables and constraints of section 2. It returns the model, "
                   "the x and y variables, and the profit, P<sub>max</sub>, D<sub>max</sub> expressions."],
    ["pareto(path, resume)", "The epsilon-constraint loop with the “jump” shortcut. Builds the model once and "
                             "only changes the two limits between solves. Prints one progress line per solve. "
                             "Keeps the non-dominated points and the schedule of the most profitable one."],
    ["read_log(path)", "For <b>--resume</b>: reads a previous progress log and returns every (α, β) already "
                       "solved with its result, so they are not solved again."],
    ["solve_point(path, P, D)", "One solve with the two limits fixed: returns the plan behind any chosen point of "
                                "the front (used by <b>--plan P D</b>)."],
    ["describe(plan)", "Prints each project of a plan: done or not, start and end day, days late, who works on it."],
    ["plot_front(front)", "3-D scatter of the Pareto front → pareto.png"],
    ["plot_schedule(plan)", "Gantt-style chart of the most profitable plan: one row per employee, one box per "
                            "day, labelled project,skill → schedule.png"],
], [3.6 * cm, 12.8 * cm]))

st.append(P("The heart of the loop", "h2"))
st.append(code(
"""for a in range(1, len(J) + 1):           # limit on projects per employee
    b = nH                               # start with the loosest duration limit
    while b >= 1:
        if (a, b) in done:               # already solved in a previous run (--resume)
            pt = done[a, b]
        else:
            cP.RHS, cD.RHS = a, b        # change the two limits, keep the model
            m.optimize()
            pt = (profit, Pmax, Dmax)    # print a progress line, remember the plan
        if pt is None:                   # infeasible: smaller limits are too
            break
        b = min(pt[2], b) - 1            # jump: limits D..b give the same plan"""))

st.append(P("How to run it", "h2"))
st.append(code(
"""python staffing.py toy_instance.json
python staffing.py medium_instance.json
python staffing.py large_instance.json --resume large_run_prev.log   # continue after a stop
python staffing.py gen4.json --plan 3 7      # schedule of one chosen point of the front
python generate_instance.py gen4.json --staff 5 --jobs 12 --horizon 16 --quals 8 --seed 4"""))
st.append(P("Each solve prints a line such as:"))
st.append(code("[118/900] Pmax<=4 Dmax<=10 status=2 solve=2256.9s elapsed=19963s -> profit=700 P=4 D=10"))
st.append(P("meaning: limits α = 4 and β = 10, status 2 = proven optimal, this solve took 2,257 s, and the best "
            "plan earns 700 with at most 4 projects per employee and a longest project of 10 days. At the end the "
            "script prints the front and writes pareto.png and schedule.png."))
st.append(P("Practical notes", "h2"))
st += [
    B("<b>Licence.</b> The free pip licence is limited to 2,000 variables/constraints and only fits the toy "
      "instance. An academic licence is installed; it is for Gurobi 13, so gurobipy 13.0.3 is used."),
    B("<b>Interruptions.</b> A Windows update rebooted the PC during the large run. Thanks to --resume, the "
      "pairs already solved were kept and the run continued where it stopped."),
    B("<b>Tie-break precision.</b> Gurobi stops when it is within 0.01 % of the optimum, which can be larger "
      "than the ε tie-breaker. Then a solve may return, say, (808, P=6, D=13) instead of (808, 6, 11). The "
      "final front is still correct (the dominated point is filtered out), but one or two extra solves are spent."),
]

# ---------- 4. results ----------
st.append(PageBreak())
st.append(P("4. Results", "h1"))
st.append(P("4.1 Toy instance (3 employees, 5 projects, 5 days)", "h2"))
st.append(P("Solved in half a second (12 solves). Nine best compromises:"))
st.append(table([["Profit", "Max projects / employee", "Longest project (days)"]] +
                [[p, a, d] for p, a, d in toy_front], [3 * cm, 5 * cm, 5 * cm]))
st.append(Spacer(1, 8))
st.append(P("The most profitable plan (65) completes Job1, Job3, Job4 and Job5, all on time, and skips Job2. "
            "Olivia works every day on 3 projects; no project lasts more than 2 days; Liam's day-1 and Emma's "
            "day-2 vacations are respected."))
st.append(img(os.path.join(proj, "toy_schedule.png"), 10 * cm))
st.append(P("Figure 1 — Toy instance, most profitable plan. Each box is one day of work: project, skill.", "cap"))

st.append(P("4.2 Medium instance (5 employees, 15 projects, 22 days)", "h2"))
st.append(P(f"Complete. The Pareto front has <b>{len(med_front)} points</b>. Each line in Figure 2 is one workload "
            "level; moving right (allowing longer projects) or to a darker line (allowing more projects per "
            "employee) raises the reachable profit, with clearly diminishing returns."))
st.append(img(os.path.join(figs, "medium_front.png"), W))
st.append(P("Figure 2 — Medium instance Pareto front: best profit for each limit on project length, one line per "
            "number of projects per employee.", "cap"))
top = [p for p in med_front if p[0] > 0][:12]
st.append(KeepTogether([
    P("The most profitable compromises:"),
    table([["Profit", "Max projects / employee", "Longest project (days)"]] + [[p, a, d] for p, a, d in top],
          [3 * cm, 5 * cm, 5 * cm])]))
st.append(Spacer(1, 6))
st.append(P("Reading the front: profit 413 is the maximum, reachable either with 6 projects per employee and "
            "8-day projects, or 5 projects and 10-day projects. Giving up only 2 % (profit 406–405) lets "
            "projects be as short as 5 days, or employees juggle only 4 projects. Below about 4 projects per "
            "employee or 5-day projects, profit drops quickly. The most profitable plan completes 11 of the 15 "
            "projects; three of them finish 1–2 days late."))
st.append(img(os.path.join(proj, "medium_schedule.png"), W))
st.append(P("Figure 3 — Medium instance, most profitable plan (profit 413).", "cap"))

st.append(P("4.3 Large instance (6 employees, 25 projects, 36 days)", "h2"))
st.append(P(f"Complete. The sweep covered all 25 workload limits with {len(done)} solves and about {lhours:.0f} hours "
            f"of solver time (the run was interrupted twice and resumed from its log). The Pareto front has "
            f"<b>{len(lfront)} points</b>. The best profit is <b>{lbest[0]}</b> (the gains of all "
            f"25 projects add up to 1,020)."))
st.append(img(os.path.join(figs, "large_front.png"), 0.9 * W))
st.append(P("Figure 4 — Large instance Pareto front: best profit for each limit on project length, one line per "
            "number of projects per employee.", "cap"))
ltop = lfront[:10]
st.append(KeepTogether([
    P("The most profitable compromises:"),
    table([["Profit", "Max projects / employee", "Longest project (days)"]] + [[p, a, d] for p, a, d in ltop],
          [3 * cm, 5 * cm, 5 * cm])]))
st.append(Spacer(1, 6))
st.append(P("Reading the front: profit 817 is the maximum, and it can be reached in three ways: 9 projects per "
            "employee with 8-day projects, 8 projects with 10-day projects, or 7 projects with 11-day projects. "
            "Giving up about 3 % (profit 794) brings the workload down to 6 projects per employee with 9-day "
            "projects; giving up about 4 % (782) allows 5 projects per employee. Allowing more than 7 projects per "
            "employee never adds profit: limits 8 and 9 keep profit 817 while shortening the longest project "
            "from 11 to 10 and then 8 days; limits 10 and 11 only appear on the front for very short projects "
            "(at most 5 days, e.g. profit 764 with 10 projects per employee and 5-day projects). Beyond 11, "
            "nothing changes.", "note"))
st.append(P("The most profitable plan (profit 817, at most 9 projects per employee, longest project 8 days) "
            "completes 17 of the 25 projects."))
st.append(img(os.path.join(proj, "large_schedule.png"), W))
st.append(P("Figure 5 — Large instance, most profitable plan (profit 817).", "cap"))
st.append(P("<b>Run time.</b> Almost all the effort went into limits 3 to 8 (3–7 hours of solving each); the "
            "hardest single solve (8 projects per employee, 4-day projects) took 3 h 15. From limit 9 on, each "
            "limit took only about 25 minutes, because those limits no longer constrain the best plans."))

st.append(P("4.4 Generated instances", "h2"))
st.append(P("The brief asks for an instance generator to test performance. <b>generate_instance.py</b> writes a "
            "JSON file in the same format as the given instances. Each employee gets 1–5 random skills (every "
            "skill is held by someone) and about 8 % of the days as leave. Each project needs 1–4 skills; the "
            "person-days are scaled so that total demand is about 1.3 times the available capacity, as in the "
            "given instances, so not every project can be done. Gains are about 3.75 per person-day (±30 %), due "
            "dates fall between a third of the horizon and its end, and the penalty is 3 per day late. The same "
            "arguments and seed always give the same file."))
st.append(table([
    ["Instance", "Staff / projects / days / skills", "Solves", "Time", "Front", "Best (profit, P, D)"],
    ["toy (given)", "3 / 5 / 5 / 3", "12", "0.5 s", "9", "65, 3, 2"],
    ["gen1", "3 / 6 / 8 / 4", "21", "1.7 s", "9", "76, 4, 3"],
    ["gen2", "4 / 8 / 10 / 5", "45", "8.4 s", "17", "103, 3, 5"],
    ["gen3", "4 / 10 / 14 / 6", "73", "90 s", "31", "180, 5, 5"],
    ["gen4", "5 / 12 / 16 / 8", "101", "56 s", "28", "222, 4, 8"],
    ["medium (given)", "5 / 15 / 22 / 10", "144", "72 min", "46", "413, 6, 8"],
    ["large (given)", "6 / 25 / 36 / 10", "347", "≈ 35 h", "92", "817, 9, 8"],
], [2.8 * cm, 4.4 * cm, 1.6 * cm, 1.8 * cm, 1.5 * cm, 3.6 * cm]))
st.append(Spacer(1, 6))
st.append(P("The number of solves grows roughly with projects × days, but the time per solve grows much faster, "
            "and size alone does not decide difficulty: gen4 is bigger than gen3 yet solved faster."))
st.append(P("<b>Decision space for any point.</b> Every point of the front can be opened as a schedule with "
            "<b>--plan P D</b>. Figure 6 shows the gen4 compromise with profit 216, at most 3 projects per "
            "employee and 7-day projects, against 222 with 4 projects and 8-day projects for the best plan."))
st.append(KeepTogether([img(os.path.join(proj, "generated", "gen4_schedule_P3_D7.png"), W),
                        P("Figure 6 — gen4, schedule of the front point (216, 3, 7), produced by "
                          "python staffing.py gen4.json --plan 3 7.", "cap")]))

# ---------- 5. conclusion ----------
st.append(P("5. Conclusions and possible next steps", "h1"))
st += [
    B("The model gives provably optimal trade-offs for the three given instances (9, 46 and 92 Pareto points) "
      "and for four generated ones, and "
      "the two formulations agree exactly where both were run."),
    B("Modelling choices matter more than hardware: replacing big-M constraints by a time-window "
      "formulation sped hard solves up by 3–28×. (A GPU would not help: Gurobi's MIP solver runs on CPU.)"),
    B("On the large instance, workload limits above 7 never raised the best profit, but they still added "
      "points: 8 and 9 reach the same profit with shorter projects, and 10 and 11 add a few trade-offs for very "
      "short projects, so stopping the sweep early would have lost points. To go faster on "
      "bigger instances: a time limit per solve (near-optimal points, flagged as such), or further "
      "strengthening, e.g. lower bounds on each project's duration from its required days and available staff."),
    B("For decision makers, the fronts suggest sweet spots rather than the maximum: on the medium instance, "
      "accepting 2 % less profit allows much shorter projects or a much lighter workload; on the large instance, "
      "3 % less profit (794) cuts the workload from 9 to 6 projects per employee."),
]

doc.build(st, onFirstPage=on_page, onLaterPages=on_page)
print("written", out)
