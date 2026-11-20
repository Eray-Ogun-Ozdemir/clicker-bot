import argparse
import sys
import json
import random
import time
from pathlib import Path
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright


def play(page, step):
    page.wait_for_url(lambda url: url == step["url"], timeout=5000)
    target = page.locator(step["selector"])
    if step["action"] == "input":
        target.fill(step["value"], timeout=5000)
    elif step["action"] == "keydown":
        target.press("Enter", timeout=5000)
    elif step["action"] == "click":
        if target.count() == 1:
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


def run(file, url_to_record=None, status=print, console=False):
    recording = url_to_record is not None
    if recording:
        if file.exists():
            raise ValueError("Bu kayıt adı kullanılıyor. Yeni bir dosya adı seç.")
        data = {"url": url_to_record, "steps": [], "viewport": {"width": 1280, "height": 800}}
    else:
        data = json.loads(file.read_text(encoding="utf-8"))
    url = urlsplit(data["url"])
    if url.scheme not in ("http", "https") or not url.hostname:
        raise ValueError("http veya https bağlantısı gir.")
    with sync_playwright() as driver:
        channel = "chrome" if sys.platform == "darwin" else None
        browser = driver.chromium.launch(channel=channel, headless=False)
        page = browser.new_page(viewport=data["viewport"])
        if recording:
            def capture(source, step):
                if source["frame"] != page.main_frame:
                    return
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
            status("Kayıt başladı. Bitirmek için kayıt sekmesini kapat.")
            with page.expect_event("close", timeout=0):
                pass
            with file.open("x", encoding="utf-8") as output:
                json.dump(data, output, ensure_ascii=False, indent=2)
            status(f'{len(data["steps"])} adım kaydedildi: {file}')
        else:
            for index, step in enumerate(data["steps"], 1):
                if index > 1:
                    time.sleep(random.uniform(1, 2))
                status(f'{index}. adım: {step["action"]}')
                play(page, step)
            browser.close()
            status("Oynatma tamamlandı. Tarayıcı kapatıldı.")


if __name__ == "__main__":
    main()
