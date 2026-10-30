"""Business logic for courses and their grade structures.

This module provides:

* ``parse_structure`` - turns a short text description of a grade structure
  (for example ``"Lab 10, Quiz 1 5/20, Exam 50"``) into component specs.
* ``CourseManager`` - an in-memory registry of ``Course`` objects with
  create / read / update / delete operations and helpers for editing each
  course's grade structure (its assessment components).
"""
from __future__ import annotations

import re
from typing import Dict, Iterable, List, Sequence, Tuple

from sms.config import DEFAULT_MAX_MARKS
from sms.exceptions import CourseNotFoundError, DuplicateCourseError, ValidationError
from sms.models.component import Component
from sms.models.course import Course

# One assessment item described as plain data before it becomes a Component.
ComponentSpec = Tuple[str, float, float]  # (name, weight %, out of)

# Matches one item such as "Quiz 1 5/20":
#   name   - any text (non-greedy, so the trailing numbers are not swallowed)
#   weight - a number, optionally followed by a "%" sign
#   max    - optional "/<out of>" part; defaults to DEFAULT_MAX_MARKS when absent
_ITEM_RE = re.compile(
    r"^(?P<name>.+?)\s+(?P<weight>\d+(?:\.\d+)?)\s*%?(?:\s*/\s*(?P<max>\d+(?:\.\d+)?))?$")


def parse_structure(text: str) -> List[ComponentSpec]:
    """Parse 'Lab 10, A1 7.5, Quiz 1 5/20, Exam 50' into component specs.

    Each comma separated item is '<name> <weight>' with an optional '/<out of>'.

    Args:
        text: The raw grade-structure text. Items may be separated by commas,
            semicolons or new lines. ``None`` or empty text gives an empty list.

    Returns:
        A list of ``(name, weight, max_marks)`` tuples in the order written.

    Raises:
        ValidationError: If an item cannot be read as '<name> <weight>[/<out of>]'.
    """
    specs: List[ComponentSpec] = []
    # Split on comma, new line or semicolon; "or ''" guards against None input.
    for raw in re.split(r"[,\n;]", text or ""):
        item = raw.strip()
        if not item:
            continue  # ignore blank pieces such as a trailing comma
        match = _ITEM_RE.match(item)
        if not match:
            raise ValidationError(f"Could not read '{item}'. Use the form 'Name weight', e.g. 'Lab 10'.")
        # Fall back to the default "out of" value when no "/<max>" was given.
        specs.append((match["name"].strip(), float(match["weight"]),
                      float(match["max"]) if match["max"] else DEFAULT_MAX_MARKS))
    return specs


class CourseManager:
    """In-memory store of courses, keyed by upper-case course code.

    Handles adding, finding, renaming and deleting courses, and delegates
    grade-structure edits to the underlying ``Course`` objects.
    """

    def __init__(self) -> None:
        """Create an empty manager with no courses."""
        # Maps course code (e.g. "CS101") -> Course object.
        self._courses: Dict[str, Course] = {}
        self._student_manager = None

    def set_courses(self, courses: Iterable[Course]) -> None:
        """Replace all stored courses with ``courses`` (used when loading from storage)."""
        self._courses = {c.code: c for c in courses}

    def add_course(self, code: str, title: str = "",
                   components: Sequence[ComponentSpec] = ()) -> Course:
        """Create a course, optionally with an initial grade structure.

        Args:
            code: Course code; normalised by the ``Course`` constructor.
            title: Optional human readable title.
            components: Optional ``(name, weight, max_marks)`` specs to add.

        Returns:
            The newly created and stored ``Course``.

        Raises:
            DuplicateCourseError: If a course with that code already exists.
            ValidationError: If any component is invalid (nothing is stored).
        """
        course = Course(code, title)
        if course.code in self._courses:
            raise DuplicateCourseError(f"Course {course.code} already exists.")
        for name, weight, max_marks in components:  # raises before anything is stored
            course.add_component(name, weight, max_marks)
        # Only reached when every component was valid, so a failure never leaves a half-built course.
        self._courses[course.code] = course
        return course

    def get_course(self, code: str) -> Course:
        """Return the course with ``code`` (case and surrounding spaces are ignored).

        Raises:
            CourseNotFoundError: If no such course exists.
        """
        try:
            return self._courses[code.strip().upper()]
        except KeyError:
            # "from None" hides the internal KeyError so the user sees a clean message.
            raise CourseNotFoundError(f"No course with code {code.upper()}.") from None

    def list_courses(self) -> List[Course]:
        """Return all courses sorted alphabetically by code."""
        return sorted(self._courses.values(), key=lambda c: c.code)

    def update_title(self, code: str, title: str) -> Course:
        """Change a course's title (whitespace trimmed) and return the course."""
        course = self.get_course(code)
        course.title = title.strip()
        return course
    
    def update_course_code(self, old_code: str, new_code: str) -> Course:
        """Rename a course by changing its code.

        Args:
            old_code: Current code of the course.
            new_code: Desired new code; validated and upper-cased.

        Returns:
            The renamed ``Course``.

        Raises:
            CourseNotFoundError: If ``old_code`` does not exist.
            ValidationError: If ``new_code`` is empty or badly formatted.
            DuplicateCourseError: If ``new_code`` is already used by another course.
        """
        old_code = old_code.strip().upper()
        new_code = Course(new_code).code  # validates the format and upper-cases it

        course = self.get_course(old_code)

        if not new_code:
            raise ValidationError("Course code cannot be empty.")

        # Renaming to the same code is allowed; any other existing code is a clash.
        if old_code != new_code and new_code in self._courses:
            raise DuplicateCourseError(f"Course {new_code} already exists.")

        # Remove old code from the dictionary
        del self._courses[old_code]

        # Change the course object's code
        course.code = new_code

        # Add it back using the new code
        self._courses[new_code] = course

        return course


    def delete_course(self, code: str) -> Course:
        """Remove a course and return it.

        Note: this only removes it from the course list. Use
        ``StudentManager.delete_course`` to also drop it from enrolled students.
        """
        course = self.get_course(code)
        del self._courses[course.code]
        return course

    # ---- grade structure -------------------------------------------------
    def add_component(self, code: str, name: str, weight: float,
                      max_marks: float = DEFAULT_MAX_MARKS) -> Component:
        """Add an assessment component (e.g. an exam) to the course ``code``."""
        return self.get_course(code).add_component(name, weight, max_marks)

    def update_component(self, code: str, component_id: str, name: str, weight: float,
                         max_marks: float = DEFAULT_MAX_MARKS) -> Component:
        """Change the name, weight and maximum marks of an existing component."""
        course = self.get_course(code)
        old_max_marks = course.get_component(component_id).max_marks
        component = course.update_component(component_id, name, weight, max_marks)
        if self._student_manager is not None:
            self._student_manager.rescale_component_scores(
                course.code, component_id, old_max_marks, component.max_marks)
        return component

    def remove_component(self, code: str, component_id: str) -> None:
        """Remove the component ``component_id`` from the course ``code``."""
        course = self.get_course(code)
        course.remove_component(component_id)
        if self._student_manager is not None:
            self._student_manager.remove_component(code, component_id)

    def __len__(self) -> int:
        """Return the number of courses stored."""
        return len(self._courses)