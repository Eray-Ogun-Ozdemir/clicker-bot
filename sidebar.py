"""The sidebar's KOLEKSİYONLAR tree: collections of recordings, opened by name."""
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, simpledialog, ttk

import theme


class NameDialog(simpledialog.Dialog):
    """Ask for a collection name, checked by the library before the dialog closes."""

    def __init__(self, parent, title, check, value=""):
        self.check = check
        self.value = value
        super().__init__(parent, title=title)

    def body(self, master):
        self.configure(bg=theme.BG)
        master.configure(bg=theme.BG, padx=10, pady=6)
        master.pack_configure(fill="both", expand=True)
        tk.Label(master, text=self.title(), bg=theme.BG, fg=theme.INK, font=theme.font(17, True)).pack(anchor="w")
        theme.divider(master, pady=(10, 12))
        tk.Label(master, text="Koleksiyon adı", bg=theme.BG, fg=theme.INK,
                 font=theme.font(12, True)).pack(anchor="w", pady=(0, 6))
        holder, self.name = theme.entry(master, self.value, width=36)
        holder.pack(fill="x")
        self.name.select_range(0, "end")
        self.error = tk.Label(master, bg=theme.BG, fg=theme.RED, font=theme.font(12), anchor="w")
        return self.name

    def buttonbox(self):
        box = tk.Frame(self, bg=theme.BG, padx=20, pady=16)
        box.pack(fill="x")
        save, _ = theme.button(box, "Kaydet", self.ok, "Primary", "Medium.")
        save.pack(side="right")
        cancel, _ = theme.button(box, "İptal", self.cancel, "Outline", "Medium.")
        cancel.pack(side="right", padx=(0, 8))
        self.name.bind("<Return>", self.ok)
        self.bind("<Escape>", self.cancel)

    def validate(self):
        try:
            self.result = self.check(self.name.get())
        except ValueError as exc:
            self.error.configure(text=f"⚠  {exc}")
            self.error.pack(anchor="w", fill="x", pady=(10, 0))
            return False
        return True


def ask_collection_name(parent, library, title="Yeni koleksiyon", current=None):
    """The checked new name, or None when cancelled."""
    check = (lambda name: library.check_name(name, current=current))
    return NameDialog(parent, title, check, current or "").result


class CollectionsPanel(tk.Frame):
    def __init__(self, parent, library, open_path, busy=lambda: False):
        super().__init__(parent, bg=theme.SIDEBAR)
        self.library = library
        self.open_path = open_path  # open_path(path, autoplay)
        self.busy = busy
        self.items = {}  # tree item id -> (collection name, recording path or None)
        header = tk.Frame(self, bg=theme.SIDEBAR)
        header.pack(fill="x", padx=(14, 7), pady=(14, 4))
        tk.Label(header, text="KOLEKSİYONLAR", bg=theme.SIDEBAR, fg=theme.MUTED,
                 font=theme.font(10, True)).pack(side="left")
        holder, self.new_button = theme.button(header, "+", self.new_collection, "Text", "Small.")
        holder.configure(bg=theme.SIDEBAR)
        holder.pack(side="right")
        self.tree = ttk.Treeview(self, show="tree", selectmode="browse", style="Sidebar.Treeview", height=7)
        self.tree.pack(fill="x", padx=(7, 7))
        self.empty = tk.Label(self, text="Henüz koleksiyon yok.\n+ ile bir tane oluştur.", bg=theme.SIDEBAR,
                              fg=theme.HINT, font=theme.font(11), justify="left")
        self.menu = tk.Menu(self, tearoff=False)
        self.tree.bind("<Double-1>", lambda e: self.activate(self.tree.identify_row(e.y)))
        self.tree.bind("<Return>", lambda e: self.activate(self.tree.focus()))
        for key in ("<Delete>", "<BackSpace>"):
            self.tree.bind(key, lambda e: self.remove_selected())
        for button in ("<Button-2>", "<Button-3>", "<Control-Button-1>"):  # right-click on macOS and Windows
            self.tree.bind(button, self.show_menu)
        library.on_change(self.refresh)
        theme.on_palette_change(self.refresh)
        self.refresh()

    # Contents

    def refresh(self):
        closed = {self.items[i][0] for i in self.tree.get_children() if not self.tree.item(i, "open")}
        chosen = self.items.get(self.tree.focus())
        self.tree.delete(*self.tree.get_children())
        self.items = {}
        self.tree.tag_configure("missing", foreground=theme.HINT)
        for name in self.library.names():
            node = self.tree.insert("", "end", text=f"▤  {name}", open=name not in closed)
            self.items[node] = (name, None)
            for path in self.library.recordings(name):
                missing = not path.is_file()
                leaf = self.tree.insert(node, "end", text=("⚠ " if missing else "") + path.stem,
                                        tags=("missing",) if missing else ())
                self.items[leaf] = (name, path)
        for item, value in self.items.items():
            if value == chosen:
                self.tree.selection_set(item)
                self.tree.focus(item)
        if self.items:
            self.empty.pack_forget()
        else:
            self.empty.pack(anchor="w", padx=14, pady=(4, 0))

    def selected_collection(self):
        """The collection that is selected, or holds the selected recording; None when nothing is."""
        value = self.items.get(self.tree.focus()) if self.tree.selection() else None
        return value[0] if value else None

    # Actions

    def activate(self, item, autoplay=False):
        if not item or item not in self.items:
            return
        name, path = self.items[item]
        if path is None:
            self.tree.item(item, open=not self.tree.item(item, "open"))
            return
        if not path.is_file():
            if messagebox.askyesno("Kayıt bulunamadı",
                                   f"{path} artık yok; taşınmış ya da silinmiş olabilir. "
                                   f"{name} koleksiyonundan çıkarılsın mı?", parent=self):
                self.library.remove(name, path)
            return
        self.open_path(path, autoplay)

    def new_collection(self):
        name = ask_collection_name(self, self.library)
        if name:
            self.library.add_collection(name)
            self.select_collection(name)

    def select_collection(self, name):
        for item, value in self.items.items():
            if value == (name, None):
                self.tree.selection_set(item)
                self.tree.focus(item)
                self.tree.see(item)

    def add_recordings(self, name):
        files = filedialog.askopenfilenames(parent=self, title=f"{name} koleksiyonuna kayıt ekle",
                                            filetypes=[("Bot kaydı", "*.json")])
        for file in files:
            self.library.add(name, Path(file))

    def rename(self, name):
        new_name = ask_collection_name(self, self.library, "Koleksiyonu yeniden adlandır", current=name)
        if new_name and new_name != name:
            self.library.rename_collection(name, new_name)

    def remove_selected(self):
        value = self.items.get(self.tree.focus()) if self.tree.selection() else None
        if not value:
            return
        name, path = value
        if path is not None:
            self.library.remove(name, path)
        elif messagebox.askyesno("Koleksiyonu sil",
                                 f"{name} koleksiyonu silinecek. İçindeki kayıt dosyaları silinmez. Devam edilsin mi?",
                                 parent=self):
            self.library.remove_collection(name)

    def show_menu(self, event):
        item = self.tree.identify_row(event.y)
        self.menu.delete(0, "end")
        if item:
            self.tree.selection_set(item)
            self.tree.focus(item)
            name, path = self.items[item]
            idle = "normal" if not self.busy() else "disabled"
            if path is not None:
                self.menu.add_command(label="Aç", command=lambda: self.activate(item), state=idle)
                self.menu.add_command(label="Oynat", command=lambda: self.activate(item, autoplay=True), state=idle)
                self.menu.add_separator()
                self.menu.add_command(label="Koleksiyondan çıkar", command=lambda: self.library.remove(name, path))
            else:
                self.menu.add_command(label="Kayıt ekle…", command=lambda: self.add_recordings(name))
                self.menu.add_command(label="Yeniden adlandır…", command=lambda: self.rename(name))
                self.menu.add_separator()
                self.menu.add_command(label="Koleksiyonu sil", command=self.remove_selected)
        else:
            self.menu.add_command(label="Yeni koleksiyon…", command=self.new_collection)
        self.menu.tk_popup(event.x_root, event.y_root)
