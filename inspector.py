import os
import subprocess
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import theme
from recorder import (ACTION_LABELS, CLICK_COORDINATES, DEFAULT_TIMEOUT, MAX_TIMEOUT, delete_credentials,
                      format_seconds, missing_credentials, origin_of, save_credentials, save_recording,
                      step_label, stored_credentials, valid_timeout)


def parse_seconds(text):
    """Read a duration typed as "5", "2.5" or "2,5"; None when it is not a usable limit."""
    try:
        value = float(text.strip().replace(",", "."))
    except ValueError:
        return None
    value = int(value) if value.is_integer() else value
    return value if valid_timeout(value) else None


def step_title(step):
    return step_label(step) if step["action"] == "assert" else f"{step_label(step)} adımı"


def field_label(master, text, first=False):
    tk.Label(master, text=text, bg=theme.BG, fg=theme.INK,
             font=theme.font(12, True)).pack(anchor="w", pady=(0 if first else 14, 6))


class StepDialog(simpledialog.Dialog):
    def __init__(self, parent, step, title="Adımı düzenle"):
        self.step = step
        super().__init__(parent, title=title)

    def body(self, master):
        self.configure(bg=theme.BG)
        master.configure(bg=theme.BG, padx=10, pady=6)
        master.pack_configure(fill="both", expand=True)
        tk.Label(master, text=step_title(self.step), bg=theme.BG, fg=theme.INK,
                 font=theme.font(17, True)).pack(anchor="w")
        theme.divider(master, pady=(10, 14))
        self.selector = self.value = self.timeout = self.expected = None
        url_check = self.step["action"] == "assert" and self.step["kind"] == "url"
        if not url_check:  # an address check looks at the page, not at an element
            field_label(master, "Hedef (selector)", first=True)
            holder, self.selector = theme.entry(master, self.step["selector"], width=58)
            self.selector.configure(font=theme.mono(12))
            holder.pack(fill="x")
        if self.step["action"] == "assert":
            field_label(master, "Sayfa adresi şununla başlamalı" if url_check else "Hedefin içermesi gereken metin",
                        first=url_check)
            holder, self.expected = theme.entry(master, self.step["expected"], width=58)
            if url_check:
                self.expected.configure(font=theme.mono(12))
            holder.pack(fill="x")
            tk.Label(master, text="Oynatma, sonuç tutana kadar en fazla adım zaman aşımı kadar bekler.",
                     bg=theme.BG, fg=theme.MUTED, font=theme.font(11)).pack(anchor="w", pady=(8, 0))
        if self.step["action"] == "wait":
            field_label(master, "Hedef görünene kadar en fazla (sn)")
            holder, self.timeout = theme.entry(master, format_seconds(self.step["timeout"]), width=8)
            holder.pack(anchor="w")
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
        # A new text check comes with a target already filled in; what is missing is the text.
        return self.expected or self.selector

    def buttonbox(self):
        box = tk.Frame(self, bg=theme.BG, padx=20, pady=16)
        box.pack(fill="x")
        save, _ = theme.button(box, "Kaydet", self.ok, "Primary", "Medium.")
        save.pack(side="right")
        cancel, _ = theme.button(box, "İptal", self.cancel, "Outline", "Medium.")
        cancel.pack(side="right", padx=(0, 8))
        for field in (self.selector, self.timeout, self.expected):
            if field is not None:
                field.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

    def validate(self):
        if self.selector is not None and not self.selector.get().strip():
            return self.reject("Hedef boş bırakılamaz.", self.selector)
        if self.expected is not None and not self.expected.get().strip():
            return self.reject("Beklenen değer boş bırakılamaz.", self.expected)
        if self.timeout is not None and parse_seconds(self.timeout.get()) is None:
            return self.reject(f"Süre 0 ile {MAX_TIMEOUT} sn arasında bir sayı olmalı.", self.timeout)
        return True

    def reject(self, message, field):
        self.error.configure(text=f"⚠  {message}")
        self.error.pack(anchor="w", fill="x", pady=(10, 0))
        field.focus_set()
        return False

    def apply(self):
        self.result = dict(self.step)
        if self.selector is not None:
            selector = self.selector.get().strip()
            if selector != self.step["selector"] and self.step["action"] == "click":
                # The old page coordinates and click offset belong to the old target.
                for key in (*CLICK_COORDINATES, "position"):
                    self.result.pop(key, None)
            self.result["selector"] = selector
        if self.expected is not None:
            self.result["expected"] = self.expected.get().strip()
        if self.value is not None:
            self.result["value"] = self.value.get("1.0", "end-1c")
        if self.timeout is not None:
            self.result["timeout"] = parse_seconds(self.timeout.get())


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
        self.start_replay = replay
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

        # Playback settings saved with the recording.
        settings = tk.Frame(header, bg=theme.BG)
        settings.pack(fill="x", pady=(10, 0))
        tk.Label(settings, text="Adım zaman aşımı (sn)", bg=theme.BG, fg=theme.MUTED,
                 font=theme.font(12)).pack(side="left", padx=(0, 8))
        holder, self.timeout_entry = theme.entry(settings, width=5, justify="right")
        holder.pack(side="left")
        self.timeout_entry.bind("<Return>", lambda _: self.apply_timeout(), add="+")
        self.timeout_entry.bind("<FocusOut>", lambda _: self.apply_timeout(), add="+")
        self.screenshot_setting = tk.BooleanVar(master=self, value=bool(data.get("failureScreenshot")))
        self.screenshot_check = ttk.Checkbutton(settings, text="Hata olunca ekran görüntüsü kaydet",
                                                variable=self.screenshot_setting, command=self.toggle_screenshot)
        self.screenshot_check.pack(side="left", padx=(20, 0))
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

        self.detail = tk.StringVar(master=self)  # playback errors and notices; set through show_message
        self.detail_error = False
        self.detail.trace_add("write", lambda *_: (self.show_screenshot(None), self.render_detail()))
        detail_row = tk.Frame(panel, bg=theme.BG)
        detail_row.pack(fill="x", pady=(10, 0))
        self.screenshot = None
        self.screenshot_holder, self.screenshot_button = theme.button(
            detail_row, "Ekran görüntüsünü aç", self.open_screenshot, "Text", "Small.")
        self.detail_label = tk.Label(detail_row, bg=theme.BG, anchor="w", justify="left", wraplength=800)
        self.detail_label.pack(side="left", fill="x", expand=True)
        self.detail_label.bind("<Configure>", lambda e: self.detail_label.configure(wraplength=max(200, e.width)))

        controls = tk.Frame(panel, bg=theme.BG)
        controls.pack(fill="x", pady=(12, 0))
        self.step_buttons = {}
        for key, text, command in (("edit", "Düzenle", self.edit_step), ("up", "Yukarı", lambda: self.move_step(-1)),
                                   ("down", "Aşağı", lambda: self.move_step(1)), ("delete", "Sil", self.delete_step)):
            holder, widget = theme.button(controls, text, command, "Outline", "Small.")
            holder.pack(side="left", padx=(0, 8))
            self.step_buttons[key] = widget
        holder, self.add_button = theme.button(controls, "Adım ekle  ▾", self.show_add_menu, "Outline", "Small.")
        holder.pack(side="left", padx=(8, 0))
        self.add_menu = tk.Menu(self, tearoff=False)
        for label, kind in (("Bekleme", "wait"), ("Metin doğrulaması", "text"), ("Adres doğrulaması", "url")):
            self.add_menu.add_command(label=label, command=lambda kind=kind: self.add_step(kind))
        self.edit_button, self.up_button = self.step_buttons["edit"], self.step_buttons["up"]
        self.down_button, self.delete_button = self.step_buttons["down"], self.step_buttons["delete"]

        footer_line = theme.divider(panel, pady=(16, 14))
        file_actions = tk.Frame(panel, bg=theme.BG)
        file_actions.pack(fill="x")
        holder, self.play_button = theme.button(file_actions, "Bu kaydı oynat",
                                                self.replay, "Primary", "Medium.")
        holder.pack(side="right")
        holder, self.save_button = theme.button(file_actions, "Kopyasını kaydet", self.save_copy, "Outline", "Medium.")
        holder.pack(side="right", padx=(0, 8))
        # Exactly one of these shows for recordings with a password step, depending on this device.
        self.forget_holder, self.forget_button = theme.button(
            file_actions, "Parolayı cihazdan sil", self.forget_password, "Text", "Medium.")
        self.enter_holder, self.enter_button = theme.button(
            file_actions, "Parolayı gir", self.enter_password, "Text", "Medium.")
        self.password_missing = False
        # Pack the step table last so that, when the window is short, it shrinks and the buttons
        # below it stay visible; the parts under it are stacked from the bottom up.
        for part in (file_actions, footer_line, controls, detail_row):
            options = {key: value for key, value in part.pack_info().items() if key != "in"}
            part.pack_forget()
            part.pack(**{**options, "side": "bottom"})
        outer.pack_forget()
        outer.pack(fill="both", expand=True)
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
            (self.add_button, not self.busy),
            (self.screenshot_check, not self.busy),
            (self.play_button, not self.busy),
            (self.save_button, not self.busy),
            (self.forget_button, not self.busy),
            (self.enter_button, not self.busy),
        ):
            button.state(["!disabled" if enabled else "disabled"])
        self.timeout_entry.configure(state="disabled" if self.busy else "normal")

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

    def show_message(self, text, error=False):
        """Show a notice, or an error in red, below the steps until the steps change."""
        self.detail_error = error
        self.detail.set(text)

    def render_detail(self):
        """Show a playback error or notice if there is one, otherwise the selected step's full target."""
        message = self.detail.get()
        if message:
            error = self.detail_error
            self.detail_label.configure(text=("⚠  " if error else "") + message, font=theme.font(11, error),
                                        fg=theme.RED if error else theme.MUTED)
            return
        index = self.selected_index()
        step = self.steps[index] if index is not None and index < len(self.steps) else {}
        text = step.get("selector") or step.get("expected", "")
        self.detail_label.configure(text=text, font=theme.mono(11), fg=theme.MUTED)

    def refresh_steps(self, selected=None):
        self.table.delete(*self.table.get_children())
        for index, step in enumerate(self.steps, 1):
            value = "Enter" if step["action"] == "keydown" else step.get("value", "")
            action = ACTION_LABELS.get(step["action"], step["action"])
            if step["action"] == "password":
                value = "Parola girilmemiş" if self.password_missing else "Cihazda saklanan parola"
            elif step["action"] == "select":
                value = ", ".join(step["values"])
            elif step["action"] == "wait":
                value = f"Görünene kadar · en fazla {format_seconds(step['timeout'])} sn"
            elif step["action"] == "assert":
                value = f"Başlar: {step['expected']}" if step["kind"] == "url" else f"İçerir: \"{step['expected']}\""
            target = "Sayfa adresi" if step["action"] == "assert" and step["kind"] == "url" else step["selector"]
            self.table.insert("", "end", iid=str(index), values=(index, action, target, value))
        if selected is not None:
            self.highlight(selected + 1)
        self.show_timeout()
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

    @property
    def timeout(self):
        return self.data.get("timeout", DEFAULT_TIMEOUT)

    def show_timeout(self):
        state = self.timeout_entry.cget("state")
        self.timeout_entry.configure(state="normal")
        self.timeout_entry.delete(0, "end")
        self.timeout_entry.insert(0, format_seconds(self.timeout))
        self.timeout_entry.configure(state=state)

    def apply_timeout(self):
        if self.busy:
            return
        value = parse_seconds(self.timeout_entry.get())
        if value is None:
            self.show_timeout()
            self.show_message(f"Zaman aşımı 0 ile {MAX_TIMEOUT} sn arasında bir sayı olmalı.", error=True)
        elif value != self.timeout:
            self.data["timeout"] = value
            self.changed(self.selected_index())

    def show_add_menu(self):
        if self.busy:
            return
        button = self.add_button
        self.add_menu.tk_popup(button.winfo_rootx(), button.winfo_rooty() + button.winfo_height())

    def add_step(self, kind):
        """Insert a wait or a check after the selected step, or at the end."""
        if self.busy:
            return
        index = self.selected_index()
        position = len(self.steps) if index is None else index + 1
        # Usually the new step guards the step that follows it, so start from that step.
        neighbours = self.steps[position:position + 1] or self.steps[position - 1:position]
        neighbour = neighbours[0] if neighbours else {"url": self.data["url"], "selector": ""}
        if kind == "wait":
            step = {"action": "wait", "url": neighbour["url"], "selector": neighbour["selector"],
                    "timeout": max(10, self.timeout)}
            title = "Bekleme ekle"
        else:
            # The page as a whole is a useful default: "this text appears somewhere".
            step = {"action": "assert", "kind": kind, "url": neighbour["url"],
                    "selector": "" if kind == "url" else "body",
                    "expected": neighbour["url"] if kind == "url" else ""}
            title = "Doğrulama ekle"
        dialog = StepDialog(self, step, title=title)
        if dialog.result is not None:
            self.steps.insert(position, dialog.result)
            self.changed(position)

    def toggle_screenshot(self):
        if self.busy:
            return
        if self.screenshot_setting.get():
            self.data["failureScreenshot"] = True
        else:
            self.data.pop("failureScreenshot", None)
        self.changed(self.selected_index())

    def show_screenshot(self, path):
        """Offer to open the screenshot of the latest failure; None hides the offer."""
        self.screenshot = path
        if path:
            self.screenshot_holder.pack(side="right", padx=(12, 0), before=self.detail_label)
        else:
            self.screenshot_holder.pack_forget()

    def open_screenshot(self):
        if not self.screenshot or not self.screenshot.exists():
            messagebox.showerror("Ekran görüntüsü", "Ekran görüntüsü dosyası bulunamadı.", parent=self)
            return
        if sys.platform == "darwin":
            subprocess.run(["open", str(self.screenshot)], check=False)
        else:
            os.startfile(self.screenshot)

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

    def replay(self):
        self.apply_timeout()  # a value typed just before clicking may not have lost focus yet
        self.start_replay(self.path, self.data)

    def save_copy(self):
        self.apply_timeout()
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
        self.show_message(f"Kopya kaydedildi · {path.name}")
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
        self.show_message("Parola cihazdan silindi." if found else "Bu kayıt için cihazda saklanan parola bulunamadı.")
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
        self.show_message("Parola bu cihaza kaydedildi.")
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
