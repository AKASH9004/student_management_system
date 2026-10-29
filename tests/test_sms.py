import tempfile
import unittest
from pathlib import Path

from sms.exceptions import (CourseNotFoundError, DuplicateComponentError, DuplicateCourseError,
                            DuplicateEnrollmentError, StudentNotFoundError, ValidationError)
from sms.services.course_manager import parse_structure
from sms.services.progress_report import render_progress_report
from sms.services.statistics import StatisticsService
from sms.services.student_manager import StudentManager
from sms.storage.json_storage import JSONStorage


class BaseCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "data.json"
        self.mgr = StudentManager(JSONStorage(self.path))
        self.courses = self.mgr.courses

    def tearDown(self):
        self.tmp.cleanup()

    def make_course(self, code="COMP9001"):
        return self.courses.add_course(
            code, "Programming", parse_structure("Lab 10, A1 7.5, A2 7.5, Project 25, Exam 50"))


class CourseTests(BaseCase):
    def test_parse_structure(self):
        self.assertEqual(parse_structure("Lab 10, Quiz 1 5/20, A1 7.5%"),
                         [("Lab", 10.0, 100.0), ("Quiz 1", 5.0, 20.0), ("A1", 7.5, 100.0)])
        with self.assertRaises(ValidationError):
            parse_structure("Lab")

    def test_structure_and_readiness(self):
        c = self.courses.add_course("comp9123", "Data Structures")
        self.assertEqual(c.code, "COMP9123")
        self.assertFalse(c.is_ready)
        c.add_component("Q1", 10)
        c.add_component("Exam", 60)
        self.assertEqual(c.remaining_weight, 30)
        with self.assertRaises(ValidationError):
            c.add_component("Big", 40)          # would exceed 100%
        with self.assertRaises(DuplicateComponentError):
            c.add_component("q1", 5)
        c.add_component("A1", 30)
        self.assertTrue(c.is_ready)

    def test_two_courses_different_structure(self):
        a = self.make_course("COMP9001")
        b = self.courses.add_course("COMP9123", "DS", parse_structure("Q1 10, Q2 10, A1 30, Exam 50"))
        self.assertNotEqual([c.name for c in a.components], [c.name for c in b.components])
        with self.assertRaises(DuplicateCourseError):
            self.courses.add_course("COMP9001")
        with self.assertRaises(CourseNotFoundError):
            self.courses.get_course("NOPE")

    def test_atomic_creation(self):
        with self.assertRaises(ValidationError):
            self.courses.add_course("BAD1", "", parse_structure("A 60, B 60"))
        self.assertEqual(len(self.courses), 0)

    def test_edit_component(self):
        c = self.make_course()
        lab = c.components[0]
        self.courses.update_component("COMP9001", lab.component_id, "Labs", 10, 20)
        self.assertEqual(c.get_component(lab.component_id).max_marks, 20)
        with self.assertRaises(ValidationError):
            self.courses.update_component("COMP9001", lab.component_id, "Labs", 30)


class StudentTests(BaseCase):
    def test_student_crud(self):
        s = self.mgr.add_student("Ava", 15, "10A")
        self.assertEqual(s.student_id, "S001")
        self.mgr.update_student("s001", name="Ava Lee")
        self.assertEqual(self.mgr.get_student("S001").name, "Ava Lee")
        self.mgr.delete_student("S001")
        with self.assertRaises(StudentNotFoundError):
            self.mgr.get_student("S001")

    def test_enroll_requires_complete_structure(self):
        s = self.mgr.add_student("Ben", 16)
        self.courses.add_course("HALF1", "", parse_structure("A 50"))
        with self.assertRaises(ValidationError):
            self.mgr.enroll(s.student_id, "HALF1")
        self.make_course()
        self.mgr.enroll(s.student_id, "comp9001")
        with self.assertRaises(DuplicateEnrollmentError):
            self.mgr.enroll(s.student_id, "COMP9001")

    def test_marks_calculation(self):
        s = self.mgr.add_student("Cy", 17)
        course = self.courses.add_course("T100", "", parse_structure("Lab 20/20, Exam 80"))
        self.mgr.enroll(s.student_id, "T100")
        lab, exam = course.components
        e = self.mgr.set_scores(s.student_id, "T100", {lab.component_id: 15})
        self.assertEqual(e.earned_points, 15.0)      # 15/20 * 20%
        self.assertEqual(e.progress, 20.0)
        self.assertEqual(e.standing, 75.0)           # 15 of the 20 assessed points
        self.assertFalse(e.is_complete)
        e = self.mgr.set_scores(s.student_id, "T100", {exam.component_id: 40})
        self.assertEqual(e.earned_points, 47.0)      # 15 + 40/100*80 = 15 + 32
        self.assertTrue(e.is_complete)
        self.assertEqual(e.grade, "E")
        with self.assertRaises(ValidationError):
            self.mgr.set_scores(s.student_id, "T100", {lab.component_id: 5, exam.component_id: 101})
        self.assertEqual(e.score(lab.component_id), 15)   # all-or-nothing: unchanged
        self.mgr.set_scores(s.student_id, "T100", {lab.component_id: None})
        self.assertIsNone(e.score(lab.component_id))

    def test_component_removal_discards_marks(self):
        course = self.make_course()
        s = self.mgr.add_student("Eli", 18)
        self.mgr.enroll(s.student_id, course.code)
        removed = course.components[-1]
        self.mgr.set_scores(s.student_id, course.code, {removed.component_id: 50})

        self.courses.remove_component(course.code, removed.component_id)
        self.assertFalse(course.has_component(removed.component_id))
        self.assertIsNone(self.mgr.get_student(s.student_id).get_enrollment(course.code).score(removed.component_id))

    def test_json_round_trip_and_cascade(self):
        self.make_course()
        s = self.mgr.add_student("Dee", 17, email="dee@example.com")
        self.mgr.enroll(s.student_id, "COMP9001")
        comp = self.courses.get_course("COMP9001").components[-1]
        self.mgr.set_scores(s.student_id, "COMP9001", {comp.component_id: 88})
        self.mgr.save()

        other = StudentManager(JSONStorage(self.path))
        self.assertEqual(other.load(), 1)
        e = other.get_student("S001").get_enrollment("COMP9001")
        self.assertEqual(e.score(comp.component_id), 88)
        self.assertEqual(len(other.courses), 1)

        self.assertEqual(other.delete_course("COMP9001"), 1)
        self.assertEqual(other.get_student("S001").enrollments, [])


class StatisticsTests(BaseCase):
    def test_statistics(self):
        course = self.courses.add_course("T100", "Test", parse_structure("Exam 100"))
        exam = course.components[0].component_id
        for name, mark in [("A", 90), ("B", 30), ("C", 60)]:
            s = self.mgr.add_student(name, 15)
            self.mgr.enroll(s.student_id, "T100")
            self.mgr.set_scores(s.student_id, "T100", {exam: mark})
        self.mgr.add_student("D", 15)  # no marks -> ignored in averages
        stats = StatisticsService(self.mgr.list_students(), self.courses.list_courses())
        self.assertEqual(stats.total_students(), 4)
        self.assertEqual(stats.average_percentage(), 60.0)
        self.assertEqual(stats.pass_count(), 2)
        self.assertEqual(stats.topper().name, "A")
        cs = stats.course_stats()[0]
        self.assertEqual((cs.enrolled, cs.marked, cs.average), (3, 3, 60.0))


class ProgressReportTests(BaseCase):
    def test_report_includes_overall_course_and_assessment_results(self):
        course = self.courses.add_course(
            "T100", "Programming & Design", parse_structure("Quiz 20/20, Final Exam 80"))
        student = self.mgr.add_student("Ava <Lee>", 16)
        self.mgr.enroll(student.student_id, course.code)
        quiz, exam = course.components
        self.mgr.set_scores(student.student_id, course.code, {quiz.component_id: 18})

        report = render_progress_report(student)

        self.assertIn("Ava &lt;Lee&gt;", report)
        self.assertIn("Overall result", report)
        self.assertIn("Assessment completion", report)
        self.assertIn("Programming &amp; Design", report)
        self.assertIn("18</td>", report)
        self.assertIn("Not marked", report)
        self.assertIn("20% assessed", report)
        self.assertIn("Quiz", report)
        self.assertIn("Final Exam", report)
        self.assertIn("Grade A+", report)

    def test_report_explains_empty_student_progress(self):
        student = self.mgr.add_student("No Marks", 16)

        report = render_progress_report(student)

        self.assertIn("No marks yet", report)
        self.assertIn("0/0 | 0%", report)
        self.assertIn("No course enrolments yet", report)


if __name__ == "__main__":
    unittest.main()
