import json
import threading
import time
from pathlib import Path

import numpy as np

from . import effects, music
from .layout import Layout
from .screen import ScreenSampler

STATE_FILE = Path.home() / ".openambit.json"

DEFAULTS = {
    "mode": "effect",            # effect | screen | music | off
    "power": True,
    "keep_on_quit": False,       # leave the last frame lit when OpenAmbit exits
    "brightness": 1.0,
    "gamma": 1.0,
    "fps": 30,
    "effect": {"name": "static", "colors": ["#ff3b00"], "speed": 0.25, "scale": 1.0},
    "screen": {"depth": 0.12, "smoothing": 0.5, "saturation": 1.2, "black_level": 12, "monitor": 1},
    "music": {"style": "spectrum", "sensitivity": 1.0, "colors": ["#ff0040", "#ffcc00", "#00ccff"]},
    "layout": {"right": 22, "top": 30, "left": 22, "bottom": 30, "reverse": False},
}


def deep_merge(a, b):
    for k, v in b.items():
        if isinstance(v, dict) and isinstance(a.get(k), dict):
            deep_merge(a[k], v)
        else:
            a[k] = v
    return a


class Engine:
    def __init__(self, device):
        self.dev = device
        self.state = json.loads(json.dumps(DEFAULTS))
        try:
            deep_merge(self.state, json.loads(STATE_FILE.read_text()))
        except Exception:
            pass
        self.layout = Layout(**self.state["layout"])
        self.screen = ScreenSampler(self.layout)
        self.audio = music.MusicAnalyzer()
        self.lock = threading.Lock()
        self.preview = np.zeros((device.n, 3))
        self._run = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def update(self, patch):
        with self.lock:
            deep_merge(self.state, patch)
            if "layout" in patch:
                self.layout = Layout(**self.state["layout"])
                self.screen = ScreenSampler(self.layout)
            try:
                STATE_FILE.write_text(json.dumps(self.state, indent=2))
            except OSError:
                pass

    def stop(self):
        self._run = False
        self._thread.join(timeout=1.0)  # let the last frame go out before the port closes
        self.audio.stop()

    def _loop(self):
        t0 = time.time()
        while self._run:
            t = time.time() - t0
            with self.lock:
                s = json.loads(json.dumps(self.state))
            n = self.dev.n
            try:
                if not s["power"] or s["mode"] == "off":
                    rgb = np.zeros((n, 3))
                elif s["mode"] == "screen":
                    rgb = self.screen.frame(s["screen"])
                elif s["mode"] == "music":
                    self.audio.start()
                    rgb = music.render(self.audio, n, s["music"], t)
                else:
                    e = s["effect"]
                    rgb = effects.EFFECTS[e["name"]](t, n, e)
                rgb = np.clip(rgb / 255.0, 0, 1) ** s["gamma"] * 255 * s["brightness"]
                self.preview = rgb
                self.dev.send(rgb)
            except Exception as ex:  # keep running, surface in UI
                self.error = str(ex)
            time.sleep(max(0.005, 1.0 / s["fps"]))
