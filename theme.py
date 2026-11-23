"""Colours, fonts and widget styles shared by every Clicker Bot window.

The values follow the Lovable design preview (project "Clicker Bot"). Change a colour or size
here and both the main window and the recording inspector pick it up.
"""
import tkinter as tk
from tkinter import font as tkfont, ttk

WHITE = "#ffffff"
INK = "#302a29"
MUTED = "#675f5c"
HINT = "#a29b96"
RED = "#c23430"
RED_HOVER = "#a62c28"
RED_TINT = "#fdf7f6"        # hover behind red text
SELECTED = "#fdf1ef"        # selected sidebar item, table row, active badge
SELECTED_BORDER = "#eea19a"
BORDER = "#e4dfdb"          # dividers, cards, outlined buttons
FIELD_BORDER = "#ded7d3"    # text fields
BAR = "#f6f5f4"             # breadcrumb bar, table header
SIDEBAR = "#faf9f8"
MUTED_SURFACE = "#f8f7f6"   # disabled cards and fields
DISABLED = "#eeeae8"
SUCCESS = "#277b43"
SUCCESS_SURFACE = "#edf8ef"

FAMILY = "Helvetica"
ACTION_LABELS = {"click": "Tıklama", "input": "Yazı", "select": "Liste seçimi",
                 "keydown": "Enter", "password": "Parola"}


def font(size, bold=False):
    return (FAMILY, size, "bold" if bold else "normal")


def mono(size=12):
    return (tkfont.nametofont("TkFixedFont").actual("family"), size)


def apply(root):
    """Configure the ttk styles once per Tk root."""
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=WHITE)
    style.configure("TLabel", background=WHITE, foreground=INK)
    style.configure("Muted.TLabel", background=WHITE, foreground=MUTED)
    style.configure("TRadiobutton", background=WHITE, foreground=INK)
    style.configure("TEntry", fieldbackground=WHITE, foreground=INK, padding=9)
    style.map("TEntry", bordercolor=[("focus", RED)])

    # Sizes from the Lovable inspector: main window 48px, footer actions 38px, step toolbar 32px.
    for size, font_size, padding in (("", 13, (12, 8)), ("Medium.", 12, (14, 9)), ("Small.", 11, (12, 7))):
        for kind, background, foreground, hover in (
            ("Primary", RED, WHITE, RED_HOVER),
            ("Outline", WHITE, INK, MUTED_SURFACE),
            ("Text", WHITE, RED, RED_TINT),
        ):
            name = f"{size}{kind}.TButton"
            style.configure(name, background=background, foreground=foreground, font=font(font_size, True),
                            padding=padding, relief="flat", borderwidth=0, focuscolor=background)
            disabled_bg = WHITE if kind == "Text" else DISABLED if kind == "Primary" else MUTED_SURFACE
            style.map(name, background=[("disabled", disabled_bg), ("active", hover)],
                      foreground=[("disabled", HINT)])

    style.configure("Steps.Treeview", background=WHITE, fieldbackground=WHITE, foreground=INK,
                    font=font(12), rowheight=40, borderwidth=0, relief="flat")
    style.map("Steps.Treeview", background=[("selected", SELECTED)], foreground=[("selected", INK)])
    style.configure("Steps.Treeview.Heading", background=BAR, foreground=MUTED, font=font(10, True),
                    relief="flat", borderwidth=0, padding=(10, 9))
    style.map("Steps.Treeview.Heading", background=[("active", BAR)])
    style.layout("Steps.Treeview", [("Steps.Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Vertical.TScrollbar", background=BAR, troughcolor=WHITE, bordercolor=WHITE,
                    arrowcolor=MUTED, relief="flat")
    return style


def bordered(parent, color=FIELD_BORDER, bg=WHITE):
    """A 1px border drawn with a frame; Tk on macOS does not draw highlight borders reliably.

    Returns (outer, inner): place the outer frame, put content into the inner one.
    """
    outer = tk.Frame(parent, bg=color)
    inner = tk.Frame(outer, bg=bg)
    inner.pack(fill="both", expand=True, padx=1, pady=1)
    return outer, inner


def button(parent, text, command, kind="Primary", size=""):
    """A themed button. Returns (holder, button): place the holder, enable/disable the button.

    Outline buttons sit in a bordered holder so their 1px border is visible on macOS.
    """
    style = f"{size}{kind}.TButton"  # size: "" (main window), "Medium." or "Small."
    if kind == "Outline":
        holder, inner = bordered(parent, BORDER)
        widget = ttk.Button(inner, text=text, command=command, style=style)
        widget.pack(fill="both", expand=True)
    else:
        holder = tk.Frame(parent, bg=WHITE)
        widget = ttk.Button(holder, text=text, command=command, style=style)
        widget.pack(fill="both", expand=True)
    return holder, widget


def entry(parent, value="", **options):
    """A text field styled like the main window's URL field. Returns (holder, entry)."""
    holder, inner = bordered(parent, FIELD_BORDER)
    widget = tk.Entry(inner, relief="flat", bg=WHITE, fg=INK, insertbackground=INK, highlightthickness=0,
                      disabledbackground=MUTED_SURFACE, disabledforeground=MUTED, font=font(13), **options)
    widget.pack(fill="x", padx=10, ipady=8)
    widget.insert(0, value)
    widget.bind("<FocusIn>", lambda _: holder.configure(bg=RED), add="+")
    widget.bind("<FocusOut>", lambda _: holder.configure(bg=FIELD_BORDER), add="+")
    return holder, widget


def badge(parent, text="", active=False):
    """A small rounded-looking tag, neutral or red-tinted."""
    return tk.Label(parent, text=text, padx=8, pady=3, font=font(11, True),
                    bg=SELECTED if active else BAR, fg=RED if active else MUTED)


def divider(parent, **pack):
    line = tk.Frame(parent, height=1, bg=BORDER)
    line.pack(fill="x", **pack)
    return line
