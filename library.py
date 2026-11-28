"""Collections: named groups of recording files, kept in collections.json next to settings.json.

A collection only remembers where its recordings are. The recording files themselves stay where
they were saved; removing one from a collection, or deleting a collection, never touches them.
"""
import json
from pathlib import Path

import theme

MAX_NAME = 40
# Python lower-cases "İ" to "i" plus a combining dot, so Turkish i/ı/İ/I are folded by hand.
_DOTLESS = str.maketrans({"İ": "i", "I": "i", "ı": "i"})


def same_name(a, b):
    return a.translate(_DOTLESS).casefold() == b.translate(_DOTLESS).casefold()


def library_path():
    return theme.settings_path().with_name("collections.json")


class Library:
    def __init__(self, path=None):
        self.path = Path(path) if path else library_path()
        self.collections = []  # [{"name": str, "recordings": [absolute path str]}]
        self.listeners = []
        self.load()

    # Reading and writing

    def load(self):
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        collections = data.get("collections") if isinstance(data, dict) else None
        self.collections = []
        for item in collections if isinstance(collections, list) else []:
            if not isinstance(item, dict) or not isinstance(item.get("name"), str):
                continue
            recordings = [r for r in item.get("recordings", []) if isinstance(r, str)]
            self.collections.append({"name": item["name"], "recordings": list(dict.fromkeys(recordings))})

    def save(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        temporary.write_text(json.dumps({"collections": self.collections}, ensure_ascii=False, indent=2),
                             encoding="utf-8")
        temporary.replace(self.path)
        for listener in self.listeners:
            listener()

    def on_change(self, callback):
        self.listeners.append(callback)

    # Queries

    def names(self):
        return [c["name"] for c in self.collections]

    def find(self, name):
        for collection in self.collections:
            if collection["name"] == name:
                return collection
        raise ValueError(f"{name} adında bir koleksiyon yok.")

    def recordings(self, name):
        return [Path(r) for r in self.find(name)["recordings"]]

    def containing(self, path):
        key = str(Path(path).resolve())
        return [c["name"] for c in self.collections if key in c["recordings"]]

    # Changes; each one is saved at once

    def check_name(self, name, current=None):
        name = " ".join(name.split())
        if not name:
            raise ValueError("Koleksiyon adı boş olamaz.")
        if len(name) > MAX_NAME:
            raise ValueError(f"Koleksiyon adı en fazla {MAX_NAME} karakter olabilir.")
        if not (current and same_name(name, current)) and any(same_name(name, n) for n in self.names()):
            raise ValueError(f"{name} adında bir koleksiyon zaten var.")
        return name

    def add_collection(self, name):
        name = self.check_name(name)
        self.collections.append({"name": name, "recordings": []})
        self.save()
        return name

    def rename_collection(self, name, new_name):
        new_name = self.check_name(new_name, current=name)
        self.find(name)["name"] = new_name
        self.save()
        return new_name

    def remove_collection(self, name):
        self.collections.remove(self.find(name))
        self.save()

    def add(self, name, path):
        """Add a recording to a collection; False when it was already there."""
        key = str(Path(path).resolve())
        recordings = self.find(name)["recordings"]
        if key in recordings:
            return False
        recordings.append(key)
        self.save()
        return True

    def remove(self, name, path):
        key = str(Path(path).resolve())
        recordings = self.find(name)["recordings"]
        if key in recordings:
            recordings.remove(key)
            self.save()
