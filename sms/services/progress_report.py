"""Generate self-contained, printable HTML reports for student progress.

The report summarizes the student's overall grade and assessment completion,
then shows each enrolled course with its current standing and component marks.
"""
from __future__ import annotations

from html import escape

from sms.models.student import Student


def render_progress_report(student: Student) -> str:
    """Render a student's current results as a complete HTML document.

    Assessment completion counts marked components across all of the student's
    enrollments. Course standings reflect only the assessments marked so far.

    Args:
        student: Student whose profile, enrollments, and marks appear in the report.

    Returns:
        A standalone HTML string that can be saved, opened in a browser, or printed.
    """
    # Flatten course components so the completion percentage uses one consistent
    # denominator across every course the student is taking.
    assessments = [
        (enrollment, component)
        for enrollment in student.enrollments
        for component in enrollment.course.components
    ]
    marked_count = sum(
        enrollment.score(component.component_id) is not None
        for enrollment, component in assessments
    )
    completion = round(marked_count / len(assessments) * 100) if assessments else 0
    overall_result = f"{student.percentage:.1f}%" if student.has_marks else "No marks yet"
    overall_grade = student.grade
    overall_status = "PASS" if student.has_passed else (
        "FAIL" if student.has_marks else "NOT GRADED"
    )

    sections = []
    for enrollment in student.enrollments:
        course = enrollment.course
        rows = []
        for component in course.components:
            score = enrollment.score(component.component_id)
            points = enrollment.points(component.component_id)
            # Escape assessment names because they are user-editable HTML content.
            rows.append(
                "<tr>"
                f"<td>{escape(component.name)}</td>"
                f"<td>{component.weight:g}%</td>"
                f"<td>{f'{score:g}' if score is not None else 'Not marked'}</td>"
                f"<td>{component.max_marks:g}</td>"
                f"<td>{f'{points:.2f}' if points is not None else '-'}</td>"
                "</tr>"
            )
        if not rows:
            rows.append('<tr><td class="empty" colspan="5">No assessments configured.</td></tr>')

        course_result = f"{enrollment.standing:.1f}%" if enrollment.has_marks else "No marks yet"
        course_grade = enrollment.grade
        progress = enrollment.progress
        # Course details are grouped into separate sections for easier screen
        # reading and to keep each course together when the report is printed.
        sections.append(
            '<section class="course">'
            '<div class="course-heading">'
            f"<div><p class=\"eyebrow\">{escape(course.code)}</p>"
            f"<h2>{escape(course.title or 'Untitled course')}</h2></div>"
            f'<div class="course-result"><strong>{course_result}</strong>'
            f"<span>Grade {escape(course_grade)} | {progress:.0f}% assessed</span></div>"
            "</div>"
            '<div class="progress-track"><div class="progress-fill" '
            f'style="width: {min(progress, 100):g}%"></div></div>'
            "<table><thead><tr><th>Assessment</th><th>Course weight</th>"
            "<th>Mark</th><th>Out of</th><th>Weighted points</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody></table>"
            "</section>"
        )

    course_content = "".join(sections) if sections else (
        '<p class="empty">No course enrolments yet. Enrol in a course to start tracking progress.</p>'
    )
    # Escape profile text before embedding it in the document title and body.
    student_name = escape(student.name)
    student_id = escape(student.student_id)
    generated_courses = len(student.enrollments)
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Progress Report - {student_name}</title>
  <style>
    :root {{ color-scheme: light; --ink: #1c2541; --muted: #65708b; --accent: #4c63d2;
      --line: #e3e7f1; --paper: #fff; --background: #f3f5fb; }}
    * {{ box-sizing: border-box; }}
    body {{ margin: 0; padding: 36px 18px; background: var(--background);
      color: var(--ink); font: 15px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
    main {{ max-width: 900px; margin: auto; }}
    header {{ padding: 30px; border-radius: 18px; color: white;
      background: linear-gradient(125deg, #303f9f, #6579e8); }}
    header p, header h1 {{ margin: 0; }}
    header h1 {{ margin: 8px 0; font-size: 30px; }}
    header .meta {{ color: #e1e6ff; }}
    .eyebrow {{ margin: 0; color: var(--accent); font-size: 12px;
      font-weight: 700; letter-spacing: .1em; text-transform: uppercase; }}
    .summary {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin: 18px 0 28px; }}
    .metric, .course {{ padding: 18px; border: 1px solid var(--line); border-radius: 14px;
      background: var(--paper); }}
    .metric span, .course-result span {{ display: block; color: var(--muted); font-size: 13px; }}
    .metric strong {{ display: block; margin-top: 5px; font-size: 22px; }}
    h2 {{ margin: 2px 0 0; font-size: 20px; }}
    .course {{ margin: 14px 0; }}
    .course-heading {{ display: flex; justify-content: space-between; gap: 16px; align-items: center; }}
    .course-result {{ text-align: right; }}
    .course-result strong {{ display: block; font-size: 21px; }}
    .progress-track {{ height: 7px; margin: 14px 0; overflow: hidden; border-radius: 8px;
      background: #edf0f8; }}
    .progress-fill {{ height: 100%; border-radius: inherit; background: var(--accent); }}
    table {{ width: 100%; border-collapse: collapse; }}
    th, td {{ padding: 10px 8px; border-top: 1px solid var(--line); text-align: left; }}
    th {{ color: var(--muted); font-size: 12px; }}
    footer {{ margin-top: 24px; color: var(--muted); font-size: 12px; text-align: center; }}
    .empty {{ color: var(--muted); }}
    @media (max-width: 620px) {{ .summary {{ grid-template-columns: repeat(2, 1fr); }}
      .course-heading {{ align-items: flex-start; }} th, td {{ padding: 8px 4px; font-size: 12px; }} }}
    @media print {{ body {{ padding: 0; background: white; }}
      header, .metric, .course {{ print-color-adjust: exact; -webkit-print-color-adjust: exact; }}
      .course {{ break-inside: avoid; }} }}
  </style>
</head>
<body>
  <main>
    <header>
      <p class="eyebrow" style="color:#dce3ff">Student success snapshot</p>
      <h1>{student_name}</h1>
      <p class="meta">Student ID: {student_id} | {generated_courses} course(s)</p>
    </header>
    <section class="summary" aria-label="Overall progress">
      <div class="metric"><span>Overall result</span><strong>{overall_result}</strong></div>
      <div class="metric"><span>Overall grade</span><strong>{escape(overall_grade)}</strong></div>
      <div class="metric"><span>Status</span><strong>{overall_status}</strong></div>
      <div class="metric"><span>Assessments marked</span>
        <strong>{marked_count}/{len(assessments)} | {completion}%</strong></div>
    </section>
    <h2>Course-by-course results</h2>
    {course_content}
    <footer>Assessment completion counts marked components across enrolled courses.
      Course result is based on the assessments marked so far.</footer>
  </main>
</body>
</html>
"""
