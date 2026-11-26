import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import theme
from recorder import (CLICK_COORDINATES, delete_credentials, missing_credentials, origin_of,
                      save_credentials, save_recording, stored_credentials)


class StepDialog(simpledialog.Dialog):
    def __init__(self, parent, step):
        self.step = step
        super().__init__(parent, title="Adımı düzenle")

    def body(self, master):
        self.configure(bg=theme.BG)
        master.configure(bg=theme.BG, padx=10, pady=6)
        master.pack_configure(fill="both", expand=True)
        tk.Label(master, text=f"{theme.ACTION_LABELS.get(self.step['action'], self.step['action'])} adımı",
                 bg=theme.BG, fg=theme.INK, font=theme.font(17, True)).pack(anchor="w")
        theme.divider(master, pady=(10, 14))
        tk.Label(master, text="Hedef (selector)", bg=theme.BG, fg=theme.INK,
                 font=theme.font(12, True)).pack(anchor="w", pady=(0, 6))
        holder, self.selector = theme.entry(master, self.step["selector"], width=58)
        self.selector.configure(font=theme.mono(12))
        holder.pack(fill="x")
        self.value = None
        if self.step["action"] == "input":
            tk.Label(master, text="Girilecek değer", bg=theme.BG, fg=theme.INK,
                     font=theme.font(12, True)).pack(anchor="w", pady=(14, 6))
            outer, inner = theme.bordered(master)
            outer.pack(fill="x")
            self.value = tk.Text(inner, width=56, height=4, relief="flat", bg=theme.BG, fg=theme.INK,
                                 insertbackground=theme.INK, highlightthickness=0, font=theme.font(13),
                                 padx=10, pady=8, wrap="word")
            self.value.insert("1.0", self.step.get("value", ""))
            self.value.pack(fill="x")
            self.value.bind("<FocusIn>", lambda _: outer.configure(bg=theme.RED))
            self.value.bind("<FocusOut>", lambda _: outer.configure(bg=theme.FIELD_BORDER))
        self.error = tk.Label(master, bg=theme.BG, fg=theme.RED, font=theme.font(12), anchor="w")
        return self.selector

    def buttonbox(self):
        box = tk.Frame(self, bg=theme.BG, padx=20, pady=16)
        box.pack(fill="x")
        save, _ = theme.button(box, "Kaydet", self.ok, "Primary", "Medium.")
        save.pack(side="right")
        cancel, _ = theme.button(box, "İptal", self.cancel, "Outline", "Medium.")
        cancel.pack(side="right", padx=(0, 8))
        self.selector.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

    def validate(self):
        if self.selector.get().strip():
            return True
        self.error.configure(text="⚠  Hedef boş bırakılamaz.")
        self.error.pack(anchor="w", fill="x", pady=(10, 0))
        self.selector.focus_set()
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


class PasswordDialog(simpledialog.Dialog):
    """Ask for the password of a recording's login; it is stored on this device only."""

    def __init__(self, parent, origin):
        self.origin = origin
        super().__init__(parent, title="Parolayı gir")

    def body(self, master):
        self.configure(bg=theme.BG)
        master.configure(bg=theme.BG, padx=10, pady=6)
        master.pack_configure(fill="both", expand=True)
        tk.Label(master, text="Parolayı gir", bg=theme.BG, fg=theme.INK,
                 font=theme.font(17, True)).pack(anchor="w")
        theme.divider(master, pady=(10, 12))
        tk.Label(master, text=f"Bu kayıt {self.origin} adresinde parola kullanıyor. Parola yalnızca bu cihazda "
                              "saklanır, kayıt dosyasına yazılmaz.",
                 bg=theme.BG, fg=theme.MUTED, font=theme.font(12), justify="left", wraplength=420).pack(anchor="w")
        tk.Label(master, text="Parola", bg=theme.BG, fg=theme.INK,
                 font=theme.font(12, True)).pack(anchor="w", pady=(14, 6))
        holder, self.password = theme.entry(master, show="•", width=40)
        holder.pack(fill="x")
        self.error = tk.Label(master, bg=theme.BG, fg=theme.RED, font=theme.font(12), anchor="w")
        self.password.bind("<Key>", lambda _: self.error.pack_forget(), add="+")
        return self.password

    def buttonbox(self):
        box = tk.Frame(self, bg=theme.BG, padx=20, pady=16)
        box.pack(fill="x")
        save, _ = theme.button(box, "Kaydet", self.ok, "Primary", "Medium.")
        save.pack(side="right")
        cancel, _ = theme.button(box, "İptal", self.cancel, "Outline", "Medium.")
        cancel.pack(side="right", padx=(0, 8))
        self.password.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

    def validate(self):
        if self.password.get():
            return True
        self.error.configure(text="⚠  Parola boş bırakılamaz.")
        self.error.pack(anchor="w", fill="x", pady=(10, 0))
        return False

    def apply(self):
        self.result = self.password.get()


class RecordingInspector(tk.Toplevel):
    def __init__(self, parent, path, data, replay):
        super().__init__(parent)
        self.path = path
        self.data = data
        self.dirty = False
        self.busy = False
        self.message = ""
        self.title(f"Kayıt adımları · {path.name}")
        self.geometry("880x500")
        self.minsize(620, 380)
        self.configure(bg=theme.BG)
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        panel = tk.Frame(self, bg=theme.BG, padx=24, pady=18)
        panel.pack(fill="both", expand=True)

        header = tk.Frame(panel, bg=theme.BG)
        header.pack(fill="x")
        tk.Label(header, text="KAYIT ADIMLARI", bg=theme.BG, fg=theme.MUTED,
                 font=theme.font(10, True)).pack(anchor="w")
        title_row = tk.Frame(header, bg=theme.BG)
        title_row.pack(fill="x", pady=(6, 0))
        self.name_label = tk.Label(title_row, bg=theme.BG, fg=theme.INK, font=theme.font(20, True))
        self.name_label.pack(side="left")
        self.count_badge = theme.badge(title_row)
        self.count_badge.pack(side="left", padx=(12, 0))
        self.dirty_badge = theme.badge(title_row, "Kaydedilmemiş değişiklikler", active=True)
        theme.divider(panel, pady=(14, 14))

        outer, grid = theme.bordered(panel, theme.BORDER)
        outer.pack(fill="both", expand=True)
        columns = ("number", "action", "selector", "value")
        # A small requested height lets the table grow into spare room without pushing the buttons out.
        self.table = ttk.Treeview(grid, columns=columns, show="headings", selectmode="browse",
                                  style="Steps.Treeview", height=4)
        for key, label, width in zip(columns, ("#", "İşlem", "Hedef", "Değer"), (44, 110, 380, 190)):
            self.table.heading(key, text=label, anchor="w")
            self.table.column(key, width=width, minwidth=width if key in ("number", "action") else 80,
                              stretch=key in ("selector", "value"), anchor="w")
        scroll = ttk.Scrollbar(grid, command=self.table.yview)

        def scrolled(first, last):  # show the scrollbar only when the steps do not fit
            scroll.set(first, last)
            if float(first) <= 0 and float(last) >= 1:
                scroll.pack_forget()
            elif not scroll.winfo_ismapped():
                scroll.pack(side="right", fill="y", before=self.table)
        self.table.configure(yscrollcommand=scrolled)
        self.table.pack(side="left", fill="both", expand=True)
        self.table.bind("<Double-1>", lambda event: self.edit_step() if self.table.identify_row(event.y) else None)
        self.table.bind("<<TreeviewSelect>>", lambda event: self.selection_changed())

        self.detail = tk.StringVar(master=self)  # playback errors and notices; app.py writes to it
        self.detail.trace_add("write", lambda *_: self.render_detail())
        self.detail_label = tk.Label(panel, bg=theme.BG, anchor="w", justify="left", wraplength=800)
        self.detail_label.pack(fill="x", pady=(10, 0))
        self.detail_label.bind("<Configure>", lambda e: self.detail_label.configure(wraplength=max(200, e.width)))

        controls = tk.Frame(panel, bg=theme.BG)
        controls.pack(fill="x", pady=(12, 0))
        self.step_buttons = {}
        for key, text, command in (("edit", "Düzenle", self.edit_step), ("up", "Yukarı", lambda: self.move_step(-1)),
                                   ("down", "Aşağı", lambda: self.move_step(1)), ("delete", "Sil", self.delete_step)):
            holder, widget = theme.button(controls, text, command, "Outline", "Small.")
            holder.pack(side="left", padx=(0, 8))
            self.step_buttons[key] = widget
        self.edit_button, self.up_button = self.step_buttons["edit"], self.step_buttons["up"]
        self.down_button, self.delete_button = self.step_buttons["down"], self.step_buttons["delete"]

        theme.divider(panel, pady=(16, 14))
        file_actions = tk.Frame(panel, bg=theme.BG)
        file_actions.pack(fill="x")
        holder, self.play_button = theme.button(file_actions, "Bu kaydı oynat",
                                                lambda: replay(self.path, self.data), "Primary", "Medium.")
        holder.pack(side="right")
        holder, self.save_button = theme.button(file_actions, "Kopyasını kaydet", self.save_copy, "Outline", "Medium.")
        holder.pack(side="right", padx=(0, 8))
        # Exactly one of these shows for recordings with a password step, depending on this device.
        self.forget_holder, self.forget_button = theme.button(
            file_actions, "Parolayı cihazdan sil", self.forget_password, "Text", "Medium.")
        self.enter_holder, self.enter_button = theme.button(
            file_actions, "Parolayı gir", self.enter_password, "Text", "Medium.")
        self.password_missing = False
        self.refresh_password_state()
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
            (self.forget_button, not self.busy),
            (self.enter_button, not self.busy),
        ):
            button.state(["!disabled" if enabled else "disabled"])

    def set_busy(self, busy):
        self.busy = busy
        self.update_controls()

    def refresh_summary(self):
        self.name_label.configure(text=self.path.name)
        self.count_badge.configure(text=f"{len(self.steps)} adım")
        if self.dirty:
            self.dirty_badge.pack(side="left", padx=(8, 0))
        else:
            self.dirty_badge.pack_forget()
        self.title(f"Kayıt adımları · {self.path.name}")

    def selection_changed(self):
        self.update_controls()
        self.render_detail()

    def render_detail(self):
        """Show a playback error or notice if there is one, otherwise the selected step's full target."""
        message = self.detail.get()
        if message:
            error = "hata" in message
            self.detail_label.configure(text=("⚠  " if error else "") + message, font=theme.font(11, error),
                                        fg=theme.RED if error else theme.MUTED)
            return
        index = self.selected_index()
        text = self.steps[index]["selector"] if index is not None and index < len(self.steps) else ""
        self.detail_label.configure(text=text, font=theme.mono(11), fg=theme.MUTED)

    def refresh_steps(self, selected=None):
        self.table.delete(*self.table.get_children())
        for index, step in enumerate(self.steps, 1):
            value = "Enter" if step["action"] == "keydown" else step.get("value", "")
            action = theme.ACTION_LABELS.get(step["action"], step["action"])
            if step["action"] == "password":
                value = "Parola girilmemiş" if self.password_missing else "Cihazda saklanan parola"
            elif step["action"] == "select":
                value = ", ".join(step["values"])
            self.table.insert("", "end", iid=str(index),
                              values=(index, action, step["selector"], value))
        if selected is not None:
            self.highlight(selected + 1)
        self.refresh_summary()
        self.update_controls()
        self.render_detail()

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

    def forget_password(self):
        if self.busy or not messagebox.askyesno(
                "Parolayı cihazdan sil",
                "Bu kayıt için saklanan parola Anahtar Zinciri / Kimlik Bilgisi Yöneticisi'nden silinecek. "
                "Bu kaydı ve kopyalarını oynatmak için parolalı adımı yeniden kaydetmen gerekecek. Devam edilsin mi?",
                icon="warning", parent=self):
            return
        try:
            found = delete_credentials(self.data)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Parolayı cihazdan sil", str(exc), parent=self)
            return
        self.detail.set("Parola cihazdan silindi." if found else "Bu kayıt için cihazda saklanan parola bulunamadı.")
        self.refresh_password_state()

    def enter_password(self):
        if self.busy or not stored_credentials(self.data):
            return
        origin = origin_of(next(s["url"] for s in self.steps if s["action"] == "password"))
        dialog = PasswordDialog(self, origin)
        if dialog.result is None:
            return
        try:
            save_credentials(self.data, dialog.result)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Parolayı gir", str(exc), parent=self)
            return
        self.detail.set("Parola bu cihaza kaydedildi.")
        self.refresh_password_state()

    def refresh_password_state(self):
        """Show "Parolayı cihazdan sil" when the password is stored, "Parolayı gir" when it is missing."""
        self.forget_holder.pack_forget()
        self.enter_holder.pack_forget()
        if not stored_credentials(self.data):
            self.password_missing = False
        else:
            try:
                self.password_missing = bool(missing_credentials(self.data))
            except (OSError, ValueError):
                self.password_missing = False  # store unavailable: offer removal, which reports the error
            (self.enter_holder if self.password_missing else self.forget_holder).pack(side="left")
        if self.table.get_children():
            selected = self.selected_index()
            self.refresh_steps(selected)

    def confirm_discard(self):
        return not self.dirty or messagebox.askyesno(
            "Kaydedilmemiş değişiklikler", "Değişiklikleri kaydetmeden devam edilsin mi?",
            parent=self if self.winfo_viewable() else self.master)

    def highlight(self, index):
        row = str(index)
        self.table.selection_set(row)
        self.table.focus(row)
        self.table.see(row)
