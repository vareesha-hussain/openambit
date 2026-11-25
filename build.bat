@echo off
rem Builds release\OpenAmbit.exe (single file). Optional: put WCH's CH341SER.EXE in drivers\ to bundle it.
set DRV=
if exist drivers\CH341SER.EXE set DRV=--add-data "drivers/CH341SER.EXE;drivers"
python -m PyInstaller --noconfirm --clean --onefile --windowed --name OpenAmbit --distpath release ^
  --add-data "openambit/web;openambit/web" %DRV% --collect-all soundcard --hidden-import cffi run.py
