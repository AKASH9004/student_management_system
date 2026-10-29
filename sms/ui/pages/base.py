"""Base class shared by all pages."""
import tkinter as tk

from sms.ui import theme as T


class Page(tk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, bg=T.BG)
        self.app = app
        self.manager = app.students
        self.courses = app.students.courses

    def header(self, title: str, subtitle: str = "") -> tk.Frame:
        """Page title row. Returns the frame on the right where action buttons go."""
        bar = tk.Frame(self, bg=T.BG)
        bar.pack(fill="x", padx=24, pady=(20, 14))
        left = tk.Frame(bar, bg=T.BG)
        left.pack(side="left")
        tk.Label(left, text=title, bg=T.BG, fg=T.TEXT, font=T.font("h1")).pack(anchor="w")
        if subtitle:
            tk.Label(left, text=subtitle, bg=T.BG, fg=T.MUTED).pack(anchor="w")
        actions = tk.Frame(bar, bg=T.BG)
        actions.pack(side="right")
        return actions

    def refresh(self) -> None:  # overridden
        pass
