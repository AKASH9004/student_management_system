# Student Management System

A Python desktop application for managing students, courses, enrolments, marks, and grade calculations in a university or school.

[GitHub repository](https://github.com/AKASH9004/student_management_system)

## Getting Started

Follow these steps to set up and run the project on your machine.
This desktop application must be downloaded and run on your computer; it will not work on ed.

### 1. Download the project, open it, and install Python

Download and unzip the project from the [GitHub repository](https://github.com/AKASH9004/student_management_system), then open a terminal in the folder containing `main.py`.

If needed, navigate to the project folder:

macOS / Linux:
```bash
cd /path/to/student_management_system
```

Windows PowerShell:
```powershell
cd C:\path\to\student_management_system
```

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

If `py` is not available, try:
```powershell
python -m tkinter
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

### 3. Optional: create a virtual environment

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

### 4. Run the application

macOS / Linux:
```bash
python3 main.py
```

Windows:
```powershell
py main.py

or 

python3 main.py
```

If `python3` is not available on macOS/Linux, try `python main.py`.

### 5. Optional: restore sample data

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

## How to Use the App

1. **Start on the Dashboard.** It shows student and course totals, grade statistics, course results, and top students.
2. **Create a course.** Open **Courses** and select **+ New Course**. Enter a course code and title. You can leave the optional grade-structure field blank and add components afterward, or enter them as `Name weight`, separated by commas. For example:

   ```text
   Lab 10, A1 20, Project 30, Exam 40
   ```

   This creates a lab worth 10% of the course, Assignment 1 worth 20%, a project worth 30%, and an exam worth 40%. The weights must total **100%** before students can enrol.
3. **Add assessment components, if needed.** Select the course, then use **+ Add** in its Grade structure panel. Enter the component name (for example, `Lab` or `A1`), its course weight, and the maximum mark. For a lab worth 10% and marked out of 20, enter `Lab`, `10`, and `20` in those fields. Use **Edit** or **Remove** to manage existing components.
4. **Add a student.** Open **Students** and choose **+ Add Student**. Enter the student's name; age, class, and email can also be provided.
5. **Enrol the student.** Select the student, then choose **+ Enrol in Course** in the student's Courses panel. The course must have a complete 100% grade structure. Alternatively, select a course on the Courses page and use **+ Enrol Student**.
6. **Enter marks.** On the Students page, select the student and their course, then choose **Enter / Edit Marks**. Enter each raw mark up to its configured maximum. Leave a field blank if that assessment has not been marked yet.
7. **Save your work.** Choose **Save** in the sidebar, or use **Ctrl+S**. The app also asks whether to save unsaved changes when you exit. Data is stored locally in `data/students.json`.
8. **Export a progress report.** Select a student and choose **Export Progress Report**. Save the HTML file, then open it in a browser to print it or save it as a PDF.

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
