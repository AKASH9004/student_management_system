"""Letter grades and pass/fail rules shared by all models."""
from sms.config import GRADE_BANDS, LOWEST_GRADE, PASS_PERCENTAGE
 
 
def letter_grade(percentage: float) -> str:
    """Return the letter grade (e.g. 'A+', 'B', 'F') for a percentage, using the bands in config.GRADE_BANDS."""
    for minimum, letter in GRADE_BANDS:
        if percentage >= minimum:
            return letter
    return LOWEST_GRADE
 
 
def is_pass(percentage: float) -> bool:
    """Return True if the percentage reaches the pass mark (config.PASS_PERCENTAGE)."""
    return percentage >= PASS_PERCENTAGE