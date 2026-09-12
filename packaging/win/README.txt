SeasonFall for Windows — portable
=================================

What is this?
  A folder with everything SeasonFall needs. No Python install, no
  admin rights, nothing to "install".

How to run
----------
1. Keep this folder in one place (do not move files out of it).
2. Double-click  "Start SeasonFall.bat"
   - First run only: it downloads the graphics toolkit (~70 MB),
     so it needs internet ONCE. After that it works offline.
3. The season picker opens — pick a season and enjoy the snow.
   After that, snow falls over your desktop every time you
   double-click the bat (or add it to shell:startup for autostart).

Buttons
-------
"Start SeasonFall.bat"     starts / adopts the falling overlay
"SeasonFall Settings.bat"  opens the settings window

Stop it / change seasons
------------------------
Open "SeasonFall Settings.bat" any time, or:
  runtime\python.exe -m seasonfall quit
  runtime\python.exe -m seasonfall pause
  runtime\python.exe -m seasonfall resume

Notes
-----
- The overlay is click-through: clicks go to your apps, not the snow.
- Works on Windows 10 / 11 (64-bit). Needs internet only for the very
  first run.
- Everything lives inside this folder (runtime + installed toolkit),
  so deleting the folder removes SeasonFall completely.
