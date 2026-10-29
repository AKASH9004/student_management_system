"""Colours, fonts and ttk styling for the whole application."""
import tkinter.font as tkfont
from tkinter import ttk

# ---- palette ---------------------------------------------------------------
BG = "#f3f5fb"
SIDEBAR = "#1b2540"
SIDEBAR_HOVER = "#27345a"
CARD = "#ffffff"
BORDER = "#e3e7f1"
STRIPE = "#f7f8fd"
TEXT = "#1f2937"
MUTED = "#6b7280"
PRIMARY = "#4f6df5"
PRIMARY_DARK = "#002aff"
PRIMARY_LIGHT = "#e3e9ff"
SUCCESS = "#12a150"
DANGER = "#e5484d"
WARNING = "#f59e0b"
INFO = "#0ea5e9"
PURPLE = "#8b5cf6"

GRADE_COLORS = {"A+": "#0f9d58", "A": "#67c680", "B": "#4f6df5", "C": "#0ea5e9",
                "D": "#f59e0b", "E": "#fb923c", "F": "#e5484d", "N/A": "#9ca3af"}

_family = "TkDefaultFont"
_SIZES = {"body": (10, ""), "small": (9, ""), "bold": (10, "bold"), "h1": (20, "bold"),
          "h2": (13, "bold"), "big": (24, "bold"), "brand": (16, "bold"), "nav": (11, "")}


def font(kind: str = "body"):
    size, weight = _SIZES[kind]
    return (_family, size, weight) if weight else (_family, size)


def apply_theme(root) -> None:
    global _family
    root.configure(bg=BG)
    _family = tkfont.nametofont("TkDefaultFont").actual("family")
    for name in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont"):
        tkfont.nametofont(name).configure(size=10)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure(".", background=BG, foreground=TEXT, font=font("body"))

    def button(name, bg, fg, active, disabled):
        style.configure(name, background=bg, foreground=fg, padding=(14, 7), borderwidth=0,
                        focusthickness=0, font=font("bold"), relief="flat")
        style.map(name, background=[("disabled", disabled), ("pressed", active), ("active", active)],
                  foreground=[("disabled", "#ffffff")])

    button("Primary.TButton", PRIMARY, "white", PRIMARY_DARK, "#aab6fa")
    button("Secondary.TButton", "#e8ecfa", PRIMARY_DARK, "#d6ddf6", "#f0f2fa")
    button("Danger.TButton", "#fde8e8", DANGER, "#fbd0d0", "#f8eeee")
    button("Ghost.TButton", CARD, MUTED, "#eef1fa", CARD)

    for name in ("TEntry", "TCombobox"):
        style.configure(name, fieldbackground="white", bordercolor=BORDER, lightcolor=BORDER,
                        darkcolor=BORDER, padding=6)
        style.map(name, bordercolor=[("focus", PRIMARY)], lightcolor=[("focus", PRIMARY)],
                  darkcolor=[("focus", PRIMARY)])
    style.map("TCombobox", fieldbackground=[("readonly", "white")],
              selectbackground=[("readonly", "white")], selectforeground=[("readonly", TEXT)])
    root.option_add("*TCombobox*Listbox.selectBackground", PRIMARY)

    style.layout("Treeview", [("Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Treeview", background=CARD, fieldbackground=CARD, foreground=TEXT,
                    rowheight=30, borderwidth=0)
    style.map("Treeview", background=[("selected", PRIMARY_LIGHT)],
              foreground=[("selected", TEXT)])
    style.configure("Treeview.Heading", background="#eef1fa", foreground=MUTED, relief="flat",
                    font=font("bold"), padding=(8, 7), borderwidth=0)
    style.map("Treeview.Heading", background=[("active", "#e2e7f6")])

    style.configure("Vertical.TScrollbar", background="#cdd4ea", troughcolor="#f0f2f9",
                    bordercolor="#f0f2f9", arrowcolor=MUTED, relief="flat")
    style.map("Vertical.TScrollbar", background=[("active", "#b8c1df")])
