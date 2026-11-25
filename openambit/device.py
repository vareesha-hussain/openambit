"""Serial driver for Ambit-style USB (CH340) LED bars.

Reverse-engineered protocol (460800 baud, 8N1):
  init : AA 55 00 00 00 0D 0A
  frame: AA 55 01 01 39 00 | N * (R,G,B) | 0D 0A      (N = 104)
"""
import threading
import time


import numpy as np
import serial
from serial.tools import list_ports

BAUD = 460800
INIT = bytes.fromhex("aa550000000d0a")
HEADER = bytes.fromhex("aa5501013900")
TAIL = b"\r\n"


def find_port():
    for p in list_ports.comports():
        if p.vid == 0x1A86 and p.pid == 0x7523:
            return p.device
    return None


def diagnose():
    """Why can't we reach the light? Returns (code, human message). No admin needed."""
    import subprocess
    if find_port():
        return "busy", ("The light is detected but its COM port can't be opened.\n"
                        "Close the official Ambit app (or any other program using it) and try again.")
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "Get-PnpDevice -PresentOnly | Where-Object { $_.InstanceId -like 'USB\\VID_1A86&PID_7523*' } "
             "| Select-Object -ExpandProperty Status"],
            capture_output=True, text=True, timeout=15, creationflags=0x08000000).stdout.split()
    except Exception:
        out = []
    if out:
        return "no_driver", ("The light's USB chip (CH340) is plugged in, but Windows has no working driver "
                             "for it, so no COM port exists.\n\n"
                             "Without administrator rights this can't be fixed by the app. Try:\n"
                             "  1. Connect to the internet and re-plug the light; Windows Update often installs "
                             "the driver automatically for standard users.\n"
                             "  2. Otherwise ask an administrator to run the driver installer once.")
    return "no_usb", ("No light was found on USB.\nCheck that the cable is plugged in directly "
                      "(a data cable, not charge-only) and try another port.")


class Device:
    def __init__(self, port=None, n_leds=104):
        self.fixed_port = port          # user-forced port; else auto-detect (port can change on re-plug)
        self.port = port or find_port()
        self.n = n_leds
        self.ser = None
        self._last_try = 0.0
        self.lock = threading.Lock()

    @property
    def connected(self):
        return self.ser is not None

    def _open(self):
        self.ser = serial.Serial(self.port, BAUD, timeout=1, write_timeout=1)
        self.ser.write(INIT)

    def open(self):
        """Strict first open, so startup can report why it failed."""
        if not self.port:
            raise RuntimeError("No CH340 device found. Is the light plugged in and Ambit closed?")
        self._open()

    def close(self, blackout=True):
        """blackout=False leaves the last frame on the light (it holds it while USB stays powered)."""
        if self.ser:
            try:
                if blackout:
                    self.send(np.zeros((self.n, 3), np.uint8))
            finally:
                try:
                    self.ser.close()
                finally:
                    self.ser = None

    def send(self, rgb):
        """rgb: (n,3) array of 0..255. Reconnects automatically after the light is unplugged/re-plugged,
        so the saved mode resumes by itself."""
        data = np.clip(rgb, 0, 255).astype(np.uint8).tobytes()
        with self.lock:
            if not self.ser:
                if time.time() - self._last_try < 1.5:
                    return
                self._last_try = time.time()
                self.port = self.fixed_port or find_port()
                if not self.port:
                    return
                try:
                    self._open()
                except (serial.SerialException, OSError):
                    self.ser = None
                    return
            try:
                self.ser.write(HEADER + data + TAIL)
            except (serial.SerialException, OSError):
                try:
                    self.ser.close()
                except Exception:
                    pass
                self.ser = None


class NullDevice(Device):
    """Used with --dry-run so the UI works without hardware."""
    def __init__(self, n_leds=104):
        super().__init__(port="none", n_leds=n_leds)
        self.last = np.zeros((n_leds, 3), np.uint8)

    connected = True

    def open(self): pass
    def close(self, blackout=True): pass
    def send(self, rgb): self.last = np.clip(rgb, 0, 255).astype(np.uint8)
