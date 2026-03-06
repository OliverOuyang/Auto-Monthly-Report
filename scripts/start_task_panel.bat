@echo off
setlocal
cd /d "%~dp0\.."

if exist "C:\Python313\python.exe" (
  set "PY_EXE=C:\Python313\python.exe"
) else (
  set "PY_EXE=python"
)

echo Starting task panel at http://127.0.0.1:8765
echo Press Ctrl+C to stop.
"%PY_EXE%" scripts\task_panel.py --host 127.0.0.1 --port 8765

endlocal
