# OpenAmbit

FOSS replacement for the official Ambit app (Flutter, `C:\Program Files\Ambit\`) controlling a USB (CH340, VID 1A86:PID 7523) ambient LED bar. Python backend + local web UI, packaged as a single Windows exe.

## Commands
- Run from source: `python -m openambit` (`--dry-run` = no hardware, `--no-browser`, `--port COM6`, `--http-port N`)
- Build exe: `python -m PyInstaller --noconfirm --onefile --windowed --name OpenAmbit --distpath dist2 --add-data "openambit/web;openambit/web" --add-data "drivers/CH341SER.EXE;drivers" --collect-all soundcard --hidden-import cffi run.py`
  - Output to a fresh `--distpath` if `dist\OpenAmbit.exe` is locked (Windows/AV locks it after a run).
- Headless test: run Python (NOT `python -I`, it ignores cwd/PYTHONPATH) from the repo root with `NullDevice` + `Engine`, cycle modes, check `engine.error`.
- Only one program can own COM6: the official Ambit app must be closed.

## Layout
- `openambit/device.py` serial driver + `NullDevice`; `layout.py` LED geometry; `effects.py`; `screen.py` (mss edge sampling); `music.py` (WASAPI loopback FFT); `engine.py` render loop + state (persisted to `~/.openambit.json`); `server.py` stdlib HTTP API (`/api/state`, `/api/update`, `/api/quit`); `web/index.html` UI; `__main__.py` entry (single-instance via port check, driver-install prompt).
- State flags worth knowing: `keep_on_quit` (Engine state; `__main__` calls `dev.close(blackout=not keep_on_quit)`), autostart via `/api/autostart`.
- If a build seems unchanged, an old instance is still running (new launches just open its page): `POST /api/quit` first. Latest build used: `dist6`.
- `run.py` is the PyInstaller entry point. `drivers/CH341SER.EXE` is WCH's signed driver, bundled into the exe.

## Protocol (reverse-engineered with Frida hooking WriteFile on Ambit.exe; 460800 8N1)
- init `AA 55 00 00 00 0D 0A`; frame `AA 55 01 01 39 00` + 104×RGB + `0D 0A`. Color order RGB (user-confirmed).
- Header bytes `01 39 00` constant in all captures, meaning unknown.
- LED order: starts bottom-right, up right edge, across top right→left, down left edge, bottom left→right. Default split 22/30/22/30 is an ESTIMATE from a sweep test, not verified by the user.

## Persistence / auto-resume
- The light has no known onboard memory (official Ambit turns it off on exit; only init + frame packets seen). "Default mode on plug-in" is host-side: settings saved to `~/.openambit.json` on every change, `Device.send()` auto-reconnects (re-detects port, re-sends init) so the saved mode resumes after re-plug, and `autostart.py` writes HKCU Run (`--autostart` = silent: no browser, no dialogs). The app must be running for the light to light up.

## Gotchas
- POST handler rejects mismatched `Origin` (CSRF guard for the localhost API); keep that.
- In `--windowed` builds `sys.stdout` is None: don't `print` in the exe path; use `_msgbox`.
- Ambit's `assets/fake/*.dll` are PNGs; its scene/music presets (`sceneConfig.json`, `musicConfig.json`) are Ambit's assets, not bundled.

## Controller replies (probed 2026-11-25, light plugged in)
- Device is Eight Limited "Ambit 2" (model C2962). Boots with an R/G/B flash, then dark until a host streams frames; no onboard mode survives a re-plug (user-verified).
- Packet = `AA 55 | cmd | len(2B BE) | payload | 0D 0A`. Frame cmd 01: len 0x0139 = 313 = 1 + 104*3.
- cmd 00 (init) replies with a 13-byte block: `42 29 00 01 2d 23 19 01 10 10 14 20 14` (probably firmware/device info).
- cmd 0A is a writable 1-byte register: reply echoes the value (tested 0-4); no visible effect, still reads 0 after re-plug.
- cmds 02-FF (other than 0A) with payload lengths 0,1,2,3,4,8 (zeros): no reply, no visible change.
- The light HOLDS its last frame after the host disconnects while USB stays powered ("Keep lit on quit" option relies on this).
