"""Main window: sidebar navigation + pages."""
from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import Dict, Optional

from sms.config import DATA_FILE
from sms.exceptions import SMSError
from sms.services.student_manager import StudentManager
from sms.storage.json_storage import JSONStorage
from sms.ui import theme as T
from sms.ui.pages.base import Page
from sms.ui.pages.courses_page import CoursesPage
from sms.ui.pages.dashboard_page import DashboardPage
from sms.ui.pages.students_page import StudentsPage
from sms.ui.widgets import button

APP_TITLE = "Student Management System"


class NavButton(tk.Frame):
    """Sidebar entry with a hover effect and an accent stripe when active."""

    def __init__(self, parent, text: str, command):
        super().__init__(parent, bg=T.SIDEBAR, cursor="arrow")
        self.stripe = tk.Frame(self, width=4, bg=T.SIDEBAR)
        self.stripe.pack(side="left", fill="y")
        self.label = tk.Label(self, text=text, bg=T.SIDEBAR, fg="#c5cdea", anchor="w",
                              font=T.font("nav"), padx=18, pady=12)
        self.label.pack(side="left", fill="x", expand=True)
        self.active = False
        for widget in (self, self.label):
            widget.bind("<Button-1>", lambda _e: command())
            widget.bind("<Enter>", lambda _e: self._paint(hover=True))
            widget.bind("<Leave>", lambda _e: self._paint(hover=False))

    def set_active(self, active: bool) -> None:
        self.active = active
        self._paint()

    def _paint(self, hover: bool = False) -> None:
        bg = T.SIDEBAR_HOVER if (self.active or hover) else T.SIDEBAR
        self.configure(bg=bg)
        self.label.configure(bg=bg, fg="white" if self.active else "#c5cdea")
        self.stripe.configure(bg=T.PRIMARY if self.active else bg)


class MainWindow(tk.Tk):
    def __init__(self, manager: StudentManager):
        super().__init__()
        self.students = manager
        self.dirty = False
        self.title(APP_TITLE)
        self.geometry("1360x820")
        self.minsize(1180, 700)
        T.apply_theme(self)

        self._build_sidebar()
        self._build_content()
        self._build_menu()
        self.bind("<Control-s>", lambda _e: self.save())
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self._load_initial()

    # ---- layout --------------------------------------------------------------
    def _build_sidebar(self) -> None:
        side = tk.Frame(self, bg=T.SIDEBAR, width=230)
        side.pack(side="left", fill="y")
        side.pack_propagate(False)

        brand = tk.Frame(side, bg=T.SIDEBAR)
        brand.pack(fill="x", padx=20, pady=(26, 24))
        tk.Label(brand, text="Student", bg=T.SIDEBAR, fg="white", font=T.font("brand")).pack(anchor="w")
        tk.Label(brand, text="Management System", bg=T.SIDEBAR, fg="#8fa0d6").pack(anchor="w")

        self.nav: Dict[str, NavButton] = {}
        for key, label in [("dashboard", "Dashboard"), ("courses", "Courses"), ("students", "Students")]:
            btn = NavButton(side, label, lambda k=key: self.show(k))
            btn.pack(fill="x")
            self.nav[key] = btn

        bottom = tk.Frame(side, bg=T.SIDEBAR)
        bottom.pack(side="bottom", fill="x", padx=18, pady=20)
        self.dirty_var = tk.StringVar(value="All changes saved")
        self.dirty_label = tk.Label(bottom, textvariable=self.dirty_var, bg=T.SIDEBAR, fg="#8fa0d6")
        self.dirty_label.pack(anchor="w", pady=(0, 8))
        button(bottom, "Save", self.save, "Primary").pack(fill="x")

    def _build_content(self) -> None:
        content = tk.Frame(self, bg=T.BG)
        content.pack(side="left", fill="both", expand=True)

        self.status = tk.StringVar(value="Ready")
        tk.Label(content, textvariable=self.status, bg="#e9edf8", fg=T.MUTED, anchor="w",
                 padx=16, pady=5).pack(side="bottom", fill="x")

        stack = tk.Frame(content, bg=T.BG)
        stack.pack(fill="both", expand=True)
        stack.rowconfigure(0, weight=1)
        stack.columnconfigure(0, weight=1)
        self.pages: Dict[str, Page] = {
            "dashboard": DashboardPage(stack, self),
            "courses": CoursesPage(stack, self),
            "students": StudentsPage(stack, self),
        }
        for page in self.pages.values():
            page.grid(row=0, column=0, sticky="nsew")

    def _build_menu(self) -> None:
        menubar = tk.Menu(self)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save)
        file_menu.add_command(label="Reload from file", command=self.reload)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_close)
        menubar.add_cascade(label="File", menu=file_menu)
        self.config(menu=menubar)

    # ---- navigation ------------------------------------------------------------
    def show(self, key: str) -> None:
        self.pages[key].tkraise()
        self.pages[key].refresh()
        for name, btn in self.nav.items():
            btn.set_active(name == key)

    def go_student(self, student_id: str, course_code: Optional[str] = None) -> None:
        self.show("students")
        self.pages["students"].select(student_id, course_code)

    # ---- state -------------------------------------------------------------------
    def _load_initial(self) -> None:
        try:
            count = self.students.load()
            self.status.set(f"Loaded {len(self.students.courses)} course(s) and {count} student(s) "
                            f"from {DATA_FILE.name}")
        except SMSError as exc:
            messagebox.showwarning("Load problem", str(exc), parent=self)
        self.show("dashboard")

    def refresh_all(self) -> None:
        for page in self.pages.values():
            page.refresh()

    def _set_dirty(self, dirty: bool) -> None:
        self.dirty = dirty
        self.title(APP_TITLE + (" *" if dirty else ""))
        self.dirty_var.set("Unsaved changes" if dirty else "All changes saved")
        self.dirty_label.configure(fg=T.WARNING if dirty else "#8fa0d6")

    def changed(self, message: str) -> None:
        """Pages call this after modifying data."""
        self._set_dirty(True)
        self.refresh_all()
        self.status.set(message)

    # ---- file actions ---------------------------------------------------------------
    def save(self) -> bool:
        try:
            self.students.save()
        except SMSError as exc:
            messagebox.showerror("Save failed", str(exc), parent=self)
            return False
        self._set_dirty(False)
        self.status.set(f"Saved to {DATA_FILE.name}")
        return True

    def reload(self) -> None:
        if self.dirty and not messagebox.askyesno(
                "Reload", "Unsaved changes will be lost. Continue?", parent=self):
            return
        try:
            count = self.students.load()
        except SMSError as exc:
            messagebox.showerror("Load failed", str(exc), parent=self)
            return
        self._set_dirty(False)
        self.refresh_all()
        self.status.set(f"Reloaded {count} student(s)")

    def on_close(self) -> None:
        if self.dirty:
            answer = messagebox.askyesnocancel("Unsaved changes", "Save changes before exiting?", parent=self)
            if answer is None:
                return
            if answer and not self.save():
                return
        self.destroy()


def run() -> None:
    MainWindow(StudentManager(JSONStorage(DATA_FILE))).mainloop()
