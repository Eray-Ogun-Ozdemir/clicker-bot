"""Colours, fonts and widget styles shared by every Clicker Bot window.

The values follow the Lovable design preview (project "Clicker Bot"). Change a colour or size
here and every window picks it up. There is a light and a dark palette with the same names;
apply() picks one from the operating system's appearance before any widget is created.
Set CLICKER_BOT_THEME=light or =dark to override the system setting.
"""
import os
import subprocess
import sys
import tkinter as tk
from tkinter import font as tkfont, ttk

LIGHT = {
    "BG": "#ffffff",               # window and field background
    "INK": "#302a29",              # main text
    "MUTED": "#675f5c",            # secondary text
    "HINT": "#a29b96",             # placeholders, disabled text
    "RED": "#c23430",              # accent text, focus and error borders
    "PRIMARY": "#c23430",          # primary button background
    "PRIMARY_HOVER": "#a62c28",
    "ON_PRIMARY": "#ffffff",       # text on primary buttons
    "RED_TINT": "#fdf7f6",         # hover behind red text
    "SELECTED": "#fdf1ef",         # selected sidebar item, table row, active badge
    "SELECTED_BORDER": "#eea19a",
    "CARD_SELECTED": "#fff8f7",    # selected method card
    "CARD_DISABLED_TEXT": "#938d88",
    "BORDER": "#e4dfdb",           # dividers, cards, outlined buttons
    "FIELD_BORDER": "#ded7d3",     # text fields
    "BADGE_RING": "#ddd6d2",       # numbered section badges
    "SLASH": "#b3ada8",            # breadcrumb separator
    "BAR": "#f6f5f4",              # breadcrumb bar, table header
    "SIDEBAR": "#faf9f8",
    "MUTED_SURFACE": "#f8f7f6",    # disabled cards and fields
    "DISABLED": "#eeeae8",
    "SUCCESS": "#277b43",
    "SUCCESS_SURFACE": "#edf8ef",
}
DARK = {
    "BG": "#1f1b1a",
    "INK": "#f2ece9",
    "MUTED": "#b0a7a3",
    "HINT": "#857d79",
    "RED": "#f0726a",
    "PRIMARY": "#c23430",
    "PRIMARY_HOVER": "#a82c28",
    "ON_PRIMARY": "#ffffff",
    "RED_TINT": "#2d2120",
    "SELECTED": "#3a2422",
    "SELECTED_BORDER": "#8a3f39",
    "CARD_SELECTED": "#2f2120",
    "CARD_DISABLED_TEXT": "#8f8783",
    "BORDER": "#3a3331",
    "FIELD_BORDER": "#4a4240",
    "BADGE_RING": "#4a4240",
    "SLASH": "#6f6763",
    "BAR": "#282322",
    "SIDEBAR": "#241f1e",
    "MUTED_SURFACE": "#2a2524",
    "DISABLED": "#332d2b",
    "SUCCESS": "#7fd39a",
    "SUCCESS_SURFACE": "#1d3324",
}
DARK_MODE = False
globals().update(LIGHT)


def use_palette(dark):
    """Switch the module's colour names to the light or dark palette."""
    global DARK_MODE
    DARK_MODE = dark
    globals().update(DARK if dark else LIGHT)


def system_prefers_dark(root=None):
    """Whether the operating system (or CLICKER_BOT_THEME) asks for dark mode."""
    choice = os.environ.get("CLICKER_BOT_THEME", "").strip().lower()
    if choice in ("light", "dark"):
        return choice == "dark"
    if sys.platform == "darwin":
        try:  # set by both the "Koyu" and the "Otomatik" appearance while it is dark
            style = subprocess.run(["defaults", "read", "-g", "AppleInterfaceStyle"],
                                   capture_output=True, text=True, timeout=2).stdout
            if "dark" in style.lower():
                return True
        except (OSError, subprocess.SubprocessError):
            pass
        if root is not None:
            try:
                return bool(int(root.tk.call("::tk::unsupported::MacWindowStyle", "isdark", root)))
            except (tk.TclError, ValueError):
                pass
    elif sys.platform == "win32":
        try:
            import winreg
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                                r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize") as key:
                return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
        except OSError:
            pass
    return False


FAMILY = "Helvetica"
ACTION_LABELS = {"click": "Tıklama", "input": "Yazı", "select": "Liste seçimi",
                 "keydown": "Enter", "password": "Parola"}


def font(size, bold=False):
    return (FAMILY, size, "bold" if bold else "normal")


def mono(size=12):
    return (tkfont.nametofont("TkFixedFont").actual("family"), size)


def apply(root):
    """Pick the palette from the system appearance and configure the ttk styles. Call it first."""
    use_palette(system_prefers_dark(root))
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=INK)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED)
    style.configure("TRadiobutton", background=BG, foreground=INK)
    # clam draws entry borders from bordercolor plus light/dark bevel colours; tie all three to the palette.
    style.configure("TEntry", fieldbackground=BG, foreground=INK, insertcolor=INK, padding=9,
                    bordercolor=FIELD_BORDER, lightcolor=BG, darkcolor=BG)
    style.map("TEntry", bordercolor=[("focus", RED)], lightcolor=[("focus", BG)],
              fieldbackground=[("disabled", MUTED_SURFACE)], foreground=[("disabled", HINT)])

    # Sizes from the Lovable inspector: main window 48px, footer actions 38px, step toolbar 32px.
    for size, font_size, padding in (("", 13, (12, 8)), ("Medium.", 12, (14, 9)), ("Small.", 11, (12, 7))):
        for kind, background, foreground, hover in (
            ("Primary", PRIMARY, ON_PRIMARY, PRIMARY_HOVER),
            ("Outline", BG, INK, MUTED_SURFACE),
            ("Text", BG, RED, RED_TINT),
        ):
            name = f"{size}{kind}.TButton"
            style.configure(name, background=background, foreground=foreground, font=font(font_size, True),
                            padding=padding, relief="flat", borderwidth=0, focuscolor=background)
            disabled_bg = BG if kind == "Text" else DISABLED if kind == "Primary" else MUTED_SURFACE
            style.map(name, background=[("disabled", disabled_bg), ("active", hover)],
                      foreground=[("disabled", HINT)])

    style.configure("Steps.Treeview", background=BG, fieldbackground=BG, foreground=INK,
                    font=font(12), rowheight=40, borderwidth=0, relief="flat")
    style.map("Steps.Treeview", background=[("selected", SELECTED)], foreground=[("selected", INK)])
    style.configure("Steps.Treeview.Heading", background=BAR, foreground=MUTED, font=font(10, True),
                    relief="flat", borderwidth=0, padding=(10, 9))
    style.map("Steps.Treeview.Heading", background=[("active", BAR)])
    style.layout("Steps.Treeview", [("Steps.Treeview.treearea", {"sticky": "nswe"})])
    style.configure("Vertical.TScrollbar", background=BAR, troughcolor=BG, bordercolor=BG,
                    arrowcolor=MUTED, relief="flat")
    return style


def bordered(parent, color=None, bg=None):
    """A 1px border drawn with a frame; Tk on macOS does not draw highlight borders reliably.

    Returns (outer, inner): place the outer frame, put content into the inner one.
    """
    outer = tk.Frame(parent, bg=color or FIELD_BORDER)  # defaults read at call time: palette may change
    inner = tk.Frame(outer, bg=bg or BG)
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
        holder = tk.Frame(parent, bg=BG)
        widget = ttk.Button(holder, text=text, command=command, style=style)
        widget.pack(fill="both", expand=True)
    return holder, widget


def entry(parent, value="", **options):
    """A text field styled like the main window's URL field. Returns (holder, entry)."""
    holder, inner = bordered(parent, FIELD_BORDER)
    widget = tk.Entry(inner, relief="flat", bg=BG, fg=INK, insertbackground=INK, highlightthickness=0,
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
