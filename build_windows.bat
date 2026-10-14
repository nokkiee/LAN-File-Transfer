@echo off
rem Build the Windows version on a Windows PC -> dist\LAN-File-Transfer-Windows.exe
rem Needs Python 3.10+ from https://www.python.org/downloads/
setlocal
cd /d "%~dp0"

set PY=python
where py >nul 2>nul && set PY=py -3

if not exist .venv-win\Scripts\python.exe %PY% -m venv .venv-win || goto :error
.venv-win\Scripts\python -m pip install -q -r requirements.txt -r requirements-build.txt || goto :error
.venv-win\Scripts\python tools\make_icon.py || goto :error
.venv-win\Scripts\pyinstaller --noconfirm --log-level WARN lan-file-transfer.spec || goto :error
echo.
echo Built: dist\LAN-File-Transfer-Windows.exe
pause
exit /b 0

:error
echo.
echo Build failed.
pause
exit /b 1
