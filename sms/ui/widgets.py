"""Reusable styled widgets: cards, stat cards, charts, chips, trees, dialogs."""
from __future__ import annotations

import tkinter as tk
from dataclasses import dataclass
from tkinter import messagebox, ttk
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from sms.exceptions import SMSError
from sms.ui import theme as T


# --------------------------------------------------------------------------
# Containers
# --------------------------------------------------------------------------
class Card(tk.Frame):
    """White rounded-looking panel with an optional title row and action area."""

    def __init__(self, parent, title: str = "", padding: int = 14):
        super().__init__(parent, bg=T.CARD, highlightbackground=T.BORDER, highlightthickness=1)
        self.title_var = tk.StringVar(value=title)
        self.actions: Optional[tk.Frame] = None
        if title:
            head = tk.Frame(self, bg=T.CARD)
            head.pack(fill="x", padx=padding, pady=(padding - 2, 0))
            tk.Label(head, textvariable=self.title_var, bg=T.CARD, fg=T.TEXT,
                     font=T.font("h2")).pack(side="left")
            self.actions = tk.Frame(head, bg=T.CARD)
            self.actions.pack(side="right")
        self.body = tk.Frame(self, bg=T.CARD)
        self.body.pack(fill="both", expand=True, padx=padding, pady=padding)

    def set_title(self, text: str) -> None:
        self.title_var.set(text)


class StatCard(tk.Frame):
    """Big number with a coloured accent stripe."""

    def __init__(self, parent, title: str, color: str):
        super().__init__(parent, bg=T.CARD, highlightbackground=T.BORDER, highlightthickness=1)
        tk.Frame(self, bg=color, width=6).pack(side="left", fill="y")
        inner = tk.Frame(self, bg=T.CARD)
        inner.pack(side="left", fill="both", expand=True, padx=14, pady=12)
        self.value = tk.StringVar(value="-")
        self.sub = tk.StringVar(value="")
        tk.Label(inner, text=title.upper(), bg=T.CARD, fg=T.MUTED, font=T.font("small")).pack(anchor="w")
        tk.Label(inner, textvariable=self.value, bg=T.CARD, fg=color, font=T.font("big")).pack(anchor="w")
        tk.Label(inner, textvariable=self.sub, bg=T.CARD, fg=T.MUTED, font=T.font("small")).pack(anchor="w")

    def set(self, value: str, sub: str = "") -> None:
        self.value.set(value)
        self.sub.set(sub)


def chip(parent, text: str, color: str, bg: str = T.CARD) -> tk.Label:
    """Small coloured pill label."""
    return tk.Label(parent, text=text, bg=color, fg="white", font=T.font("small"),
                    padx=9, pady=2)


# --------------------------------------------------------------------------
# Charts
# --------------------------------------------------------------------------
class BarChart(tk.Canvas):
    """Horizontal bar chart with per-bar colours."""

    ROW_H, PAD, LABEL_W, VALUE_W = 30, 8, 96, 84

    def __init__(self, parent, color: str = T.PRIMARY):
        super().__init__(parent, height=60, highlightthickness=0, bg=T.CARD)
        self.color = color
        self.items: List[Tuple[str, float]] = []
        self.colors: Optional[List[str]] = None
        self.max_value = 1.0
        self.fmt = "{:.1f}"
        self.bind("<Configure>", lambda _e: self.redraw())

    def set_data(self, items: Sequence[Tuple[str, float]], max_value: Optional[float] = None,
                 fmt: str = "{:.1f}", colors: Optional[Sequence[str]] = None) -> None:
        self.items = list(items)
        self.colors = list(colors) if colors else None
        self.fmt = fmt
        self.max_value = max_value or max((v for _, v in self.items), default=1) or 1
        self.configure(height=max(60, self.PAD * 2 + self.ROW_H * len(self.items)))
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        if not self.items:
            self.create_text(self.PAD, 30, text="No data yet", anchor="w", fill=T.MUTED, font=T.font())
            return
        bar_max = max(self.winfo_width() - self.LABEL_W - self.VALUE_W - 2 * self.PAD, 20)
        for i, (label, value) in enumerate(self.items):
            top = self.PAD + i * self.ROW_H
            mid = top + self.ROW_H / 2
            length = bar_max * min(value / self.max_value, 1)
            color = self.colors[i] if self.colors else self.color
            self.create_text(self.PAD, mid, text=label, anchor="w", fill=T.TEXT, font=T.font("bold"))
            self.create_rectangle(self.LABEL_W, top + 5, self.LABEL_W + bar_max, top + self.ROW_H - 7,
                                  fill="#eef1fa", width=0)
            if length > 0:
                self.create_rectangle(self.LABEL_W, top + 5, self.LABEL_W + max(length, 3),
                                      top + self.ROW_H - 7, fill=color, width=0)
            self.create_text(self.LABEL_W + bar_max + 10, mid, text=self.fmt.format(value),
                             anchor="w", fill=T.TEXT, font=T.font())


class WeightMeter(tk.Canvas):
    """Progress bar showing how much of a course's 100% has been allocated."""

    def __init__(self, parent):
        super().__init__(parent, height=44, highlightthickness=0, bg=T.CARD)
        self.total, self.target = 0.0, 100.0
        self.bind("<Configure>", lambda _e: self.redraw())

    def set(self, total: float, target: float = 100.0) -> None:
        self.total, self.target = total, target
        self.redraw()

    def redraw(self) -> None:
        self.delete("all")
        w = max(self.winfo_width(), 50)
        done = abs(self.total - self.target) < 1e-6
        color = T.SUCCESS if done else (T.DANGER if self.total > self.target else T.WARNING)
        self.create_rectangle(0, 4, w, 18, fill="#eef1fa", width=0)
        fill_w = w * min(self.total / self.target, 1) if self.target else 0
        if fill_w > 0:
            self.create_rectangle(0, 4, fill_w, 18, fill=color, width=0)
        if done:
            text = f"{self.total:g}% allocated - structure complete"
        elif self.total > self.target:
            text = f"{self.total:g}% allocated - over by {self.total - self.target:g}%"
        else:
            text = f"{self.total:g}% of {self.target:g}% allocated - {self.target - self.total:g}% still to add"
        self.create_text(0, 32, text=text, anchor="w", fill=color, font=T.font("bold"))


# --------------------------------------------------------------------------
# Tables
# --------------------------------------------------------------------------
def make_tree(parent, columns: Sequence[tuple], height: int = 8) -> Tuple[tk.Frame, ttk.Treeview]:
    """Create a styled Treeview with a scrollbar.

    `columns` items are (id, heading, width[, anchor]).
    """
    frame = tk.Frame(parent, bg=T.CARD)
    tree = ttk.Treeview(frame, columns=[c[0] for c in columns], show="headings",
                        height=height, selectmode="browse")
    for col in columns:
        cid, text, width = col[0], col[1], col[2]
        anchor = col[3] if len(col) > 3 else "w"
        tree.heading(cid, text=text, anchor="w" if anchor == "w" else "center")
        tree.column(cid, width=width, minwidth=40, anchor=anchor)
    scroll = ttk.Scrollbar(frame, orient="vertical", command=tree.yview)

    def on_scroll(first, last):  # only show the scrollbar when there is something to scroll
        if float(first) <= 0 and float(last) >= 1:
            scroll.pack_forget()
        elif not scroll.winfo_ismapped():
            scroll.pack(side="left", fill="y")
        scroll.set(first, last)

    tree.configure(yscrollcommand=on_scroll)
    tree.pack(side="left", fill="both", expand=True)
    tree.tag_configure("odd", background=T.STRIPE)
    tree.tag_configure("fail", foreground=T.DANGER)
    tree.tag_configure("good", foreground=T.SUCCESS)
    tree.tag_configure("muted", foreground=T.MUTED)
    return frame, tree


def fill_tree(tree: ttk.Treeview, rows: Sequence[Tuple[str, Sequence, Sequence[str]]]) -> None:
    """Replace the rows (iid, values, tags) and restore the previous selection."""
    selected = tree.selection()
    tree.delete(*tree.get_children())
    for i, (iid, values, tags) in enumerate(rows):
        row_tags = list(tags) + (["odd"] if i % 2 else [])
        tree.insert("", "end", iid=iid, values=list(values), tags=row_tags)
    for iid in selected:
        if tree.exists(iid):
            tree.selection_set(iid)


def button(parent, text: str, command: Callable, kind: str = "Secondary") -> ttk.Button:
    return ttk.Button(parent, text=text, style=f"{kind}.TButton", command=command, cursor="arrow")


# --------------------------------------------------------------------------
# Dialog
# --------------------------------------------------------------------------
@dataclass
class Field:
    key: str
    label: str
    initial: str = ""
    choices: Optional[Sequence[str]] = None  # drop-down when given
    hint: str = ""


class FormDialog(tk.Toplevel):
    """Modal form. `submit(values)` may raise to keep the dialog open."""

    def __init__(self, parent: tk.Misc, title: str, fields: Sequence[Field],
                 submit: Callable[[Dict[str, str]], None], ok_text: str = "Save", subtitle: str = ""):
        super().__init__(parent, bg=T.CARD)
        self.title(title)
        self.transient(parent)
        self.resizable(False, False)
        self._submit = submit
        self._vars: Dict[str, tk.StringVar] = {}

        head = tk.Frame(self, bg=T.PRIMARY)
        head.pack(fill="x")
        tk.Label(head, text=title, bg=T.PRIMARY, fg="white", font=T.font("h2"),
                 padx=20, pady=14).pack(anchor="w")

        body = tk.Frame(self, bg=T.CARD, padx=20, pady=14)
        body.pack(fill="both")
        row = 0
        if subtitle:
            tk.Label(body, text=subtitle, bg=T.CARD, fg=T.MUTED, wraplength=420,
                     justify="left").grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 8))
            row += 1

        first = None
        for f in fields:
            pad = (6, 0 if f.hint else 6)
            tk.Label(body, text=f.label, bg=T.CARD, fg=T.TEXT, anchor="w").grid(
                row=row, column=0, sticky="w", padx=(0, 16), pady=pad)
            var = tk.StringVar(value=f.initial)
            if f.choices is not None:
                widget = ttk.Combobox(body, textvariable=var, values=list(f.choices),
                                      state="readonly", width=36)
                if not f.initial and f.choices:
                    var.set(f.choices[0])
            else:
                widget = ttk.Entry(body, textvariable=var, width=38)
            widget.grid(row=row, column=1, pady=pad)
            self._vars[f.key] = var
            first = first or widget
            row += 1
            if f.hint:
                tk.Label(body, text=f.hint, bg=T.CARD, fg=T.MUTED, font=T.font("small"),
                         wraplength=300, justify="left").grid(row=row, column=1, sticky="w", pady=(2, 6))
                row += 1

        buttons = tk.Frame(body, bg=T.CARD)
        buttons.grid(row=row, column=0, columnspan=2, sticky="e", pady=(14, 0))
        button(buttons, ok_text, self._on_ok, "Primary").pack(side="right")
        button(buttons, "Cancel", self.destroy, "Ghost").pack(side="right", padx=(0, 8))

        self.bind("<Return>", lambda _e: self._on_ok())
        self.bind("<Escape>", lambda _e: self.destroy())
        self.update_idletasks()
        x = parent.winfo_rootx() + (parent.winfo_width() - self.winfo_width()) // 2
        y = parent.winfo_rooty() + (parent.winfo_height() - self.winfo_height()) // 3
        self.geometry(f"+{max(x, 0)}+{max(y, 0)}")
        try:
            self.grab_set()
        except tk.TclError:
            pass
        if first:
            first.focus_set()

    def _on_ok(self) -> None:
        values = {k: v.get().strip() for k, v in self._vars.items()}
        try:
            self._submit(values)
        except SMSError as exc:
            messagebox.showerror("Error", str(exc), parent=self)
        except ValueError as exc:
            messagebox.showerror("Invalid input", str(exc), parent=self)
        else:
            self.destroy()
