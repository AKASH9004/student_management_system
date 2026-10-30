"""Business logic for students, enrollments and marks.

``StudentManager`` is the main service used by the UI: it keeps the students in
memory, enrols them in courses (via ``CourseManager``), records marks, and
loads/saves everything through ``JSONStorage``.
"""
from __future__ import annotations

from typing import Dict, List, Optional

from sms.exceptions import DuplicateStudentError, StorageError, StudentNotFoundError
from sms.models.enrollment import Enrollment
from sms.models.student import Student
from sms.services.course_manager import CourseManager
from sms.storage.json_storage import JSONStorage


class StudentManager:
    """CRUD for students plus enrolling them in courses and recording marks."""

    def __init__(self, storage: JSONStorage, courses: Optional[CourseManager] = None):
        """Create a manager.

        Args:
            storage: Backend used to load and save data.
            courses: Course manager to use; a new empty one is created if omitted.
        """
        self._storage = storage
        self.courses = courses or CourseManager()
        self.courses._student_manager = self
        # Maps student ID (e.g. "S001") -> Student object.
        self._students: Dict[str, Student] = {}
        self._load_failed = False

    # ---- persistence -----------------------------------------------------
    def load(self) -> int:
        """Load courses and students from storage, replacing what is in memory.

        Returns:
            The number of students loaded.
        """
        try:
            courses, students = self._storage.load()
        except StorageError:
            self._load_failed = True
            raise
        self.courses.set_courses(courses)
        self._students = {s.student_id: s for s in students}
        self._load_failed = False
        return len(self._students)

    def save(self) -> None:
        """Write all courses and students to storage."""
        if self._load_failed:
            raise StorageError("Cannot save because the data file failed to load. Fix the file and reload before saving.")
        self._storage.save(self.courses.list_courses(), self._students.values())

    # ---- students --------------------------------------------------------
    def _next_id(self) -> str:
        """Generate the next free student ID in the form S001, S002, ...

        It takes the highest existing number and adds one, so IDs are never
        reused after a delete of a lower-numbered student.
        """
        # Only IDs like "S012" count; anything with a non-numeric tail is ignored.
        numbers = [int(sid[1:]) for sid in self._students if sid[1:].isdigit()]
        return f"S{(max(numbers) if numbers else 0) + 1:03d}"

    def add_student(self, name: str, age: int, class_name: str = "", email: str = "",
                    student_id: Optional[str] = None) -> Student:
        """Create and store a new student.

        Args:
            name: Student's full name.
            age: Student's age.
            class_name: Optional class or group name.
            email: Optional email address.
            student_id: Optional explicit ID; generated automatically if omitted.

        Returns:
            The new ``Student``.

        Raises:
            DuplicateStudentError: If the ID is already in use.
        """
        student_id = (student_id or self._next_id()).upper()
        if student_id in self._students:
            raise DuplicateStudentError(f"Student ID {student_id} already exists.")
        student = Student(student_id, name, age, class_name, email)
        self._students[student_id] = student
        return student

    def get_student(self, student_id: str) -> Student:
        """Return the student with ``student_id`` (case and surrounding spaces are ignored).

        Raises:
            StudentNotFoundError: If no such student exists.
        """
        try:
            return self._students[student_id.strip().upper()]
        except KeyError:
            # "from None" hides the internal KeyError so the user sees a clean message.
            raise StudentNotFoundError(f"No student with ID {student_id.upper()}.") from None

    def list_students(self) -> List[Student]:
        """Return all students sorted by ID."""
        return sorted(self._students.values(), key=lambda s: s.student_id)

    def search(self, term: str) -> List[Student]:
        """Return students whose name, ID or class contains ``term`` (case-insensitive).

        An empty term matches every student.
        """
        term = term.strip().lower()
        return [s for s in self.list_students()
                if term in s.name.lower() or term in s.student_id.lower()
                or term in s.class_name.lower()]

    def update_student(self, student_id: str, **fields) -> Student:
        """Update profile details (e.g. name, age, class_name, email) and return the student."""
        student = self.get_student(student_id)
        student.update_details(**fields)
        return student

    def delete_student(self, student_id: str) -> Student:
        """Remove a student (and their marks) and return the removed record."""
        student = self.get_student(student_id)
        del self._students[student.student_id]
        return student

    # ---- enrollments & marks ---------------------------------------------
    def enroll(self, student_id: str, course_code: str) -> Enrollment:
        """Enrol a student in a course and return the new ``Enrollment``."""
        return self.get_student(student_id).enroll(self.courses.get_course(course_code))

    def drop(self, student_id: str, course_code: str) -> None:
        """Remove a student from a course; their marks for it are lost."""
        self.get_student(student_id).drop(course_code.strip().upper())

    def remove_component(self, course_code: str, component_id: str) -> None:
        """Discard any stored marks for a component removed from a course."""
        course_code = course_code.strip().upper()
        for student in self.list_students():
            if student.is_enrolled(course_code):
                student.get_enrollment(course_code).remove_component(component_id)

    def rescale_component_scores(self, course_code: str, component_id: str,
                                 old_max_marks: float, new_max_marks: float) -> None:
        """Preserve each recorded percentage when a component's maximum marks changes."""
        course_code = course_code.strip().upper()
        for student in self.list_students():
            if not student.is_enrolled(course_code):
                continue
            enrollment = student.get_enrollment(course_code)
            score = enrollment.score(component_id)
            if score is not None:
                bounded_score = min(max(score, 0.0), old_max_marks)
                scaled_score = min(bounded_score / old_max_marks * new_max_marks, new_max_marks)
                enrollment.set_scores({component_id: scaled_score})

    def set_scores(self, student_id: str, course_code: str,
                   scores: Dict[str, Optional[float]]) -> Enrollment:
        """Record marks for a student in a course.

        Args:
            student_id: The student.
            course_code: The course (the student must be enrolled in it).
            scores: Mapping of component ID -> mark; ``None`` means "not marked yet".

        Returns:
            The updated ``Enrollment``.
        """
        enrollment = self.get_student(student_id).get_enrollment(course_code.strip().upper())
        enrollment.set_scores(scores)
        return enrollment

    def students_in_course(self, course_code: str) -> List[Student]:
        """Return the students enrolled in ``course_code``, sorted by ID."""
        return [s for s in self.list_students() if s.is_enrolled(course_code)]

    def delete_course(self, course_code: str) -> int:
        """Delete a course and drop it from every student. Returns students affected."""
        course = self.courses.get_course(course_code)
        # Work out who is enrolled first, because the course is removed afterwards.
        affected = self.students_in_course(course.code)
        for student in affected:
            student.drop(course.code)
        self.courses.delete_course(course.code)
        return len(affected)

    def __len__(self) -> int:
        """Return the number of students stored."""
        return len(self._students)