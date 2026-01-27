"""
Mic Recorder - A lightweight, system-tray based voice recorder for Windows.
Open Source Project
"""
import pyaudio
import wave
import keyboard
import threading
import os
import sys
import json
import time
import audioop
import ctypes
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime
from pystray import Icon, MenuItem as item, Menu
from PIL import Image, ImageDraw, ImageTk
import subprocess
import winreg # Kept just in case, but unused for startup now

def resource_path(relative_path):
    """
    获取资源绝对路径，适用于开发环境和 PyInstaller 打包后的环境。
    Get absolute path to resource, works for dev and for PyInstaller
    """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

# ================= Translations =================
TRANSLATIONS = {
    "en": {
        "status_idle": "Status: Idle",
        "status_recording": "Status: Recording...",
        "status_paused": "Status: Paused",
        "btn_toggle": "START / PAUSE",
        "btn_stop": "STOP",
        "lbl_volume": "Mic Volume Gain:",
        "lbl_save_path": "Save Path:",
        "btn_browse": "Browse...",
        "lbl_hotkeys": "Hotkeys Configuration",
        "lbl_toggle": "Start/Pause:",
        "lbl_stop": "Stop:",
        "btn_save_hotkeys": "Save & Apply Hotkeys",
        "chk_startup": "Run at Startup",
        "btn_open_folder": "Open Recordings Folder",
        "msg_hotkeys_saved": "Hotkeys updated!",
        "tray_show": "Show Window",
        "tray_toggle": "Start/Pause",
        "tray_stop": "Stop Recording",
        "tray_exit": "Exit",
        "title_setup": "Mic Recorder Setup",
        "lbl_language": "Language / 语言:",
        "lbl_controls": "Controls",
        "lbl_settings": "Settings",
        "msg_exit_title": "Exit Application",
        "msg_exit_body": "Do you want to minimize to the system tray instead of exiting?\n\nYes = Minimize to Tray\nNo = Exit Application\nCancel = Stay Open",
        "msg_hotkey_conflict_title": "Hotkey Conflict",
        "msg_hotkey_conflict_body": "The 'Start/Pause' and 'Stop' hotkeys are identical.\nThis might cause unexpected behavior.\n\nDo you want to continue?",
        "toast_start": "Recording Started",
        "toast_pause": "Recording Paused",
        "toast_resume": "Recording Resumed",
        "toast_stop": "Recording Stopped"
    },
    "zh": {
        "status_idle": "状态: 空闲",
        "status_recording": "状态: 录音中...",
        "status_paused": "状态: 已暂停",
        "btn_toggle": "开始 / 暂停",
        "btn_stop": "停止",
        "lbl_volume": "麦克风增益:",
        "lbl_save_path": "保存路径:",
        "btn_browse": "浏览...",
        "lbl_hotkeys": "热键配置",
        "lbl_toggle": "开始/暂停:",
        "lbl_stop": "停止:",
        "btn_save_hotkeys": "保存并应用热键",
        "chk_startup": "开机自启",
        "btn_open_folder": "打开录音文件夹",
        "msg_hotkeys_saved": "热键已更新!",
        "tray_show": "显示窗口",
        "tray_toggle": "开始/暂停",
        "tray_stop": "停止录音",
        "tray_exit": "退出",
        "title_setup": "麦克风录音设置",
        "lbl_language": "Language / 语言:",
        "lbl_controls": "控制",
        "lbl_settings": "设置",
        "msg_exit_title": "退出程序",
        "msg_exit_body": "您希望最小化到系统托盘而不是退出吗？\n\n是 (Yes) = 最小化\n否 (No) = 退出程序\n取消 (Cancel) = 取消操作",
        "msg_hotkey_conflict_title": "热键冲突",
        "msg_hotkey_conflict_body": "“开始/暂停”和“停止”热键相同。\n这可能会导致意外行为。\n\n您确定要继续吗？",
        "toast_start": "录音已开启",
        "toast_pause": "录音已暂停",
        "toast_resume": "录音已继续",
        "toast_stop": "录音已终止"
    }
}

# ================= Single Instance Lock =================
class SingleInstanceChecker:
    """
    单实例检查器，防止程序重复运行。
    Uses Windows Mutex to ensure only one instance runs.
    """
    def __init__(self, name="MicRecorder_Instance_Lock"):
        self.mutex = ctypes.windll.kernel32.CreateMutexW(None, False, name)
        self.last_error = ctypes.windll.kernel32.GetLastError()
    
    def is_already_running(self):
        # ERROR_ALREADY_EXISTS = 183
        return self.last_error == 183

# ================= Configuration =================
class ConfigManager:
    """
    配置管理器，处理配置文件的加载和保存。
    Handles loading and saving of configuration (json).
    """
    DEFAULT_CONFIG = {
        "hotkey_toggle": "ctrl+1",
        "hotkey_stop": "ctrl+2",
        "save_path": os.path.expanduser("~\\Music\\Recordings"),
        "startup": False,
        "volume": 1.0,
        "language": "zh"
    }

    def __init__(self):
        self.config_file = self._get_config_path()
        self.config = self.load_config()
        self.ensure_save_path()

    def _get_config_path(self):
        """
        获取配置文件的绝对路径。
        Resolve absolute path for config.json to avoid permission errors when CWD is system32.
        """
        try:
            if getattr(sys, 'frozen', False):
                base_path = os.path.dirname(sys.executable)
            else:
                base_path = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base_path, "config.json")
        except Exception:
            return "config.json"

    def load_config(self):
        if not os.path.exists(self.config_file):
            self.save_config(self.DEFAULT_CONFIG)
            return self.DEFAULT_CONFIG
        try:
            with open(self.config_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading config: {e}")
            return self.DEFAULT_CONFIG

    def save_config(self, config=None):
        if config:
            self.config = config
        try:
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            print(f"Error saving config: {e}")

    def get(self, key):
        return self.config.get(key, self.DEFAULT_CONFIG.get(key))

    def set(self, key, value):
        self.config[key] = value
        self.save_config()

    def ensure_save_path(self):
        path = self.get("save_path")
        if not os.path.exists(path):
            try:
                os.makedirs(path)
            except Exception as e:
                print(f"Error creating save path: {e}")

# ================= Startup Handler =================
class StartupHandler:
    """
    启动项管理器，用于设置 Windows 任务计划以实现开机自启 (支持管理员权限)。
    Manages Windows Task Scheduler for 'Run at Startup' functionality with Admin rights.
    """
    TASK_NAME = "MicRecorderAutoStart"

    @staticmethod
    def set_startup(enable=True):
        try:
            if enable:
                # 1. Determine command
                if getattr(sys, 'frozen', False):
                    # EXE
                    app_path = sys.executable
                    cmd_args = "--minimized"
                    cwd = os.path.dirname(app_path)
                else:
                    # Script
                    script_path = os.path.abspath(__file__)
                    cwd = os.path.dirname(script_path)
                    
                    # Use pythonw.exe if available
                    py_exe = sys.executable
                    if "python.exe" in py_exe:
                        w_exe = py_exe.replace("python.exe", "pythonw.exe")
                        if os.path.exists(w_exe):
                            py_exe = w_exe
                    
                    app_path = py_exe
                    cmd_args = f'\\"{script_path}\\" --minimized'

                # 2. Build Create Command
                # /SC ONLOGON : Run at login
                # /RL HIGHEST : Run with highest privileges (Admin)
                # /F : Force create (overwrite)
                # /TR : Task run command
                
                # Note: schtasks requires proper quoting.
                # TR command: "\path\to\exe" --arguments
                tr_cmd = f'\\"{app_path}\\" {cmd_args}'
                
                command = (
                    f'schtasks /Create /TN "{StartupHandler.TASK_NAME}" '
                    f'/TR "{tr_cmd}" '
                    f'/SC ONLOGON /RL HIGHEST /F'
                )
                
                # Execute creation
                # shell=True to hide console window if possible, though we are already in GUI app mostly
                subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[INFO] Task Scheduler task created: {StartupHandler.TASK_NAME}")
                
            else:
                # Delete Task
                command = f'schtasks /Delete /TN "{StartupHandler.TASK_NAME}" /F'
                subprocess.run(command, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                print(f"[INFO] Task Scheduler task deleted: {StartupHandler.TASK_NAME}")

        except subprocess.CalledProcessError:
            # Often happens if deleting a task that doesn't exist, which is fine.
            if enable:
                print(f"[ERROR] Failed to create startup task.")
            else:
                print(f"[INFO] Startup task not found or already deleted.")
        except Exception as e:
            print(f"Startup Handler Error: {e}")

# ... (Previous code remains, skipping to Main block) ...



# ================= Recorder Logic =================
class AudioRecorder:
    """
    音频录制器，使用 PyAudio 在后台线程录制音频。
    Handles audio recording in a separate thread using PyAudio.
    """
    def __init__(self, config_manager, on_status_change=None):
        self.config = config_manager
        self.recording = False
        self.paused = False
        self.frames = []
        self.thread = None
        self.p = None
        self.stream = None
        self.on_status_change = on_status_change
        self.start_time = None

    def start(self):
        if self.recording:
            return
        self.recording = True
        self.paused = False
        self.start_time = time.time()
        self._notify_status()
        self.thread = threading.Thread(target=self._record_loop, daemon=True)
        self.thread.start()
        print("[INFO] Recording started...")

    def pause(self):
        if not self.recording:
            return
        self.paused = not self.paused
        self._notify_status()
        print(f"[INFO] Recording {'paused' if self.paused else 'resumed'}.")

    def stop(self):
        if not self.recording:
            return
        self.recording = False
        self.paused = False
        if self.thread:
            self.thread.join()
        
        self.save_file()
        self._notify_status()
        print("[INFO] Recording stopped.")

    def _notify_status(self):
        if self.on_status_change:
            # Status: 0=Idle, 1=Recording, 2=Paused
            if not self.recording:
                state = 0
            elif self.paused:
                state = 2
            else:
                state = 1
            self.on_status_change(state)

    def toggle_recording(self):
        """
        切换录制状态。
        Logic:
        1. If Idle -> Start
        2. If Recording -> Pause
        3. If Paused -> Resume
        """
        if not self.recording:
            self.start()
        elif self.paused:
            self.pause() # Resumes
        else:
            self.pause() # Pauses

    def _record_loop(self):
        self.p = pyaudio.PyAudio()
        try:
            # Using default input device
            # 使用默认输入设备
            self.stream = self.p.open(format=pyaudio.paInt16,
                                      channels=1,
                                      rate=44100,
                                      input=True,
                                      frames_per_buffer=1024)
            self.frames = []
            
            while self.recording:
                if self.paused:
                    time.sleep(0.05)
                    continue

                try:
                    data = self.stream.read(1024)
                    
                    # Apply Volume Gain / 应用增益
                    vol_factor = float(self.config.get("volume"))
                    if vol_factor != 1.0:
                        try:
                            data = audioop.mul(data, 2, vol_factor)
                        except Exception:
                            pass
                    
                    self.frames.append(data)
                except Exception as read_err:
                     print(f"[WARN] Stream read error: {read_err}")
        except Exception as e:
            print(f"[ERROR] Recording initialization error: {e}")
        finally:
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            self.p.terminate()

    def save_file(self):
        if not self.frames:
            return
        
        filename = datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".wav"
        save_path = self.config.get("save_path")
        filepath = os.path.join(save_path, filename)

        try:
            wf = wave.open(filepath, 'wb')
            wf.setnchannels(1)
            wf.setsampwidth(self.p.get_sample_size(pyaudio.paInt16) if self.p else 2) 
            wf.setframerate(44100)
            wf.writeframes(b''.join(self.frames))
            wf.close()
            print(f"[INFO] Saved: {filepath}")
        except Exception as e:
            print(f"[ERROR] Save file error: {e}")

# ================= GUI (Tkinter) =================
class MainApp(tk.Tk):
    """
    主应用程序窗口。
    Main Application Window (GUI).
    """
    def __init__(self, config_manager, recorder, start_minimized=False):
        super().__init__()
        self.config = config_manager
        self.recorder = recorder
        self.tray_icon = None

        self.lang = self.config.get("language")
        
        self.title(self.tr("title_setup"))
        
        # Calculate Window Position (Centered but slightly top-right)
        # Target Size: 420x720 (Increased from 550 to ensure all elements fit)
        w_width = 420
        w_height = 720
        
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # True Center
        x_c = (screen_width - w_width) // 2
        y_c = (screen_height - w_height) // 2
        
        # Adjust: Move right by 100px, Up by 50px
        x = x_c + 100
        y = y_c - 50
        
        # Bounds check
        if x + w_width > screen_width: x = screen_width - w_width - 20
        if y < 0: y = 20
        
        self.geometry(f"{w_width}x{w_height}+{x}+{y}")
        self.resizable(False, False)
        
        # Hide immediately if minimized
        if start_minimized:
            self.withdraw()
        
        # Icon
        try:
            icon_path = resource_path("microphone.ico")
            if os.path.exists(icon_path):
                self.iconbitmap(icon_path)
                print(f"[INFO] Set taskbar icon: {icon_path}")
            else:
                print("[WARN] microphone.ico not found for taskbar")
            
            # Fallback/Titlbar icon
            png_path = resource_path("microphone.png")
            if os.path.exists(png_path):
                self.icon_img = Image.open(png_path)
                self.iconphoto(True, ImageTk.PhotoImage(self.icon_img))
        except Exception as e:
            print(f"Icon load error: {e}")

        # Intercept Close Button
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # --- Styles & Theme ---
        style = ttk.Style()
        # Use 'vista' or 'winnative' for standard Windows checkmarks (V instead of X)
        # 'vista' works well on Win10/11
        style.theme_use('vista') 
        
        # Custom colors/fonts
        bg_color = "#f4f4f4"
        self.configure(bg=bg_color)
        
        style.configure("TFrame", background=bg_color)
        style.configure("TLabelframe", background=bg_color, font=("Segoe UI", 10, "bold"))
        style.configure("TLabelframe.Label", background=bg_color, font=("Segoe UI", 10, "bold"))
        style.configure("TLabel", background=bg_color, font=("Segoe UI", 10))
        style.configure("TButton", font=("Segoe UI", 10), padding=5)
        style.configure("Header.TLabel", font=("Segoe UI", 18, "bold"), foreground="#333")
        
        # --- UI Elements ---
        
        # Header
        lbl_header = ttk.Label(self, text="Mic Recorder", style="Header.TLabel")
        lbl_header.pack(pady=(20, 10))

        # Status Label
        self.status_var = tk.StringVar(value=self.tr("status_idle"))
        self.lbl_status = ttk.Label(self, textvariable=self.status_var, font=("Segoe UI", 12, "bold"), foreground="gray")
        self.lbl_status.pack(pady=5)

        # Controls Group
        self.group_controls = ttk.LabelFrame(self, text=f" {self.tr('lbl_controls')} ", padding=(20, 10))
        self.group_controls.pack(fill="x", padx=20, pady=10)

        self.btn_toggle = ttk.Button(self.group_controls, text=self.tr("btn_toggle"), command=lambda: self.recorder.toggle_recording())
        self.btn_toggle.pack(side="left", fill="x", expand=True, padx=5)

        self.btn_stop = ttk.Button(self.group_controls, text=self.tr("btn_stop"), command=lambda: self.recorder.stop(), state="disabled")
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=5)

        # Settings Group
        self.group_settings = ttk.LabelFrame(self, text=f" {self.tr('lbl_settings')} ", padding=(20, 10))
        self.group_settings.pack(fill="x", padx=20, pady=10)

        # Volume
        self.lbl_volume = ttk.Label(self.group_settings, text=self.tr("lbl_volume"))
        self.lbl_volume.pack(anchor="w")
        self.vol_var = tk.DoubleVar(value=self.config.get("volume"))
        
        frame_vol = ttk.Frame(self.group_settings)
        frame_vol.pack(fill="x", pady=5)
        self.scale_vol = ttk.Scale(frame_vol, from_=0.1, to=5.0, variable=self.vol_var, command=self.on_volume_change)
        self.scale_vol.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self.lbl_vol_val = ttk.Label(frame_vol, text=f"{self.vol_var.get():.1f}x", width=4)
        self.lbl_vol_val.pack(side="right")

        # Save Path
        self.lbl_path = ttk.Label(self.group_settings, text=self.tr("lbl_save_path"))
        self.lbl_path.pack(anchor="w", pady=(10, 0))
        frame_path = ttk.Frame(self.group_settings)
        frame_path.pack(fill="x", pady=5)
        
        self.path_var = tk.StringVar(value=self.config.get("save_path"))
        self.entry_path = ttk.Entry(frame_path, textvariable=self.path_var, state="readonly")
        self.entry_path.pack(side='left', fill='x', expand=True)

        self.btn_browse = ttk.Button(frame_path, text="...", command=self.browse_path, width=4)
        self.btn_browse.pack(side='right', padx=(5, 0))

        # Hotkeys Group
        self.group_hk = ttk.LabelFrame(self, text=f" {self.tr('lbl_hotkeys')} ", padding=(20, 10))
        self.group_hk.pack(fill="x", padx=20, pady=10)

        frame_hk_inner = ttk.Frame(self.group_hk)
        frame_hk_inner.pack(fill="x")
        
        # Grid layout for hotkeys
        self.lbl_hk_toggle = ttk.Label(frame_hk_inner, text=self.tr("lbl_toggle"))
        self.lbl_hk_toggle.grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.entry_toggle = ttk.Entry(frame_hk_inner, width=20)
        self.entry_toggle.insert(0, self.config.get("hotkey_toggle"))
        self.entry_toggle.grid(row=0, column=1, padx=5, pady=5)
        self.attach_hotkey_listener(self.entry_toggle)

        self.lbl_hk_stop = ttk.Label(frame_hk_inner, text=self.tr("lbl_stop"))
        self.lbl_hk_stop.grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.entry_stop = ttk.Entry(frame_hk_inner, width=20)
        self.entry_stop.insert(0, self.config.get("hotkey_stop"))
        self.entry_stop.grid(row=1, column=1, padx=5, pady=5)
        self.attach_hotkey_listener(self.entry_stop)
        
        self.btn_save_hk = ttk.Button(self.group_hk, text=self.tr("btn_save_hotkeys"), command=self.save_hotkeys)
        self.btn_save_hk.pack(pady=(10, 0), fill="x")

        # Bottom Frame (Startup, Lang, Open)
        frame_bottom = ttk.Frame(self)
        frame_bottom.pack(fill="x", padx=20, pady=20)

        self.var_startup = tk.BooleanVar(value=self.config.get("startup"))
        self.cb_startup = ttk.Checkbutton(frame_bottom, text=self.tr("chk_startup"), variable=self.var_startup, command=self.toggle_startup)
        self.cb_startup.pack(side="left")

        self.box_lang = ttk.Combobox(frame_bottom, values=["English", "中文"], state="readonly", width=8)
        self.box_lang.set("English" if self.lang == "en" else "中文")
        self.box_lang.bind("<<ComboboxSelected>>", self.change_language)
        self.box_lang.pack(side="right")
        ttk.Label(frame_bottom, text=self.tr("lbl_language")).pack(side="right", padx=5)

        self.btn_open = ttk.Button(self, text=self.tr("btn_open_folder"), command=self.open_folder)
        self.btn_open.pack(fill="x", padx=40, pady=(0, 20))

    def tr(self, key):
        return TRANSLATIONS.get(self.lang, TRANSLATIONS["en"]).get(key, key)

    def change_language(self, event):
        val = self.box_lang.get()
        new_lang = "en" if val == "English" else "zh"
        if new_lang != self.lang:
            self.lang = new_lang
            self.config.set("language", new_lang)
            self.refresh_ui_text()

    def refresh_ui_text(self):
        self.title(self.tr("title_setup"))
        self.status_var.set(self.tr("status_idle")) # Reset status text for simplicity, or check state
        
        self.group_controls.config(text=f" {self.tr('lbl_controls')} ")
        self.btn_toggle.config(text=self.tr("btn_toggle"))
        self.btn_stop.config(text=self.tr("btn_stop"))
        
        self.group_settings.config(text=f" {self.tr('lbl_settings')} ")
        self.lbl_volume.config(text=self.tr("lbl_volume"))
        self.lbl_path.config(text=self.tr("lbl_save_path"))
        self.btn_browse.config(text=self.tr("btn_browse"))
        
        self.group_hk.config(text=f" {self.tr('lbl_hotkeys')} ")
        self.lbl_hk_toggle.config(text=self.tr("lbl_toggle"))
        self.lbl_hk_stop.config(text=self.tr("lbl_stop"))
        
        self.btn_save_hk.config(text=self.tr("btn_save_hotkeys"))
        self.cb_startup.config(text=self.tr("chk_startup"))
        self.btn_open.config(text=self.tr("btn_open_folder"))
        
        # Refresh Status based on current state
        if self.recorder.recording:
            if self.recorder.paused:
                self.status_var.set(self.tr("status_paused"))
            else:
                self.status_var.set(self.tr("status_recording"))
        else:
             self.status_var.set(self.tr("status_idle"))

    def browse_path(self):
        path = filedialog.askdirectory()
        if path:
            self.path_var.set(path)
            self.config.set("save_path", path)

    def attach_hotkey_listener(self, entry):
        entry.bind("<FocusIn>", lambda e: self.on_entry_focus_in(entry))
        entry.bind("<FocusOut>", lambda e: self.on_entry_focus_out(entry))
        entry.bind("<Key>", lambda e: self.on_hotkey_press(e, entry))
        
    def on_entry_focus_in(self, entry):
        entry.config(background="#ffffe0")
        # Global unhook to prevent conflict while typing
        try:
            keyboard.unhook_all_hotkeys()
        except:
            pass

    def on_entry_focus_out(self, entry):
        entry.config(background="white")
        # Rebind global hotkeys when done typing
        self.bind_hotkeys()

    def on_hotkey_press(self, event, entry):
        # Ignore modifiers alone
        if event.keysym in ("Control_L", "Control_R", "Shift_L", "Shift_R", "Alt_L", "Alt_R", "Win_L", "Win_R"):
            return "break"

        # Check for Backspace to clear
        if event.keysym == "BackSpace":
            entry.delete(0, tk.END)
            return "break"

        modifiers = []
        # Bitmasks for Windows (State)
        # Shift: 0x1, Ctrl: 0x4, Alt: 0x20000 or 0x2
        # Note: Tkinter state handling can be tricky.
        
        # Simpler way: build from implicit knowledge + event.state
        state = event.state
        if state & 0x0004: modifiers.append("ctrl")
        if state & 0x0001: modifiers.append("shift")
        if state & 0x20000 or state & 0x0002: modifiers.append("alt")

        key = event.keysym.lower()
        
        # Mappings for common keys
        if key == "return": return "break" # Confirm?
        if key == "escape": return "break" # Cancel? 

        # If it's a special char, might need mapping, but 'keyboard' lib is usually okay with lower keysyms
        # e.g. 'period', 'comma', 'f1'...
        
        full_hotkey = "+".join(modifiers + [key])
        
        # Update Entry
        entry.delete(0, tk.END)
        entry.insert(0, full_hotkey)
        
        return "break"

    def toggle_startup(self):
        val = self.var_startup.get()
        self.config.set("startup", val)
        StartupHandler.set_startup(val)

    def save_hotkeys(self):
        new_toggle = self.entry_toggle.get().strip()
        new_stop = self.entry_stop.get().strip()

        # Conflict Check
        if new_toggle and new_stop and new_toggle.lower() == new_stop.lower():
            ans = messagebox.askyesno(
                self.tr("msg_hotkey_conflict_title"), 
                self.tr("msg_hotkey_conflict_body"),
                icon='warning'
            )
            if not ans:
                return

        self.config.set("hotkey_toggle", new_toggle)
        self.config.set("hotkey_stop", new_stop)
        
        # Rebind
        self.bind_hotkeys()
        messagebox.showinfo("Success", self.tr("msg_hotkeys_saved"))

    def bind_hotkeys(self):
        # Unbind all first to avoid duplicates
        try:
            keyboard.unhook_all_hotkeys()
        except:
            pass
        
        toggle_hk = self.config.get("hotkey_toggle")
        stop_hk = self.config.get("hotkey_stop")
        
        def run_async(func):
            threading.Thread(target=func, daemon=True).start()

        if toggle_hk:
            try: 
                keyboard.add_hotkey(toggle_hk, lambda: run_async(self.recorder.toggle_recording))
                print(f"[INFO] Bound toggle hotkey: {toggle_hk}")
            except Exception as e: 
                print(f"[ERROR] Failed to bind toggle: {toggle_hk}, error: {e}")
                
        if stop_hk: 
            try: 
                keyboard.add_hotkey(stop_hk, lambda: run_async(self.recorder.stop))
                print(f"[INFO] Bound stop hotkey: {stop_hk}")
            except Exception as e: 
                print(f"[ERROR] Failed to bind stop: {stop_hk}, error: {e}")

    def on_volume_change(self, val):
        v = float(val)
        self.lbl_vol_val.config(text=f"{v:.1f}x")
        self.config.set("volume", v)

    def update_status(self, state):
        # 0=Idle, 1=Recording, 2=Paused
        self.after(0, lambda: self._update_gui(state))
        if self.tray_icon:
             self.tray_icon.update_icon(state)
        
        # Check if minimized/hidden and show notification
        if not self.winfo_viewable():
            # Logic to determine message
            if not hasattr(self, '_last_state'): self._last_state = 0
            
            text = ""
            if state == 1:
                # If we transitioned from 2->1, it is Resume. From 0->1 is Start.
                if self._last_state == 2:
                    text = "Recording Resumed"
                else:
                    text = "Recording Started"
            elif state == 2:
                text = "Recording Paused"
            elif state == 0:
                # If we came from 1 or 2 to 0, it is Stopped.
                if self._last_state != 0:
                    text = "Recording Stopped"
                
            self._last_state = state
            
            if text:
                self.after(0, lambda: self.show_toast(text))

    def _update_gui(self, state):
        if state == 1: # Recording
            self.status_var.set(self.tr("status_recording"))
            self.lbl_status.config(foreground="red")
            self.btn_toggle.config(text=self.tr("btn_toggle"))
            self.btn_stop.config(state="normal")
        elif state == 2: # Paused
            self.status_var.set(self.tr("status_paused"))
            self.lbl_status.config(foreground="orange")
            self.btn_toggle.config(text=self.tr("btn_toggle"))
            self.btn_stop.config(state="normal")
        else: # Idle
            self.status_var.set(self.tr("status_idle"))
            self.lbl_status.config(foreground="blue")
            self.btn_toggle.config(text=self.tr("btn_toggle"), state="normal")
            self.btn_stop.config(state="disabled")

    def on_closing(self):
        # Allow user to choose
        ans = messagebox.askyesnocancel(self.tr("msg_exit_title"), self.tr("msg_exit_body"))
        if ans is True:
            # Yes -> Minimize
            self.hide_to_tray()
        elif ans is False:
            # No -> Exit
            self.quit_app()
        # Cancel -> Do nothing
    
    def hide_to_tray(self):
        self.withdraw()

    def show_window(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def open_folder(self):
        path = self.config.get("save_path")
        os.startfile(path)

    def quit_app(self):
        self.recorder.stop()
        if self.tray_icon:
            self.tray_icon.stop()
        self.destroy()
        sys.exit(0)

    def show_toast(self, message):
        try:
            # Create a top-level window
            toast = tk.Toplevel(self)
            toast.overrideredirect(True) # Remove title bar
            toast.attributes("-topmost", True)
            toast.attributes("-alpha", 0.9) # Slight transparency
            
            # Grey background, white text
            toast.configure(bg="#333333")
            
            lbl = tk.Label(toast, text=message, fg="white", bg="#333333", font=("Segoe UI", 10), padx=20, pady=10)
            lbl.pack()
            
            # Position bottom-right
            screen_width = self.winfo_screenwidth()
            screen_height = self.winfo_screenheight()
            
            # Taskbar height estimation (approx 40-50px usually, but safe margin)
            # We want it in bottom right corner
            
            w = 200 # approx width
            h = 50  # approx height
            toast.update_idletasks() # Realize to get actual size
            w = toast.winfo_width()
            h = toast.winfo_height()
            
            x = screen_width - w - 20
            y = screen_height - h - 50 # 50px buffer for taskbar
            
            toast.geometry(f"+{x}+{y}")
            
            # Auto close after 2 seconds
            self.after(2000, toast.destroy)
        except Exception as e:
            print(f"Toast error: {e}")

# ================= Tray (Pystray) =================
def create_image(color="blue"):
    image = None
    try:
        # Try to load our icon
        icon_path = resource_path("microphone.ico")
        if os.path.exists(icon_path):
            image = Image.open(icon_path)
            print(f"[INFO] Loaded tray icon from: {icon_path}")
        else:
            # Try png
            png_path = resource_path("microphone.png")
            if os.path.exists(png_path):
                image = Image.open(png_path)
                print(f"[INFO] Loaded tray icon from: {png_path}")
    except Exception as e:
        print(f"[ERROR] Failed to load icon file: {e}")

    if image is None:
        # Fallback
        print("[INFO] Using generated fallback icon")
        width = 64
        height = 64
        image = Image.new('RGBA', (width, height), (0, 0, 0, 0)) # Transparent bg
        dc = ImageDraw.Draw(image)
        # Draw a simple blue circle
        dc.ellipse((8, 8, 56, 56), fill=color)
        dc.rectangle((24, 24, 40, 40), fill='white')
    
    # Resize and convert to RGBA to ensure compatibility
    return image.resize((64, 64)).convert("RGBA")

class TrayIconWrapper:
    def __init__(self, app):
        self.app = app
        self.icon = None

    def run(self):
        try:
            # Pre-calculate strings to avoid lambda issues in thread
            t_toggle = self.app.tr('tray_toggle')
            t_stop = self.app.tr('tray_stop')
            t_show = self.app.tr('tray_show')
            t_exit = self.app.tr('tray_exit')

            menu = Menu(
                item(t_toggle, lambda: self.app.recorder.toggle_recording()),
                item(t_stop, lambda: self.app.recorder.stop()),
                item(t_show, self.app.show_window, default=True),
                item(t_exit, self.app.quit_app)
            )
            
            self.icon = Icon("MicRecorder", create_image(), "MicRecorder", menu)
            print("[INFO] System Tray Icon initialized. Running...")
            self.icon.run()
        except Exception as e:
            print(f"[ERROR] System Tray Thread Crashed: {e}")

    def stop(self):
        if self.icon:
            self.icon.stop()

    def update_icon(self, state):
        if self.icon:
            # state: 0=Idle, 1=Recording, 2=Paused
            # Update tooltip/title
            try:
                if state == 1:
                    self.icon.title = self.app.tr("status_recording")
                elif state == 2:
                    self.icon.title = self.app.tr("status_paused")
                else:
                    self.icon.title = self.app.tr("status_idle")
            except Exception as e:
                print(f"[WARN] Failed to update tray tooltip: {e}")

# ================= Main =================
def run_tray_thread(wrapper):
    wrapper.run()

if __name__ == "__main__":
    # 0. Admin Rights Check
    def is_admin():
        try:
            return ctypes.windll.shell32.IsUserAnAdmin()
        except:
            return False

    if not is_admin():
        # Re-run the program with admin rights
        # "runas" verb triggers UAC
        try:
            if getattr(sys, 'frozen', False):
                # If EXE, re-launch EXE
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv[1:]), None, 1)
            else:
                # If Python Script, re-launch python with script
                # Note: This might open a new console window for the elevated process
                ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{__file__}" ' + " ".join(sys.argv[1:]), None, 1)
            sys.exit(0)
        except Exception as e:
            ctypes.windll.user32.MessageBoxW(0, f"Failed to elevate: {e}", "Error", 0x10)
            sys.exit(1)

    # 1. Single Instance Check
    checker = SingleInstanceChecker()
    if checker.is_already_running():
        ctypes.windll.user32.MessageBoxW(0, "MicRecorder is already running!", "Error", 0x10)
        sys.exit(0)

    # 2. Config & Recorder
    conf = ConfigManager()
    
    start_minimized = False
    if "--minimized" in sys.argv:
        print("[INFO] Starting minimized to tray...")
        start_minimized = True
    
    # 3. GUI
    app = MainApp(conf, None, start_minimized=start_minimized) # Recorder needs app for callback
    
    # Recorder needs to call app.update_status
    recorder = AudioRecorder(conf, on_status_change=app.update_status)
    app.recorder = recorder

    # 4. Tray (Run in separate thread)
    tray_wrapper = TrayIconWrapper(app)
    app.tray_icon = tray_wrapper
    
    t = threading.Thread(target=run_tray_thread, args=(tray_wrapper,), daemon=True)
    t.start()

    # 5. Global Hotkeys
    # Delay binding slightly to ensure Tkinter loop is running and system is ready
    app.after(500, app.bind_hotkeys)

    # 6. Apply Startup (Re-apply to ensure flag is present if checked)
    if conf.get("startup"):
        StartupHandler.set_startup(True)

    # 6. Run GUI
    app.mainloop()
