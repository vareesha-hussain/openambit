"""Music sync via WASAPI loopback (whatever your speakers are playing)."""
import threading
import numpy as np
from .effects import palette_sample, hex_to_rgb

RATE, BLOCK = 44100, 1024


class MusicAnalyzer:
    def __init__(self):
        self.bands = np.zeros(32)
        self.level = 0.0
        self.beat = 0.0
        self._avg = 1e-3
        self._run = False
        self._thread = None
        self.error = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._run = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._run = False

    def _loop(self):
        try:
            import soundcard as sc
            spk = sc.default_speaker()
            mic = sc.get_microphone(spk.name, include_loopback=True)
            win = np.hanning(BLOCK)
            edges = np.geomspace(30, 16000, 33)
            freqs = np.fft.rfftfreq(BLOCK, 1 / RATE)
            with mic.recorder(samplerate=RATE, channels=1, blocksize=BLOCK) as rec:
                while self._run:
                    x = rec.record(numframes=BLOCK)[:, 0] * win
                    mag = np.abs(np.fft.rfft(x))
                    b = np.array([mag[(freqs >= lo) & (freqs < hi)].mean() if ((freqs >= lo) & (freqs < hi)).any() else 0
                                  for lo, hi in zip(edges[:-1], edges[1:])])
                    b = np.log1p(b * 20) / 4
                    self.bands = np.maximum(b, self.bands * 0.8)
                    lvl = float(np.sqrt((x ** 2).mean()))
                    self._avg = self._avg * 0.98 + lvl * 0.02
                    self.beat = 1.0 if lvl > self._avg * 1.6 and lvl > 0.01 else self.beat * 0.85
                    self.level = lvl
        except Exception as e:  # noqa
            self.error = str(e)


def render(an, n, p, t):
    sens = float(p.get("sensitivity", 1.0))
    cols = p.get("colors", ["#ff0040", "#ffcc00", "#00ccff"])
    style = p.get("style", "spectrum")
    if style == "pulse":
        c = hex_to_rgb(cols[int(t * 0.5) % len(cols)])
        return np.tile(c, (n, 1)) * min(1.0, 0.15 + an.beat * sens + an.level * 6 * sens)
    if style == "level":
        lit = int(np.clip(an.level * 10 * sens, 0, 1) * n)
        out = palette_sample(cols, np.arange(n) / n)
        out[lit:] = 0
        return out
    # spectrum: mirrored around the strip, bass at index 0
    idx = np.abs(np.linspace(-1, 1, n)) * 31
    amp = np.clip(np.interp(idx, np.arange(32), an.bands) * sens, 0, 1)
    return palette_sample(cols, np.arange(n) / n) * amp[:, None]
