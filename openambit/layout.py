"""LED strip geometry. Order (measured on hardware): starts bottom-right,
up the right side, across the top right->left, down the left side,
then along the bottom left->right."""
import numpy as np


class Layout:
    def __init__(self, right=22, top=30, left=22, bottom=30, reverse=False):
        self.right, self.top, self.left, self.bottom = right, top, left, bottom
        self.n = right + top + left + bottom
        self.reverse = reverse

    def positions(self):
        """Normalised (x, y) per LED, origin top-left, plus edge name."""
        pts, edges = [], []
        def line(count, a, b, name):
            for i in range(count):
                t = (i + 0.5) / count
                pts.append((a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t))
                edges.append(name)
        line(self.right, (1, 1), (1, 0), "right")
        line(self.top, (1, 0), (0, 0), "top")
        line(self.left, (0, 0), (0, 1), "left")
        line(self.bottom, (0, 1), (1, 1), "bottom")
        pts, edges = np.array(pts), np.array(edges)
        if self.reverse:
            pts, edges = pts[::-1], edges[::-1]
        return pts, edges
