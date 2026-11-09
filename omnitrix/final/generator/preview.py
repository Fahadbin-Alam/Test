"""Render preview images of the assembled prop (needs matplotlib)."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import build  # noqa: E402

COLORS = {"cuff": "#262626", "stripe": "#2fbf4a", "bars": "#3dff6a", "housing": "#d9dbe0", "bezel": "#2a2a2a",
          "dial": "#8d929b", "face": "#141414", "insert": "#3dff6a"}
LIGHT = np.array([0.4, 0.8, 0.6]) / np.linalg.norm([0.4, 0.8, 0.6])


def raster(parts, offsets, elev, azim, size=1100, ss=2):
    """Tiny z-buffer renderer (numpy only) so parts hide each other correctly."""
    W = size * ss
    tris_all, cols_all = [], []
    for name, m in parts.items():
        if offsets and name in offsets:
            m = m.translate(offsets[name])
        mesh = m.to_mesh()
        v = np.asarray(mesh.vert_properties)[:, :3][:, [0, 2, 1]]   # face points up (+z)
        v[:, 1] *= -1
        t = v[np.asarray(mesh.tri_verts)]
        n = np.cross(t[:, 1] - t[:, 0], t[:, 2] - t[:, 0])
        n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
        base = np.array(matplotlib.colors.to_rgb(COLORS[name]))
        tris_all.append(t); cols_all.append((n, base))
    # camera rotation
    a, e = np.radians(azim), np.radians(elev)
    Rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    Rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    R = Rx @ Rz
    light = R.T @ np.array([-0.3, 0.5, 0.8]) / np.linalg.norm([-0.3, 0.5, 0.8])
    allv = np.concatenate([t.reshape(-1, 3) for t in tris_all]) @ R.T
    lo, hi = allv.min(0), allv.max(0)
    scale = 0.9 * W / max(hi[0] - lo[0], hi[2] - lo[2])
    ctr = (lo + hi) / 2
    img = np.ones((W, W, 3)); zb = np.full((W, W), -np.inf)
    for t, (n, base) in zip(tris_all, cols_all):
        shade = 0.25 + 0.75 * np.clip(n @ light, 0, 1) + 0.15 * np.clip(-(n @ light), 0, 1) * 0
        col = np.clip(base[None] * (0.55 + 1.0 * shade[:, None]), 0, 1)
        p = (t @ R.T - ctr)
        X = p[..., 0] * scale + W / 2; Y = W / 2 - p[..., 2] * scale; Z = p[..., 1] * -1
        for i in range(len(t)):
            x, y, z = X[i], Y[i], Z[i]
            x0, x1 = int(max(0, np.floor(x.min()))), int(min(W - 1, np.ceil(x.max())))
            y0, y1 = int(max(0, np.floor(y.min()))), int(min(W - 1, np.ceil(y.max())))
            if x1 < x0 or y1 < y0:
                continue
            d = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(d) < 1e-9:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / d
            w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / d
            w2 = 1 - w0 - w1
            inside = (w0 >= 0) & (w1 >= 0) & (w2 >= 0)
            if not inside.any():
                continue
            zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            upd = inside & (zz > sub)
            sub[upd] = zz[upd]
            img[y0:y1 + 1, x0:x1 + 1][upd] = col[i]
    img = img.reshape(size, ss, size, ss, 3).mean((1, 3))
    return img


def render(path, offsets=None, elev=30, azim=-35):
    img = raster(build.assembly(), offsets, elev, azim)
    plt.imsave(path, img)


if __name__ == "__main__":
    out = os.path.join(os.path.dirname(__file__), "..", "images")
    os.makedirs(out, exist_ok=True)
    render(os.path.join(out, "assembled.png"))
    up = lambda d: [0, d, 0]
    render(os.path.join(out, "exploded.png"),
           offsets={"housing": up(8), "bars": up(16), "dial": up(22), "bezel": up(36), "insert": up(46), "face": up(56)})
    print("images written to", os.path.abspath(out))
