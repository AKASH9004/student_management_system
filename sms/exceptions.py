"""Custom exceptions used across the application."""


class SMSError(Exception):
    """Base class for all application errors."""


class ValidationError(SMSError):
    """Raised when user supplied data is invalid."""


class StudentNotFoundError(SMSError):
    """Raised when a student ID does not exist."""


class DuplicateStudentError(SMSError):
    """Raised when a student ID already exists."""


class CourseNotFoundError(SMSError):
    """Raised when a course code does not exist."""


class DuplicateCourseError(SMSError):
    """Raised when a course code already exists."""


class ComponentNotFoundError(SMSError):
    """Raised when an assessment component does not exist in a course."""


class DuplicateComponentError(SMSError):
    """Raised when a course already has a component with that name."""


class DuplicateEnrollmentError(SMSError):
    """Raised when a student is already enrolled in a course."""


class EnrollmentNotFoundError(SMSError):
    """Raised when a student is not enrolled in a course."""


class StorageError(SMSError):
    """Raised when reading or writing the data file fails."""
