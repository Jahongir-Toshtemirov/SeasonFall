@echo off
setlocal
cd /d "%~dp0"

set PY=python
where py >nul 2>nul && set PY=py
echo ==^> Using %PY%

if not exist .venv\Scripts\python.exe (
    echo ==^> Creating virtual environment .venv ...
    %PY% -m venv .venv
)
if exist .venv\Scripts\python.exe (set PYBIN=.venv\Scripts\python.exe) else (set PYBIN=%PY%)

echo ==^> Installing PySide6 ...
%PYBIN% -m pip install -r requirements.txt
if errorlevel 1 %PYBIN% -m pip install --user -r requirements.txt

%PYBIN% -c "import PySide6" >nul 2>nul
if errorlevel 1 (
    echo ERROR: PySide6 is not importable - see README troubleshooting.
    exit /b 1
)
echo ==^> PySide6 OK

if "%1"=="--startup" %PYBIN% -m seasonfall startup on

echo.
echo SeasonFall is ready!  Run:  run.bat
