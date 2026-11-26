import tkinter as tk
from pathlib import Path

import theme

ASSETS = Path(__file__).with_name("mascot")
IDLE = ("idle", "hourglass", "tap", "sleep")
# Poses that move on by themselves: (next pose, after how many milliseconds).
NEXT = {"idle": ("hourglass", 60_000), "hourglass": ("tap", 10_000), "tap": ("idle", 10_000),
        "playing": ("playing_tv", 10_000)}
SLEEP_AFTER_MS = 180_000


class Mascot:
    """The llama in the main window. Poses switch directly, without transition animations."""

    def __init__(self, parent):
        self.label = tk.Label(parent, bg=theme.BG, borderwidth=0)
        self.label.pack(side="right")
        self.poses = {p.stem: tk.PhotoImage(file=str(p)) for p in ASSETS.glob("*.png")}
        self.timer = None
        self.sleep_timer = None
        self.state = "idle"
        self.show()
        theme.on_palette_change(self.paint)
        window = self.label.winfo_toplevel()
        for event in ("<Motion>", "<ButtonPress>", "<KeyPress>", "<FocusIn>", "<MouseWheel>"):
            window.bind(event, self.activity, add="+")
        self.activity()

    def activity(self, event=None):
        if self.state == "sleep":
            self.move("idle")
        if self.state in IDLE:  # any interaction restarts the sleep countdown
            self.schedule_sleep()

    def schedule_sleep(self):
        if self.sleep_timer is not None:
            self.label.after_cancel(self.sleep_timer)
            self.sleep_timer = None
        if self.state in IDLE and self.state != "sleep":
            self.sleep_timer = self.label.after(SLEEP_AFTER_MS, lambda: self.move("sleep"))

    def paint(self):
        """Show the current pose, using its *_dark variant on the dark palette when there is one."""
        dark = f"{self.state}_dark"
        self.label.configure(image=self.poses[dark if theme.DARK_MODE and dark in self.poses else self.state])

    def show(self):
        self.paint()
        if self.state in NEXT:
            next_pose, delay_ms = NEXT[self.state]
            self.timer = self.label.after(delay_ms, lambda: self.move(next_pose))

    def move(self, target):
        if target == self.state:
            return
        if self.timer:
            self.label.after_cancel(self.timer)
            self.timer = None
        was_idle = self.state in IDLE
        self.state = target
        # The idle cycle keeps the running sleep countdown; every other change restarts or stops it.
        if not (was_idle and target in IDLE and target != "sleep"):
            self.schedule_sleep()
        self.show()
