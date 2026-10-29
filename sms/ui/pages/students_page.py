"""Students: profiles, course enrolments and mark entry."""
import re
import tkinter as tk
from tkinter import filedialog, messagebox
from typing import Dict, Optional

from sms.models.enrollment import Enrollment
from sms.models.student import Student
from sms.services.progress_report import render_progress_report
from sms.ui import theme as T
from sms.ui.pages.base import Page
from sms.ui.utils import fmt, to_float, to_int
from sms.ui.widgets import Card, Field, FormDialog, button, chip, fill_tree, make_tree


class StudentsPage(Page):
    """Page for managing students, their course enrolments and their marks.

    Layout is a two-column master/detail view:

    * Left: a searchable list of all students with summary results.
    * Right (top to bottom): the selected student's profile, the courses they
      are enrolled in, and the per-component marks for the selected course.

    Selecting a row in one table drives the content of the tables below/beside
    it: student -> enrolments -> marks.
    """

    def __init__(self, parent, app):
        """Build all widgets and wire up event bindings.

        Args:
            parent: The Tk container this page is placed in.
            app: The main application window; used as the parent for dialogs
                and for notifying the rest of the UI of data changes.
        """
        super().__init__(parent, app)
        actions = self.header("Students", "Profiles, course enrolments and marks")
        self.report_btn = button(actions, "Export Progress Report", self.export_progress_report, "Secondary")
        self.report_btn.pack(side="left", padx=(0, 8))
        button(actions, "+ Add Student", self.add_student, "Primary").pack(side="left")

        # Two-column body; "uniform" keeps the 3:4 width ratio stable.
        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        body.columnconfigure(0, weight=3, uniform="c")
        body.columnconfigure(1, weight=4, uniform="c")
        body.rowconfigure(0, weight=1)

        # ---- left: list
        left = Card(body, "All students")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        bar = tk.Frame(left.body, bg=T.CARD)
        bar.pack(fill="x", pady=(0, 8))
        from tkinter import ttk
        # Any change to the search text re-filters the list immediately.
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *_: self.refresh())
        tk.Label(bar, text="Search", bg=T.CARD, fg=T.MUTED).pack(side="left", padx=(0, 8))
        ttk.Entry(bar, textvariable=self.search_var).pack(side="left", fill="x", expand=True)
        button(bar, "Clear", lambda: self.search_var.set(""), "Ghost").pack(side="left", padx=(6, 0))

        frame, self.tree = make_tree(left.body, [
            ("id", "ID", 50), ("name", "Name", 104), ("class", "Class", 58),
            ("courses", "Courses", 76, "center"), ("result", "Result", 62, "center"),
            ("grade", "Grade", 60, "center")], height=14)
        frame.pack(fill="both", expand=True)
        # Selection updates the detail panes; double-click edits; Delete key removes.
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.refresh_detail())
        self.tree.bind("<Double-1>", lambda _e: self.edit_student())
        self.tree.bind("<Delete>", lambda _e: self.delete_student())
        row = tk.Frame(left.body, bg=T.CARD)
        row.pack(fill="x", pady=(10, 0))
        button(row, "Edit", self.edit_student, "Secondary").pack(side="left")
        button(row, "Delete", self.delete_student, "Danger").pack(side="left", padx=6)

        # ---- right: profile, courses, marks
        right = tk.Frame(body, bg=T.BG)
        right.grid(row=0, column=1, sticky="nsew")

        # Profile card: name + info line, with result chips on the right.
        profile = Card(right)
        profile.pack(fill="x")
        top = tk.Frame(profile.body, bg=T.CARD)
        top.pack(fill="x")
        self.chip_box = tk.Frame(top, bg=T.CARD)   # packed first so the chips never get squeezed
        self.chip_box.pack(side="right", anchor="n")
        self.name_var, self.info_var = tk.StringVar(value="Select a student"), tk.StringVar()
        tk.Label(top, textvariable=self.name_var, bg=T.CARD, fg=T.TEXT, font=T.font("h1")).pack(side="left")
        tk.Label(profile.body, textvariable=self.info_var, bg=T.CARD, fg=T.MUTED,
                 anchor="w").pack(fill="x")

        # Courses card: the selected student's enrolments.
        courses = Card(right, "Courses")
        courses.pack(fill="both", expand=True, pady=10)
        self.enrol_btn = button(courses.actions, "+ Enrol in Course", self.enroll, "Primary")
        self.enrol_btn.pack(side="left")
        button(courses.actions, "Drop", self.drop, "Danger").pack(side="left", padx=(6, 0))
        frame, self.enrol_tree = make_tree(courses.body, [
            ("code", "Course", 90), ("title", "Title", 170), ("done", "Marked", 70, "center"),
            ("result", "Result", 76, "center"), ("grade", "Grade", 56, "center")], height=4)
        frame.pack(fill="both", expand=True)
        self.enrol_tree.bind("<<TreeviewSelect>>", lambda _e: self.refresh_marks())

        # Marks card: component-level marks for the selected enrolment.
        marks = Card(right, "Marks")
        marks.pack(fill="both", expand=True)
        self.marks_btn = button(marks.actions, "Enter / Edit Marks", self.enter_marks, "Primary")
        self.marks_btn.pack(side="left")
        self.marks_card = marks
        self.footer_var = tk.StringVar()
        tk.Label(marks.body, textvariable=self.footer_var, bg=T.CARD, fg=T.TEXT, anchor="w",
                 font=T.font("bold")).pack(side="bottom", fill="x", pady=(6, 0))
        frame, self.marks_tree = make_tree(marks.body, [
            ("name", "Component", 160), ("weight", "Weight", 70, "center"), ("score", "Mark", 70, "center"),
            ("out", "Out of", 70, "center"), ("points", "Points", 80, "center")], height=5)
        frame.pack(fill="both", expand=True)
        self.marks_tree.bind("<Double-1>", lambda _e: self.enter_marks())

    # ---- selection helpers ----------------------------------------------
    def selected_id(self) -> Optional[str]:
        """Return the student ID selected in the main list, or None if nothing is selected."""
        sel = self.tree.selection()
        return sel[0] if sel else None

    def current_student(self) -> Optional[Student]:
        """Return the Student for the selected row, or None if there is no selection."""
        sid = self.selected_id()
        return self.manager.get_student(sid) if sid else None

    def current_enrollment(self) -> Optional[Enrollment]:
        """Return the Enrollment selected in the courses table.

        Returns None if no student or course row is selected, or if the
        selected course is no longer one of the student's enrolments.
        """
        student, sel = self.current_student(), self.enrol_tree.selection()
        if student and sel and student.is_enrolled(sel[0]):
            return student.get_enrollment(sel[0])
        return None

    def _need_student(self) -> Optional[Student]:
        """Return the selected student, or show a hint dialog and return None.

        Used by actions that cannot proceed without a selected student.
        """
        student = self.current_student()
        if not student:
            messagebox.showinfo("Select a student", "Please select a student in the list first.", parent=self.app)
        return student

    def select(self, student_id: str, course_code: Optional[str] = None) -> None:
        """Programmatically select a student (and optionally one of their courses).

        The search box is cleared first so the target row is not filtered out.

        Args:
            student_id: ID of the student to select.
            course_code: Optional course code to select in the courses table.
        """
        self.search_var.set("")
        if self.tree.exists(student_id):
            self.tree.selection_set(student_id)
            self.tree.see(student_id)
            if course_code and self.enrol_tree.exists(course_code):
                self.enrol_tree.selection_set(course_code)

    # ---- refresh -----------------------------------------------------------
    def refresh(self) -> None:
        """Reload the student list (applying the search term) and refresh the detail panes."""
        term = self.search_var.get().strip()
        students = self.manager.search(term) if term else self.manager.list_students()
        # Each row is (item id, displayed values, tags); failing students get the "fail" tag.
        fill_tree(self.tree, [
            (s.student_id, (s.student_id, s.name, s.class_name or "-", len(s.enrollments),
                            f"{s.percentage:.1f}%" if s.has_marks else "-", s.grade),
             ("fail",) if s.has_marks and not s.has_passed else ())
            for s in students])
        # Keep something selected whenever the list is non-empty.
        if not self.tree.selection() and self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])
        self.refresh_detail()

    def refresh_detail(self) -> None:
        """Update the profile card and courses table for the selected student."""
        student = self.current_student()
        # Result chips are rebuilt from scratch each time.
        for child in self.chip_box.winfo_children():
            child.destroy()
        self.enrol_btn.configure(state="normal" if student else "disabled")
        self.report_btn.configure(state="normal" if student else "disabled")
        if not student:
            # Empty state: no students exist or none is selected.
            self.name_var.set("No student selected")
            self.info_var.set("Add a student with '+ Add Student' to get started.")
            fill_tree(self.enrol_tree, [])
            self.refresh_marks()
            return

        self.name_var.set(student.name)
        # Optional fields (class, email) are skipped when empty.
        bits = [student.student_id, f"Class {student.class_name}" if student.class_name else None,
                f"Age {student.age}", student.email or None]
        self.info_var.set("   |   ".join(b for b in bits if b))
        # Chips are packed right-to-left, so the first one packed ends up rightmost.
        if student.has_marks:
            chip(self.chip_box, "PASS" if student.has_passed else "FAIL",
                 T.SUCCESS if student.has_passed else T.DANGER).pack(side="right", padx=(6, 0))
            chip(self.chip_box, f"Grade {student.grade}", T.GRADE_COLORS[student.grade]).pack(side="right", padx=(6, 0))
            chip(self.chip_box, f"{student.percentage:.1f}% overall", T.PRIMARY).pack(side="right")
        else:
            chip(self.chip_box, "No marks yet", T.GRADE_COLORS["N/A"]).pack(side="right")

        # "Marked" shows how much of the course has been assessed; "Result" is the current standing.
        fill_tree(self.enrol_tree, [
            (e.course_code, (e.course_code, e.course.title or "-", f"{e.progress:.0f}%",
                             f"{e.standing:.1f}%" if e.has_marks else "-", e.grade),
             ("fail",) if e.has_marks and not e.has_passed else ())
            for e in student.enrollments])
        if not self.enrol_tree.selection() and self.enrol_tree.get_children():
            self.enrol_tree.selection_set(self.enrol_tree.get_children()[0])
        self.refresh_marks()

    def export_progress_report(self) -> None:
        """Save a printable HTML progress report for the selected student."""
        student = self._need_student()
        if not student:
            return
        safe_id = re.sub(r"[^A-Za-z0-9_-]+", "_", student.student_id).strip("_") or "student"
        destination = filedialog.asksaveasfilename(
            parent=self.app,
            title="Export Student Progress Report",
            initialfile=f"{safe_id}_progress_report.html",
            defaultextension=".html",
            filetypes=[("HTML report", "*.html"), ("All files", "*.*")],
        )
        if not destination:
            return
        try:
            with open(destination, "w", encoding="utf-8") as report_file:
                report_file.write(render_progress_report(student))
        except OSError as exc:
            messagebox.showerror("Export failed", f"Could not save the report:\n{exc}", parent=self.app)
            return
        messagebox.showinfo("Report exported", f"Progress report saved to:\n{destination}", parent=self.app)

    def refresh_marks(self) -> None:
        """Update the marks table and its footer for the selected enrolment."""
        enrollment = self.current_enrollment()
        self.marks_btn.configure(state="normal" if enrollment else "disabled")
        if not enrollment:
            # Nothing to show: reset the card and explain what to do next.
            self.marks_card.set_title("Marks")
            fill_tree(self.marks_tree, [])
            self.footer_var.set("Enrol the student in a course to enter marks." if self.current_student() else "")
            return
        course = enrollment.course
        self.marks_card.set_title(f"Marks - {course.code}")
        rows = []
        for comp in course.components:
            score, points = enrollment.score(comp.component_id), enrollment.points(comp.component_id)
            # Unmarked components are shown dimmed with "-" placeholders.
            rows.append((comp.component_id, (
                comp.name, f"{comp.weight:g}%", fmt(score) if score is not None else "-",
                fmt(comp.max_marks), f"{points:.2f}" if points is not None else "-"),
                ("muted",) if score is None else ()))
        fill_tree(self.marks_tree, rows)
        status = "complete" if enrollment.is_complete else f"{enrollment.progress:.0f}% of course marked"
        self.footer_var.set(f"Earned {enrollment.earned_points:g} of {enrollment.assessed_weight:g} points "
                            f"assessed  |  {enrollment.standing:.1f}%  |  Grade {enrollment.grade}  |  {status}")

    # ---- student actions ---------------------------------------------------
    def _profile_fields(self, s: Optional[Student] = None):
        """Build the profile form fields, pre-filled from ``s`` when editing.

        Shared by the Add and Edit dialogs.
        """
        return [Field("name", "Name", s.name if s else ""), Field("age", "Age", str(s.age) if s else ""),
                Field("class", "Class", s.class_name if s else ""), Field("email", "Email", s.email if s else "")]

    def add_student(self) -> None:
        """Open the Add Student dialog; on submit create the student and select them."""
        def submit(v: Dict[str, str]) -> None:
            # to_int validates the age text and reports errors using the field label.
            student = self.manager.add_student(v["name"], to_int(v["age"], "Age"), v["class"], v["email"])
            self.app.changed(f"Added {student.name} ({student.student_id})")
            self.select(student.student_id)

        FormDialog(self.app, "Add Student", self._profile_fields(), submit, ok_text="Add")

    def edit_student(self) -> None:
        """Open the Edit Student dialog for the selected student."""
        student = self._need_student()
        if not student:
            return

        def submit(v: Dict[str, str]) -> None:
            self.manager.update_student(student.student_id, name=v["name"], age=to_int(v["age"], "Age"),
                                        class_name=v["class"], email=v["email"])
            self.app.changed(f"Updated {student.name}")

        FormDialog(self.app, f"Edit Student - {student.student_id}", self._profile_fields(student), submit)

    def delete_student(self) -> None:
        """Delete the selected student after the user confirms (irreversible)."""
        student = self._need_student()
        if student and messagebox.askyesno(
                "Delete student", f"Delete {student.name} ({student.student_id}) and all their marks?\n"
                "This cannot be undone.", parent=self.app):
            self.manager.delete_student(student.student_id)
            self.app.changed(f"Deleted {student.name}")

    # ---- enrolment & marks -------------------------------------------------
    def enroll(self) -> None:
        """Enrol the selected student in a course chosen from a dialog.

        Only courses that are ready (grade structure totals 100%) and that the
        student is not already enrolled in are offered.
        """
        student = self._need_student()
        if not student:
            return
        ready = [c for c in self.courses.list_courses() if c.is_ready and not student.is_enrolled(c.code)]
        if not ready:
            messagebox.showinfo(
                "No courses available",
                "There is no course to enrol in.\nCreate a course on the Courses page and make sure its grade "
                "structure adds up to 100%.", parent=self.app)
            return

        def submit(v: Dict[str, str]) -> None:
            # Choices look like "CODE - Title"; the course code is the part before " - ".
            code = v["course"].split(" - ")[0]
            self.manager.enroll(student.student_id, code)
            self.app.changed(f"Enrolled {student.name} in {code}")
            self.select(student.student_id, code)

        FormDialog(self.app, f"Enrol {student.name}",
                   [Field("course", "Course", choices=[f"{c.code} - {c.title or 'Untitled'}" for c in ready])],
                   submit, ok_text="Enrol")

    def drop(self) -> None:
        """Drop the selected student from the selected course after confirmation.

        All marks recorded for that course are lost.
        """
        student, enrollment = self.current_student(), self.current_enrollment()
        if not student or not enrollment:
            messagebox.showinfo("Select a course", "Please select a course in the Courses table first.",
                                parent=self.app)
            return
        if messagebox.askyesno("Drop course", f"Drop {student.name} from {enrollment.course_code}?\n"
                               "Their marks for this course will be lost.", parent=self.app):
            self.manager.drop(student.student_id, enrollment.course_code)
            self.app.changed(f"Dropped {enrollment.course_code}")

    def enter_marks(self) -> None:
        """Open a dialog to enter or edit marks for each component of the selected enrolment."""
        student, enrollment = self.current_student(), self.current_enrollment()
        if not student or not enrollment:
            return
        course = enrollment.course
        # One field per grading component, pre-filled with any existing mark.
        fields = []
        for comp in course.components:
            score = enrollment.score(comp.component_id)
            fields.append(Field(comp.component_id, f"{comp.name}  ({comp.weight:g}%)",
                                fmt(score) if score is not None else "",
                                hint=f"out of {comp.max_marks:g}"))

        def submit(v: Dict[str, str]) -> None:
            # Empty boxes become None, meaning "not marked yet".
            scores = {comp.component_id: (to_float(v[comp.component_id], comp.name)
                                          if v[comp.component_id] else None)
                      for comp in course.components}
            self.manager.set_scores(student.student_id, course.code, scores)
            self.app.changed(f"Saved marks for {student.name} in {course.code}")

        FormDialog(self.app, f"Marks - {student.name} / {course.code}", fields, submit,
                   ok_text="Save marks", subtitle="Leave a box empty if that item has not been marked yet.")