"""Dashboard: headline numbers, charts and leaderboards."""
import tkinter as tk

from sms.services.statistics import StatisticsService
from sms.ui import theme as T
from sms.ui.pages.base import Page
from sms.ui.widgets import BarChart, Card, StatCard, fill_tree, make_tree


class DashboardPage(Page):
    """Overview page: headline numbers, two bar charts and two tables."""

    def __init__(self, parent, app):
        """Build the static layout; the numbers are filled in later by refresh().

        Args:
            parent: The container widget the page is placed in.
            app: The main application window.
        """
        super().__init__(parent, app)
        self.header("Dashboard", "An overview of your students, courses and results")

        # Grid layout: row 0 = five stat cards, row 1 = two charts, row 2 = two tables.
        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        # Five equal-width columns (uniform) so every stat card is the same size.
        for c in range(5):
            body.columnconfigure(c, weight=1, uniform="stat")
        body.rowconfigure(2, weight=1)

        # Headline stat cards, stored by key so refresh() can update them.
        self.cards = {}
        for i, (key, title, color) in enumerate([
                ("students", "Students", T.PRIMARY), ("courses", "Courses", T.PURPLE),
                ("enrol", "Enrollments", T.INFO), ("avg", "Average result", T.SUCCESS),
                ("pass", "Pass rate", T.SUCCESS)]):
            card = StatCard(body, title, color)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == 4 else 6))
            self.cards[key] = card

        # Row 1, left: bar chart of how many students got each grade (spans 2 columns).
        grade_card = Card(body, "Grade distribution (students)")
        grade_card.grid(row=1, column=0, columnspan=2, sticky="nsew", pady=12, padx=(0, 6))
        self.grade_chart = BarChart(grade_card.body)
        self.grade_chart.pack(fill="x")

        # Row 1, right: bar chart of the average result per course (spans 3 columns).
        course_card = Card(body, "Average result by course")
        course_card.grid(row=1, column=2, columnspan=3, sticky="nsew", pady=12, padx=(6, 0))
        self.course_chart = BarChart(course_card.body, color=T.PRIMARY)
        self.course_chart.pack(fill="x")

        # Row 2, left: table of the top 5 students.
        top_card = Card(body, "Top students")
        top_card.grid(row=2, column=0, columnspan=2, sticky="nsew", padx=(0, 6))
        frame, self.top_tree = make_tree(top_card.body, [
            ("rank", "#", 34), ("name", "Student", 130), ("standing", "Result", 70), ("grade", "Grade", 50)], height=5)
        frame.pack(fill="both", expand=True)

        # Row 2, right: per-course overview table.
        overview = Card(body, "Course overview")
        overview.grid(row=2, column=2, columnspan=3, sticky="nsew", padx=(6, 0))
        frame, self.course_tree = make_tree(overview.body, [
            ("code", "Code", 80), ("title", "Title", 150), ("enrolled", "Enrolled", 80, "center"),
            ("marked", "Marked", 72, "center"), ("avg", "Average", 78, "center"),
            ("pass", "Pass rate", 84, "center")], height=5)
        frame.pack(fill="both", expand=True)

    def refresh(self) -> None:
        """Recompute all statistics and redraw the cards, charts and tables."""
        # Fresh statistics object built from the current data.
        stats = StatisticsService(self.manager.list_students(), self.courses.list_courses())
        # Headline cards: each gets a main value and a caption underneath.
        self.cards["students"].set(str(stats.total_students()), f"{len(stats.graded)} with marks")
        self.cards["courses"].set(str(stats.total_courses()),
                                  f"{sum(1 for c in self.courses.list_courses() if c.is_ready)} ready for students")
        self.cards["enrol"].set(str(stats.total_enrollments()), "student-course pairs")
        self.cards["avg"].set(f"{stats.average_percentage():.2f}%" if stats.graded else "-",
                              f"{stats.topper().name} leads" if stats.topper() else "no marks yet")
        self.cards["pass"].set(f"{stats.pass_rate():.0f}%" if stats.graded else "-",
                               f"{stats.pass_count()} pass / {stats.fail_count()} fail")

        # Grade chart: one bar per grade, coloured with that grade's theme colour.
        dist = stats.grade_distribution()
        self.grade_chart.set_data(list(dist.items()), fmt="{}",
                                  colors=[T.GRADE_COLORS[g] for g in dist])

        # Course chart: only courses with marks; each bar is coloured by the grade band of its average.
        cstats = [c for c in stats.course_stats() if c.marked]
        self.course_chart.set_data([(c.code, c.average) for c in cstats], max_value=100, fmt="{:.2f}%",
                                   colors=[T.GRADE_COLORS[_band(c.average)] for c in cstats])

        # Top-students table: rank, name, result and grade.
        fill_tree(self.top_tree, [
            (s.student_id, (i, s.name, f"{s.percentage:.2f}%", s.grade), ())
            for i, s in enumerate(stats.top_students(5), 1)])
        # Course overview table: one row per course.
        fill_tree(self.course_tree, [
            (c.code, (c.code, c.title or "-", c.enrolled, c.marked,
                      f"{c.average:.2f}%" if c.marked else "-", f"{c.pass_rate:.0f}%" if c.marked else "-"), ())
            for c in stats.course_stats()])


def _band(percentage: float) -> str:
    """Return the letter grade for a percentage (used to colour the course chart)."""
    from sms.models.grading import letter_grade
    return letter_grade(percentage)