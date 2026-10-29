"""Enrollment: one student's marks in one course."""
from __future__ import annotations

from typing import Any, Dict, Optional

from sms.exceptions import ValidationError
from sms.models.course import Course
from sms.models.grading import is_pass, letter_grade


class Enrollment:
    """Marks are stored per component id. Each mark is converted to points:
    points = mark / max_marks * weight, so the points of all components add up to
    the course total (out of 100 when the structure is complete)."""

    def __init__(self, course: Course, scores: Optional[Dict[str, float]] = None):
        """Link a student's marks to a course.
        `scores` maps component id to mark; marks for components that no longer exist are ignored.
        """
        self.course = course
        self._scores: Dict[str, float] = {}
        for cid, mark in (scores or {}).items():
            if course.has_component(cid):  # ignore marks of components that were deleted
                self._scores[cid] = float(mark)

    @property
    def course_code(self) -> str:
        """Code of the course this enrollment belongs to."""
        return self.course.code

    # ---- marks -----------------------------------------------------------
    def score(self, component_id: str) -> Optional[float]:
        """The mark entered for a component, or None if it has not been marked yet."""
        return self._scores.get(component_id)

    def set_scores(self, scores: Dict[str, Optional[float]]) -> None:
        """Set/clear several marks at once. `None` clears a mark. All-or-nothing."""
        for cid, mark in scores.items():
            comp = self.course.get_component(cid)
            if mark is not None and not 0 <= mark <= comp.max_marks:
                raise ValidationError(f"{comp.name}: marks must be between 0 and {comp.max_marks:g}.")
        for cid, mark in scores.items():
            if mark is None:
                self._scores.pop(cid, None)
            else:
                self._scores[cid] = float(mark)

    def remove_component(self, component_id: str) -> None:
        """Discard any score recorded for a component that was removed from the course."""
        self._scores.pop(component_id, None)

    def points(self, component_id: str) -> Optional[float]:
        """Points a component's mark is worth: mark / max_marks * weight. None if not marked yet."""
        mark = self._scores.get(component_id)
        if mark is None:
            return None
        comp = self.course.get_component(component_id)
        return mark / comp.max_marks * comp.weight

    # ---- calculations ----------------------------------------------------
    @property
    def has_marks(self) -> bool:
        return any(self.course.has_component(c) for c in self._scores)

    @property
    def earned_points(self) -> float:
        return round(sum(self.points(c.component_id) or 0 for c in self.course.components), 2)

    @property
    def assessed_weight(self) -> float:
        """Total weight of the components that have a mark so far."""
        return round(sum(c.weight for c in self.course.components if c.component_id in self._scores), 2)

    @property
    def progress(self) -> float:
        total = self.course.total_weight
        return round(self.assessed_weight / total * 100, 1) if total else 0.0

    @property
    def is_complete(self) -> bool:
        comps = self.course.components
        return bool(comps) and all(c.component_id in self._scores for c in comps)

    @property
    def standing(self) -> float:
        """Percentage achieved on the work assessed so far (the final mark once complete)."""
        assessed = self.assessed_weight
        return round(self.earned_points / assessed * 100, 2) if assessed else 0.0

    @property
    def grade(self) -> str:
        return letter_grade(self.standing) if self.has_marks else "N/A"

    @property
    def has_passed(self) -> bool:
        return self.has_marks and is_pass(self.standing)

    # ---- serialisation ---------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        """Return the enrollment (course code and marks) as a dictionary, ready to be saved as JSON."""
        return {"course_code": self.course_code, "scores": dict(self._scores)}

    @classmethod
    def from_dict(cls, data: Dict[str, Any], course: Course) -> "Enrollment":
        return cls(course, data.get("scores", {}))
