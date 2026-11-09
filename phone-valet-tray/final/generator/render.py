#!/usr/bin/env python3
"""Render preview.png (three views + a cut through the phone dock) with a
small z-buffer rasteriser. Needs numpy, matplotlib, trimesh, manifold3d."""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import trimesh

import build

here = os.path.dirname(os.path.abspath(__file__))
stl = os.path.join(here, "..", "stl", "nightstand_valet.stl")
N = 800
COLOUR = np.array([0.20, 0.55, 0.85])


def rot(elev, azim):
    a, e = np.radians(azim), np.radians(elev)
    rz = np.array([[np.cos(a), -np.sin(a), 0], [np.sin(a), np.cos(a), 0], [0, 0, 1]])
    rx = np.array([[1, 0, 0], [0, np.cos(e), -np.sin(e)], [0, np.sin(e), np.cos(e)]])
    return rx @ rz


def render(m, elev, azim):
    R = rot(elev, azim)
    centre = m.bounds.mean(0)
    v = (m.vertices - centre) @ R.T
    n = m.face_normals @ R.T
    keep = n[:, 2] > 0
    tri, nn = v[m.faces[keep]], n[keep]
    light = np.array([0.3, 0.6, 0.75]); light /= np.linalg.norm(light)
    shade = (0.25 + 0.75 * np.clip(nn @ light, 0, 1))[:, None] * COLOUR
    ext = np.abs(v[:, :2]).max() * 1.08
    scale, off = N / (2 * ext), N / 2
    img = np.full((N, N, 3), 0.96)
    zbuf = np.full((N, N), -np.inf)
    px, py = tri[:, :, 0] * scale + off, off - tri[:, :, 1] * scale
    for t in range(len(tri)):
        x, y, z = px[t], py[t], tri[t, :, 2]
        x0, x1 = int(max(np.floor(x.min()), 0)), int(min(np.ceil(x.max()), N - 1))
        y0, y1 = int(max(np.floor(y.min()), 0)), int(min(np.ceil(y.max()), N - 1))
        if x1 < x0 or y1 < y0:
            continue
        den = (y[1] - y[2]) * (x[0] - x[2]) + (x[2] - x[1]) * (y[0] - y[2])
        if abs(den) < 1e-12:
            continue
        gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
        w0 = ((y[1] - y[2]) * (gx - x[2]) + (x[2] - x[1]) * (gy - y[2])) / den
        w1 = ((y[2] - y[0]) * (gx - x[2]) + (x[0] - x[2]) * (gy - y[2])) / den
        w2 = 1 - w0 - w1
        inside = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
        zz = w0 * z[0] + w1 * z[1] + w2 * z[2]
        sub = zbuf[y0:y1 + 1, x0:x1 + 1]
        upd = inside & (zz > sub)
        sub[upd] = zz[upd]
        img[y0:y1 + 1, x0:x1 + 1][upd] = shade[t]
    return img


m = trimesh.load(stl)
fig, axs = plt.subplots(2, 2, figsize=(13, 11))
for ax, (e, a, title) in zip(axs.flat, [(-60, -30, "front left"),
                                         (-60, 150, "back (cable slit)"),
                                         (0, 0, "top")]):
    ax.imshow(render(m, e, a)); ax.set_title(title); ax.axis("off")

# Section through the dock centre line: shows slot, plug pocket and slit.
x_mid = build.WALL + build.DOCK_W / 2 - build.WALL / 2
sec = m.section(plane_origin=[x_mid + 4.5, 0, 0], plane_normal=[1, 0, 0])
ax = axs.flat[3]
for ent in sec.discrete:
    ax.fill(ent[:, 1], ent[:, 2], color=COLOUR, alpha=0.35)
    ax.plot(ent[:, 1], ent[:, 2], color="k", lw=0.8)
ax.set_aspect("equal"); ax.set_title("cut through the phone dock (side view, mm)")
ax.set_xlabel("front  <-  y  ->  back"); ax.set_ylabel("z")
ax.grid(alpha=0.3)
plt.tight_layout()
plt.savefig(os.path.join(here, "..", "preview.png"), dpi=90)
print("wrote preview.png")
