"""Courses: create courses, design their grade structure, enrol students."""
import tkinter as tk
from tkinter import messagebox
from typing import Dict, Optional

from sms.models.course import Course
from sms.services.course_manager import parse_structure
from sms.ui import theme as T
from sms.ui.pages.base import Page
from sms.ui.utils import fmt, to_float
from sms.ui.widgets import (Card, Field, FormDialog, WeightMeter, button, chip, fill_tree, make_tree)

# Help text shown under the 'Grade structure' field of the New Course dialog.
STRUCTURE_HINT = ("Optional. Quick-add components as 'Name weight', separated by commas, e.g. "
                  "Lab 10, A1 7.5, Exam 50. Add '/20' if a mark is out of 20, e.g. Quiz 5/20.")


class CoursesPage(Page):
    """Page for managing courses: the list, each course's grade structure and its enrolled students."""

    def __init__(self, parent, app):
        """Build the page layout and wire up the buttons and table events.

        Args:
            parent: The container widget the page is placed in.
            app: The main application window.
        """
        super().__init__(parent, app)
        actions = self.header("Courses", "Design each course's grade structure, then enrol students")
        button(actions, "+ New Course", self.new_course, "Primary").pack(side="left")

        # Two columns: course list on the left (weight 3), details on the right (weight 4).
        body = tk.Frame(self, bg=T.BG)
        body.pack(fill="both", expand=True, padx=24, pady=(0, 16))
        body.columnconfigure(0, weight=3, uniform="c")
        body.columnconfigure(1, weight=4, uniform="c")
        body.rowconfigure(0, weight=1)

        # ---- left: course list
        left = Card(body, "All courses")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        frame, self.tree = make_tree(left.body, [
            ("code", "Code", 84), ("title", "Title", 120), ("weight", "Weight", 64, "center"),
            ("students", "Students", 70, "center")], height=14)
        frame.pack(fill="both", expand=True)
        # Selecting a course refreshes the details; the Delete key removes the selected course.
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self.refresh_detail())
        self.tree.bind("<Delete>", lambda _e: self.delete_course())
        row = tk.Frame(left.body, bg=T.CARD)
        row.pack(fill="x", pady=(10, 0))
        button(row, "Delete Course", self.delete_course, "Danger").pack(side="left")

        # ---- right: details
        right = tk.Frame(body, bg=T.BG)
        right.grid(row=0, column=1, sticky="nsew")

        info = Card(right)
        info.pack(fill="x")
        top = tk.Frame(info.body, bg=T.CARD)
        top.pack(fill="x")
        # Info card: course code, READY/INCOMPLETE chip, title and the weight meter.
        self.code_var, self.title_var = tk.StringVar(value="Select a course"), tk.StringVar()
        tk.Label(top, textvariable=self.code_var, bg=T.CARD, fg=T.PRIMARY, font=T.font("big")).pack(side="left")
        self.chip_box = tk.Frame(top, bg=T.CARD)
        self.chip_box.pack(side="left", padx=12)
        # The 'Edit Title' dialog lets you change the code as well as the title.
        self.edit_btn = button(top, "Edit Title", self.edit_title, "Secondary")
        self.edit_btn.pack(side="right")
        tk.Label(info.body, textvariable=self.title_var, bg=T.CARD, fg=T.MUTED, anchor="w").pack(fill="x")
        self.meter = WeightMeter(info.body)
        self.meter.pack(fill="x", pady=(8, 0))

        structure = Card(right, "Grade structure")
        structure.pack(fill="both", expand=True, pady=10)
        button(structure.actions, "+ Add", self.add_component, "Primary").pack(side="left")
        button(structure.actions, "Edit", self.edit_component, "Secondary").pack(side="left", padx=6)
        button(structure.actions, "Remove", self.remove_component, "Danger").pack(side="left")
        frame, self.comp_tree = make_tree(structure.body, [
            ("name", "Component", 190), ("weight", "Weight", 90, "center"),
            ("max", "Marked out of", 110, "center")], height=5)
        frame.pack(fill="both", expand=True)
        self.comp_tree.bind("<Double-1>", lambda _e: self.edit_component())

        enrolled = Card(right, "Enrolled students")
        enrolled.pack(fill="both", expand=True)
        # Summary line (enrolled count, average, passing) shown under the students table.
        self.stats_var = tk.StringVar()
        tk.Label(enrolled.body, textvariable=self.stats_var, bg=T.CARD, fg=T.MUTED,
                 anchor="w").pack(side="bottom", fill="x", pady=(6, 0))
        self.enrol_btn = button(enrolled.actions, "+ Enrol Student", self.enroll_student, "Primary")
        self.enrol_btn.pack(side="left")
        button(enrolled.actions, "Remove", self.remove_student, "Danger").pack(side="left", padx=(6, 0))
        frame, self.enrol_tree = make_tree(enrolled.body, [
            ("id", "ID", 60), ("name", "Student", 160), ("done", "Marked", 80, "center"),
            ("standing", "Result", 80, "center"), ("grade", "Grade", 60, "center")], height=5)
        frame.pack(fill="both", expand=True)
        # Double-click a student to open their record on the Students page.
        self.enrol_tree.bind("<Double-1>", self._open_student)

    # ---- selection helpers ----------------------------------------------
    def current_course(self) -> Optional[Course]:
        """Return the course selected in the list, or None if nothing is selected."""
        sel = self.tree.selection()
        return self.courses.get_course(sel[0]) if sel else None

    def _need_course(self) -> Optional[Course]:
        """Return the selected course, or show a hint and return None if none is selected."""
        course = self.current_course()
        if not course:
            messagebox.showinfo("Select a course", "Please select a course in the list first.", parent=self.app)
        return course

    def select(self, code: str) -> None:
        """Select (and scroll to) the course with this code, if it is in the list."""
        if self.tree.exists(code):
            self.tree.selection_set(code)
            self.tree.see(code)

    # ---- refresh -----------------------------------------------------------
    def refresh(self) -> None:
        """Rebuild the course list, keep a course selected and refresh the detail panels."""
        # Courses whose grade structure is not yet 100% are shown muted.
        fill_tree(self.tree, [
            (c.code, (c.code, c.title or "-", f"{c.total_weight:g}%",
                      len(self.manager.students_in_course(c.code))),
             () if c.is_ready else ("muted",))
            for c in self.courses.list_courses()])
        # Select the first course by default so the details are never empty.
        if not self.tree.selection() and self.tree.get_children():
            self.tree.selection_set(self.tree.get_children()[0])
        self.refresh_detail()

    def refresh_detail(self) -> None:
        """Update the info card, grade-structure table and enrolled-students table for the selected course."""
        course = self.current_course()
        for child in self.chip_box.winfo_children():
            child.destroy()
        # Buttons only work while a course is selected.
        state = "normal" if course else "disabled"
        self.edit_btn.configure(state=state)
        self.enrol_btn.configure(state=state)
        if not course:
            self.code_var.set("No course selected")
            self.title_var.set("Create a course with '+ New Course' to get started.")
            self.meter.set(0)
            fill_tree(self.comp_tree, [])
            fill_tree(self.enrol_tree, [])
            self.stats_var.set("")
            return

        # Info card: code, status chip and weight meter.
        self.code_var.set(course.code)
        self.title_var.set(course.title or "No title")
        chip(self.chip_box, "READY" if course.is_ready else "INCOMPLETE STRUCTURE",
             T.SUCCESS if course.is_ready else T.WARNING).pack()
        self.meter.set(course.total_weight)

        # Grade-structure table: one row per component.
        fill_tree(self.comp_tree, [
            (c.component_id, (c.name, f"{c.weight:g}%", f"{c.max_marks:g}"), ())
            for c in course.components])

        # Enrolled-students table with each student's progress, result and grade.
        students = self.manager.students_in_course(course.code)
        rows, marked = [], []
        for s in students:
            e = s.get_enrollment(course.code)
            # Highlight a failing result, but only once something has been marked.
            tags = () if not e.has_marks else (("fail",) if not e.has_passed else ())
            rows.append((s.student_id, (s.student_id, s.name,
                                        f"{e.progress:.0f}%", f"{e.standing:.1f}%" if e.has_marks else "-",
                                        e.grade), tags))
            if e.has_marks:
                marked.append(e)
        fill_tree(self.enrol_tree, rows)
        # Summary line: average result and pass count over students who have marks.
        if marked:
            avg = sum(e.standing for e in marked) / len(marked)
            passed = sum(1 for e in marked if e.has_passed)
            self.stats_var.set(f"{len(students)} enrolled  |  average {avg:.1f}%  |  {passed}/{len(marked)} passing")
        else:
            self.stats_var.set(f"{len(students)} enrolled  |  no marks entered yet")

    # ---- course actions ----------------------------------------------------
    def new_course(self) -> None:
        """Open the New Course dialog (code, title and optional quick-add grade structure)."""
        def submit(v: Dict[str, str]) -> None:
            """Create the course from the form values and select it."""
            # parse_structure turns the quick-add text (e.g. 'Lab 10, Exam 50') into component specs.
            course = self.courses.add_course(v["code"], v["title"], parse_structure(v["structure"]))
            self.app.changed(f"Created course {course.code}")
            self.select(course.code)

        FormDialog(self.app, "New Course", [
            Field("code", "Course code", hint="e.g. COMP1234"),
            Field("title", "Title"),
            Field("structure", "Grade structure", hint=STRUCTURE_HINT)], submit, ok_text="Create")

    def edit_title(self) -> None:
        """Open a dialog to edit the selected course's code and title."""
        course = self._need_course()
        if not course:
            return

        def submit(v: Dict[str, str]) -> None:
            """Apply the new code, then the new title, then refresh and re-select the course."""
            old_code = course.code

            # Update the course code first
            updated = self.courses.update_course_code(
                old_code,
                v["code"]
            )

            # Then update the title
            self.courses.update_title(
                updated.code,
                v["title"]
            )

            self.app.changed(f"Updated {updated.code}")

            # Refresh the course list and select the renamed course
            self.refresh()
            self.select(updated.code)

        fields = [
            Field("code", "Course code", course.code,
                hint="e.g. COMP1234"), 
            Field("title", "Title", course.title),
        ]

        FormDialog(
            self.app,
            f"Edit {course.code}",
            fields,
            submit,
            ok_text="Save"
        )


    def delete_course(self) -> None:
        """Delete the selected course after confirmation; enrolled students are dropped from it."""
        course = self._need_course()
        if not course:
            return
        count = len(self.manager.students_in_course(course.code))
        # Warn how many students will lose their marks (empty text when nobody is enrolled).
        extra = f"\n\n{count} student(s) will be removed from it and their marks lost." if count else ""
        if messagebox.askyesno("Delete course", f"Delete {course.code}?{extra}", parent=self.app):
            self.manager.delete_course(course.code)
            self.app.changed(f"Deleted course {course.code}")

    # ---- component actions -------------------------------------------------
    def _component_fields(self, name="", weight="", max_marks="100", remaining=None):
        """Build the form fields shared by the add and edit component dialogs.

        Args:
            name: Pre-filled component name.
            weight: Pre-filled weight (% of the course), as text.
            max_marks: Pre-filled 'marked out of' value, as text.
            remaining: Percentage of the course still unallocated; shown as a hint when given.
        """
        hint = f"{remaining:g}% of the course is still unallocated." if remaining is not None else ""
        return [Field("name", "Component name", name, hint="e.g. Lab, A1, Quiz 1, Exam"),
                Field("weight", "Weight (% of course)", weight, hint=hint),
                Field("max", "Marked out of", max_marks, hint="Raw marks are scaled to the weight.")]

    def add_component(self) -> None:
        """Open the dialog to add a component (e.g. Lab, Exam) to the selected course."""
        course = self._need_course()
        if not course:
            return

        def submit(v: Dict[str, str]) -> None:
            """Add the component using the form values (text converted to numbers)."""
            self.courses.add_component(course.code, v["name"], to_float(v["weight"], "Weight"),
                                       to_float(v["max"], "Marked out of"))
            self.app.changed(f"Added {v['name']} to {course.code}")

        FormDialog(self.app, f"Add component - {course.code}",
                   self._component_fields(remaining=course.remaining_weight), submit, ok_text="Add")

    def _selected_component(self, course: Course):
        """Return the component selected in the table, or show a hint and return None."""
        sel = self.comp_tree.selection()
        if not sel:
            messagebox.showinfo("Select a component", "Please select a component in the table first.",
                                parent=self.app)
            return None
        return course.get_component(sel[0])

    def edit_component(self) -> None:
        """Open the dialog to edit the component selected in the grade-structure table."""
        course = self._need_course()
        # 'course and ...' short-circuits to None when no course is selected.
        comp = course and self._selected_component(course)
        if not comp:
            return

        def submit(v: Dict[str, str]) -> None:
            """Save the edited name, weight and 'out of' value."""
            self.courses.update_component(course.code, comp.component_id, v["name"],
                                          to_float(v["weight"], "Weight"), to_float(v["max"], "Marked out of"))
            self.app.changed(f"Updated {v['name']} in {course.code}")

        FormDialog(self.app, f"Edit component - {course.code}",
                   self._component_fields(comp.name, fmt(comp.weight), fmt(comp.max_marks),
                                          remaining=course.remaining_weight), submit)

    def remove_component(self) -> None:
        """Remove the selected component after confirmation; marks entered for it are discarded."""
        course = self._need_course()
        comp = course and self._selected_component(course)
        if comp and messagebox.askyesno(
                "Remove component",
                f"Remove '{comp.name}' from {course.code}?\nMarks already entered for it will be discarded.",
                parent=self.app):
            self.courses.remove_component(course.code, comp.component_id)
            self.app.changed(f"Removed {comp.name} from {course.code}")

    # ---- enrolment actions ---------------------------------------------------
    def enroll_student(self) -> None:
        """Open the dialog to enrol a student in the selected course."""
        course = self._need_course()
        if not course:
            return
        # Students can only join a course whose components add up to 100%.
        if not course.is_ready:
            messagebox.showinfo(
                "Finish the grade structure",
                f"{course.code}'s components add up to {course.total_weight:g}%.\n"
                "Complete the structure to 100% before enrolling students.", parent=self.app)
            return
        # Students who are not already enrolled in this course.
        available = [s for s in self.manager.list_students() if not s.is_enrolled(course.code)]
        if not available:
            messagebox.showinfo("No students available", "Every student is already enrolled in this course "
                                "(or there are no students yet).", parent=self.app)
            return

        def submit(v: Dict[str, str]) -> None:
            """Enrol the chosen student."""
            # The dropdown shows 'ID - Name'; keep only the ID.
            sid = v["student"].split(" - ")[0]
            self.manager.enroll(sid, course.code)
            self.app.changed(f"Enrolled {sid} in {course.code}")

        FormDialog(self.app, f"Enrol student - {course.code}",
                   [Field("student", "Student", choices=[f"{s.student_id} - {s.name}" for s in available])],
                   submit, ok_text="Enrol")

    def remove_student(self) -> None:
        """Remove the selected student from the course after confirmation (their marks are lost)."""
        course = self._need_course()
        sel = self.enrol_tree.selection()
        # Show the 'select a student' hint only when a course is selected but no student row is.
        if not course or not sel:
            if course:
                messagebox.showinfo("Select a student", "Please select a student in the table first.",
                                    parent=self.app)
            return
        student = self.manager.get_student(sel[0])
        if messagebox.askyesno("Remove student", f"Remove {student.name} from {course.code}?\n"
                               "Their marks for this course will be lost.", parent=self.app):
            self.manager.drop(student.student_id, course.code)
            self.app.changed(f"Removed {student.name} from {course.code}")

    def _open_student(self, _event=None) -> None:
        """Jump to the double-clicked student's record on the Students page."""
        sel = self.enrol_tree.selection()
        course = self.current_course()
        if sel and course:
            self.app.go_student(sel[0], course.code)