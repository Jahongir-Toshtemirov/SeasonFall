@echo off
setlocal
cd /d "%~dp0"

rem ---- 0) make sure Python 3 exists (bare machines) ----
set PY=py
where py >nul 2>nul && goto :havepy
where python >nul 2>nul && goto :havepy

echo ==^> Python not found. Trying winget...
winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
where py >nul 2>nul && goto :havepy

echo ==^> winget unavailable - downloading the official Python installer...
powershell -NoProfile -Command "Invoke-WebRequest -UseBasicParsing -Uri 'https://www.python.org/ftp/python/3.12.8/python-3.12.8-amd64.exe' -OutFile '%TEMP%\python-installer.exe'"
if exist "%TEMP%\python-installer.exe" (
    "%TEMP%\python-installer.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
    set "PATH=%PATH%;%LOCALAPPDATA%\Programs\Python\Launcher;%LOCALAPPDATA%\Programs\Python\Python312"
)
where py >nul 2>nul && goto :havepy
echo ERROR: could not install Python automatically. Install Python 3 from python.org and re-run.
exit /b 1

:havepy
%PY% -c "import sys; sys.exit(0 if sys.version_info[0]>=3 else 1)" >nul 2>nul
if errorlevel 1 (
    echo ERROR: Python 2 found but Python 3 is required.
    exit /b 1
)
echo ==^> Using Python via %PY%

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

echo ==^> Adding SeasonFall to the Start Menu ...
%PYBIN% -m seasonfall install

if "%1"=="--startup" %PYBIN% -m seasonfall startup on

echo.
echo SeasonFall is installed!  Open "SeasonFall" from the Start Menu (no console).
echo Terminal commands:  run.bat settings ^| overlay ^| startup on ^| quit
