# Clicker Bot

Clicker Bot is a Python desktop app for recording browser interactions and replaying them with Playwright. It saves each recording as a local JSON file containing the starting URL, viewport and ordered steps. The desktop interface is in Turkish.

## Run from source

Use Python 3 with Tkinter. Run the commands below from the project directory.

### macOS

Install Google Chrome first. The app launches the installed Chrome browser.

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python app.py
```

After setup, you can also open **Clicker Bot.app** from the project directory. Its launcher uses the adjacent virtual environment.

### Windows

From Command Prompt, install the dependencies and Playwright's Chromium browser.

```bat
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m playwright install chromium
.venv\Scripts\python.exe app.py
```

To build a standalone executable on Windows, run `build-windows.cmd`. The script packages Chromium and the mascot assets into `dist\ClickerBot.exe`.

## Record and replay

1. Enter the starting URL under **Başlangıç URL’si**. Include `http://` or `https://`.
2. Click **Kaydı başlat** (Start recording) and choose a new JSON filename.
3. Interact with the page in the browser window. The recorder captures clicks, text edits in supported fields, and Enter presses in inputs on the main page.
4. Close the recording tab to finish and save. Recorded text values are stored in the JSON file, so review it before sharing.
5. Click **Kayıt dosyasını oynat** (Replay recording) and select the saved file. Playback opens the recorded URL, waits one to two seconds between actions and closes the browser on completion.

You can also use the command line from the activated environment:

```sh
python recorder.py record https://example.com session.json
python recorder.py play session.json
```

## Mascot behavior

The llama holds a camera while recording and a tablet during playback. After ten seconds of playback, it switches to the TV pose. Errors have a dedicated pose. Each available transition plays once and settles on its destination image.

While the app is idle, the llama holds its tea pose for one minute and its hourglass and impatient poses for ten seconds each. After three minutes without interaction, it falls asleep. Returning focus to the window or using the mouse or keyboard wakes it.
