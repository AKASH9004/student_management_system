# Student Management System

A Python desktop application for managing students, courses, enrolments, marks, and grade calculations in a university or school.

## Getting Started

Follow these steps to set up and run the project on your machine.

### 1. Download the project and install Python

Download and unzip the project, then open a terminal in the folder containing `main.py`.
Install Python 3.8 or newer from [python.org](https://www.python.org/downloads/) if it is not already installed.
On Windows, enable **Add Python to PATH** during installation.

Check that Python is available:

macOS / Linux:
```bash
python3 --version
```

Windows:
```powershell
py --version
```

### 2. Install Tkinter

This project uses Tkinter for its desktop GUI. Check that Tkinter is available:

macOS / Linux:
```bash
python3 -m tkinter
```

Windows:
```powershell
py -m tkinter
```

This should open a small test window. Close it to continue.

On Ubuntu/Debian:

```bash
sudo apt install python3-tk
```

On macOS, Tkinter is included with the python.org installer. If it is missing when using Homebrew Python, install it with:

```bash
brew install python-tk
```

No additional Python packages are required; there is nothing to install with `pip`.

### 3. Open the project folder

If you have not already opened a terminal in the folder containing `main.py`, navigate to it:

macOS / Linux:
```bash
cd /path/to/student_management_system
```

Windows PowerShell:
```powershell
cd C:\path\to\student_management_system
```

### 4. Optional: create a virtual environment

macOS / Linux:
```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:
```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### 5. Run the application

macOS / Linux:
```bash
python3 main.py
```

Windows:
```powershell
py main.py
```

If `python3` is not available on macOS/Linux, try `python main.py`.

### 6. Optional: restore sample data

The seed script overwrites `data/students.json`. Back up your existing data before running it:

macOS / Linux:
```bash
python3 tools/seed_sample_data.py
```

Windows:
```powershell
py tools\seed_sample_data.py
```

## Overview

This project is a Tkinter-based student management app that lets you:

- add and update student records
- create courses with custom assessment structures
- enrol students in multiple courses
- enter marks for each assessment component
- calculate weighted results and overall standings
- view student and course statistics
- save all data into a local JSON file

The app is designed for local desktop use and stores data in `data/students.json`.

On the Students page, select a student and choose **Export Progress Report** to save a printable HTML report. It includes the overall grade and assessment completion, course-by-course standings, and each assessment's mark, weight, and weighted points. Open the saved file in a browser to print it or save it as a PDF.

## Features

- Course creation with custom assessment weights
- Flexible grade components such as `Lab`, `Quiz`, `Assignment`, `Project`, and `Exam`
- Validation that each course totals 100% before enrolment is allowed
- Student tracking with details like age, class, and email
- Enrolment management per student and per course
- Weighted mark calculation using each component's percentage and out-of value
- Progress tracking for incomplete assessments
- Exportable personalized student progress reports with overall results, course progress, and assessment-level marks
- Grade conversion based on configured grade bands
- Dashboard-style statistics for course performance and top students

## Course Structure Format

Courses are defined as comma-separated assessment items in the format:

```text
Lab 10, A1 7.5, A2 7.5, Project 25, Exam 50
```

The parser also accepts semicolons or new lines. A component may optionally include a maximum marks value:

```text
Quiz 1 5/20, Final Exam 50
```

In this example, `Quiz 1` is worth 5% of the course grade and its mark is out of 20. `Final Exam` is worth 50% and, because no maximum marks value is specified, its mark is out of the default 100. The comma separates the two assessment components. Together they account for 55% of the course grade, so add components worth the remaining 45% to complete the course structure.

Important rules from the code:

- each component has a weight percentage
- the default marks-out-of value is `100`
- the sum of all component weights must equal `100.0`
- invalid structures raise a validation error before a course is saved

## Grade Rules

The app uses the grade bands defined in `sms/config.py`:

- `A+` for 90+
- `A` for 80+
- `B` for 70+
- `C` for 60+
- `D` for 50+
- `E` for 40+
- `F` below 40

The pass percentage is set to `40.0`.

## Project Structure

```text
student_management_system/
├── main.py                       # Entry point for the application
├── README.md                    # Project documentation
├── data/
│   └── students.json            # Saved app data
├── tools/
│   └── seed_sample_data.py      # Creates sample students, courses, and marks
├── sms/
│   ├── __init__.py
│   ├── config.py                # Core configuration values, grade bands, pass mark
│   ├── exceptions.py            # Custom validation and domain exceptions
│   ├── models/
│   │   ├── component.py
│   │   ├── course.py
│   │   ├── enrollment.py
│   │   ├── grading.py
│   │   └── student.py
│   ├── services/
│   │   ├── course_manager.py
│   │   ├── progress_report.py   # Builds printable student progress reports
│   │   ├── statistics.py
│   │   └── student_manager.py
│   ├── storage/
│   │   └── json_storage.py
│   └── ui/
│       ├── app.py
│       ├── theme.py
│       ├── utils.py
│       ├── widgets.py
│       └── pages/
│           ├── base.py
│           ├── courses_page.py
│           ├── dashboard_page.py
│           └── students_page.py # Student records, marks, and report export
├── tests/
│   └── test_sms.py              # Unit tests for core logic and reports
```

## Notes

- The app keeps its data in JSON, not in a database.
- Data is saved locally to `data/students.json`.
- The app is intentionally lightweight and uses only the Python standard library plus Tkinter.
- The sample seed script populates several demo courses such as `COMP1234`, `COMP6789`, and `MATH1001`.
