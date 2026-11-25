"""Start-with-Windows via HKCU\\...\\Run (per-user, no admin needed)."""
import sys

KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
NAME = "OpenAmbit"


def _command():
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --autostart'
    return None  # only meaningful for the packaged exe


def is_enabled():
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY) as k:
            return winreg.QueryValueEx(k, NAME)[0] == _command()
    except Exception:
        return False


def set_enabled(on):
    """Returns (ok, message)."""
    import winreg
    cmd = _command()
    if on and not cmd:
        return False, "Start-with-Windows only works from the packaged OpenAmbit.exe."
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, KEY, 0, winreg.KEY_SET_VALUE) as k:
        if on:
            winreg.SetValueEx(k, NAME, 0, winreg.REG_SZ, cmd)
        else:
            try:
                winreg.DeleteValue(k, NAME)
            except FileNotFoundError:
                pass
    return True, "ok"
