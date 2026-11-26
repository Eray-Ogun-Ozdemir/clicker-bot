import argparse
import sys
import json
import random
import re
import threading
import time
import uuid
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import Error as PlaywrightError, TimeoutError as PlaywrightTimeout, sync_playwright


CLICK_COORDINATES = ("x", "y", "scrollX", "scrollY")
OVERLAY = Path(__file__).with_name("overlay.js")
DEFAULT_TIMEOUT = 5  # seconds each step may wait for its page and target
MAX_TIMEOUT = 300
MAX_HOLD = 30  # seconds a hold step may keep the mouse button down
KEEP_SCREENSHOTS = 5  # failure screenshots kept per recording
ACTION_LABELS = {"click": "Tıklama", "input": "Yazı", "select": "Liste seçimi", "keydown": "Enter",
                 "password": "Parola", "wait": "Bekleme", "sleep": "Sabit bekleme", "assert": "Doğrulama", "scroll": "Kaydırma",
                 "hover": "Üzerine gelme", "hold": "Basılı tutma", "dblclick": "Çift tıklama",
                 "rightclick": "Sağ tıklama", "press": "Tuşa basma", "drag": "Sürükle-bırak"}
# Steps that may leave the selector empty to act on the page as a whole.
PAGE_ACTIONS = ("scroll", "press")


def step_label(step):
    """The Turkish name of a step, as the app, the log and the in-browser bar show it."""
    if step["action"] == "assert":
        return "Adres doğrulaması" if step.get("kind") == "url" else "Metin doğrulaması"
    return ACTION_LABELS.get(step["action"], step["action"])


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


class StepFailure(ValueError):
    """A step that ran but did not find what it expected on the page."""

    def __init__(self, message, expected, actual):
        super().__init__(f"{message}\nBeklenen: {expected}\nGerçekte: {actual}")
        self.expected, self.actual = expected, actual


def normalize(text):
    return " ".join(text.split())


def shorten(text, limit=160):
    return text if len(text) <= limit else text[:limit - 1] + "…"


def check(page, step):
    """Whether an assert step holds right now, and what the page shows instead when it does not."""
    if step["kind"] == "url":
        return page.url.startswith(step["expected"]), page.url
    expected = normalize(step["expected"])
    texts = [normalize(text) for text in page.locator(step["selector"]).all_inner_texts()]
    if any(expected in text for text in texts):
        return True, None
    return False, f'"{shorten(texts[0])}"' if texts else "Hedefle eşleşen öğe yok"


def failure_screenshot(page, file):
    """Save what the page shows next to the recording; None when the page cannot be captured."""
    path = file.with_name(f"{file.stem}-hata-{time.strftime('%Y%m%d-%H%M%S')}.png")
    try:
        page.screenshot(path=str(path))
    except PlaywrightError:
        return None
    prune_screenshots(file)
    return path


def prune_screenshots(file, keep=KEEP_SCREENSHOTS):
    """Delete all but the newest failure screenshots of a recording."""
    pattern = re.compile(re.escape(file.stem) + r"-hata-\d{8}-\d{6}\.png")
    shots = sorted(p for p in file.parent.iterdir() if pattern.fullmatch(p.name))  # names sort by time
    for old in shots[:-keep]:
        old.unlink(missing_ok=True)


def valid_timeout(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and 0 < value <= MAX_TIMEOUT


def step_timeout(data, step):
    """Seconds a step may wait: a wait step's own limit, otherwise the recording's."""
    return step.get("timeout") or data.get("timeout") or DEFAULT_TIMEOUT


def format_seconds(value):
    return f"{value:g}"


def play(page, step, timeout=DEFAULT_TIMEOUT, stopped=lambda: False):
    if step["action"] == "sleep":
        # Wait in short slices so Durdur ends it at once.
        end = time.monotonic() + step["seconds"]
        while not stopped() and (left := end - time.monotonic()) > 0:
            page.wait_for_timeout(min(200, left * 1000))
        return
    if step["action"] == "assert":
        verify(page, step, timeout, stopped)
        return
    try:
        perform(page, step, timeout * 1000)
    except PlaywrightTimeout:
        seconds = format_seconds(timeout)
        if step["action"] != "wait" and page.url != step["url"]:
            raise ValueError(f"Sayfa {seconds} sn içinde beklenen adrese geçmedi: {step['url']}") from None
        if step["action"] == "drag":
            raise ValueError(f"Sürüklenecek hedef veya bırakılacak yer {seconds} sn içinde hazır olmadı: "
                             f"{step['selector']} → {step['to']}") from None
        raise ValueError(f"Hedef {seconds} sn içinde hazır olmadı: {step['selector']}") from None
    except PlaywrightError as exc:
        if step["action"] == "press" and "Unknown key" in str(exc):
            raise ValueError(f"Bilinmeyen tuş: {step['key']}") from None
        raise


def verify(page, step, timeout, stopped):
    # Pages keep loading after the previous step, so give the check until the timeout to hold.
    deadline = time.monotonic() + timeout
    while True:
        try:
            passed, actual = check(page, step)
        except PlaywrightError:  # the page is navigating; look again
            passed, actual = False, "Sayfa yükleniyordu"
        if passed:
            return
        if stopped() or time.monotonic() >= deadline:
            break
        try:
            page.wait_for_timeout(200)
        except PlaywrightError:
            break
    seconds = format_seconds(timeout)
    if step["kind"] == "url":
        raise StepFailure(f"Sayfa adresi {seconds} sn içinde beklenen adrese ulaşmadı.",
                          f"{step['expected']} ile başlayan adres", actual)
    raise StepFailure(f"Beklenen metin {seconds} sn içinde görünmedi.",
                      f"{step['selector']} içinde \"{step['expected']}\"", actual)


def perform(page, step, timeout):
    target = page.locator(step["selector"])
    if step["action"] == "wait":
        # Several matches are fine: the step only waits until one of them shows up.
        target.first.wait_for(state="visible", timeout=timeout)
        return
    page.wait_for_url(lambda url: url == step["url"], timeout=timeout)
    if step["action"] == "password":
        origin = origin_of(step["url"])
        password = credential_store().get_password(credential_service(step["url"]), step["credential"])
        if password is None:
            raise ValueError("Bu kayıt için cihazda saklanan parola bulunamadı. "
                             "Kaydı incele penceresindeki Parolayı gir ile ekleyebilirsin.")
        fill_password(target, origin, password)
    elif step["action"] == "input":
        target.fill(step["value"], timeout=timeout)
    elif step["action"] == "select":
        target.select_option(value=step["values"], timeout=timeout)
    elif step["action"] == "keydown":
        target.press("Enter", timeout=timeout)
    elif step["action"] == "scroll":
        if step["selector"]:
            target.scroll_into_view_if_needed(timeout=timeout)
        else:
            page.mouse.wheel(0, step["amount"])
    elif step["action"] == "hover":
        target.hover(timeout=timeout)
    elif step["action"] == "dblclick":
        target.dblclick(timeout=timeout)
    elif step["action"] == "rightclick":
        target.click(button="right", timeout=timeout)
    elif step["action"] == "press":
        if step["selector"]:
            target.press(step["key"], timeout=timeout)
        else:
            page.keyboard.press(step["key"])
    elif step["action"] == "drag":
        target.drag_to(page.locator(step["to"]), timeout=timeout)
    elif step["action"] == "hold":
        target.scroll_into_view_if_needed(timeout=timeout)
        box = target.bounding_box(timeout=timeout)
        if box is None:
            raise ValueError(f"Basılı tutulacak hedef görünmüyor: {step['selector']}")
        page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        page.mouse.down()
        try:
            page.wait_for_timeout(step["duration"] * 1000)
        finally:
            page.mouse.up()
    elif step["action"] == "click":
        if target.count() == 1 or not all(key in step for key in CLICK_COORDINATES):
            target.click(position=step.get("position"), timeout=timeout)
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


def valid_step_fields(step):
    """Check the fields the newer interaction steps need; older step types pass through."""
    action, selector = step["action"], step["selector"]
    if action in ("hover", "hold", "dblclick", "rightclick", "drag") and not selector:
        return False
    if action == "scroll":
        amount = step.get("amount")
        return bool(selector) or (isinstance(amount, int) and not isinstance(amount, bool) and amount != 0)
    if action == "press":
        return isinstance(step.get("key"), str) and bool(step["key"].strip())
    if action == "drag":
        return isinstance(step.get("to"), str) and bool(step["to"].strip())
    if action == "sleep":
        return valid_timeout(step.get("seconds"))
    if action == "hold":
        duration = step.get("duration")
        return isinstance(duration, (int, float)) and not isinstance(duration, bool) and 0 < duration <= MAX_HOLD
    return True


def load_recording(file):
    data = json.loads(file.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or not isinstance(data.get("steps"), list):
        raise ValueError("Kayıtta adım listesi bulunamadı.")
    for index, step in enumerate(data["steps"], 1):
        if not isinstance(step, dict) or not all(isinstance(step.get(k), str)
                                                for k in ("action", "selector", "url")):
            raise ValueError(f"{index}. adım geçersiz.")
        if "timeout" in step and not (step["action"] == "wait" and valid_timeout(step["timeout"])):
            raise ValueError(f"{index}. adımın bekleme süresi geçersiz.")
        if not valid_step_fields(step):
            raise ValueError(f"{index}. adımın ({step_label(step)}) bilgileri eksik veya geçersiz.")
        if step["action"] == "assert" and not (
                step.get("kind") in ("text", "url") and isinstance(step.get("expected"), str)
                and step["expected"] and (step["kind"] == "url" or step["selector"])):
            raise ValueError(f"{index}. adımdaki doğrulama eksik.")
    if "timeout" in data and not valid_timeout(data["timeout"]):
        raise ValueError(f"Zaman aşımı 0 ile {MAX_TIMEOUT} sn arasında olmalı.")
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
                state["text"] = f"{index}/{total}. adım · {step_label(step)}"
                overlay(page, "progress", state["text"])
                status(f"{index}. adım: {step_label(step)}")
                # Hide the bar so it never covers the element being clicked.
                overlay(page, "visible", False)
                try:
                    play(page, step, step_timeout(data, step), lambda: control.stopped)
                except Exception as exc:
                    if control.stopped:  # the page was closed or stop was pressed mid-step
                        break
                    if data.get("failureScreenshot") and file is not None:
                        exc.screenshot = failure_screenshot(page, file)
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
