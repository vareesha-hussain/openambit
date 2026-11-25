import argparse
import socket
import sys
import webbrowser

from .device import Device, NullDevice, diagnose
from .engine import Engine
from .server import serve


def _msgbox(text):
    try:
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, text, "OpenAmbit", 0x10)
    except Exception:
        print(text, file=sys.stderr)


def _offer_driver(why):
    """CH340 present but no driver: offer to run the bundled (signed) WCH installer. True if launched."""
    import ctypes
    import os
    import shutil
    import tempfile
    base = getattr(sys, "_MEIPASS", os.path.join(os.path.dirname(__file__), ".."))
    src = os.path.join(base, "drivers", "CH341SER.EXE")
    if not os.path.isfile(src):
        _msgbox(why)
        return False
    ans = ctypes.windll.user32.MessageBoxW(
        0, why + "\n\nIf you have an administrator password, run the bundled driver installer now?\n"
                 "(Windows will ask for it. Re-open OpenAmbit afterwards.)", "OpenAmbit", 0x24)
    if ans != 6:  # IDYES
        return False
    dst = os.path.join(tempfile.mkdtemp(), "CH341SER.EXE")
    shutil.copy(src, dst)
    ctypes.windll.shell32.ShellExecuteW(None, "runas", dst, None, None, 1)
    return True


def _port_in_use(port):
    with socket.socket() as s:
        return s.connect_ex(("127.0.0.1", port)) == 0


def main():
    ap = argparse.ArgumentParser(prog="openambit")
    ap.add_argument("--port", help="serial port, e.g. COM6 (auto-detects CH340 by default)")
    ap.add_argument("--dry-run", action="store_true", help="no hardware; UI preview only")
    ap.add_argument("--http-port", type=int, default=8765)
    ap.add_argument("--no-browser", action="store_true")
    ap.add_argument("--autostart", action="store_true", help="launched at login: silent, no browser, no dialogs")
    a = ap.parse_args()
    url = f"http://127.0.0.1:{a.http_port}"

    if _port_in_use(a.http_port):  # already running: just show the UI
        webbrowser.open(url)
        return

    dev = NullDevice() if a.dry_run else Device(a.port)
    try:
        dev.open()
    except Exception as e:
        # Keep running and wait for the light: Device.send() reconnects when it appears, and the saved
        # mode then resumes. Only nag the user when launched by hand, never from the login autostart.
        code, msg = diagnose()
        if not a.autostart:
            if code == "no_driver":
                if _offer_driver(msg):
                    return
            elif code == "busy":
                _msgbox(f"{msg}\n\n(Details: {e})")
    eng = Engine(dev)
    if a.autostart:
        a.no_browser = True
    if not a.no_browser:
        webbrowser.open(url)
    try:
        serve(eng, port=a.http_port)
    except KeyboardInterrupt:
        pass
    finally:
        eng.stop()
        dev.close(blackout=not eng.state.get("keep_on_quit"))


if __name__ == "__main__":
    main()
