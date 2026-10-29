"""Central configuration values."""
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_FILE = BASE_DIR / "data" / "students.json"

COURSE_TOTAL_WEIGHT = 100.0     # a course's components must add up to this
DEFAULT_MAX_MARKS = 100.0       # default "marked out of" for a component
PASS_PERCENTAGE = 40.0

# (minimum percentage, letter grade) - checked from top to bottom
GRADE_BANDS = [(90, "A+"), (80, "A"), (70, "B"), (60, "C"), (50, "D"), (40, "E")]
LOWEST_GRADE = "F"
