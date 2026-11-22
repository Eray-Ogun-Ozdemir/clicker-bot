import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

from recorder import CLICK_COORDINATES, save_recording


class StepDialog(simpledialog.Dialog):
    def __init__(self, parent, step):
        self.step = step
        super().__init__(parent, title="Adımı düzenle")

    def body(self, master):
        ttk.Label(master, text="Hedef (selector)").grid(row=0, column=0, sticky="w")
        self.selector = ttk.Entry(master, width=55)
        self.selector.insert(0, self.step["selector"])
        self.selector.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        self.value = None
        if self.step["action"] == "input":
            ttk.Label(master, text="Girilecek değer").grid(row=2, column=0, sticky="w")
            self.value = tk.Text(master, width=48, height=4)
            self.value.insert("1.0", self.step.get("value", ""))
            self.value.grid(row=3, column=0, sticky="ew")
        return self.selector

    def validate(self):
        if self.selector.get().strip():
            return True
        messagebox.showerror("Adımı düzenle", "Hedef boş bırakılamaz.", parent=self)
        return False

    def apply(self):
        self.result = dict(self.step)
        selector = self.selector.get().strip()
        if selector != self.step["selector"] and self.step["action"] == "click":
            # The old page coordinates and click offset belong to the old target.
            for key in (*CLICK_COORDINATES, "position"):
                self.result.pop(key, None)
        self.result["selector"] = selector
        if self.value is not None:
            self.result["value"] = self.value.get("1.0", "end-1c")


class RecordingInspector(tk.Toplevel):
    def __init__(self, parent, path, data, replay):
        super().__init__(parent)
        self.path = path
        self.data = data
        self.dirty = False
        self.busy = False
        self.title(f"Kayıt adımları · {path.name}")
        self.geometry("760x400")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        panel = ttk.Frame(self, padding=14)
        panel.pack(fill="both", expand=True)
        self.summary = ttk.Label(panel)
        self.summary.pack(anchor="w")
        grid = ttk.Frame(panel)
        grid.pack(fill="both", expand=True, pady=8)
        columns = ("number", "action", "selector", "value")
        self.table = ttk.Treeview(grid, columns=columns, show="headings", selectmode="browse")
        for key, label, width in zip(columns, ("#", "İşlem", "Hedef", "Değer"), (40, 90, 320, 150)):
            self.table.heading(key, text=label)
            self.table.column(key, width=width, stretch=key in ("selector", "value"))
        scroll = ttk.Scrollbar(grid, command=self.table.yview)
        scroll.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scroll.set)
        self.table.pack(fill="both", expand=True)
        self.table.bind("<<TreeviewSelect>>", lambda event: self.update_controls())

        self.detail = tk.StringVar(master=self)
        ttk.Label(panel, textvariable=self.detail, wraplength=680).pack(anchor="w")
        controls = ttk.Frame(panel)
        controls.pack(fill="x", pady=(6, 0))
        self.edit_button = ttk.Button(controls, text="Düzenle", command=self.edit_step)
        self.up_button = ttk.Button(controls, text="Yukarı", command=lambda: self.move_step(-1))
        self.down_button = ttk.Button(controls, text="Aşağı", command=lambda: self.move_step(1))
        self.delete_button = ttk.Button(controls, text="Sil", command=self.delete_step)
        for button in (self.edit_button, self.up_button, self.down_button, self.delete_button):
            button.pack(side="left", padx=(0, 4))
        self.play_button = ttk.Button(controls, text="Bu kaydı oynat",
                                      command=lambda: replay(self.path, self.data))
        self.play_button.pack(side="right")
        self.save_button = ttk.Button(controls, text="Kopyasını kaydet", command=self.save_copy)
        self.save_button.pack(side="right", padx=(0, 4))
        self.refresh_steps()

    @property
    def steps(self):
        return self.data["steps"]

    def selected_index(self):
        selection = self.table.selection()
        return int(selection[0]) - 1 if selection else None

    def update_controls(self):
        index = self.selected_index()
        selected = not self.busy and index is not None
        for button, enabled in (
            (self.edit_button, selected),
            (self.delete_button, selected),
            (self.up_button, selected and index > 0),
            (self.down_button, selected and index < len(self.steps) - 1),
            (self.play_button, not self.busy),
            (self.save_button, not self.busy),
        ):
            button.state(["!disabled" if enabled else "disabled"])

    def set_busy(self, busy):
        self.busy = busy
        self.update_controls()

    def refresh_summary(self):
        marker = " · Kaydedilmemiş değişiklikler" if self.dirty else ""
        self.summary.configure(text=f"{self.path.name} · {len(self.steps)} adım{marker}")
        self.title(f"Kayıt adımları · {self.path.name}")

    def refresh_steps(self, selected=None):
        self.table.delete(*self.table.get_children())
        for index, step in enumerate(self.steps, 1):
            value = "Enter" if step["action"] == "keydown" else step.get("value", "")
            self.table.insert("", "end", iid=str(index),
                              values=(index, step["action"], step["selector"], value))
        if selected is not None:
            self.highlight(selected + 1)
        self.refresh_summary()
        self.update_controls()

    def changed(self, selected):
        self.dirty = True
        self.detail.set("")
        self.refresh_steps(selected)

    def edit_step(self):
        index = self.selected_index()
        if self.busy or index is None:
            return
        dialog = StepDialog(self, self.steps[index])
        if dialog.result is not None and dialog.result != self.steps[index]:
            self.steps[index] = dialog.result
            self.changed(index)

    def move_step(self, direction):
        index = self.selected_index()
        if self.busy or index is None:
            return
        target = index + direction
        if 0 <= target < len(self.steps):
            self.steps[index], self.steps[target] = self.steps[target], self.steps[index]
            self.changed(target)

    def delete_step(self):
        index = self.selected_index()
        if self.busy or index is None:
            return
        del self.steps[index]
        self.changed(min(index, len(self.steps) - 1) if self.steps else None)

    def save_copy(self):
        filename = filedialog.asksaveasfilename(
            parent=self, defaultextension=".json", filetypes=[("Bot kaydı", "*.json")],
            initialdir=self.path.parent, initialfile=f"{self.path.stem}-edited.json")
        if not filename:
            return
        path = Path(filename)
        try:
            save_recording(path, self.data)
        except FileExistsError:
            messagebox.showerror("Kayıt", "Bu dosya zaten var. Yeni bir ad seç.", parent=self)
            return
        except (OSError, ValueError) as exc:
            messagebox.showerror("Kayıt", str(exc), parent=self)
            return
        self.path = path
        self.dirty = False
        self.detail.set(f"Kopya kaydedildi · {path.name}")
        self.refresh_summary()

    def confirm_discard(self):
        return not self.dirty or messagebox.askyesno(
            "Kaydedilmemiş değişiklikler", "Değişiklikleri kaydetmeden devam edilsin mi?",
            parent=self if self.winfo_viewable() else self.master)

    def highlight(self, index):
        row = str(index)
        self.table.selection_set(row)
        self.table.focus(row)
        self.table.see(row)
