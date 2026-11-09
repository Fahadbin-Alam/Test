#!/usr/bin/env python3
"""Render preview PNGs of the three-colour ring with a tiny z-buffer
rasteriser (numpy + matplotlib only, no GPU needed)."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh

here = os.path.dirname(os.path.abspath(__file__))
tag = sys.argv[1] if len(sys.argv) > 1 else "us10"
d = os.path.join(here, "..", "stl", tag)
colours = {"body": (0.74, 0.75, 0.78), "frame": (0.90, 0.68, 0.20),
           "inlay": (0.12, 0.90, 0.30)}
N = 700  # image size in pixels


def rot(elev, azim):
    a, e = np.radians(azim), np.radians(elev)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    return rx @ rz


def render(elev, azim):
    R = rot(elev, azim)
    img = np.full((N, N, 3), 0.11)
    zbuf = np.full((N, N), -np.inf)
    light = np.array([0.3, 0.5, 0.8]); light /= np.linalg.norm(light)
    scale, off = N / 36.0, N / 2
    for name, c in colours.items():
        m = trimesh.load(os.path.join(d, f"ring_{tag}_{name}.stl"))
        v = (m.vertices - [0, 0, 2]) @ R.T          # camera looks down -z... uses +z toward viewer
        n = m.face_normals @ R.T
        keep = n[:, 2] > 0
        tri = v[m.faces[keep]]
        nn = n[keep]
        diff = np.clip(nn @ light, 0, 1)
        spec = np.clip(nn @ (light + [0, 0, 1]) / np.linalg.norm(light + [0, 0, 1]), 0, 1) ** 30
        shade = (0.25 + 0.75 * diff)[:, None] * np.array(c) + 0.35 * spec[:, None]
        if name == "body":  # darken the crack grooves so they read on screen
            hull = m.convex_hull
            ctr = m.triangles_center[keep]
            dist = (ctr @ hull.face_normals.T - (hull.face_normals * hull.triangles_center).sum(1)).max(1)
            sidewall = np.abs(m.face_normals[keep][:, 0]) > 0.6
            shade[(dist < -0.25) & sidewall] *= 0.35
        px = tri[:, :, 0] * scale + off
        py = off - tri[:, :, 1] * scale
        for t in range(len(tri)):
            x, y, z = px[t], py[t], tri[t, :, 2]
            x0, x1 = int(max(np.floor(x.min()), 0)), int(min(np.ceil(x.max()), N - 1))
            y0, y1 = int(max(np.floor(y.min()), 0)), int(min(np.ceil(y.max()), N - 1))
            if x1 < x0 or y1 < y0:
                continue
            gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
            if abs(den) < 1e-12:
                continue
            w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
            w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
            w2 = 1 - w0 - w1
            inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
            sub = zbuf[y0:y1 + 1, x0:x1 + 1]
            upd = inside & (zz > sub)
            sub[upd] = zz[upd]
            img[y0:y1 + 1, x0:x1 + 1][upd] = np.clip(shade[t], 0, 1)
    return img


views = [(-55, -35), (-75, -70), (0, 0)]
fig, axs = plt.subplots(1, 3, figsize=(15, 5), facecolor="#1c1c1c")
for ax, (e, a) in zip(axs, views):
    ax.imshow(render(e, a)); ax.axis("off")
plt.tight_layout()
out = os.path.abspath(os.path.join(here, "..", "preview.png"))
plt.savefig(out, dpi=110, facecolor=fig.get_facecolor())
print(out)
