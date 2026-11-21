import tkinter as tk
from tkinter import ttk


class RecordingInspector(tk.Toplevel):
    def __init__(self, parent, path, data, replay):
        super().__init__(parent)
        self.title(f"Kayıt adımları · {path.name}")
        self.geometry("760x400")
        self.protocol("WM_DELETE_WINDOW", self.withdraw)
        panel = ttk.Frame(self, padding=14)
        panel.pack(fill="both", expand=True)
        ttk.Label(panel, text=f"{path.name} · {len(data['steps'])} adım").pack(anchor="w")
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
        for index, step in enumerate(data["steps"], 1):
            value = "Enter" if step["action"] == "keydown" else step.get("value", "")
            self.table.insert("", "end", iid=str(index),
                              values=(index, step["action"], step["selector"], value))
        self.detail = tk.StringVar()
        ttk.Label(panel, textvariable=self.detail, wraplength=680).pack(anchor="w")
        self.play_button = ttk.Button(panel, text="Bu kaydı oynat", command=replay)
        self.play_button.pack(anchor="e")

    def highlight(self, index):
        row = str(index)
        self.table.selection_set(row)
        self.table.focus(row)
        self.table.see(row)
