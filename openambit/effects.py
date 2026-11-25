"""Static / animated effects. Each takes (t, n, params) and returns (n,3) floats 0..255."""
import colorsys
import numpy as np


def hex_to_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def palette_sample(colors, x):
    """colors: list of hex; x: array in [0,1) -> (len(x),3) smooth cyclic gradient."""
    pal = np.array([hex_to_rgb(c) for c in colors])
    k = len(pal)
    if k == 1:
        return np.tile(pal[0], (len(x), 1))
    pos = (np.asarray(x) % 1.0) * k
    i = np.floor(pos).astype(int) % k
    f = (pos - np.floor(pos))[:, None]
    return pal[i] * (1 - f) + pal[(i + 1) % k] * f


def static(t, n, p):
    return np.tile(hex_to_rgb(p["colors"][0]), (n, 1))


def gradient(t, n, p):
    return palette_sample(p["colors"], np.arange(n) / n)


def rainbow(t, n, p):
    sp = p.get("speed", 0.2)
    h = (np.arange(n) / n * p.get("scale", 1.0) + t * sp) % 1.0
    return np.array([colorsys.hsv_to_rgb(x, 1, 1) for x in h]) * 255


def breathing(t, n, p):
    sp = p.get("speed", 0.3)
    lvl = 0.5 - 0.5 * np.cos(2 * np.pi * t * sp)
    return np.tile(hex_to_rgb(p["colors"][0]), (n, 1)) * lvl


def chase(t, n, p):
    sp = p.get("speed", 0.3)
    x = (np.arange(n) / n - t * sp) % 1.0
    base = palette_sample(p["colors"], x * 0 + (t * 0.05))  # first->cycling colour
    glow = np.exp(-((x) * n / max(3, n * 0.12)))  # comet tail
    return base * glow[:, None]


def twinkle(t, n, p):
    rng = np.random.default_rng(int(t * p.get("speed", 4)))
    cols = palette_sample(p["colors"], rng.random(n))
    return cols * (rng.random(n) > 0.7)[:, None]


def fire(t, n, p):
    rng = np.random.default_rng(int(t * 12))
    v = rng.random(n) * 0.6 + 0.4
    return np.stack([v * 255, v * v * 110, np.zeros(n)], 1)


EFFECTS = {
    "static": static, "gradient": gradient, "rainbow": rainbow,
    "breathing": breathing, "chase": chase, "twinkle": twinkle, "fire": fire,
}
