"""Course model: a code, a title and a grade structure (list of components)."""
from __future__ import annotations

import re
from typing import Any, Dict, List

from sms.config import COURSE_TOTAL_WEIGHT, DEFAULT_MAX_MARKS
from sms.exceptions import ComponentNotFoundError, DuplicateComponentError, ValidationError
from sms.models.component import Component

_CODE_RE = re.compile(r"^[A-Za-z0-9_-]+$")
_EPS = 1e-6


class Course:
    """A course with a code, a title and a grade structure made of weighted components.
    Each component has a weight (its % of the final mark). The weights must add up to
    exactly 100% before students can be enrolled in the course.
    """
    def __init__(self, code: str, title: str = ""):
        """Create a course. The code is upper-cased and checked; raises ValidationError if it is not valid."""
        code = (code or "").strip().upper()
        if not _CODE_RE.match(code):
            raise ValidationError("Course code may only contain letters, digits, '-' and '_' (e.g. COMP1234).")
        self.code = code
        self.title = (title or "").strip()
        self._components: Dict[str, Component] = {}

    # ---- structure -------------------------------------------------------
    @property
    def components(self) -> List[Component]:
        """The grade-structure components, in the order they were added."""
        return list(self._components.values())

    @property
    def total_weight(self) -> float:
        """Sum of all component weights in percent (rounded to avoid floating-point noise)."""
        return round(sum(c.weight for c in self._components.values()), 6)

    @property
    def remaining_weight(self) -> float:
        """Percent of the course still to be allocated (100 minus the total weight)."""
        return round(COURSE_TOTAL_WEIGHT - self.total_weight, 6)

    @property
    def is_ready(self) -> bool:
        """A course can take students once its weights add up to exactly 100%."""
        return bool(self._components) and abs(self.remaining_weight) < _EPS

    def _next_id(self) -> str:
        nums = [int(i[1:]) for i in self._components if i[1:].isdigit()]
        return f"c{(max(nums) if nums else 0) + 1}"

    def _check_name(self, name: str, ignore_id: str = "") -> None:
        wanted = name.strip().lower()
        for comp in self._components.values():
            if comp.component_id != ignore_id and comp.name.lower() == wanted:
                raise DuplicateComponentError(f"{self.code} already has a component called '{comp.name}'.")

    def _check_total(self, new_total: float, own_weight: float = 0.0) -> None:
        """`own_weight` is the weight of the component being edited (it is freed up while editing)."""
        if new_total > COURSE_TOTAL_WEIGHT + _EPS:
            room = max(self.remaining_weight + own_weight, 0)
            if room <= _EPS:
                raise ValidationError(
                    f"{self.code} is already at {COURSE_TOTAL_WEIGHT:g}%. Reduce another component first.")
            raise ValidationError(
                f"Total weight would be {new_total:g}% (limit {COURSE_TOTAL_WEIGHT:g}%). "
                f"This component can be at most {room:g}%.")

    def add_component(self, name: str, weight: float, max_marks: float = DEFAULT_MAX_MARKS) -> Component:
        """Add a component to the grade structure and return it.
        Raises ValidationError if a value is invalid or the total would pass 100%,
        and DuplicateComponentError if the name is already used.
        """
        comp = Component(self._next_id(), name, weight, max_marks)  # validates
        self._check_name(comp.name)
        self._check_total(self.total_weight + comp.weight)
        self._components[comp.component_id] = comp
        return comp

    def get_component(self, component_id: str) -> Component:
        """Return the component with this id, or raise ComponentNotFoundError."""
        try:
            return self._components[component_id]
        except KeyError:
            raise ComponentNotFoundError(f"Component not found in {self.code}.") from None

    def has_component(self, component_id: str) -> bool:
        return component_id in self._components

    def update_component(self, component_id: str, name: str, weight: float,
                         max_marks: float = DEFAULT_MAX_MARKS) -> Component:
        """Change a component's name, weight and 'out of' marks, and return it.
        The new values are checked before anything is changed; the same errors as add_component can be raised."""
        comp = self.get_component(component_id)
        Component(component_id, name, weight, max_marks)   # validate the new values first
        self._check_name(name, ignore_id=component_id)
        self._check_total(self.total_weight - comp.weight + weight, own_weight=comp.weight)
        comp.update(name, weight, max_marks)
        return comp

    def remove_component(self, component_id: str) -> None:
        self.get_component(component_id)
        del self._components[component_id]

    # ---- serialisation ---------------------------------------------------
    def to_dict(self) -> Dict[str, Any]:
        return {"code": self.code, "title": self.title,
                "components": [c.to_dict() for c in self.components]}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Course":
        """Build a Course (with its components) from a dictionary made by to_dict()."""
        course = cls(data["code"], data.get("title", ""))
        for item in data.get("components", []):
            comp = Component.from_dict(item)
            course._components[comp.component_id] = comp
        return course

    def __repr__(self) -> str:
        return f"Course({self.code!r}, {self.total_weight:g}%)"