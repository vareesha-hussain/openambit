"""Screen sync: sample screen edges, one region per LED.

Capture runs in its own thread and only grabs the four edge strips (not the whole screen), so the render
loop can keep streaming frames to the light at full rate no matter how slow a capture is. The light shows
white if frames arrive too slowly.
"""
import threading
import time

import numpy as np
import mss


class ScreenSampler:
    def __init__(self, layout, monitor=1):
        self.layout = layout
        self.monitor = monitor
        self.prev = None
        self.latest = None
        self.p = {}
        self._seen = 0.0
        self._lock = threading.Lock()
        self._thread = None
        self.error = None

    def frame(self, p):
        """Return the newest (n,3) float colours instantly. Params: depth (0.02-0.5), smoothing (0-0.95),
        saturation, black_level, monitor."""
        with self._lock:
            self.p = p
            self._seen = time.time()
            if self._thread is None or not self._thread.is_alive():
                self._thread = threading.Thread(target=self._run, daemon=True)
                self._thread.start()
            latest = self.latest
        if latest is None:
            return np.zeros((self.layout.n, 3))
        return latest.copy()

    def _run(self):
        try:
            with mss.MSS() if hasattr(mss, "MSS") else mss.mss() as sct:
                while time.time() - self._seen < 1.5:   # idle out when screen mode isn't in use
                    t0 = time.time()
                    out = self._compute(sct, self.p)
                    with self._lock:
                        self.latest = out
                    time.sleep(max(0.0, 0.015 - (time.time() - t0)))
        except Exception as ex:
            self.error = str(ex)

    def _compute(self, sct, p):
        mons = sct.monitors
        mon = mons[min(max(int(p.get("monitor", self.monitor)), 1), len(mons) - 1)]
        W, H = mon["width"], mon["height"]
        depth = float(p.get("depth", 0.12))
        # cap strip thickness: grab cost scales with pixels and >120px adds nothing but blur on 4K
        dwp, dhp = min(120, max(4, int(W * depth))), min(120, max(4, int(H * depth)))

        def grab(l, t, w, h):  # BGRA -> RGB, downscale by 4
            box = {"left": mon["left"] + l, "top": mon["top"] + t, "width": w, "height": h}
            return np.asarray(sct.grab(box))[::4, ::4, 2::-1].astype(float)

        # ~25 ms fixed GDI cost per grab (parallel grabs don't help: GDI serializes them)
        strips = {"top": grab(0, 0, W, dhp), "bottom": grab(0, H - dhp, W, dhp),
                  "left": grab(0, 0, dwp, H), "right": grab(W - dwp, 0, dwp, H)}
        w, h = strips["top"].shape[1], strips["left"].shape[0]
        pts, edges = self.layout.positions()
        out = np.zeros((len(pts), 3))
        span = max(1, int(1.2 * max(w, h) / max(self.layout.top, self.layout.right)))
        for i, ((x, y), e) in enumerate(zip(pts, edges)):
            cx, cy = int(min(x, 0.999) * w), int(min(y, 0.999) * h)
            s = strips[e]
            if e in ("top", "bottom"):
                reg = s[:, max(0, cx - span):min(w, cx + span)]
            else:
                reg = s[max(0, cy - span):min(h, cy + span), :]
            out[i] = reg.reshape(-1, 3).mean(0)
        sat = float(p.get("saturation", 1.2))   # saturation boost
        grey = out.mean(1, keepdims=True)
        out = np.clip(grey + (out - grey) * sat, 0, 255)
        out[out.max(1) < float(p.get("black_level", 12))] = 0
        s = float(p.get("smoothing", 0.5))      # temporal smoothing
        if self.prev is not None and self.prev.shape == out.shape:
            out = self.prev * s + out * (1 - s)
        self.prev = out
        return out
