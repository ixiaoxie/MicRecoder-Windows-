@echo off
echo [INFO] Installing PyInstaller...
pip install pyinstaller

echo [INFO] Building executable from spec...
pyinstaller MicRecorder.spec --clean --noconfirm

echo.
echo [INFO] Build finished.
echo [INFO] You can find 'MicRecorder.exe' in the 'dist' folder.
pause
