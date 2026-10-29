"""Statistics used by the dashboard.

``StatisticsService`` computes totals, averages, pass rates, rankings and the
grade distribution over a list of students and courses. ``CourseStat`` holds
the per-course figures.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional

from sms.config import GRADE_BANDS, LOWEST_GRADE
from sms.models.course import Course
from sms.models.student import Student


@dataclass
class CourseStat:
    """Summary figures for a single course."""
    code: str          # course code, e.g. "CS101"
    title: str         # course title
    enrolled: int      # students enrolled in the course
    marked: int        # enrolments that have at least one mark
    average: float     # mean standing (%) of the marked enrolments
    pass_rate: float   # percentage of marked enrolments that passed


class StatisticsService:
    """Aggregate numbers over students and courses."""

    def __init__(self, students: List[Student], courses: List[Course]):
        """Store the data and pre-compute which students have marks.

        Args:
            students: All students to include.
            courses: All courses to include.
        """
        self.students = students
        self.courses = courses
        # Students without any marks are left out of averages, rankings and pass rates.
        self.graded = [s for s in students if s.has_marks]

    def total_students(self) -> int:
        """Return the number of students."""
        return len(self.students)

    def total_courses(self) -> int:
        """Return the number of courses."""
        return len(self.courses)

    def total_enrollments(self) -> int:
        """Return the total number of course enrolments across all students."""
        return sum(len(s.enrollments) for s in self.students)

    def average_percentage(self) -> float:
        """Return the mean overall percentage of graded students (0.0 if none), to 2 decimals."""
        if not self.graded:
            return 0.0
        return round(sum(s.percentage for s in self.graded) / len(self.graded), 2)

    def topper(self) -> Optional[Student]:
        """Return the graded student with the highest percentage, or None if nobody is graded."""
        return max(self.graded, key=lambda s: s.percentage, default=None)

    def lowest(self) -> Optional[Student]:
        """Return the graded student with the lowest percentage, or None if nobody is graded."""
        return min(self.graded, key=lambda s: s.percentage, default=None)

    def pass_count(self) -> int:
        """Return how many graded students have passed."""
        return sum(1 for s in self.graded if s.has_passed)

    def fail_count(self) -> int:
        """Return how many graded students have failed (graded but not passed)."""
        return len(self.graded) - self.pass_count()

    def pass_rate(self) -> float:
        """Return the percentage of graded students who passed (0.0 if none), to 2 decimals."""
        return round(self.pass_count() / len(self.graded) * 100, 2) if self.graded else 0.0

    def grade_distribution(self) -> Dict[str, int]:
        """Return a mapping of grade -> number of students, ordered best to worst.

        Grades nobody received are left out.
        """
        counts = Counter(s.grade for s in self.graded)
        order = [g for _, g in GRADE_BANDS] + [LOWEST_GRADE]  # best to worst
        return {g: counts[g] for g in order if counts[g]}

    def top_students(self, n: int = 5) -> List[Student]:
        """Return the ``n`` graded students with the highest percentages, best first."""
        return sorted(self.graded, key=lambda s: s.percentage, reverse=True)[:n]

    def course_stats(self) -> List[CourseStat]:
        """Return one ``CourseStat`` per course (enrolled, marked, average, pass rate)."""
        result = []
        for course in self.courses:
            # Collect this course's enrolment from every student who takes it.
            enrollments = [e for s in self.students for e in s.enrollments if e.course_code == course.code]
            # Only enrolments with marks count towards the average and pass rate.
            marked = [e for e in enrollments if e.has_marks]
            avg = round(sum(e.standing for e in marked) / len(marked), 2) if marked else 0.0
            rate = round(sum(1 for e in marked if e.has_passed) / len(marked) * 100, 1) if marked else 0.0
            result.append(CourseStat(course.code, course.title, len(enrollments), len(marked), avg, rate))
        return result