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
3. Interact with the page in the browser window. The recorder captures clicks, text edits in supported fields, dropdown selections and Enter presses in inputs on the main page. Pressing and holding the mouse button on an element for at least 0.6 seconds without moving records a **Basılı tutma** (Hold) step with that duration instead of a click. Dragging an element onto another one records a **Sürükle-bırak** (Drag and drop) step. This works for the browser's built-in drag and drop, for pages that move elements with the mouse, such as jQuery UI, and for lists that reorder while you drag, such as SortableJS. Selecting text by dragging is not recorded as a drag.
4. A red frame and a control bar appear in the browser. Click **Bitir** (Finish) to save, or **İptal** (Cancel) to close without creating a file. Closing the tab or clicking **Kaydı bitir** in the app also saves. Recorded text values are stored in the JSON file, so review it before sharing.
5. Click **Kayıt dosyasını oynat** (Replay recording) and select the saved file. Playback opens the recorded URL, waits one to two seconds between actions and closes the browser on completion. The bar in the browser shows the current step; **Durdur** (Stop) there, **Oynatmayı durdur** in the app, or closing the tab stops playback after the current step.

### Account details

Under **Hesap bilgileri** you can optionally enter a username and password before recording. They require an `https://` starting URL. When you focus a username or password field on that site during recording, Clicker Bot fills it for you. The username is saved in the JSON file as a normal input step. The password is never written to the file: it is stored in the macOS Keychain or Windows Credential Manager, and the recording only keeps a reference to it. Playback on another computer therefore cannot fill the password. The password is stored only after the recording file has been saved. To remove it from this device, open the recording with **Kaydı incele** and choose **Parolayı cihazdan sil**. When no password is stored for a recording, for example after removing it or on another computer, the same place offers **Parolayı gir** to store one without recording the login again. Copies of the recording share the same stored password.

Choose **Kaydı incele** to inspect a saved JSON recording before launching a browser. The inspector lists the steps in order with their targets and input values. **Bu kaydı oynat** runs the displayed recording, highlights the current step and shows the error beside the list if a step fails.

In the inspector, select a step and use **Düzenle** (Edit) to change its selector or input value. Use **Yukarı** (Up), **Aşağı** (Down), or **Sil** (Delete) to adjust the sequence. **Bu kaydı oynat** runs the edited steps, and **Kopyasını kaydet** saves a new JSON file.

Each step waits for its page and target before it fails. Set this limit for the whole recording in seconds under **Adım zaman aşımı (sn)**, below the recording name in the inspector. The default is 5 seconds and the maximum is 300.

To insert a step after the selected step, or at the end when no step is selected, click **Adım ekle** (Add step) and choose one of these:

- **Kaydırma** (Scroll): with a target, scrolls until that element is visible. With no target, scrolls the page by a number of pixels: positive scrolls down and negative scrolls up.
- **Üzerine gelme** (Hover): moves the mouse over the target, for example to open a menu.
- **Basılı tutma** (Hold): holds the mouse button down on the target for up to 30 seconds.
- **Çift tıklama** (Double-click) and **Sağ tıklama** (Right-click): click the target twice, or with the right button.
- **Tuşa basma** (Key press): presses a key or shortcut such as `Tab`, `Escape`, `ArrowDown` or `Control+A`. With a target the key goes to that element; with no target it goes to the page.
- **Sürükle-bırak** (Drag and drop): drags the target onto a second element. If a page sets up dragging only after it loads, add a **Bekleme** step before a drag that comes first in a recording.

Below a separator, the same menu offers waits and checks:

- **Bekleme** (Wait): waits until an element is visible, for something slow such as a result that loads after a search. The target starts as the following step's target. The time starts at 10 seconds or the recording's limit, whichever is longer.
- **Sabit bekleme** (Fixed wait): pauses playback for a set number of seconds, up to 300, without looking at the page. **Durdur** ends it at once.
- **Metin doğrulaması** (Text check): checks that the target's text contains the expected text. Spacing and line breaks are ignored, and the check is case-sensitive. The target starts as `body`, which checks the whole page.
- **Adres doğrulaması** (Address check): checks that the page address starts with the expected address, so query strings may differ. The address starts as the following step's address.

During playback, checks look again until they pass or the step's time limit runs out. When a check fails, the inspector shows the failed step with the expected and actual results.

Select **Hata olunca ekran görüntüsü kaydet** (Save a screenshot on failure) to capture the page when any step fails. The screenshot is saved as a PNG file next to the recording, named `<recording>-hata-<date-time>.png`, and **Ekran görüntüsünü aç** opens it. Only the five newest screenshots of each recording are kept; older ones are deleted when a new one is saved. The setting is off by default because screenshots can show personal data. The time limit, added steps and screenshot setting are saved with **Kopyasını kaydet**.

### Build a flow by hand

To write a flow without recording it, choose **Manuel hazırla** under **Hazırlama yöntemi**, enter the starting URL and click **Akışı oluştur**. Choose a JSON filename. Clicker Bot saves an empty flow and opens it in the inspector. Account details do not apply to these flows, so their fields are turned off.

Add steps with **Adım ekle**. Besides the steps described above, the menu offers the steps a recording creates: **Tıklama** (Click), **Yazı** (Type text), **Enter tuşu** (Enter key) and **Liste seçimi** (Dropdown selection). For a dropdown selection, enter the option's `value` attribute, not its visible label, and separate several values with commas. **Kaydet** saves a hand-built flow over its own file. Recorded flows are only saved as copies, so the original recording stays intact.

You can also use the command line from the activated environment:

```sh
python recorder.py record https://example.com session.json
python recorder.py play session.json
```

## Appearance

Clicker Bot opens in a light or dark palette that matches the system appearance: the macOS **Açık**, **Koyu** and **Otomatik** settings, or the Windows app mode. When the system appearance changes while the app is open, every window switches within a couple of seconds, keeping what you have typed and any recording or playback in progress. Use **Görünüm** in the top bar to choose **Sistem** (follow the system), **Açık** or **Koyu**. The choice applies at once and is remembered in `settings.json` in the app's data folder (`~/Library/Application Support/Clicker Bot` on macOS, `%APPDATA%\Clicker Bot` on Windows). For testing, `CLICKER_BOT_THEME=light` or `CLICKER_BOT_THEME=dark` overrides both. All colours, fonts and button styles are defined in `theme.py`.

## Mascot behavior

The llama holds a camera while recording and a tablet during playback. After ten seconds of playback, it switches to the TV pose. Errors have a dedicated pose. Poses switch directly, without transition animations. In the dark palette, the sleep and impatient poses use variants with lighter "zzz" letters and motion lines.

While the app is idle, the llama holds its tea pose for one minute and its hourglass and impatient poses for ten seconds each. After three minutes without interaction, it falls asleep. Returning focus to the window or using the mouse or keyboard wakes it.
