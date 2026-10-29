"""Regenerate data/students.json with sample courses, students and marks.

Run from the project root:  python tools/seed_sample_data.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sms.config import DATA_FILE
from sms.services.course_manager import parse_structure
from sms.services.student_manager import StudentManager
from sms.storage.json_storage import JSONStorage

COURSES = {
    "COMP9001": ("Programming Fundamentals", "Lab 10/10, A1 7.5/10, A2 7.5/10, Project 25/25, Final Exam 50/50"),
    "COMP9123": ("Data Structures", "Q1 5/10, Q2 5/10, A1 15/15, A2 15/15, Midterm 20/40, Final Exam 40/40"),
    "MATH1001": ("Calculus I", "Quiz 1 10/20, Quiz 2 10/20, Assignment 20/20, Final Exam 60/60"),
}

# student -> (age, class, email, {course: [raw marks in component order, None = not marked yet]})
# Marks are out of each component's "out of" value (the number after "/" in the structure).
STUDENTS = [
    ("Ava Thompson", 19, "CS-1", "ava@example.com",
     {"COMP9001": [9, 7, 6.5, 22, 44], "COMP9123": [8, 9, 13, 12, 32, 33]}),
    ("Liam Nguyen", 20, "CS-1", "liam@example.com",
     {"COMP9001": [7, 5, 6, 18, 36], "MATH1001": [14, 12, 15, 40]}),
    ("Sofia Patel", 19, "CS-2", "sofia@example.com",
     {"COMP9001": [5, 4, 3, 12, 20], "COMP9123": [5, 4, 9, 8, None, None]}),
    ("Noah Brown", 21, "CS-2", "noah@example.com",
     {"COMP9123": [10, 9, 14, 14, 38, 38], "MATH1001": [19, 18, 18, 55]}),
    ("Mia Wilson", 20, "SE-1", "mia@example.com",
     {"COMP9001": [8, 6, 7, 20, None], "MATH1001": [16, 15, None, None]}),
    ("Ethan Clarke", 22, "SE-1", "", {}),
]

mgr = StudentManager(JSONStorage(DATA_FILE))
for code, (title, structure) in COURSES.items():
    mgr.courses.add_course(code, title, parse_structure(structure))
for name, age, cls, email, enrolments in STUDENTS:
    student = mgr.add_student(name, age, cls, email)
    for code, marks in enrolments.items():
        mgr.enroll(student.student_id, code)
        comps = mgr.courses.get_course(code).components
        mgr.set_scores(student.student_id, code,
                       {c.component_id: m for c, m in zip(comps, marks) if m is not None})
mgr.save()
print(f"Wrote {len(mgr.courses)} courses and {len(mgr)} students to {DATA_FILE}")
