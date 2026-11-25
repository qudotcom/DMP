"""Build the project report (staffing_report.pdf).

Usage: python build_report.py [project_dir] [output.pdf]
"""
import json
import os
import re
import sys

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas as rl_canvas
from reportlab.platypus import (HRFlowable, Image, KeepTogether, PageBreak, Paragraph, Preformatted,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

proj = sys.argv[1] if len(sys.argv) > 1 else "."
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(proj, "staffing_report.pdf")

AUTHORS = ["Abdelouahed TAHRI", "Lucien DESMOULINS", "Eric KAMBIRÉ"]
TITLE = "Staffing Collaborators on Projects"
SUBTITLE = "A multi-objective MILP for CompuOpti"
REPO = "https://github.com/qudotcom/DMP"

# colours of the slides
CARDINAL = colors.HexColor("#8C1515")
SANDSTONE = colors.HexColor("#D2C295")
INK = colors.HexColor("#4D4F53")
MUTED = colors.HexColor("#7A7C80")
FOG = colors.HexColor("#F4F4F4")

base = dict(fontName="Helvetica", textColor=INK)
S = {
    "h1": ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=15, leading=19, textColor=CARDINAL,
                         spaceBefore=14, spaceAfter=2),
    "h2": ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=15, textColor=CARDINAL,
                         spaceBefore=10, spaceAfter=4, keepWithNext=1),
    "body": ParagraphStyle("body", **base, fontSize=10, leading=14.2, spaceAfter=6),
    "bullet": ParagraphStyle("bullet", **base, fontSize=10, leading=14, leftIndent=14, bulletIndent=3,
                             bulletFontName="ZapfDingbats", bulletFontSize=5.5, bulletColor=CARDINAL,
                             spaceAfter=2.5),
    "cap": ParagraphStyle("cap", fontName="Helvetica", fontSize=8.5, leading=11, textColor=MUTED, spaceAfter=10),
    "cell": ParagraphStyle("cell", **base, fontSize=8.8, leading=11.2),
    "cellb": ParagraphStyle("cellb", fontName="Helvetica-Bold", fontSize=8.8, leading=11.2, textColor=INK),
    "code": ParagraphStyle("code", fontName="Courier", fontSize=8, leading=10.2, textColor=INK, backColor=FOG,
                           borderPadding=(6, 6, 6, 6), leftIndent=6, rightIndent=6, spaceBefore=4, spaceAfter=10),
    "math": ParagraphStyle("math", **base, fontSize=10, leading=15, leftIndent=18, spaceAfter=3),
    "note": ParagraphStyle("note", **base, fontSize=9.5, leading=13.5),
}


def note(text):
    """Grey box with a red bar on the left."""
    box = Table([[Paragraph(text, S["note"])]], colWidths=[A4[0] - 4 * cm], hAlign="LEFT")
    box.setStyle(TableStyle([("BACKGROUND", (0, 0), (-1, -1), FOG),
                             ("LINEBEFORE", (0, 0), (0, -1), 3, CARDINAL),
                             ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
                             ("LEFTPADDING", (0, 0), (-1, -1), 10), ("RIGHTPADDING", (0, 0), (-1, -1), 10)]))
    return KeepTogether([Spacer(1, 4), box, Spacer(1, 10)])


def P(text, style="body"):
    if style == "note":
        return note(text)
    if style == "h1":
        return KeepTogether([Paragraph(text, S["h1"]),
                             HRFlowable(width="100%", thickness=1.5, color=CARDINAL, spaceAfter=8)])
    return Paragraph(text, S[style])


def B(text):
    return Paragraph(text, S["bullet"], bulletText="n")  # "n" is a filled square in ZapfDingbats


def M(text):
    return Paragraph(text, S["math"])


def code(text):
    return Preformatted(text, S["code"])


def table(rows, widths):
    data = [[Paragraph(str(c), S["cellb" if r == 0 else "cell"]) for c in row] for r, row in enumerate(rows)]
    t = Table(data, colWidths=widths, hAlign="LEFT", repeatRows=1)
    t.setStyle(TableStyle([("VALIGN", (0, 0), (-1, -1), "TOP"),
                           ("LINEABOVE", (0, 0), (-1, 0), 1.1, INK),
                           ("LINEBELOW", (0, 0), (-1, 0), 0.6, INK),
                           ("LINEBELOW", (0, -1), (-1, -1), 1.1, INK),
                           ("TOPPADDING", (0, 0), (-1, -1), 2.5), ("BOTTOMPADDING", (0, 0), (-1, -1), 2.5),
                           ("LEFTPADDING", (0, 0), (-1, -1), 5), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]))
    return t


def img(path, width):
    w, h = ImageReader(path).getSize()
    return Image(path, width=width, height=width * h / w)


def figure(path, width, caption):
    return KeepTogether([img(path, width), P(caption, "cap")])


# ---------- data ----------
def read_front_txt(path):
    pts = []
    for line in open(path):
        m = re.match(r"profit=\s*(-?\d+)\s+maxProj/emp=(\d+)\s+maxDuration=(\d+)", line)
        if m:
            pts.append(tuple(map(int, m.groups())))
    return sorted(pts, reverse=True)


def solve_times(path):
    """Solver time of every solve in a progress log, in the order of the log."""
    times = []
    for line in open(path, encoding="utf-8", errors="replace"):
        m = re.search(r"Pmax<=\d+ Dmax<=\d+ status=\d+ solve=([\d.]+)s", line)
        if m:
            times.append(float(m[1]))
    return times


# The first 100 solves of large_run.log were made with the big-M model, before the run was resumed with
# the time-window model. Re-solving 47 of these bounds with the time-window model was 5.69 times faster
# (ratio of the total solver times), which gives the estimate of the full sweep with the final model.
LARGE_BIGM_SOLVES, LARGE_SPEEDUP = 100, 5.69

toy_front = [(65, 3, 2), (65, 2, 3), (59, 4, 1), (55, 2, 2), (49, 3, 1),
             (42, 1, 3), (37, 2, 1), (30, 1, 2), (20, 1, 1)]
med_front = read_front_txt(os.path.join(proj, "medium_front.txt"))
lfront = read_front_txt(os.path.join(proj, "large_front.txt"))
lbest = lfront[0]
ltimes = solve_times(os.path.join(proj, "large_run.log"))
lsolves = len(ltimes)
lhours = sum(ltimes) / 3600
lbigm = sum(ltimes[:LARGE_BIGM_SOLVES]) / 3600
ltw = (sum(ltimes[:LARGE_BIGM_SOLVES]) / LARGE_SPEEDUP + sum(ltimes[LARGE_BIGM_SOLVES:])) / 3600

vop = json.load(open(os.path.join(proj, "medium_value_of_person.json")))
minst = json.load(open(os.path.join(proj, "medium_instance.json")))
vh = minst["horizon"]
vbase = vop["baseline"]["profit_no_limit"]
vrows = sorted(vop["rows"], key=lambda r: (r["new_person"] == "all skills", -r["gain_no_limit"]))
vtop = vrows[0]
vall = next(r for r in vrows if r["new_person"] == "all skills")
vmore = vtop["projects_no_limit"] - vop["baseline"]["projects_no_limit"]
same_caps = all(r["gain_caps"] == r["gain_no_limit"] for r in vrows)
vavg = sum(j["gain"] for j in minst["jobs"]) / sum(sum(j["working_days_per_qualification"].values())
                                                   for j in minst["jobs"])


# ---------- page decoration ----------
class NumberedCanvas(rl_canvas.Canvas):
    """Red footer bar with the page number, on every page except the cover."""

    def __init__(self, *a, **k):
        super().__init__(*a, **k)
        self._pages = []

    def showPage(self):
        self._pages.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        total = len(self._pages) - 1
        for state in self._pages:
            self.__dict__.update(state)
            if self._pageNumber > 1:
                self.saveState()
                self.setFillColor(CARDINAL)
                self.rect(0, 0, A4[0], 0.75 * cm, stroke=0, fill=1)
                self.setFillColor(colors.white)
                self.setFont("Helvetica", 8)
                self.drawString(2 * cm, 0.28 * cm, "CompuOpti Staffing")
                self.drawRightString(A4[0] - 2 * cm, 0.28 * cm, f"{self._pageNumber - 1}/{total}")
                self.restoreState()
            super().showPage()
        super().save()


def draw_cover(c, doc):
    """Cover page, drawn directly on the canvas."""
    import random
    pw, ph = A4
    x0 = 3.2 * cm                      # left edge of the text block
    c.saveState()

    # red band on the left, thin sandstone line next to it
    c.setFillColor(CARDINAL)
    c.rect(0, 0, 1.5 * cm, ph, stroke=0, fill=1)
    c.setFillColor(SANDSTONE)
    c.rect(1.5 * cm, 0, 0.12 * cm, ph, stroke=0, fill=1)

    # logo and course name
    lw = 5.2 * cm
    iw, ih = ImageReader(os.path.join(proj, "centralesupelec_logo.png")).getSize()
    lh = lw * ih / iw
    c.drawImage(os.path.join(proj, "centralesupelec_logo.png"), x0, ph - 1.9 * cm - lh, lw, lh, mask="auto")
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 10)
    c.drawRightString(pw - 2 * cm, ph - 2.6 * cm, "Decision Modelling")
    c.drawRightString(pw - 2 * cm, ph - 3.15 * cm, "Project report, 2026")

    # title block
    y = ph - 9.4 * cm
    c.setFillColor(colors.HexColor("#A8925A"))
    c.setFont("Helvetica-Bold", 10)
    c.drawString(x0, y, "P R O J E C T   R E P O R T")
    c.setFillColor(CARDINAL)
    c.setFont("Helvetica-Bold", 34)
    c.drawString(x0, y - 1.45 * cm, "Staffing Collaborators")
    c.drawString(x0, y - 2.75 * cm, "on Projects")
    c.setFillColor(CARDINAL)
    c.rect(x0, y - 3.45 * cm, 3.2 * cm, 0.12 * cm, stroke=0, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica", 15)
    c.drawString(x0, y - 4.35 * cm, SUBTITLE)
    c.setFont("Helvetica", 11)
    c.setFillColor(MUTED)
    c.drawString(x0, y - 5.0 * cm, "Exact Pareto fronts for profit, workload and project duration")

    # stylised Gantt chart: rows of days, a nod to the schedules in the report
    rng = random.Random(7)
    tints = ["#8C1515", "#B5524F", "#D9A3A1", "#D2C295", "#E8DDBE", "#9A9CA1", "#C9CACD"]
    cols, rows = 22, 6
    gx0, gx1, gtop = x0, pw - 2 * cm, ph - 15.85 * cm
    cw, rh = (gx1 - gx0) / cols, 0.62 * cm
    for r in range(rows):
        t = rng.randint(0, 2)
        while t < cols:
            length = min(rng.randint(2, 6), cols - t)
            c.setFillColor(colors.HexColor(rng.choice(tints)))
            c.setFillAlpha(0.55 if r % 2 else 0.8)
            c.roundRect(gx0 + t * cw + 1, gtop - r * (rh + 0.18 * cm) - rh, length * cw - 2, rh, 2.5,
                        stroke=0, fill=1)
            t += length + rng.randint(0, 2)
    c.setFillAlpha(1)

    # authors, place and date, link
    yb = 5.6 * cm
    c.setFillColor(colors.HexColor("#A8925A"))
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x0, yb + 1.9 * cm, "A U T H O R S")
    # the three names on one line, in three equal columns
    colw = (pw - 2 * cm - x0) / len(AUTHORS)
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 12)
    for k, a in enumerate(AUTHORS):
        c.drawString(x0 + k * colw, yb + 1.0 * cm, a)
    c.setFont("Helvetica", 11)
    c.setFillColor(MUTED)
    c.drawString(x0, yb - 0.1 * cm, "CentraleSupélec, November 2026")

    # bottom line with the repository link
    c.setStrokeColor(colors.HexColor("#D5D5D5"))
    c.setLineWidth(0.6)
    c.line(x0, 2.6 * cm, pw - 2 * cm, 2.6 * cm)
    c.setFillColor(MUTED)
    c.setFont("Helvetica", 9.5)
    label = "Source code and results:  "
    c.drawString(x0, 1.9 * cm, label)
    lx = x0 + c.stringWidth(label, "Helvetica", 9.5)
    link = REPO.replace("https://", "")
    c.setFillColor(CARDINAL)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(lx, 1.9 * cm, link)
    c.linkURL(REPO, (lx, 1.8 * cm, lx + c.stringWidth(link, "Helvetica-Bold", 9.5), 2.3 * cm), relative=0)
    c.restoreState()


doc = SimpleDocTemplate(out, pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm,
                        bottomMargin=2 * cm, title=TITLE, author=", ".join(AUTHORS))
W = A4[0] - 4 * cm
st = []

# ---------- cover page (drawn by draw_cover) ----------
st += [Spacer(1, 1), PageBreak()]

# ---------- summary ----------
st.append(P("Summary", "h1"))
st.append(P("This report presents our work on the CompuOpti staffing problem. The company has a team of "
            "employees, each with some skills and some days off, and a list of projects. Each project needs a "
            "given number of working days in some skills, brings a gain when it is fully completed, and costs a "
            "penalty for every day it ends after its due date. We look for plans that are good on three criteria "
            "at the same time: a high profit, few projects per employee and short projects."))
st.append(P("We model the problem as a mixed-integer linear program and solve it with Gurobi. The three criteria "
            "are in conflict, so instead of a single solution we compute the set of non-dominated plans, the "
            "Pareto front, with the epsilon-constraint method."))
st.append(P("Three changes made the computation practical. The sweep skips the solves whose answer is already "
            "known, a resume option lets a long run restart after an interruption, and a tighter formulation of "
            "the project time windows made the hardest solves up to 28 times faster, with the same optimal "
            "values."))
st.append(Spacer(1, 4))
st.append(table([
    ["Instance", "Size", "Computation", "Best profit", "Pareto points"],
    ["Toy", "3 employees, 5 projects, 5 days", "0.5 s, 12 solves",
     "65 (at most 3 projects per employee, longest project 2 days)", "9"],
    ["Medium", "5 employees, 15 projects, 22 days", "23 min, 151 solves",
     "413 (at most 6 projects per employee, longest project 8 days)", "46"],
    ["Large", "6 employees, 25 projects, 36 days", f"about {ltw:.0f} h (estimated), {lsolves} solves",
     f"{lbest[0]} (at most {lbest[1]} projects per employee, longest project {lbest[2]} days)", f"{len(lfront)}"],
], [1.9 * cm, 3.4 * cm, 3.3 * cm, 5.6 * cm, 2.2 * cm]))

# ---------- 1. problem ----------
st.append(P("1. Problem description", "h1"))
st.append(P("Each instance is a JSON file that gives:"))
st += [
    B("the planning horizon, in working days (5, 22 and 36 for the three given instances);"),
    B("the employees, with their skills (A, B, C, ...) and their days off;"),
    B("the projects, with the number of working days needed in each skill (for example, Job2 needs one day "
      "of A and two days of B), the gain earned when the project is completed, its due date and its penalty "
      "per day of delay."),
]
st.append(P("A plan must respect a few rules. An employee can only work with a skill they have, and never on "
            "a day off. An employee works on at most one project and one skill per day. A project only brings its "
            "gain if all its required days are covered, so a plan never contains partial work, and some projects "
            "may be left out entirely."))
st.append(P("We consider three criteria:"))
st.append(table([
    ["Criterion", "Definition", "Direction"],
    ["f1, profit", "gains of the completed projects minus the delay penalties", "maximise"],
    ["f2, workload", "largest number of different projects an employee works on", "minimise"],
    ["f3, duration", "longest duration (from first to last day) of a completed project", "minimise"],
], [3.2 * cm, 10.6 * cm, 2.6 * cm]))
st.append(P("These criteria are in conflict. The most profitable plans spread employees over many projects and "
            "let projects last longer, so no plan is the best on all three at once. This is why we compute the "
            "Pareto front rather than a single solution.", "note"))

# ---------- 2. model ----------
st.append(P("2. Mathematical model", "h1"))
st.append(P("2.1 Decision variables", "h2"))
st.append(table([
    ["Variable", "Type", "Meaning"],
    ["x<sub>i,j,k,t</sub>", "binary", "1 if employee <i>i</i> works on project <i>j</i> with skill <i>k</i> on day "
     "<i>t</i>. We only create it when <i>i</i> has skill <i>k</i>, project <i>j</i> needs <i>k</i> and <i>t</i> "
     "is not a day off of <i>i</i>, so these two rules hold by construction."],
    ["y<sub>j</sub>", "binary", "1 if project <i>j</i> is completed"],
    ["z<sub>i,j</sub>", "binary", "1 if employee <i>i</i> works on project <i>j</i> at least once"],
    ["b<sub>j,t</sub>, f<sub>j,t</sub>", "binary", "1 if project <i>j</i> starts (b) or finishes (f) on day <i>t</i>"],
    ["a<sub>j,t</sub>", "in [0, 1]", "1 if project <i>j</i> is in progress on day <i>t</i>, between its start "
     "and its end"],
    ["P<sub>max</sub>, D<sub>max</sub>", "continuous", "largest number of projects per employee (f2) and longest "
     "project duration (f3)"],
], [2.6 * cm, 1.8 * cm, 12.0 * cm]))

st.append(P("2.2 Constraints", "h2"))
rules = [
    ("One task per day", "For each employee <i>i</i> and each day <i>t</i>:",
     "Σ<sub>j,k</sub> x<sub>i,j,k,t</sub> ≤ 1"),
    ("Full coverage", "For each project <i>j</i> and each skill <i>k</i> it needs (n<sub>j,k</sub> days):",
     "Σ<sub>i,t</sub> x<sub>i,j,k,t</sub> = n<sub>j,k</sub> · y<sub>j</sub>"),
    ("Start and end", "A completed project has exactly one start day and one end day:",
     "Σ<sub>t</sub> b<sub>j,t</sub> = y<sub>j</sub>, &nbsp;&nbsp; Σ<sub>t</sub> f<sub>j,t</sub> = y<sub>j</sub>"),
    ("Active period", "The variable a counts the starts up to day <i>t</i> minus the ends before day <i>t</i>. "
     "With 0 ≤ a ≤ 1, it equals 1 exactly between the start and the end, and the end cannot come before the "
     "start:",
     "a<sub>j,t</sub> = Σ<sub>u≤t</sub> b<sub>j,u</sub> − Σ<sub>u&lt;t</sub> f<sub>j,u</sub>, "
     "&nbsp;&nbsp; 0 ≤ a<sub>j,t</sub> ≤ 1"),
    ("Work inside the active period", "For each employee, project and day:",
     "Σ<sub>k</sub> x<sub>i,j,k,t</sub> ≤ a<sub>j,t</sub>"),
    ("Projects per employee", "z records the projects each employee takes part in, and P<sub>max</sub> bounds "
     "their number:",
     "Σ<sub>k</sub> x<sub>i,j,k,t</sub> ≤ z<sub>i,j</sub>, &nbsp;&nbsp; P<sub>max</sub> ≥ Σ<sub>j</sub> z<sub>i,j</sub>"),
    ("Project duration", "The duration of a project is its number of active days:",
     "D<sub>max</sub> ≥ Σ<sub>t</sub> a<sub>j,t</sub>"),
]
for name, text, eq in rules:
    st.append(KeepTogether([P(f"<b>{name}.</b> {text}"), M(eq)]))

st.append(P("2.3 Objective functions", "h2"))
st.append(P("The delay of a project is read from its end day: if project <i>j</i> ends on day <i>t</i> after its "
            "due date <i>d<sub>j</sub></i>, it is <i>t − d<sub>j</sub></i> days late. This gives"))
st.append(M("late<sub>j</sub> = Σ<sub>t &gt; d<sub>j</sub></sub> (t − d<sub>j</sub>) · f<sub>j,t</sub>, "
            "&nbsp;&nbsp;&nbsp; f1 = Σ<sub>j</sub> ( g<sub>j</sub> · y<sub>j</sub> − c<sub>j</sub> · "
            "late<sub>j</sub> )"))
st.append(P("The two other criteria are f2 = P<sub>max</sub> and f3 = D<sub>max</sub>, both minimised."))

st.append(P("2.4 Epsilon-constraint method", "h2"))
st.append(P("We turn f2 and f3 into constraints and maximise the profit for every pair of bounds (α, β):"))
st.append(M("maximise &nbsp; f1 − ε (P<sub>max</sub> + D<sub>max</sub>) &nbsp;&nbsp; subject to "
            "&nbsp; P<sub>max</sub> ≤ α, &nbsp; D<sub>max</sub> ≤ β, &nbsp; and the constraints above"))
st.append(P("The small term ε = 0.001 breaks ties: among plans with the same profit, it favours fewer projects "
            "per employee and shorter projects. Each solve gives a candidate point (profit, P, D), and at the end "
            "we keep the points that are not dominated by any other point. These points form the Pareto front."))
st.append(P("<b>Skipping redundant solves.</b> For a fixed α, we start with β equal to the horizon and decrease "
            "it. If the optimal plan for the bound β has a longest project of D days, the same plan stays optimal "
            "for every bound between D and β, since it is still feasible and the feasible set only gets smaller. "
            "We can therefore go directly to β = D − 1. The front is the same as when every pair is solved, with "
            "far fewer solves (12 instead of 25 for the toy instance, 151 instead of 330 for the medium one).",
            "note"))

st.append(P("2.5 Big-M versus time-window formulation", "h2"))
st.append(P("Our first model used integer variables s<sub>j</sub> and e<sub>j</sub> for the start and end days "
            "of each project, linked to the assignments by big-M constraints, with the horizon h as M:"))
st.append(M("e<sub>j</sub> ≥ t · x<sub>i,j,k,t</sub>, &nbsp;&nbsp; s<sub>j</sub> ≤ t + h (1 − x<sub>i,j,k,t</sub>), "
            "&nbsp;&nbsp; D<sub>max</sub> ≥ e<sub>j</sub> − s<sub>j</sub> + 1 − h (1 − y<sub>j</sub>)"))
st.append(P("These constraints are valid, but their linear relaxation is weak. When Gurobi relaxes x to "
            "fractional values, for instance x = 0.1, the term h(1 − x) is close to h and the constraints barely "
            "restrict s and e. The relaxed problem then allows very short and very profitable projects, the upper "
            "bound stays far from the optimum and the branch-and-bound tree becomes very large. Some solves took "
            "more than two hours."))
st.append(P("The current model uses the indicators b, f and a of section 2.2. No large constant appears: the "
            "duration is the number of active days and the delay is a weighted sum of the end-day indicators. The "
            "relaxation is much closer to the integer problem, so optimality is proved much sooner, and the model "
            "has about half as many constraints."))
st.append(table([
    ["Instance", "Big-M model: variables / constraints", "Time-window model: variables / constraints"],
    ["Toy", "127 / 308", "187 / 182"],
    ["Medium", "1,435 / 4,073", "2,380 / 2,248"],
    ["Large", "4,191 / 12,149", "6,816 / 6,973"],
], [2.4 * cm, 7 * cm, 7 * cm]))
st.append(Spacer(1, 8))
st.append(P("We ran both formulations on the same problems. They return the same optimal values:"))
st.append(table([
    ["Test", "Big-M model", "Time-window model", "Result (identical)"],
    ["Large, α = 4, β = 13 (one solve)", "644 s", "227 s (2.8 times faster)", "profit 726, P = 4, D = 13"],
    ["Large, α = 4, β = 9 (one solve)", "7,071 s (1 h 58)", "251 s (28 times faster)", "profit 670, P = 4, D = 9"],
    ["Medium, whole front", "3 h 37 (8 cores, 330 solves)", "23 min (8 cores, 151 solves)", "same 46 points"],
    ["Toy, whole front", "about 5 s", "0.5 s", "same 9 points"],
], [4.6 * cm, 3.8 * cm, 3.9 * cm, 4.1 * cm]))

# ---------- 3. implementation ----------
st.append(P("3. Implementation", "h1"))
st.append(P("The model is written in Python in <b>staffing.py</b> (about 260 lines), with <b>gurobipy</b> for the "
            "solver and <b>matplotlib</b> for the figures. Its main functions are:"))
st.append(table([
    ["Function", "Role"],
    ["load(path)", "Reads a JSON instance and returns the horizon, the skills, the employees with their skills and "
                   "days off, and the projects with their requirements, gains, penalties and due dates."],
    ["build(...)", "Builds the Gurobi model of section 2 and returns it with the x and y variables and the "
                   "expressions of the profit, P<sub>max</sub> and D<sub>max</sub>."],
    ["pareto(path, resume)", "Runs the epsilon-constraint sweep. The model is built once and only the right-hand "
                             "sides of the two bounds change between solves. One progress line is printed per "
                             "solve, and the non-dominated points are kept with the plan of the most profitable one."],
    ["read_log(path)", "Reads a previous progress log so that the pairs (α, β) already solved are not solved "
                       "again (option <b>--resume</b>)."],
    ["solve_point(path, P, D)", "Solves the model for one pair of bounds and returns the corresponding plan "
                                "(option <b>--plan P D</b>)."],
    ["describe(plan)", "Prints, for each project of a plan, whether it is done, its first and last day, its delay "
                       "and the employees working on it."],
    ["plot_front(front)", "Draws the front in three dimensions (pareto.png)."],
    ["plot_schedule(plan)", "Draws a plan as a Gantt chart with one row per employee and one box per working day "
                            "(schedule.png). Horizons longer than 24 days are split into two halves."],
], [3.6 * cm, 12.8 * cm]))

st.append(P("Main loop", "h2"))
st.append(code(
"""for a in range(1, len(J) + 1):           # bound on projects per employee
    b = nH                               # start from the loosest duration bound
    while b >= 1:
        if (a, b) in done:               # pair already solved in a previous run
            pt = done[a, b]
        else:
            cP.RHS, cD.RHS = a, b        # update the two bounds, keep the model
            m.optimize()
            pt = (profit, Pmax, Dmax)
        if pt is None:                   # infeasible, so smaller bounds are too
            break
        b = min(pt[2], b) - 1            # same plan for every bound from D to b"""))

st.append(P("Running the code", "h2"))
st.append(code(
"""python staffing.py toy_instance.json
python staffing.py medium_instance.json
python staffing.py large_instance.json --resume large_run_prev.log   # continue after a stop
python staffing.py gen4.json --plan 3 7      # schedule of one point of the front
python generate_instance.py gen4.json --staff 5 --jobs 12 --horizon 16 --quals 8 --seed 4
python value_of_person.py medium_instance.json --caps 6 8 --out medium_value_of_person.json
python plot_cubes.py                         # 3-D fronts from the saved results"""))
st.append(P("Each solve prints a line such as:"))
st.append(code("[118/900] Pmax<=4 Dmax<=10 status=2 solve=2256.9s elapsed=19963s -> profit=700 P=4 D=10"))
st.append(P("Here the bounds are α = 4 and β = 10, status 2 means that the solution is proved optimal, the solve "
            "took 2,257 seconds, and the best plan earns 700 with at most 4 projects per employee and a longest "
            "project of 10 days. At the end, the script prints the front and saves pareto.png and schedule.png."))
st.append(P("Practical remarks", "h2"))
st += [
    B("<b>Licence.</b> The free licence installed with pip is limited to 2,000 variables and constraints, which "
      "only fits the toy instance. We used an academic licence for Gurobi 13, with gurobipy 13.0.3."),
    B("<b>Interruptions.</b> A Windows update restarted the computer during the large run. With --resume, the "
      "pairs already solved were kept and the run continued from where it stopped."),
    B("<b>Tie-breaking precision.</b> Gurobi stops when the gap to the optimum is below 0.01 %, which can exceed "
      "the ε term. A solve can then return, for example, (808, P = 6, D = 13) instead of (808, 6, 11). The "
      "dominance filter removes such points, so the front is still exact, but a few solves are added and their "
      "number varies between runs (144 and 151 for the medium instance, with the same 46 points)."),
]

# ---------- 4. results ----------
st.append(P("4. Results", "h1"))
st.append(P("4.1 Toy instance (3 employees, 5 projects, 5 days)", "h2"))
st.append(KeepTogether([
    P("The front is computed in half a second with 12 solves. It has nine points:"),
    table([["Profit", "Projects per employee", "Longest project (days)"]] + [[p, a, d] for p, a, d in toy_front],
          [3 * cm, 5 * cm, 5 * cm])]))
st.append(Spacer(1, 8))
st.append(P("The most profitable plan (profit 65) completes Job1, Job3, Job4 and Job5 on time and leaves out Job2. "
            "Olivia works every day, on three projects, no project lasts more than two days, and the days off of "
            "Liam (day 1) and Emma (day 2) are respected."))
st.append(figure(os.path.join(proj, "toy_schedule.png"), 10 * cm,
                 "Figure 1. Toy instance, most profitable plan. Each box is one day of work, labelled with the "
                 "project and the skill."))

st.append(P("4.2 Medium instance (5 employees, 15 projects, 22 days)", "h2"))
st.append(P(f"The front has {len(med_front)} points. In Figure 2, each line corresponds to one bound on the number "
            "of projects per employee. Moving to the right (longer projects allowed) or to a darker line (more "
            "projects per employee) increases the best profit, with clearly decreasing returns."))
st.append(figure(os.path.join(proj, "medium_front.png"), W,
                 "Figure 2. Medium instance: best profit for each bound on the project duration, one line per bound "
                 "on the number of projects per employee."))
top = [p for p in med_front if p[0] > 0][:12]
st.append(KeepTogether([
    P("Most profitable points of the front:"),
    table([["Profit", "Projects per employee", "Longest project (days)"]] + [[p, a, d] for p, a, d in top],
          [3 * cm, 5 * cm, 5 * cm])]))
st.append(Spacer(1, 6))
st.append(P("The maximum profit is 413. It is reached with 6 projects per employee and 8-day projects, or with 5 "
            "projects and 10-day projects. Accepting about 2 % less (406 or 405) allows projects of 5 days, or at "
            "most 4 projects per employee. Below 4 projects per employee or 5-day projects, the profit falls "
            "quickly. The most profitable plan completes 11 of the 15 projects, and three of them finish one or two "
            "days late."))
st.append(figure(os.path.join(proj, "medium_schedule.png"), W,
                 "Figure 3. Medium instance, most profitable plan (profit 413)."))

st.append(P("4.3 Large instance (6 employees, 25 projects, 36 days)", "h2"))
st.append(P(f"The sweep covered the 25 bounds on the number of projects per employee with {lsolves} solves. The run "
            f"was interrupted twice and resumed from its log. Its first {LARGE_BIGM_SOLVES} solves were still made "
            f"with the big-M model: the log adds up to {lhours:.0f} h of solver time, of which {lbigm:.1f} h with "
            f"big-M. We solved 47 of these bounds again with the time-window model and measured a speedup of "
            f"{LARGE_SPEEDUP:.1f}, so we estimate the whole sweep with the final model at about {ltw:.0f} h. The "
            f"front has {len(lfront)} points and the best profit is {lbest[0]}, out of 1,020 if all 25 projects "
            f"were completed."))
st.append(figure(os.path.join(proj, "large_front.png"), 0.9 * W,
                 "Figure 4. Large instance: best profit for each bound on the project duration, one line per bound "
                 "on the number of projects per employee."))
st.append(KeepTogether([
    P("Most profitable points of the front:"),
    table([["Profit", "Projects per employee", "Longest project (days)"]] + [[p, a, d] for p, a, d in lfront[:10]],
          [3 * cm, 5 * cm, 5 * cm])]))
st.append(Spacer(1, 6))
st.append(P("The maximum profit of 817 can be reached in three ways: 9 projects per employee with 8-day projects, "
            "8 projects with 10-day projects, or 7 projects with 11-day projects. Going down to 6 projects per "
            "employee costs only about 1 % (808, with 11-day projects), or about 3 % (794) if projects must also "
            "stay within 9 days, and about 4 % (782) gives 5 projects per employee. Bounds above 7 never increase "
            "the profit: bounds 8 and 9 keep 817 with a longest project of 10 and then 8 days, and bounds 10 and 11 "
            "only add points with very short projects (at most 5 days, for example 764 with 10 projects per "
            "employee). Above 11, the front does not change.", "note"))
st.append(P("The most profitable plan (817, at most 9 projects per employee, longest project 8 days) completes "
            "17 of the 25 projects."))
st.append(figure(os.path.join(proj, "large_schedule.png"), W,
                 "Figure 5. Large instance, most profitable plan (profit 817), days 1 to 18 (top) and 19 to 36 "
                 "(bottom)."))
st.append(P("<b>Computing time.</b> With the time-window model, most of the time goes to bounds 5 to 8, with 3 to 7 "
            "hours each. The longest single solve (8 projects per employee, 4-day projects) took 3 h 15. Bounds 1 "
            "to 4 take less than 1.5 h each, bound 9 less than one hour, and each bound from 10 on about 25 "
            "minutes, since they no longer restrict the best plans."))

st.append(P("4.4 Generated instances", "h2"))
st.append(P("The project asks for an instance generator to study performance. <b>generate_instance.py</b> writes a "
            "JSON file in the same format as the given instances. Each employee receives 1 to 5 random skills, "
            "every skill being held by at least one employee, and about 8 % of the days off. Each project requires "
            "1 to 4 skills, and the numbers of days are scaled so that the total demand is about 1.3 times the "
            "available capacity, as in the given instances, so that not all projects can be completed. Gains are "
            "about 3.75 per person-day (plus or minus 30 %), due dates are drawn between one third of the horizon "
            "and its end, and the penalty is 3 per day of delay. The same arguments and seed always produce the "
            "same file."))
st.append(table([
    ["Instance", "Employees / projects / days / skills", "Solves", "Time", "Front", "Best (profit, P, D)"],
    ["toy (given)", "3 / 5 / 5 / 3", "12", "0.5 s", "9", "65, 3, 2"],
    ["gen1", "3 / 6 / 8 / 4", "21", "1.7 s", "9", "76, 4, 3"],
    ["gen2", "4 / 8 / 10 / 5", "45", "8.4 s", "17", "103, 3, 5"],
    ["gen3", "4 / 10 / 14 / 6", "73", "90 s", "31", "180, 5, 5"],
    ["gen4", "5 / 12 / 16 / 8", "101", "56 s", "28", "222, 4, 8"],
    ["medium (given)", "5 / 15 / 22 / 10", "151", "23 min", "46", "413, 6, 8"],
    ["large (given)", "6 / 25 / 36 / 10", f"{lsolves}", f"about {ltw:.0f} h (*)", f"{len(lfront)}", "817, 9, 8"],
], [2.8 * cm, 4.4 * cm, 1.6 * cm, 2.2 * cm, 1.4 * cm, 3.6 * cm]))
st.append(Spacer(1, 4))
st.append(P(f"Times are for the whole sweep on an idle machine with 8 cores. (*) Large instance: estimated time with "
            f"the time-window model, the first {LARGE_BIGM_SOLVES} solves of the run having been made with big-M "
            f"and scaled by the measured speedup of {LARGE_SPEEDUP:.1f} (see section 4.3).", "cap"))
st.append(P("The number of solves grows roughly with the number of projects times the number of days, and the "
            "time per solve grows faster. Size alone does not determine the difficulty: gen4 is larger than gen3 "
            "but was solved faster."))
st.append(P("Any point of the front can be turned into a schedule with <b>--plan P D</b>. Figure 6 shows the gen4 "
            "point with profit 216, at most 3 projects per employee and 7-day projects. The best plan earns 222 "
            "with 4 projects per employee and 8-day projects."))
st.append(figure(os.path.join(proj, "generated", "gen4_schedule_P3_D7.png"), W,
                 "Figure 6. gen4, schedule of the front point (216, 3, 7), obtained with "
                 "python staffing.py gen4.json --plan 3 7."))

st.append(P("4.5 The three fronts in 3-D", "h2"))
st.append(P("Figure 7 shows each front as a set of points in the space of the three criteria. A vertical line links "
            "each point to its position (P, D) on the floor, the colour goes from light (low profit) to dark red "
            "(high profit), and the circled points reach the maximum profit. On all three instances the profit "
            "rises quickly and then levels off: the last few percent require much looser bounds on P or D."))
st.append(figure(os.path.join(proj, "pareto_cubes.png"), W,
                 "Figure 7. Pareto fronts of the toy, medium and large instances in the space of the three criteria "
                 "(plot_cubes.py)."))

st.append(P("4.6 Value of an additional employee (medium instance)", "h2"))
st.append(P(f"We also used the model to see which skill a new hire should have. Dual values are not meaningful for "
            f"a MILP, so we solve the problem again: <b>value_of_person.py</b> adds one employee, available on all "
            f"{vh} days with a single skill, and computes the new optimal profit. We repeat this for each of the "
            f"{len(vrows) - 1} skills, and once more with an employee who has all the skills, which gives an upper "
            f"bound."))
st.append(table([["Skill of the new employee", "Best profit", "Gain", "Completed projects"]] +
                [[r["new_person"], r["profit_no_limit"], f"+{r['gain_no_limit']}", r["projects_no_limit"]]
                 for r in vrows] +
                [["(no new employee)", vbase, "0", vop["baseline"]["projects_no_limit"]]],
                [4.4 * cm, 3.2 * cm, 2.4 * cm, 3.8 * cm]))
st.append(Spacer(1, 6))
st.append(P(f"A specialist in {vtop['new_person']} gives the largest gain, +{vtop['gain_no_limit']} "
            f"({100 * vtop['gain_no_limit'] / vbase:.1f} %), with {vmore} more projects completed. This is "
            f"{100 * vtop['gain_no_limit'] / vall['gain_no_limit']:.0f} % of the gain of an employee with all ten "
            f"skills (+{vall['gain_no_limit']}). Specialists in B or H only add 4, since these skills are not a "
            f"bottleneck. The ranking does not simply follow the scarcity of the skills: F is held by a single "
            f"employee but comes third, because the value of a skill depends on how the skills compete for the "
            f"same employees on the same days."
            + (f" With the bounds of the best plan (at most {vop['caps'][0]} projects per employee and "
               f"{vop['caps'][1]}-day projects), every skill gives exactly the same value, so the ranking is "
               f"unchanged." if same_caps else "")))
st.append(P(f"These gains do not include any salary. The {vtop['new_person']} specialist adds "
            f"{vtop['gain_no_limit']} over the {vh} days, that is {vtop['gain_no_limit'] / vh:.2f} per day, and "
            f"works {vtop['days_worked']} of the {vh} days in the plan found "
            f"({vtop['gain_no_limit'] / vtop['days_worked']:.2f} per day worked). The hire is profitable only if a "
            f"person-day costs less than this. For comparison, the projects of this instance bring {vavg:.2f} per "
            f"person-day on average."))

# ---------- 5. conclusion ----------
st.append(P("5. Conclusion", "h1"))
st += [
    B("We obtained the exact Pareto fronts of the three given instances (9, 46 and 92 points) and of four "
      "generated instances. Where both formulations were run, they give the same results."),
    B("The formulation mattered more than the hardware: replacing the big-M constraints by the time-window "
      "formulation made difficult solves 3 to 28 times faster. A GPU would not help, as Gurobi's MIP solver runs "
      "on the CPU."),
    B("On the large instance, bounds above 7 projects per employee never increase the profit but still add points "
      "to the front (shorter projects at the same profit, and a few points with very short projects), so stopping "
      "the sweep earlier would lose points. For larger instances, a time limit per solve, with the resulting "
      "points marked as approximate, or a stronger formulation, such as lower bounds on project durations, would "
      "reduce the computing time."),
    B("For a decision maker, the front shows good compromises close to the maximum. On the medium instance, 2 % "
      "less profit gives much shorter projects or a lighter workload. On the large instance, about 1 % less (808) "
      "is enough to keep every employee at 6 projects or fewer, or about 3 % (794) if projects must also stay "
      "within 9 days."),
    B(f"The model can also answer what-if questions. On the medium instance, an additional "
      f"{vtop['new_person']} specialist increases the profit by {100 * vtop['gain_no_limit'] / vbase:.1f} % "
      f"({vmore} more projects), which is worth it if a person-day costs less than "
      f"{vtop['gain_no_limit'] / vh:.1f}."),
]

doc.build(st, onFirstPage=draw_cover, canvasmaker=NumberedCanvas)
print("written", out)
