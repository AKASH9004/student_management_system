"""Student model: profile details plus course enrollments."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Mapping, Optional

from sms.config import COURSE_TOTAL_WEIGHT
from sms.exceptions import (DuplicateEnrollmentError, EnrollmentNotFoundError, ValidationError)
from sms.models.course import Course
from sms.models.enrollment import Enrollment
from sms.models.grading import is_pass, letter_grade

_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class Student:
    """A student's profile plus the courses they are enrolled in.
    Marks are stored in the Enrollment objects. The overall result is the average
    over the courses that have marks.
    """
    def __init__(self, student_id: str, name: str, age: int, class_name: str = "", email: str = ""):
        """Create a student. Raises ValidationError if the name, age or email is not valid."""
        self.student_id = student_id
        self.update_details(name=name, age=age, class_name=class_name, email=email)
        self._enrollments: List[Enrollment] = []

    # ---- profile ---------------------------------------------------------
    def update_details(self, name: Optional[str] = None, age: Optional[int] = None,
                       class_name: Optional[str] = None, email: Optional[str] = None) -> None:
        """Validate and apply any provided profile fields."""
        if name is not None:
            name = name.strip()
            if not name:
                raise ValidationError("Student name cannot be empty.")
        if age is not None and not 3 <= int(age) <= 100:
            raise ValidationError("Age must be between 3 and 100.")
        if email is not None:
            email = email.strip()
            if email and not _EMAIL_RE.match(email):
                raise ValidationError("Email address is not valid.")

        if name is not None:
            self.name = name
        if age is not None:
            self.age = int(age)
        if class_name is not None:
            self.class_name = class_name.strip()
        if email is not None:
            self.email = email

    # ---- enrollments -----------------------------------------------------
    @property
    def enrollments(self) -> List[Enrollment]:
        """All of the student's enrollments, sorted by course code."""
        return sorted(self._enrollments, key=lambda e: e.course_code)

    def is_enrolled(self, course_code: str) -> bool:
        """True if the student is enrolled in the course with this code."""
        return any(e.course_code == course_code for e in self._enrollments)

    def enroll(self, course: Course) -> Enrollment:
        """Enroll the student in a course and return the new Enrollment.
        Raises ValidationError if the course's grade structure does not total 100%,
        and DuplicateEnrollmentError if the student is already enrolled.
        """
        if not course.is_ready:
            raise ValidationError(
                f"{course.code}'s grade structure must add up to {COURSE_TOTAL_WEIGHT:g}% before students "
                f"can be enrolled (currently {course.total_weight:g}%).")
        if self.is_enrolled(course.code):
            raise DuplicateEnrollmentError(f"{self.name} is already enrolled in {course.code}.")
        enrollment = Enrollment(course)
        self._enrollments.append(enrollment)
        return enrollment

    def get_enrollment(self, course_code: str) -> Enrollment:
        """Return the enrollment for a course code, or raise EnrollmentNotFoundError."""
        for enrollment in self._enrollments:
            if enrollment.course_code == course_code:
                return enrollment
        raise EnrollmentNotFoundError(f"{self.name} is not enrolled in {course_code}.")

    def drop(self, course_code: str) -> None:
        self._enrollments.remove(self.get_enrollment(course_code))

    # ---- overall result --------------------------------------------------
    @property
    def has_marks(self) -> bool:
        """True if at least one enrollment has a mark."""
        return any(e.has_marks for e in self._enrollments)

    @property
    def percentage(self) -> float:
        """Average standing over the courses that have marks."""
        marked = [e.standing for e in self._enrollments if e.has_marks]
        return round(sum(marked) / len(marked), 2) if marked else 0.0

    @property
    def grade(self) -> str:
        """Letter grade for the overall result, or 'N/A' if no marks exist yet."""
        return letter_grade(self.percentage) if self.has_marks else "N/A"

    @property
    def has_passed(self) -> bool:
        return self.has_marks and is_pass(self.percentage)

    # ---- serialisation ---------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {"student_id": self.student_id, "name": self.name, "age": self.age,
                "class_name": self.class_name, "email": self.email,
                "enrollments": [e.to_dict() for e in self.enrollments]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any], courses: Mapping[str, Course]) -> "Student":
        """Build a Student from a dictionary made by to_dict().
        `courses` maps course code to Course; enrollments in unknown or duplicate courses are skipped.
        """
        student = cls(data["student_id"], data["name"], data["age"],
                      data.get("class_name", ""), data.get("email", ""))
        for item in data.get("enrollments", []):
            course = courses.get(item["course_code"])
            if course and not student.is_enrolled(course.code):  # skip missing courses / duplicates
                student._enrollments.append(Enrollment.from_dict(item, course))
        return student

    def __repr__(self) -> str:
        """Short text form for debugging, e.g. Student('S001', 'Ava Thompson')."""
        return f"Student({self.student_id!r}, {self.name!r})"