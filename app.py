import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlsplit

import theme
from mascot import Mascot
from inspector import RecordingInspector
from recorder import Control, load_recording, run

URL_MESSAGE = "http:// veya https:// ile başlayan bir URL gir. Örnek: https://example.com"


def main():
    root = tk.Tk()
    root.title("Clicker Bot")
    logo_path = Path(__file__).with_name("logo.png")
    if logo_path.is_file():
        logo = tk.PhotoImage(file=str(logo_path))
        root.iconphoto(True, logo)
    theme.apply(root)  # picks the light or dark palette; everything below reads it
    white, ink, muted, red = theme.BG, theme.INK, theme.MUTED, theme.RED
    root.geometry("1000x700")
    root.minsize(800, 620)
    bar = tk.Frame(root, bg=theme.BAR)
    bar.pack(fill="x")
    for text, color, bold, padx in (("➤", red, False, (20, 0)), ("Clicker Bot", ink, True, (10, 0)),
                                    ("/", theme.SLASH, False, 14), ("Çalışma alanım", muted, False, 0)):
        tk.Label(bar, text=text, bg=theme.BAR, fg=color, pady=12,
                 font=(theme.FAMILY, 12, "bold" if bold else "normal")).pack(side="left", padx=padx)

    # "Görünüm" segmented control: follow the system, or keep the app light or dark.
    appearance = tk.Frame(bar, bg=theme.BAR)
    appearance.pack(side="right", padx=16)
    tk.Label(appearance, text="Görünüm", bg=theme.BAR, fg=muted,
             font=(theme.FAMILY, 11)).pack(side="left", padx=(0, 8))
    segment_box, segments = theme.bordered(appearance, theme.BORDER, theme.BAR)
    segment_box.pack(side="left")
    appearance_options = {}
    for value, text in (("system", "Sistem"), ("light", "Açık"), ("dark", "Koyu")):
        option = tk.Label(segments, text=text, padx=10, pady=3, cursor="hand2", takefocus=1,
                          highlightthickness=1, highlightbackground=theme.BAR, highlightcolor=theme.RED)
        option.pack(side="left")
        for event in ("<Button-1>", "<Return>", "<space>"):
            option.bind(event, lambda _, v=value: theme.set_preference(root, v))
        appearance_options[value] = option

    def paint_appearance():
        for value, option in appearance_options.items():
            chosen = theme.PREFERENCE == value
            option.configure(bg=theme.SELECTED if chosen else theme.BAR, fg=theme.RED if chosen else theme.MUTED,
                             highlightbackground=theme.SELECTED if chosen else theme.BAR,
                             font=(theme.FAMILY, 11, "bold" if chosen else "normal"))
    paint_appearance()
    theme.on_palette_change(paint_appearance)
    tk.Frame(root, bg=theme.BORDER, height=1).pack(fill="x")
    body = tk.Frame(root, bg=white)
    body.pack(fill="both", expand=True)
    sidebar = tk.Frame(body, bg=theme.SIDEBAR, width=190)
    sidebar.pack(side="left", fill="y")
    sidebar.pack_propagate(False)
    tk.Label(sidebar, text="ÇALIŞMA ALANI", bg=theme.SIDEBAR, fg=muted,
             font=(theme.FAMILY, 10, "bold"), padx=14, pady=18).pack(anchor="w")
    selected = tk.Frame(sidebar, bg=theme.SELECTED)
    selected.pack(fill="x")
    tk.Frame(selected, bg=red, width=3).pack(side="left", fill="y")
    tk.Label(selected, text="◍   Tarayıcı otomasyonu", bg=theme.SELECTED, fg=ink,
             anchor="w", padx=12, pady=11).pack(side="left", fill="x", expand=True)
    tk.Frame(body, bg=theme.BORDER, width=1).pack(side="left", fill="y")
    panel = ttk.Frame(body, padding=(24, 18))
    panel.pack(side="left", fill="both", expand=True)
    header = ttk.Frame(panel)
    header.pack(fill="x")
    mascot = Mascot(header)

    title = ttk.Frame(header)
    title.pack(side="left")
    ttk.Label(title, text="➤   MASAÜSTÜ YARDIMCISI", foreground=muted,
              font=(theme.FAMILY, 10, "bold")).pack(anchor="w")
    ttk.Label(title, text="Clicker Bot", font=(theme.FAMILY, 38, "bold")).pack(anchor="w", pady=8)
    tk.Frame(title, width=34, height=3, bg=red).pack(anchor="w")
    tk.Frame(panel, height=1, bg=theme.BORDER).pack(fill="x", pady=(16, 18))

    def section(number, title):
        row = ttk.Frame(panel)
        row.pack(fill="x")
        badge = tk.Canvas(row, width=26, height=26, bg=white, highlightthickness=0)
        badge.pack(side="left")
        badge.create_oval(1, 1, 24, 24, outline=theme.BADGE_RING)
        badge.create_text(13, 13, text=number, fill=muted, font=(theme.FAMILY, 10))
        ttk.Label(row, text=title, font=(theme.FAMILY, 15, "bold")).pack(side="left", padx=8)

    section("01", "Başlangıç URL’si")
    # A 1px frame around a white box: Tk on macOS does not draw highlight borders reliably.
    field = tk.Frame(panel, bg=theme.FIELD_BORDER)
    field.pack(fill="x", pady=(12, 0))
    url_box = tk.Frame(field, bg=white)
    url_box.pack(fill="both", padx=1, pady=1)
    tk.Label(url_box, text="◎", fg=muted, bg=white).pack(side="left", padx=12)
    url = tk.Entry(url_box, relief="flat", bg=white, fg=ink, insertbackground=ink,
                   disabledbackground=theme.MUTED_SURFACE, disabledforeground=muted,
                   highlightthickness=0, font=(theme.FAMILY, 14))
    url.pack(side="left", fill="x", expand=True, ipady=11)
    hint = tk.Label(url, text="https://example.com", bg=white, fg=theme.HINT)
    hint.place(x=3, rely=0.5, anchor="w")
    hint.bind("<Button-1>", lambda _: url.focus_set())
    address_text = tk.StringVar()
    url.configure(textvariable=address_text)
    url_error = tk.Label(panel, bg=white, fg=red, anchor="w", font=(theme.FAMILY, 12))

    def show_url_error(message):
        url_error.configure(text="⚠  " + message)
        url_error.pack(after=field, fill="x", pady=(8, 0))
        field.configure(bg=theme.RED)

    def clear_url_error():
        url_error.pack_forget()
        field.configure(bg=theme.RED if root.focus_get() == url else theme.FIELD_BORDER)

    def valid_url(address):
        try:
            parsed = urlsplit(address)
            return parsed.scheme in ("http", "https") and bool(parsed.hostname)
        except ValueError:
            return False

    def show_hint(*_):
        clear_url_error()
        if address_text.get():
            hint.place_forget()
        else:
            hint.place(x=3, rely=0.5, anchor="w")
    address_text.trace_add("write", show_hint)

    def leave_url(_):
        address = address_text.get().strip()
        if address and not valid_url(address):
            show_url_error(URL_MESSAGE)
        elif not url_error.winfo_ismapped():
            field.configure(bg=theme.FIELD_BORDER)
    url.bind("<FocusIn>", lambda _: field.configure(bg=theme.RED))
    url.bind("<FocusOut>", leave_url)
    url.focus_set()
    ttk.Frame(panel, height=18).pack()
    section("02", "Hazırlama yöntemi")
    modes = ttk.Frame(panel)
    modes.pack(fill="x", pady=(10, 0))
    for column, (label, bg, border, color) in enumerate([
            ("●    Kaydederek hazırla", theme.CARD_SELECTED, theme.SELECTED_BORDER, red),
            ("○    Manuel hazırla     ·  yakında", theme.MUTED_SURFACE, theme.BORDER, theme.CARD_DISABLED_TEXT)]):
        modes.columnconfigure(column, weight=1, uniform="cards")
        card = tk.Frame(modes, bg=border)
        card.grid(row=0, column=column, sticky="ew", padx=(0, 7) if column == 0 else (7, 0))
        tk.Label(card, text=label, anchor="w", padx=18, pady=20, bg=bg, fg=color).pack(
            fill="x", padx=1, pady=1)
    ttk.Frame(panel, height=14).pack()
    section("03", "Hesap bilgileri · isteğe bağlı")
    account = ttk.Frame(panel)
    account.pack(fill="x", pady=(6, 0))
    fields = []
    for column, label in enumerate(("Kullanıcı adı / e-posta", "Parola")):
        account.columnconfigure(column, weight=1, uniform="account")
        ttk.Label(account, text=label).grid(row=0, column=column, sticky="w", pady=(0, 5))
        holder, entry = theme.entry(account, show="•" if column else "")
        holder.grid(row=1, column=column, sticky="ew", padx=(0, 6) if not column else (6, 0))
        fields.append(entry)
    status = tk.StringVar(value="Hazır")
    events = queue.Queue()
    busy = False

    inspector = None
    active_step = None
    control = None

    def stop():
        if control and not control.stopped:
            control.stop()
            buttons[0].state(["disabled"])
            log("Durduruluyor…")

    def open_recording(autoplay):
        nonlocal inspector
        filename = filedialog.askopenfilename(filetypes=[("Bot kaydı", "*.json")])
        if not filename:
            return
        path = Path(filename)
        if inspector and inspector.path == path and inspector.dirty:
            inspector.deiconify()
            inspector.lift()
            if autoplay:
                start(False, path, inspector.data)
            return
        try:
            data = load_recording(path)
        except (OSError, ValueError) as exc:
            messagebox.showerror("Kayıt", str(exc))
            return
        if inspector:
            if not inspector.confirm_discard():
                return
            inspector.destroy()
        inspector = RecordingInspector(root, path, data, lambda path, data: start(False, path, data))
        if autoplay:
            start(False, path, data)

    def start(recording, path=None, data=None):
        nonlocal busy, active_step, control
        if busy:
            return
        address = url.get().strip() if recording else None
        if recording:
            if not valid_url(address):
                mascot.move("fail")
                status.set("Hata")
                show_url_error(URL_MESSAGE)
                url.focus_set()
                return
            if any(field.get() for field in fields) and urlsplit(address).scheme != "https":
                show_url_error("Hesap bilgileri için HTTPS adresi gir.")
                return
            path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("Bot kaydı", "*.json")])
            if not path:
                return
        credentials = dict(zip(("username", "password"), (field.get() for field in fields))) if recording else {}
        if recording:
            fields[1].delete(0, "end")
        for field_entry in fields:
            field_entry.configure(state="disabled")
        url.configure(state="disabled")
        active_step = None
        if inspector:
            inspector.set_busy(True)
            if not recording:
                inspector.detail.set("")
                inspector.table.selection_remove(*inspector.table.selection())
        busy = True
        control = Control()
        mascot.move("recording" if recording else "playing")
        buttons[0].configure(text="■   Kaydı bitir" if recording else "■   Oynatmayı durdur")
        for button in buttons[1:]:
            button.state(["disabled"])
        status.set("Kaydediliyor" if recording else "Oynatılıyor")
        log("Tarayıcı açılıyor…")

        def worker():
            try:
                def report(msg):
                    events.put(("status", msg))
                run(Path(path), address, report, data=data, credentials=credentials, control=control,
                    on_step=lambda index: events.put(("step", index)))
            except Exception as exc:
                events.put(("error", (str(exc), getattr(exc, "screenshot", None))))
            finally:
                events.put(("done", None))
        threading.Thread(target=worker, daemon=True).start()

    def update():
        nonlocal busy, active_step
        while not events.empty():
            kind, value = events.get()
            if kind == "done":
                busy = False
                for field_entry in fields:
                    field_entry.configure(state="normal")
                url.configure(state="normal")
                if inspector:
                    inspector.set_busy(False)
                if status.get() != "Hata":
                    mascot.move("idle")
                    status.set("Hazır")
                buttons[0].configure(text="Kaydı başlat")
                for button in buttons:
                    button.state(["!disabled"])
            elif kind == "step":
                active_step = value
                if value is not None:
                    inspector.highlight(value)
            elif kind == "error":
                message, screenshot = value
                if active_step is not None:
                    inspector.highlight(active_step)
                    inspector.show_message(f"{active_step}. adımda hata · {message}", error=True)
                    inspector.show_screenshot(screenshot)
                    inspector.deiconify()
                if screenshot:
                    message += f"\n\nEkran görüntüsü kaydedildi: {screenshot.name}"
                mascot.move("fail")
                status.set("Hata")
                log(message)
                messagebox.showerror("Clicker Bot", message)
            else:
                log(value)
        root.after(100, update)

    actions = ttk.Frame(panel)
    actions.pack(fill="x", pady=(20, 0))
    buttons = [ttk.Button(actions, style="Primary.TButton", text="Kaydı başlat", command=lambda: stop() if busy else start(True)),
               ttk.Button(tk.Frame(actions, bg=theme.BORDER), style="Outline.TButton", text="Kayıt dosyasını oynat",
                          command=lambda: open_recording(True)),
               ttk.Button(actions, style="Text.TButton", text="Kaydı incele", command=lambda: open_recording(False))]
    actions.rowconfigure(0, minsize=48)
    for col, button in enumerate(buttons):
        actions.columnconfigure(col * 2, weight=1, uniform="actions")
        if button.master is actions:
            button.grid(row=0, column=col * 2, sticky="nsew")
        else:  # outlined button: its frame supplies the 1px border
            button.master.grid(row=0, column=col * 2, sticky="nsew")
            button.pack(fill="both", expand=True, padx=1, pady=1)
        if col < len(buttons) - 1:
            actions.columnconfigure(col * 2 + 1, minsize=14)
    journal = tk.Frame(sidebar, bg=white, highlightbackground=theme.BORDER, highlightthickness=1)
    journal.pack(fill="both", expand=True, padx=7, pady=16)
    tk.Label(journal, text="∿    İşlem günlüğü", bg=theme.MUTED_SURFACE, fg=ink,
             anchor="w", padx=14, pady=8).pack(fill="x")
    history = tk.Text(journal, height=3, width=1, bg=white, fg=ink, wrap="word",
                      relief="flat", highlightthickness=0, padx=12, pady=8, state="disabled")
    history.pack(fill="both", expand=True)
    empty = tk.Label(history, text="Henüz bir işlem yok.", bg=white, fg=muted)
    empty.place(relx=.5, rely=.5, anchor="center")

    def log(message):
        empty.place_forget()
        history.configure(state="normal")
        history.insert("end", message + "\n")
        history.see("end")
        history.configure(state="disabled")

    ttk.Frame(panel).pack(fill="both", expand=True)
    tk.Frame(panel, height=1, bg=theme.BORDER).pack(fill="x")
    footer = ttk.Frame(panel)
    footer.pack(fill="x", pady=(10, 0))
    ttk.Label(footer, text="Durum", foreground=muted).pack(side="left")
    badge = tk.Label(footer, padx=8, pady=3)
    badge.pack(side="left", padx=8)

    def paint_status(*_):
        ready = status.get() == "Hazır"
        badge.configure(text="● " + status.get(), bg=theme.SUCCESS_SURFACE if ready else theme.SELECTED,
                        fg=theme.SUCCESS if ready else theme.RED)
    status.trace_add("write", paint_status)
    paint_status()

    def close():
        if busy:
            messagebox.showinfo("Clicker Bot", "Önce tarayıcıdaki Bitir veya Durdur düğmesini kullan.")
        elif inspector is None or inspector.confirm_discard():
            root.destroy()
    root.protocol("WM_DELETE_WINDOW", close)
    update()
    root.mainloop()


if __name__ == "__main__":
    main()
