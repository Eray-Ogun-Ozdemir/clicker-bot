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
3. Interact with the page in the browser window. The recorder captures clicks, text edits in supported fields, dropdown selections and Enter presses in inputs on the main page.
4. A red frame and a control bar appear in the browser. Click **Bitir** (Finish) to save, or **İptal** (Cancel) to close without creating a file. Closing the tab or clicking **Kaydı bitir** in the app also saves. Recorded text values are stored in the JSON file, so review it before sharing.
5. Click **Kayıt dosyasını oynat** (Replay recording) and select the saved file. Playback opens the recorded URL, waits one to two seconds between actions and closes the browser on completion. The bar in the browser shows the current step; **Durdur** (Stop) there, **Oynatmayı durdur** in the app, or closing the tab stops playback after the current step.

### Account details

Under **Hesap bilgileri** you can optionally enter a username and password before recording. They require an `https://` starting URL. When you focus a username or password field on that site during recording, Clicker Bot fills it for you. The username is saved in the JSON file as a normal input step. The password is never written to the file: it is stored in the macOS Keychain or Windows Credential Manager, and the recording only keeps a reference to it. Playback on another computer therefore cannot fill the password. The password is stored only after the recording file has been saved. To remove it from this device, open the recording with **Kaydı incele** and choose **Parolayı cihazdan sil**. When no password is stored for a recording, for example after removing it or on another computer, the same place offers **Parolayı gir** to store one without recording the login again. Copies of the recording share the same stored password.

Choose **Kaydı incele** to inspect a saved JSON recording before launching a browser. The inspector lists the steps in order with their targets and input values. **Bu kaydı oynat** runs the displayed recording, highlights the current step and shows the error beside the list if a step fails.

In the inspector, select a step and use **Düzenle** (Edit) to change its selector or input value. Use **Yukarı** (Up), **Aşağı** (Down), or **Sil** (Delete) to adjust the sequence. **Bu kaydı oynat** runs the edited steps, and **Kopyasını kaydet** saves a new JSON file.

You can also use the command line from the activated environment:

```sh
python recorder.py record https://example.com session.json
python recorder.py play session.json
```

## Mascot behavior

The llama holds a camera while recording and a tablet during playback. After ten seconds of playback, it switches to the TV pose. Errors have a dedicated pose. Each available transition plays once and settles on its destination image.

While the app is idle, the llama holds its tea pose for one minute and its hourglass and impatient poses for ten seconds each. After three minutes without interaction, it falls asleep. Returning focus to the window or using the mouse or keyboard wakes it.
