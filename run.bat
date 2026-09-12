@echo off
rem Launch SeasonFall on Windows. Sets up the environment on first run.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe call install.bat
if exist .venv\Scripts\python.exe (set PYBIN=.venv\Scripts\python.exe) else (set PYBIN=python)
"%PYBIN%" -m seasonfall %*
