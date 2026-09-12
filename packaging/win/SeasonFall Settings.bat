@echo off
rem SeasonFall settings window (Windows)
cd /d "%~dp0"
set PYTHON=runtime\python.exe
set PYTHONW=runtime\pythonw.exe

%PYTHON% -c "import PySide6" >nul 2>&1
if errorlevel 1 (
  echo First run: downloading the graphics toolkit, one moment...
  %PYTHON% get-pip.py --no-warn-script-location --quiet
  if errorlevel 1 goto :fail
  %PYTHON% -m pip install --no-warn-script-location --quiet PySide6
  if errorlevel 1 goto :fail
)
start "" "%PYTHONW%" -m seasonfall settings
exit /b 0

:fail
echo Could not set up SeasonFall. Check your internet connection and try again.
pause
exit /b 1
