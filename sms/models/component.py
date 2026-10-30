"""An assessment component of a course, e.g. 'Lab' worth 10% of the final mark."""
from __future__ import annotations

import math
from typing import Any, Dict

from sms.config import COURSE_TOTAL_WEIGHT, DEFAULT_MAX_MARKS
from sms.exceptions import ValidationError


class Component:
    """One graded item. `weight` is its share of the course (in %),
    `max_marks` is what a student's raw mark is out of."""

    def __init__(self, component_id: str, name: str, weight: float,
                 max_marks: float = DEFAULT_MAX_MARKS):
        self.component_id = component_id
        self.update(name, weight, max_marks)

    def update(self, name: str, weight: float, max_marks: float = DEFAULT_MAX_MARKS) -> None:
        """Validate everything first so a failed update changes nothing."""
        name = (name or "").strip()
        if not name:
            raise ValidationError("Component name cannot be empty.")
        if not math.isfinite(weight) or not 0 < weight <= COURSE_TOTAL_WEIGHT:
            raise ValidationError(
                f"Weight must be a finite number greater than 0 and at most {COURSE_TOTAL_WEIGHT:g}%.")
        if not math.isfinite(max_marks) or max_marks <= 0:
            raise ValidationError("'Out of' marks must be a finite number greater than 0.")
        self.name = name
        self.weight = float(weight)
        self.max_marks = float(max_marks)

    def to_dict(self) -> Dict[str, Any]:
        return {"id": self.component_id, "name": self.name,
                "weight": self.weight, "max_marks": self.max_marks}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Component":
        return cls(data["id"], data["name"], data["weight"],
                   data.get("max_marks", DEFAULT_MAX_MARKS))

    def __repr__(self) -> str:
        return f"Component({self.name!r}, {self.weight:g}%)"
