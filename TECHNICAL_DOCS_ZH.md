# Mic Recorder 技术实现文档

本文档详细说明了 Mic Recorder (Python版) 的代码实现细节、架构设计、技术难点及解决方案。

## 1. 架构概览

本项目采用 **Python** 编写，主要依赖 `Tkinter` (GUI), `PyAudio` (录音), `Keyboard` (全局热键) 和 `Pystray` (系统托盘)。

### 核心类设计 (Class Design)

*   **`SingleInstanceChecker`**: 
    *   **作用**: 防止程序多开。
    *   **实现**: 使用 `ctypes.windll.kernel32.CreateMutexW` 创建一个命名互斥体。如果再次启动时发现互斥体已存在 (`ERROR_ALREADY_EXISTS`)，则退出程序。
    
*   **`ConfigManager`**:
    *   **作用**: 管理通过 `config.json` 持久化的配置（热键、保存路径、音量、语言等）。
    *   **实现**: 封装 `json` 读取/写入操作，提供 `get/set` 接口，并确保默认配置的完整性。

*   **`StartupHandler`**:
    *   **作用**: 管理 Windows 开机自启。
    *   **实现**: 操作注册表 `HKCU\Software\Microsoft\Windows\CurrentVersion\Run`。
    *   **技巧**: 区分“脚本运行”和“打包EXE运行”两种环境，写入不同的启动命令（EXE模式下添加 `--minimized` 参数实现静默启动）。

*   **`AudioRecorder`**:
    *   **作用**: 后台录音核心逻辑。
    *   **实现**: 
        *   运行在独立的 `threading.Thread` 中，避免阻塞 GUI。
        *   使用 `PyAudio` 流式读取麦克风数据 (`stream.read`)。
        *   **暂停功能**: 引入 `paused` 标志位。暂停时流保持开启但不读取/写入数据，循环 `sleep`，实现“软暂停”。
        *   **音量增益**: 使用 `audioop.mul` 对二进制音频数据进行乘法运算，实现软件层面的音量放大。

*   **`MainApp` (Tkinter)**:
    *   **作用**: 主界面与用户交互。
    *   **实现**: 
        *   继承自 `tk.Tk`。
        *   **热键监听**: 实现了 `attach_hotkey_listener`，通过绑定 `<Key>` 事件并在 `Entry` 组件聚焦时捕获按键组合，实现“按下即绑定”的智能交互。
        *   **国际化 (i18n)**: 通过 `TRANSLATIONS` 字典和 `tr()` 方法实现中英文动态切换。
        *   **线程安全**: 录音线程通过回调 `app.update_status` 更新 UI 时，使用 `self.after(0, ...)` 将操作调度回主线程执行，防止 GUI 崩溃。

*   **`TrayIconWrapper` (Pystray)**:
    *   **作用**: 系统托盘图标管理。
    *   **实现**: 运行在独立线程。提供右键菜单（开始、停止、显示、退出）和气泡通知。

## 2. 关键技术与难点 (Techniques & Challenges)

### 2.1 全局热键与系统钩子 (Global Hotkeys)
*   **难点**: `keyboard` 库的钩子在某些情况下（如 UI 线程繁忙或启动初期）可能阻塞或失效。用户反馈“最小化启动时热键无效”。
*   **解决方案**:
    1.  **延迟绑定**: 在 `MainApp` 启动后，通过 `app.after(500, ...)` 延迟 500ms 再绑定热键，确保 Windows 消息循环已完全就绪。
    2.  **异步执行**: 热键触发的回调函数中，使用 `threading.Thread` 包装执行逻辑 (`run_async`)。防止录音操作（涉及 IO）阻塞键盘钩子线程，导致系统判定程序无响应而移除钩子。

### 2.2 资源文件与打包 (PyInstaller)
*   **难点**: 
    1.  打包后的 EXE 找不到图标文件。
    2.  构建时出现 `EndUpdateResourceW` 错误（文件被锁）。
*   **解决方案**:
    1.  **资源路径**: 编写 `resource_path` 函数，判断 `sys._MEIPASS`（临时解压目录）来定位打包进 EXE 的资源文件。
    2.  **构建配置**: 在 `MicRecorder.spec` 中设置 `upx=False`，禁用 UPX 压缩，避免杀毒软件扫描压缩壳导致的构建失败或误报。

### 2.3 录音状态管理 (State Management)
*   **技巧**: 明确区分三种状态 `Idle` (空闲), `Recording` (录制中), `Paused` (暂停)。
*   **实现**: 
    *   UI 按钮状态互斥：录音时禁用“开始”，启用“暂停/停止”。
    *   文件保存时机：仅在 `Stop` 时写入 WAV 文件头，保证文件结构完整。

### 2.4 "智能按键绑定" (Smart Binding)
*   **实现**: 
    *   使用 Tkinter 的 `bind('<Key>')`。
    *   解析 `event.state` 位掩码来判断修饰键 (Ctrl/Shift/Alt)。
    *   拦截默认输入 (`return "break"`)，将识别到的组合键格式化为字符串（如 `ctrl+alt+a`）填入输入框。

## 3. 项目结构说明

根目录下生成的 `project_structure.canvas` 文件可视化展示了各模块之间的调用关系。
