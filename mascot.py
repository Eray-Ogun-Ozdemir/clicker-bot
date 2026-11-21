import tkinter as tk
from pathlib import Path

ASSETS = Path(__file__).with_name("mascot")
SIZE = 144
IDLE = ("idle", "hourglass", "tap", "sleep")


class Mascot:
    def __init__(self, parent):
        self.label = tk.Label(parent, bg="white", borderwidth=0)
        self.label.pack(side="right")
        self.poses = {p.stem: tk.PhotoImage(file=str(p)) for p in ASSETS.glob("*.png")
                      if "_to_" not in p.stem}
        self.frame = tk.PhotoImage(width=SIZE, height=SIZE)
        self.timer = None
        self.sheet = None
        self.pending = None
        self.sleep_timer = None
        self.state = "idle"
        self.hold()
        window = self.label.winfo_toplevel()
        for event in ("<Motion>", "<ButtonPress>", "<KeyPress>", "<FocusIn>", "<MouseWheel>"):
            window.bind(event, self.activity, add="+")
        self.activity()

    def activity(self, event=None):
        if self.state == "sleep":
            self.move("idle")
        if self.state in IDLE:
            self.schedule_sleep()

    def schedule_sleep(self):
        if self.sleep_timer is not None:
            self.label.after_cancel(self.sleep_timer)
            self.sleep_timer = None
        if self.state in IDLE and self.state != "sleep" and not self.pending:
            self.sleep_timer = self.label.after(180_000, lambda: self.move("sleep"))

    def hold(self):
        self.sheet = None
        self.timer = None
        self.label.configure(image=self.poses[self.state])
        if self.pending:
            target, self.pending = self.pending, None
            self.timer = self.label.after(83, lambda: self.move(target))
            return
        next_pose = {"idle": "hourglass", "hourglass": "tap", "tap": "idle",
                     "playing": "playing_tv"}.get(self.state)
        if next_pose:
            delay_ms = 60_000 if self.state == "idle" else 10_000
            self.timer = self.label.after(delay_ms, lambda: self.move(next_pose))

    def move(self, target):
        self.pending = None
        if target == self.state:
            return
        if self.timer:
            self.label.after_cancel(self.timer)
            self.timer = None
        source = self.state
        if source == "fail" and target in ("playing", "recording"):
            self.pending = target
            target = "idle"
        self.state = target
        if source not in IDLE or target not in IDLE or target == "sleep":
            self.schedule_sleep()
        if source in IDLE and target in ("recording", "fail"):
            source = "idle"
        if source == "playing_tv":
            source = "playing"
        path = ASSETS / f"{source}_to_{target}.png"
        if not path.exists():
            self.hold()
            return
        self.sheet = tk.PhotoImage(file=str(path))
        self.draw(0)

    def draw(self, index):
        y = index * SIZE
        if y >= self.sheet.height():
            self.hold()
            return
        self.frame.tk.call(str(self.frame), "copy", str(self.sheet), "-from",
                           0, y, SIZE, y + SIZE, "-to", 0, 0)
        self.label.configure(image=self.frame)
        self.timer = self.label.after(83, lambda: self.draw(index + 1))
