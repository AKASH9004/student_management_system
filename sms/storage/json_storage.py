"""JSON persistence for courses and students."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Iterable, List, Tuple, Union

from sms.exceptions import StorageError, ValidationError
from sms.models.course import Course
from sms.models.student import Student


class JSONStorage:
    """Reads and writes all courses and students to one JSON file."""

    def __init__(self, file_path: Union[str, Path]):
        """Remember where the data file lives.
        Args:
            file_path: Location of the JSON file; it need not exist yet.
        """
        self.file_path = Path(file_path)

    def save(self, courses: Iterable[Course], students: Iterable[Student]) -> None:
        """Write all courses and students to the JSON file.
        Args:
            courses: Courses to store.
            students: Students to store (each includes its enrolments and marks).
        Raises:
            StorageError: If the file cannot be written.
        """
        payload = {"courses": [c.to_dict() for c in courses],
                   "students": [s.to_dict() for s in students]}
        try:
            # Create the data folder if it does not exist yet.
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
            # Write to a temp file first so a crash can't corrupt existing data.
            fd, tmp_path = tempfile.mkstemp(dir=self.file_path.parent, suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                json.dump(payload, tmp, indent=4)
            os.replace(tmp_path, self.file_path)
        except OSError as exc:
            raise StorageError(f"Could not save data: {exc}") from exc

    def load(self) -> Tuple[List[Course], List[Student]]:
        """Read courses and students from the JSON file.
 
        Returns:
            A ``(courses, students)`` tuple of lists. Both are empty when the file does not exist yet.
 
        Raises:
            StorageError: If the file is unreadable or its contents are malformed.
        """
        if not self.file_path.exists():
            return [], []
        try:
            with open(self.file_path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            # Courses are built first because students refer to them.
            courses = [Course.from_dict(c) for c in data.get("courses", [])]
            # Code -> Course map so each student's enrolments can be linked to the right course.
            lookup = {c.code: c for c in courses}
            students = [Student.from_dict(s, lookup) for s in data.get("students", [])]
            return courses, students
        # Cover unreadable files, invalid JSON and missing or wrongly-typed fields.
        except (OSError, ValueError, OverflowError, KeyError, TypeError, AttributeError,
                ValidationError) as exc:
            raise StorageError(f"Could not load data from {self.file_path}: {exc}") from exc