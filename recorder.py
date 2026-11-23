import argparse
import sys
import json
import random
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError, sync_playwright


CLICK_COORDINATES = ("x", "y", "scrollX", "scrollY")
OVERLAY = Path(__file__).with_name("overlay.js")


class Control:
    """Stop request shared by the Tk thread, the in-browser bar and the Playwright thread."""

    def __init__(self):
        self.event = threading.Event()
        self.cancelled = False

    def stop(self, cancel=False):
        self.cancelled = self.cancelled or cancel
        self.event.set()

    @property
    def stopped(self):
        return self.event.is_set()


def overlay(page, name, value):
    # The page may be navigating or closed; the bar is a convenience, never a failure.
    try:
        page.evaluate("([name, value]) => window.__clickerBotOverlay?.[name](value)", [name, value])
    except PlaywrightError:
        pass


def pause(page, seconds, control):
    # Wait through Playwright so clicks on the in-browser bar are still delivered.
    end = time.monotonic() + seconds
    while not control.stopped and (left := end - time.monotonic()) > 0:
        try:
            page.wait_for_timeout(min(200, left * 1000))
        except PlaywrightError:
            return


def credential_store():
    if sys.platform == "darwin":
        from mac_credentials import Keyring
        return Keyring()
    if sys.platform == "win32":
        from keyring.backends.Windows import WinVaultKeyring
        return WindowsStore(WinVaultKeyring())
    raise ValueError("Parola saklama macOS ve Windows üzerinde destekleniyor.")


class WindowsStore:
    """Credential Manager with the same delete_password contract as mac_credentials."""

    def __init__(self, backend):
        self.backend = backend
        self.get_password = backend.get_password
        self.set_password = backend.set_password

    def has_password(self, service, account):
        return self.backend.get_password(service, account) is not None

    def delete_password(self, service, account):
        from keyring.errors import PasswordDeleteError
        try:
            self.backend.delete_password(service, account)
        except PasswordDeleteError:
            return False
        return True


def credential_service(url):
    return "Clicker Bot " + origin_of(url)


def stored_credentials(data):
    """(service, account) pairs of the passwords a recording refers to."""
    return sorted({(credential_service(step["url"]), step["credential"])
                   for step in data["steps"] if step["action"] == "password" and step.get("credential")})


def missing_credentials(data):
    """The recording's password references that have no stored password on this device."""
    pairs = stored_credentials(data)
    if not pairs:
        return []
    store = credential_store()
    return [pair for pair in pairs if not store.has_password(*pair)]


def save_credentials(data, password):
    """Store (or replace) the password for every password step of the recording on this device."""
    pairs = stored_credentials(data)
    if not password or not pairs:
        raise ValueError("Kaydedilecek parola bulunamadı.")
    store = credential_store()
    for service, account in pairs:
        store.delete_password(service, account)
        store.set_password(service, account, password)
    return len(pairs)


def delete_credentials(data):
    """Remove the recording's passwords from this device. Returns how many were found."""
    pairs = stored_credentials(data)
    if not pairs:
        return 0
    store = credential_store()
    return sum(store.delete_password(service, account) for service, account in pairs)


def origin_of(url):
    parts = urlsplit(url)
    if parts.scheme != "https" or not parts.hostname:
        raise ValueError("Parola kullanmak için HTTPS adresi gerekli.")
    return "https://" + parts.netloc.lower()


def fill_password(target, origin, password):
    # Check the document and field in the same call that writes the secret.
    ok = target.evaluate("""(el, [origin, value]) => {
        if (location.origin !== origin || !(el instanceof HTMLInputElement)
            || el.type !== 'password') return false;
        const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
        setter.call(el, value);
        el.dispatchEvent(new Event('input', {bubbles:true}));
        el.dispatchEvent(new Event('change', {bubbles:true}));
        return true;
    }""", [origin, password])
    if not ok:
        raise ValueError("Parola alanı veya site adresi değişti.")


def play(page, step):
    page.wait_for_url(lambda url: url == step["url"], timeout=5000)
    target = page.locator(step["selector"])
    if step["action"] == "password":
        origin = origin_of(step["url"])
        password = credential_store().get_password(credential_service(step["url"]), step["credential"])
        if password is None:
            raise ValueError("Bu kayıt için cihazda saklanan parola bulunamadı. "
                             "Kaydı incele penceresindeki Parolayı gir ile ekleyebilirsin.")
        fill_password(target, origin, password)
    elif step["action"] == "input":
        target.fill(step["value"], timeout=5000)
    elif step["action"] == "select":
        target.select_option(value=step["values"], timeout=5000)
    elif step["action"] == "keydown":
        target.press("Enter", timeout=5000)
    elif step["action"] == "click":
        if target.count() == 1 or not all(key in step for key in CLICK_COORDINATES):
            target.click(position=step.get("position"), timeout=5000)
        else:
            page.evaluate("p => window.scrollTo(p)", {
                "left": step["scrollX"], "top": step["scrollY"], "behavior": "instant"
            })
            page.mouse.click(step["x"], step["y"])
    else:
        raise ValueError("Bilinmeyen işlem")


def main():
    parser = argparse.ArgumentParser(description="Tarayıcı hareketlerini kaydet ve oynat")
    modes = parser.add_subparsers(dest="mode", required=True)
    record = modes.add_parser("record")
    record.add_argument("url")
    for command in (record, modes.add_parser("play")):
        command.add_argument("file", type=Path)
    args = parser.parse_args()
    try:
        run(args.file, getattr(args, "url", None), console=True)
    except ValueError as exc:
        parser.error(str(exc))


def load_recording(file):
    data = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("steps"), list):
        raise ValueError("Kayıtta adım listesi bulunamadı.")
    for index, step in enumerate(data["steps"], 1):
        if not isinstance(step, dict) or not all(isinstance(step.get(k), str)
                                                for k in ("action", "selector", "url")):
            raise ValueError(f"{index}. adım geçersiz.")
    return data


def save_recording(file, data):
    content = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
    output = file.open("xb")
    try:
        with output:
            output.write(content)
    except OSError:
        file.unlink(missing_ok=True)
        raise


def run(file, url_to_record=None, status=print, console=False, *, data=None, on_step=None, credentials=None,
        control=None):
    recording = url_to_record is not None
    if recording:
        if file.exists():
            raise ValueError("Bu kayıt adı kullanılıyor. Yeni bir dosya adı seç.")
        data = {"url": url_to_record, "steps": [], "viewport": {"width": 1280, "height": 800}}
    elif data is None:
        data = load_recording(file)
    url = urlsplit(data["url"])
    if url.scheme not in ("http", "https") or not url.hostname:
        raise ValueError("http veya https bağlantısı gir.")
    control = control or Control()
    state = {"text": ""}
    with sync_playwright() as driver:
        channel = "chrome" if sys.platform == "darwin" else None
        browser = driver.chromium.launch(channel=channel, headless=False)
        page = browser.new_page(viewport=data["viewport"])
        page.on("close", lambda _: control.stop())
        page.expose_binding("clickerBotControl",
                            lambda source, command: control.stop(cancel=command == "cancel"))
        page.expose_function("clickerBotState", lambda: state["text"])
        page.add_init_script(script=f"window.__clickerBotMode = {json.dumps('record' if recording else 'play')};\n"
                             + OVERLAY.read_text(encoding="utf-8"))
        if recording:
            references = {}
            def capture(source, step):
                if source["frame"] != page.main_frame:
                    return
                steps = data["steps"]
                if step["action"] == "accountFocus":
                    kind = step.get("kind")
                    if not credentials or not credentials.get(kind) or kind not in ("username", "password"):
                        return
                    if page.url != step["url"] or urlsplit(page.url).scheme != "https" or origin_of(page.url) != origin_of(url_to_record):
                        return
                    target = page.locator(step["selector"])
                    if not target.evaluate("el => el === document.activeElement"):
                        return
                    if kind == "password":
                        fill_password(target, origin_of(page.url), credentials[kind])
                        reference = references.setdefault(kind, str(uuid.uuid4()))
                        steps.append(dict(action=kind, url=step["url"], selector=step["selector"], credential=reference))
                    else:
                        target.fill(credentials[kind], timeout=3000)
                        # fill() also fires an input event that capture.js may report first; merge with it.
                        add(dict(action="input", url=step["url"], selector=step["selector"], value=credentials[kind]))
                    return
                add(step)

            def add(step):
                steps = data["steps"]
                if step["action"] == "input" and steps and all(
                    steps[-1].get(k) == step[k] for k in ("action", "url", "selector")
                ):
                    steps[-1] = step
                else:
                    steps.append(step)

            page.expose_binding("recordAction", capture)
            page.add_init_script(path=Path(__file__).with_name("capture.js"))
        page.goto(data["url"], wait_until="domcontentloaded")
        if recording:
            status("Kayıt başladı. Bitirmek için tarayıcıdaki Bitir düğmesini kullan.")
            pause(page, float("inf"), control)
            browser.close()
            if control.cancelled:
                status("Kayıt iptal edildi. Dosya oluşturulmadı.")
                return
            # Write the file first: a password is only stored once a recording refers to it.
            save_recording(file, data)
            if "password" in references:
                try:
                    credential_store().set_password(credential_service(url_to_record),
                                                    references["password"], credentials["password"])
                except Exception:
                    file.unlink(missing_ok=True)
                    raise
            status(f'{len(data["steps"])} adım kaydedildi: {file}')
        else:
            total = len(data["steps"])
            for index, step in enumerate(data["steps"], 1):
                if index > 1:
                    pause(page, random.uniform(1, 2), control)
                if control.stopped:
                    break
                if on_step:
                    on_step(index)
                state["text"] = f"{index}/{total}. adım · {step['action']}"
                overlay(page, "progress", state["text"])
                status(f'{index}. adım: {step["action"]}')
                # Hide the bar so it never covers the element being clicked.
                overlay(page, "visible", False)
                try:
                    play(page, step)
                except Exception:
                    if control.stopped:  # the page was closed or stop was pressed mid-step
                        break
                    raise
                overlay(page, "visible", True)
            if on_step:
                on_step(None)
            stopped = control.stopped  # read before close(), whose close event also sets it
            browser.close()
            status("Oynatma durduruldu. Tarayıcı kapatıldı." if stopped
                   else "Oynatma tamamlandı. Tarayıcı kapatıldı.")


if __name__ == "__main__":
    main()
