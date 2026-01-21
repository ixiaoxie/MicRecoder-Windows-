# 🎙️ Mic Recorder (Python)

[简体中文](README.md) | **English**

A lightweight, system-tray based voice recorder for Windows. Features global hotkeys, minimized background recording, and auto-start.

![Screenshot](screenshot.png)
*(Screenshot placeholder)*

## ✨ Features

*   **🎧 High Quality Recording**: Lossless WAV recording powered by `PyAudio`.
*   **⌨️ Global Hotkeys**: Custom hotkeys (Default: `Ctrl+1` Start/Pause, `Ctrl+2` Stop) work even when the app is in the background or while gaming.
    *   *Stability Optimized*: Uses async threads to prevent hotkey timeouts or unhooking.
*   **🛡️ Admin Rights**: Enforced Administrator privileges ensure hotkeys work on all surfaces, including Desktop and elevated apps.
*   **📥 System Tray Integration**: Minimizes to the system tray on close. Right-click menu supported.
*   **🚀 Silent Startup**: Supports "Run at Startup" and launches silently (minimized) to the tray without showing a window.
*   **🎨 Native UI**: Clean Tkinter interface that matches native Windows style. Supports English/Chinese switching.
*   **📂 Custom Save Path**: Browse and select any folder to save your recordings.
*   **⌨️ Smart Hotkey Binding**: Click the hotkey field and simply press your desired key combination (e.g., `Ctrl+Shift+A`) to bind it automatically.
*   **🔊 Real-time Feedback**: Toast notifications and tray icon changes provide instant status updates.

## 🛠️ Installation & Usage

### Requirements
*   Windows 10 / 11
*   Python 3.8+

### 1. Clone
```bash
git clone https://github.com/your-username/mic-recorder.git
cd mic-recorder
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```
*Note: If running as a script, please ensure your terminal is running as Administrator.*

### 3. Run
```bash
python mic_recorder.py
```

## 📦 Build EXE

If you want to build a standalone EXE that runs without Python:

1.  Install PyInstaller:
    ```bash
    pip install pyinstaller
    ```
2.  Run build script:
    ```bash
    build.bat
    ```
3.  Find `MicRecorder.exe` in the `dist` folder.
    *   The EXE is configured to request Administrator rights automatically (UAC Shield).

## ⚠️ FAQ

**Q: Why does it ask for Administrator permission (UAC)?**
A: To ensure **Global Hotkeys** work reliably in all scenarios (like full-screen games or the Desktop), the application must have Administrator privileges.

**Q: Where is the window after startup?**
A: This is the **Silent Startup** feature. The app launches minimized to the System Tray (bottom right) to avoid disturbing you. Double-click the tray icon to show the window.

**Q: Antivirus false positive?**
A: Because the app uses global keyboard hooks and modifies the registry for startup, some sensitive antivirus software might flag it. Please whitelist it. This project is open source, and you are welcome to audit the code.

## 📜 License

[MIT License](LICENSE)
