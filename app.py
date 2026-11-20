import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from urllib.parse import urlsplit

from recorder import run


def main():
    root = tk.Tk()
    root.title("Clicker Bot")
    logo_path = Path(__file__).with_name("logo.png")
    if logo_path.is_file():
        logo = tk.PhotoImage(file=str(logo_path))
        root.iconphoto(True, logo)
    white = "#ffffff"
    ink = "#302a29"
    muted = "#675f5c"
    red = "#c23430"
    root.configure(bg=white)
    root.minsize(600, 650)
    root.geometry("840x720")
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=white)
    style.configure("TLabel", background=white, foreground=ink)
    style.configure("TRadiobutton", background=white, foreground=ink)
    style.configure("TEntry", fieldbackground=white, foreground=ink, padding=9)
    style.map("TEntry", bordercolor=[("focus", red)])
    for name, background, foreground, hover in (
        ("Record.TButton", red, white, "#a62c28"),
        ("Play.TButton", "#f7f4f2", ink, "#eee8e5"),
    ):
        style.configure(name, background=background, foreground=foreground,
                        font=("Helvetica", 13, "bold"), padding=(16, 11), borderwidth=0)
        style.map(name, background=[("disabled", "#eeeae8"), ("active", hover)],
                  foreground=[("disabled", muted)])
    panel = ttk.Frame(root, padding=(40, 18))
    panel.pack(fill="both", expand=True)
    header = ttk.Frame(panel)
    header.pack(fill="x")
    if logo_path.is_file():
        mascot = logo.subsample(5)
        ttk.Label(header, image=mascot).pack(side="right")
    title = ttk.Frame(header)
    title.pack(side="left")
    ttk.Label(title, text="➤   MASAÜSTÜ YARDIMCISI", foreground=muted,
              font=("Helvetica", 10, "bold")).pack(anchor="w")
    ttk.Label(title, text="Clicker Bot", font=("Helvetica", 38, "bold")).pack(anchor="w", pady=8)
    tk.Frame(title, width=34, height=3, bg=red).pack(anchor="w")
    tk.Frame(panel, height=1, bg="#e5dfdb").pack(fill="x", pady=(16, 18))

    def section(number, title):
        row = ttk.Frame(panel)
        row.pack(fill="x")
        badge = tk.Canvas(row, width=26, height=26, bg=white, highlightthickness=0)
        badge.pack(side="left")
        badge.create_oval(1, 1, 24, 24, outline="#ddd6d2")
        badge.create_text(13, 13, text=number, fill=muted, font=("Helvetica", 10))
        ttk.Label(row, text=title, font=("Helvetica", 15, "bold")).pack(side="left", padx=8)

    section("01", "Başlangıç")
    ttk.Label(panel, text="Başlangıç URL’si").pack(anchor="w", pady=(12, 5))
    field = tk.Frame(panel, bg=white, highlightthickness=1, highlightbackground="#ded7d3")
    field.pack(fill="x")
    tk.Label(field, text="◎", fg=muted, bg=white).pack(side="left", padx=12)
    url = tk.Entry(field, relief="flat", bg=white, fg=ink, insertbackground=ink,
                   highlightthickness=0, font=("Helvetica", 14))
    url.pack(side="left", fill="x", expand=True, ipady=11)
    hint = tk.Label(url, text="https://example.com", bg=white, fg="#a29b96")
    hint.place(x=3, rely=0.5, anchor="w")
    hint.bind("<Button-1>", lambda _: url.focus_set())
    address_text = tk.StringVar()
    url.configure(textvariable=address_text)
    def show_hint(*_):
        if address_text.get():
            hint.place_forget()
        else:
            hint.place(x=3, rely=0.5, anchor="w")
    address_text.trace_add("write", show_hint)
    url.bind("<FocusIn>", lambda _: field.configure(highlightbackground=red))
    url.bind("<FocusOut>", lambda _: field.configure(highlightbackground="#ded7d3"))
    url.focus_set()
    ttk.Frame(panel, height=18).pack()
    section("02", "Hazırlama yöntemi")
    modes = ttk.Frame(panel)
    modes.pack(fill="x", pady=(10, 0))
    for column, (label, bg, border, color) in enumerate([
            ("●    Kaydederek hazırla", "#fff8f7", "#eea19a", red),
            ("○    Manuel hazırla     ·  yakında", "#f8f7f6", "#e4dfdb", "#938d88")]):
        modes.columnconfigure(column, weight=1, uniform="cards")
        tk.Label(modes, text=label, anchor="w", padx=15, pady=15, bg=bg, fg=color,
                 highlightbackground=border, highlightthickness=1).grid(
                     row=0, column=column, sticky="ew", padx=(0, 6) if column == 0 else (6, 0))
    status = tk.StringVar(value="Hazır")
    events = queue.Queue()
    busy = False

    def start(recording):
        nonlocal busy
        address = url.get().strip() if recording else None
        if recording:
            try:
                parsed = urlsplit(address)
                if parsed.scheme not in ("http", "https") or not parsed.hostname:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Adres", "http:// veya https:// ile başlayan bir URL gir.")
                return
        options = {"filetypes": [("Bot kaydı", "*.json")]}
        path = (filedialog.asksaveasfilename(defaultextension=".json", **options)
                if recording else filedialog.askopenfilename(**options))
        if not path:
            return
        busy = True
        for button in buttons:
            button.state(["disabled"])
        status.set("Kaydediliyor" if recording else "Oynatılıyor")
        log("Tarayıcı açılıyor…")

        def worker():
            try:
                def report(msg):
                    events.put(("status", msg))
                run(Path(path), address, report)
            except Exception as exc:
                events.put(("error", str(exc)))
            finally:
                events.put(("done", None))
        threading.Thread(target=worker, daemon=True).start()

    def update():
        nonlocal busy
        while not events.empty():
            kind, value = events.get()
            if kind == "done":
                busy = False
                if status.get() != "Hata":
                    status.set("Hazır")
                for button in buttons:
                    button.state(["!disabled"])
            elif kind == "error":
                status.set("Hata")
                log(value)
                messagebox.showerror("Clicker Bot", value)
            else:
                log(value)
        root.after(100, update)

    actions = ttk.Frame(panel)
    actions.pack(fill="x", pady=(20, 0))
    buttons = [ttk.Button(actions, style="Record.TButton", text="Kaydı başlat", command=lambda: start(True)),
               ttk.Button(actions, style="Play.TButton", text="Kayıt dosyasını oynat", command=lambda: start(False))]
    for col, button in enumerate(buttons):
        actions.columnconfigure(col, weight=1, uniform="actions")
        button.grid(row=0, column=col, sticky="ew", padx=(0, 6) if col == 0 else (6, 0))
    journal = tk.Frame(panel, bg=white, highlightbackground="#e4dfdb", highlightthickness=1)
    journal.pack(fill="both", expand=True, pady=18)
    tk.Label(journal, text="∿    İşlem günlüğü", bg="#f8f7f6", fg=ink,
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

    tk.Frame(panel, height=1, bg="#e5dfdb").pack(fill="x")
    footer = ttk.Frame(panel)
    footer.pack(fill="x", pady=(10, 0))
    ttk.Label(footer, text="Durum", foreground=muted).pack(side="left")
    tk.Label(footer, textvariable=status, bg="#edf8ef", fg="#277b43",
             padx=8, pady=3).pack(side="left", padx=8)

    def close():
        if busy:
            messagebox.showinfo("Clicker Bot", "Önce işlem yapılan tarayıcı sekmesini kapat.")
        else:
            root.destroy()
    root.protocol("WM_DELETE_WINDOW", close)
    update()
    root.mainloop()


if __name__ == "__main__":
    main()
