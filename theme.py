"""Colours, fonts and widget styles shared by every Clicker Bot window.

The values follow the Lovable design preview (project "Clicker Bot"). Change a colour or size
here and every window picks it up. There is a light and a dark palette with the same names;
apply() picks one before any widget is created and switches live afterwards. The choice comes,
in order, from CLICKER_BOT_THEME=light/dark, the in-app "Görünüm" setting (Sistem / Açık / Koyu,
saved in settings.json in the user's application data folder), and the operating system.
"""
import json
import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
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
    "HINT": "#9a928e",
    "RED": "#f0726a",
    "PRIMARY": "#c23430",
    "PRIMARY_HOVER": "#a82c28",
    "ON_PRIMARY": "#ffffff",
    "RED_TINT": "#2d2120",
    "SELECTED": "#3a2422",
    "SELECTED_BORDER": "#8a3f39",
    "CARD_SELECTED": "#2f2120",
    "CARD_DISABLED_TEXT": "#9b938f",  # distinct from HINT so live switching maps it back correctly
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


PREFERENCES = ("system", "light", "dark")
PREFERENCE = "system"


def settings_path():
    if sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support" / "Clicker Bot"
    elif sys.platform == "win32":
        base = Path(os.environ.get("APPDATA") or Path.home()) / "Clicker Bot"
    else:
        base = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "clicker-bot"
    return base / "settings.json"


def _read_settings():
    try:
        data = json.loads(settings_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_preference():
    value = _read_settings().get("appearance")
    return value if value in PREFERENCES else "system"


def save_preference(value):
    data = _read_settings()
    data["appearance"] = value
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    temporary.replace(path)


def wants_dark(root=None):
    """The palette to show: CLICKER_BOT_THEME, then the in-app setting, then the system."""
    choice = os.environ.get("CLICKER_BOT_THEME", "").strip().lower()
    if choice in ("light", "dark"):
        return choice == "dark"
    if PREFERENCE in ("light", "dark"):
        return PREFERENCE == "dark"
    return system_prefers_dark(root)


def set_preference(root, value):
    """Apply the in-app "Görünüm" choice now and remember it for the next start."""
    global PREFERENCE
    if value not in PREFERENCES:
        return
    PREFERENCE = value
    try:
        save_preference(value)
    except OSError:
        pass  # cannot write the settings file: keep the choice for this session
    dark = wants_dark(root)
    if dark != DARK_MODE:
        switch_palette(root, dark)
    else:
        for callback in _listeners:
            callback()


def system_prefers_dark(root=None):
    """Whether the operating system is in dark mode."""
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


def font(size, bold=False):
    return (FAMILY, size, "bold" if bold else "normal")


def mono(size=12):
    return (tkfont.nametofont("TkFixedFont").actual("family"), size)


CHECK_EVERY_MS = 2000
COLOR_OPTIONS = ("background", "foreground", "highlightbackground", "highlightcolor", "insertbackground",
                 "disabledbackground", "disabledforeground", "selectbackground", "selectforeground",
                 "activebackground", "activeforeground", "readonlybackground")
_listeners = []


def apply(root):
    """Pick the palette from the system appearance, style ttk, and follow later appearance changes.

    Call it before creating any widget. While the app runs, the system appearance is checked every
    few seconds; when it changes, every window is repainted in place (see switch_palette).
    """
    global PREFERENCE
    PREFERENCE = load_preference()
    use_palette(wants_dark(root))
    style = _style(root)
    root.after(CHECK_EVERY_MS, lambda: _watch(root))
    return style


def on_palette_change(callback):
    """Call callback() after the palette or the appearance setting changes, e.g. to swap images."""
    _listeners.append(callback)


def _watch(root):
    try:
        dark = wants_dark(root)
        if dark != DARK_MODE:
            switch_palette(root, dark)
    finally:
        if root.winfo_exists():
            root.after(CHECK_EVERY_MS, lambda: _watch(root))


def switch_palette(root, dark):
    """Repaint every existing widget with the other palette, keeping all their contents and state."""
    old = DARK if DARK_MODE else LIGHT
    use_palette(dark)
    new = DARK if dark else LIGHT
    mapping = {}
    for key, value in old.items():  # first name wins where two names share a colour
        mapping.setdefault(value.lower(), new[key])
    _style(root)
    _recolor(root, mapping)
    for callback in _listeners:
        callback()


def _recolor(widget, mapping):
    for option in COLOR_OPTIONS:
        try:
            value = str(widget.cget(option)).lower()
        except tk.TclError:
            continue  # ttk widgets take most colours from their style instead
        if value in mapping:
            widget.configure({option: mapping[value]})
    if isinstance(widget, tk.Canvas):
        for item in widget.find_all():
            for option in ("fill", "outline"):
                try:
                    value = widget.itemcget(item, option).lower()
                except tk.TclError:
                    continue
                if value in mapping:
                    widget.itemconfigure(item, {option: mapping[value]})
    for child in widget.winfo_children():
        _recolor(child, mapping)


def _style(root):
    root.configure(bg=BG)
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=BG)
    style.configure("TLabel", background=BG, foreground=INK)
    style.configure("Muted.TLabel", background=BG, foreground=MUTED)
    style.configure("TRadiobutton", background=BG, foreground=INK)
    style.configure("TCheckbutton", background=BG, foreground=MUTED, font=font(12), focuscolor=BG,
                    indicatorbackground=BG, indicatorforeground=ON_PRIMARY,
                    upperbordercolor=FIELD_BORDER, lowerbordercolor=FIELD_BORDER)
    style.map("TCheckbutton", background=[("active", BG)], foreground=[("disabled", HINT)],
              indicatorbackground=[("selected", RED), ("disabled", MUTED_SURFACE)])
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
