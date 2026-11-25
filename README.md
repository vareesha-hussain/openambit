# OpenAmbit

Free/open-source controller for the **Eight Limited Ambit 2** USB (CH340) ambient light bar, and similar
Ambit-style bars. A small local web UI (127.0.0.1 only) with effects, screen sync, music sync, a live LED
preview, a layout editor, auto-reconnect and optional start-with-Windows.

Not affiliated with Eight Limited. "Ambit" is their product name; the protocol below was reverse-engineered
by observing the official app's serial traffic.

## Download (no install, no admin)
Grab `OpenAmbit.exe` from the [latest release](../../releases/latest) and run it. It is a single file with the
web UI bundled. Close the official Ambit app first (only one program can own the COM port).

The light needs the CH340 driver (WCH `CH341SER`). Windows 10/11 usually fetches it from Windows Update when
the light is plugged in. If not, install it once from <https://www.wch-ic.com/downloads/CH341SER_EXE.html>
(needs admin rights once).

## Notes
- The light has no onboard mode memory: after power-up it flashes R/G/B and stays dark until a host sends
  frames. It does hold its last frame while it keeps USB power, so **Keep lit on quit** leaves it on after you
  exit. **Start with Windows** (per-user, no admin) restores your saved mode at login.
- Settings persist in `~/.openambit.json`.
- Known issue: on at least one setup, screen sync shows plain white on the light even though the app computes the
  correct edge colours. Effects and music sync are unaffected. Under investigation.

## Run from source
    pip install -r requirements.txt
    python -m openambit            # --dry-run = UI only, no hardware; --port COM6; --no-browser

## Build the exe
    pip install pyinstaller
    build.bat
`build.bat` bundles `drivers\CH341SER.EXE` if you place WCH's installer there (optional; not included in this
repo because it is WCH's binary).

## Protocol (reverse-engineered, 460800 8N1)
Packet: `AA 55 | cmd | len (2 bytes, big-endian) | payload | 0D 0A`

| cmd | Meaning |
|---|---|
| `00` | init, no payload. Replies with a 13-byte info block (`42 29 00 01 2D 23 19 01 10 10 14 20 14`) |
| `01` | frame: len `0x0139` (313) = 1 byte `00` + 104 × `R G B` |
| `0A` | 1-byte register, echoes the value; no visible effect found |

All other command numbers (02–FF) gave no reply for payload lengths 0–4 and 8.
LED order: starts bottom-right, up the right edge, across the top (right→left), down the left edge, along the
bottom (left→right). Default split is right 22 / top 30 / left 22 / bottom 30; adjust it in the UI.

License: MIT
