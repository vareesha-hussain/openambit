"""Screen sync: sample screen edges, one region per LED."""
import threading
import numpy as np
import mss


class ScreenSampler:
    def __init__(self, layout, monitor=1):
        self.layout = layout
        self.monitor = monitor
        self._local = threading.local()
        self.prev = None

    def _sct(self):
        if not hasattr(self._local, "sct"):
            self._local.sct = mss.mss()
        return self._local.sct

    def frame(self, p):
        """Return (n,3) float colours. Params: depth (0.02-0.5), smoothing (0-0.95),
        saturation, black_level, region ('edges')."""
        sct = self._sct()
        mons = sct.monitors
        mon = mons[min(max(int(p.get("monitor", self.monitor)), 1), len(mons) - 1)]
        img = np.asarray(sct.grab(mon))[:, :, 2::-1][::4, ::4].astype(float)  # BGRA->RGB, downscale
        h, w, _ = img.shape
        depth = float(p.get("depth", 0.12))
        pts, edges = self.layout.positions()
        out = np.zeros((len(pts), 3))
        dw, dh = max(1, int(w * depth)), max(1, int(h * depth))
        span = max(1, int(1.2 * max(w, h) / max(self.layout.top, self.layout.right)))
        for i, ((x, y), e) in enumerate(zip(pts, edges)):
            cx, cy = int(min(x, 0.999) * w), int(min(y, 0.999) * h)
            if e in ("top", "bottom"):
                x0, x1 = max(0, cx - span), min(w, cx + span)
                y0, y1 = (0, dh) if e == "top" else (h - dh, h)
            else:
                y0, y1 = max(0, cy - span), min(h, cy + span)
                x0, x1 = (0, dw) if e == "left" else (w - dw, w)
            out[i] = img[y0:y1, x0:x1].reshape(-1, 3).mean(0)
        # saturation boost
        sat = float(p.get("saturation", 1.2))
        grey = out.mean(1, keepdims=True)
        out = np.clip(grey + (out - grey) * sat, 0, 255)
        out[out.max(1) < float(p.get("black_level", 12))] = 0
        # temporal smoothing
        s = float(p.get("smoothing", 0.5))
        if self.prev is not None and self.prev.shape == out.shape:
            out = self.prev * s + out * (1 - s)
        self.prev = out
        return out
