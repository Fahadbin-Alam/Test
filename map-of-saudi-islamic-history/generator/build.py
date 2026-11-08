#!/usr/bin/env python3
"""Build the printable tiles for the map of the Hijaz in the time of the Prophet.

    pip install -r requirements.txt
    python build.py            # writes ../stl/*.stl and ../preview/*.png

Everything is parametric: change the constants below (bed size, scale,
vertical exaggeration, tile layout) and re-run.

Terrain comes from the free "Terrarium" elevation tiles (SRTM/GMTED based),
downloaded once and cached in generator/.cache/.
"""
import io
import math
import os
import sys
import urllib.request

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from pyproj import Transformer
import manifold3d as m3
from manifold3d import Manifold, CrossSection, FillRule
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties

sys.path.insert(0, os.path.dirname(__file__))
from sites import MAIN_SITES, MECCA_INSET, MEDINA_INSET  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT_STL = os.path.join(HERE, "..", "stl")
OUT_PNG = os.path.join(HERE, "..", "preview")
CACHE = os.path.join(HERE, ".cache")

# ----------------------------------------------------------------- parameters
TILE = 200.0               # mm, square tile edge (fits a 220 x 220 mm bed)
BASE = 4.0                 # mm, thickness under sea level / lowest ground
SEA_DROP = 0.6             # mm, sea surface sits this far below the coast
# Main map: UTM zone 37N grid, 1 mm on the print = 1 km on the ground.
MAIN_KM_PER_MM = 1.0       # 1:1,000,000  ->  1 cm = 10 km, 1 inch = 25.4 km
MAIN_M_PER_MM_Z = 100.0    # 1 mm of height = 100 m  (10x vertical exaggeration)
MAIN_COLS, MAIN_ROWS = 2, 3
MAIN_E0, MAIN_N0 = 340.0, 2330.0   # km, UTM 37N south-west corner of the map
MAIN_STEP = 1.0            # mm, mesh grid spacing
# Insets: 1 mm = 100 m  ->  1 cm = 1 km
INSET_KM_PER_MM = 0.1
INSET_M_PER_MM_Z = 40.0    # 2.5x vertical exaggeration
INSET_STRIP = 15.0         # mm, flat label strip along the south edge
INSET_STEP = 0.6
# Markers & joints
PEG_R, PEG_H = 1.2, 2.0          # peg on the tile that markers press onto
SOCKET_R, SOCKET_H = 1.4, 2.3    # hole in the bottom of each marker
PAD_R = 3.5                      # flattened pad around each marker
KEY_DEPTH, KEY_THICK, KEY_CLEAR = 2.0, 1.8, 0.15
EMBOSS = 0.8                     # raised text/scale-bar height
ENGRAVE = 0.6                    # bottom tile-ID engraving depth

to_utm = Transformer.from_crs(4326, 32637, always_xy=True)
to_geo = Transformer.from_crs(32637, 4326, always_xy=True)


# ------------------------------------------------------------------- DEM data
def _tile(z, x, y):
    os.makedirs(CACHE, exist_ok=True)
    p = os.path.join(CACHE, f"{z}_{x}_{y}.png")
    if not os.path.exists(p):
        url = f"https://s3.amazonaws.com/elevation-tiles-prod/terrarium/{z}/{x}/{y}.png"
        for attempt in range(4):
            try:
                data = urllib.request.urlopen(url, timeout=60).read()
                break
            except Exception:
                if attempt == 3:
                    raise
        with open(p, "wb") as f:
            f.write(data)
    a = np.asarray(Image.open(p).convert("RGB"), dtype=np.float64)
    return a[..., 0] * 256 + a[..., 1] + a[..., 2] / 256 - 32768


def _merc(lon, lat, z):
    n = 256 * 2 ** z
    x = (lon + 180) / 360 * n
    lr = np.radians(lat)
    y = (1 - np.log(np.tan(lr) + 1 / np.cos(lr)) / math.pi) / 2 * n
    return x, y


class DEM:
    """Mosaic of terrarium tiles covering a lon/lat box, sampled bilinearly."""

    def __init__(self, lon0, lat0, lon1, lat1, zoom, smooth_px=0.0):
        x0, y1 = _merc(lon0, lat0, zoom)
        x1, y0 = _merc(lon1, lat1, zoom)
        tx0, tx1 = int(x0 // 256), int(x1 // 256)
        ty0, ty1 = int(y0 // 256), int(y1 // 256)
        rows = []
        for ty in range(ty0, ty1 + 1):
            rows.append(np.hstack([_tile(zoom, tx, ty) for tx in range(tx0, tx1 + 1)]))
        self.a = np.vstack(rows)
        if smooth_px > 0:
            self.a = gaussian_filter(self.a, smooth_px)
        self.ox, self.oy, self.z = tx0 * 256, ty0 * 256, zoom

    def __call__(self, lon, lat):
        x, y = _merc(np.asarray(lon), np.asarray(lat), self.z)
        return map_coordinates(self.a, [y - self.oy, x - self.ox], order=1, mode="nearest")


# ------------------------------------------------------------ mesh utilities
def heightfield_solid(h, step):
    """Watertight solid: top surface h[j, i] (mm) over a grid, flat bottom z=0."""
    ny, nx = h.shape
    xs, ys = np.meshgrid(np.arange(nx) * step, np.arange(ny) * step)
    top = np.column_stack([xs.ravel(), ys.ravel(), h.ravel()])
    idx = np.arange(nx * ny).reshape(ny, nx)
    a, b = idx[:-1, :-1].ravel(), idx[:-1, 1:].ravel()
    c, d = idx[1:, 1:].ravel(), idx[1:, :-1].ravel()
    tris = [np.column_stack([a, b, c]), np.column_stack([a, c, d])]
    # perimeter, counter-clockwise seen from above
    per = np.concatenate([idx[0, :], idx[1:, -1], idx[-1, -2::-1], idx[-2:0:-1, 0]])
    nt = len(top)
    bot = top[per].copy()
    bot[:, 2] = 0.0
    nb = len(per)
    centre = np.array([[xs.max() / 2, ys.max() / 2, 0.0]])
    ci = nt + nb
    k = np.arange(nb)
    k1 = (k + 1) % nb
    tris.append(np.column_stack([np.full(nb, ci), nt + k1, nt + k]))          # bottom
    tris.append(np.column_stack([nt + k, nt + k1, per[k1]]))                  # sides
    tris.append(np.column_stack([nt + k, per[k1], per[k]]))
    verts = np.vstack([top, bot, centre]).astype(np.float32)
    mesh = m3.Mesh(vert_properties=verts, tri_verts=np.vstack(tris).astype(np.uint32))
    return Manifold(mesh)


def cyl(r, z0, z1, x, y, seg=32, r_top=None):
    return Manifold.cylinder(z1 - z0, r, r if r_top is None else r_top, seg).translate((x, y, z0))


def text_cs(s, size, x, y, align="left", mirror=False, bold=True):
    prop = FontProperties(family="DejaVu Sans", weight="bold" if bold else "normal")
    tp = TextPath((0, 0), s, size=size, prop=prop)
    polys = [p[:-1] for p in tp.to_polygons(closed_only=True) if len(p) > 3]
    allp = np.vstack(polys)
    w = allp[:, 0].max() - allp[:, 0].min()
    dx = {"left": 0, "center": -w / 2, "right": -w}[align] - allp[:, 0].min()
    out = []
    for p in polys:
        q = p + [dx, 0]
        if mirror:
            q = q * [-1, 1]
        out.append(q + [x, y])
    return CrossSection(out, FillRule.EvenOdd)


def poly_cs(pts):
    return CrossSection([np.asarray(pts, float)], FillRule.EvenOdd)


def save_stl(man, name):
    mesh = man.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3]
    t = np.asarray(mesh.tri_verts)
    tri = v[t]
    n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = n, tri
    os.makedirs(OUT_STL, exist_ok=True)
    path = os.path.join(OUT_STL, name)
    with open(path, "wb") as f:
        f.write(b"Hijaz map - generated by build.py".ljust(80, b" "))
        f.write(np.uint32(len(t)).tobytes())
        f.write(rec.tobytes())
    bb = man.bounding_box()
    print(f"  {name}: {len(t)} triangles, {bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f} mm")
    return path


# ---------------------------------------------------------------- shaping
def flatten_pad(h, step, px, py, r):
    """Flatten the terrain around (px, py) mm so a marker sits level. Returns pad z."""
    ny, nx = h.shape
    ys, xs = np.mgrid[0:ny, 0:nx] * step
    d = np.hypot(xs - px, ys - py)
    inner = d <= r
    z = float(np.median(h[inner])) if inner.any() else float(h[int(py / step), int(px / step)])
    blend = np.clip((d - r) / 2.0, 0, 1)        # 2 mm smooth skirt
    ring = d <= r + 2.0
    h[ring] = z * (1 - blend[ring]) + h[ring] * blend[ring]
    return z


def peg(x, y, z):
    return cyl(PEG_R, z - 1.0, z + PEG_H, x, y, 24)


def pad_radius(i, pts, default):
    others = [math.hypot(pts[i][0] - p[0], pts[i][1] - p[1]) for j, p in enumerate(pts) if j != i]
    return min([default] + [d / 2 - 0.1 for d in others])


# -------------------------------------------------------------- the main map
def build_main():
    print("Main map: downloading / sampling terrain ...")
    W, H = MAIN_COLS * TILE, MAIN_ROWS * TILE
    nx, ny = int(round(W / MAIN_STEP)) + 1, int(round(H / MAIN_STEP)) + 1
    ex = MAIN_E0 + np.arange(nx) * MAIN_STEP * MAIN_KM_PER_MM
    nn = MAIN_N0 + np.arange(ny) * MAIN_STEP * MAIN_KM_PER_MM
    E, N = np.meshgrid(ex * 1000, nn * 1000)
    lon, lat = to_geo.transform(E, N)
    dem = DEM(lon.min() - .05, lat.min() - .05, lon.max() + .05, lat.max() + .05, 9, smooth_px=1.2)
    elev = dem(lon, lat)
    sea = elev < 0
    h = BASE + np.clip(elev, 0, None) / MAIN_M_PER_MM_Z
    h[sea] = BASE - SEA_DROP
    sea_z = BASE - SEA_DROP

    # site positions in mm on the assembled map
    pts = []
    for s in MAIN_SITES:
        e, n = to_utm.transform(s[2], s[1])
        pts.append(((e / 1000 - MAIN_E0) / MAIN_KM_PER_MM, (n / 1000 - MAIN_N0) / MAIN_KM_PER_MM))
    pads = []
    for i, (px, py) in enumerate(pts):
        r = pad_radius(i, pts, PAD_R)
        pads.append(flatten_pad(h, MAIN_STEP, px, py, r))

    np.save(os.path.join(CACHE, "main_h.npy"), h)

    # bow-tie key pockets along every internal seam: (x, y, angle)
    keys = []
    for c in range(1, MAIN_COLS):
        for r in range(MAIN_ROWS):
            for f in (0.25, 0.75):
                keys.append((c * TILE, (r + f) * TILE, 0))
    for r in range(1, MAIN_ROWS):
        for c in range(MAIN_COLS):
            for f in (0.25, 0.75):
                keys.append(((c + f) * TILE, r * TILE, 90))
    for (kx, ky, _a) in keys:
        for (px, py) in pts:
            if math.hypot(kx - px, ky - py) < 20:
                print(f"  warning: key at {kx},{ky} is close to a marker")

    full = None  # not built as one piece; tiles are cut from the heightfield
    tiles = []
    per = int(round(TILE / MAIN_STEP))
    for r in range(MAIN_ROWS):
        for c in range(MAIN_COLS):
            name = f"{'AB'[c]}{r + 1}"
            sub = h[r * per:(r + 1) * per + 1, c * per:(c + 1) * per + 1]
            ox, oy = c * TILE, r * TILE
            solid = heightfield_solid(sub, MAIN_STEP)
            adds, cuts = [], []
            for (px, py), z, s in zip(pts, pads, MAIN_SITES):
                if ox <= px < ox + TILE and oy <= py < oy + TILE:
                    adds.append(peg(px - ox, py - oy, z))
            for (kx, ky, a) in keys:
                lx, ly = kx - ox, ky - oy
                if -16 <= lx <= TILE + 16 and -16 <= ly <= TILE + 16:
                    cuts.append(key_shape(0).rotate(a).translate((lx, ly)).extrude(KEY_DEPTH + 1).translate((0, 0, -1)))
            # tile ID + north arrow engraved (mirrored) on the bottom
            lab = text_cs(f"{name}", 22, TILE / 2, TILE / 2 - 8, "center", mirror=True)
            lab2 = text_cs("N^  top edge", 6, TILE / 2, TILE / 2 + 22, "center", mirror=True)
            lab3 = text_cs("Hijaz 1:1,000,000", 6, TILE / 2, TILE / 2 - 22, "center", mirror=True)
            for cs in (lab, lab2, lab3):
                cuts.append(cs.extrude(ENGRAVE + 1).translate((0, 0, -1)))
            if name == "A1":
                adds += scale_bar_main(sub, sea_z)
            if name == "A2":
                adds.append(text_cs("RED SEA", 9, 12, 78).extrude(EMBOSS + 0.3).translate((0, 0, sea_z - 0.3)))
                adds.append(text_cs("Bahr al-Qulzum", 5, 12, 68).extrude(EMBOSS + 0.3).translate((0, 0, sea_z - 0.3)))
                check_sea(sub, sea_z, 10, 66, 70, 90, "A2 label")
            if adds:
                solid = solid + Manifold.batch_boolean(adds, m3.OpType.Add)
            if cuts:
                solid = solid - Manifold.batch_boolean(cuts, m3.OpType.Add)
            tiles.append((name, solid))
            save_stl(solid, f"main_{name}.stl")
    return h, pts


def check_sea(h, sea_z, x0, y0, x1, y1, what):
    sl = h[int(y0 / MAIN_STEP):int(y1 / MAIN_STEP) + 1, int(x0 / MAIN_STEP):int(x1 / MAIN_STEP) + 1]
    land = (sl > sea_z + 0.01).mean()
    if land > 0:
        print(f"  warning: {what} overlaps land ({land:.0%} of its box)")


def scale_bar_main(h, sea_z):
    """100 km scale bar, ticks every 10 km, with labels and a north arrow, on the A1 sea."""
    x0, y0 = 12.0, 14.0
    z0 = sea_z - 0.3
    parts = []
    L = 100.0 / MAIN_KM_PER_MM
    # alternating blocks so the 10 km segments can be counted
    for i in range(10):
        hgt = 3.0 if i % 2 == 0 else 1.6
        yy = y0 if i % 2 == 0 else y0 + 0.7
        parts.append(Manifold.cube((L / 10, hgt, EMBOSS + 0.3)).translate((x0 + i * L / 10, yy, z0)))
    parts.append(Manifold.cube((L, 0.8, EMBOSS + 0.3)).translate((x0, y0 + 1.1, z0)))
    for i in (0, 5, 10):
        parts.append(Manifold.cube((0.8, 6.0, EMBOSS + 0.3)).translate((x0 + i * L / 10 - 0.4, y0 - 1.5, z0)))
    for i, t in ((0, "0"), (5, "50"), (10, "100")):
        parts.append(text_cs(t, 5, x0 + i * L / 10, y0 + 6, "center").extrude(EMBOSS + 0.3).translate((0, 0, z0)))
    parts.append(text_cs("km", 5, x0 + L + 3, y0 + 0.2).extrude(EMBOSS + 0.3).translate((0, 0, z0)))
    parts.append(text_cs("1 cm = 10 km   1 in = 25.4 km", 4.5, x0, y0 - 9).extrude(EMBOSS + 0.3).translate((0, 0, z0)))
    # north arrow (UTM grid north)
    ax, ay = 135.0, 18.0
    arrow = poly_cs([(ax - 4, ay), (ax, ay + 14), (ax + 4, ay), (ax, ay + 4)])
    parts.append(arrow.extrude(EMBOSS + 0.3).translate((0, 0, z0)))
    parts.append(text_cs("N", 6, ax, ay + 16, "center").extrude(EMBOSS + 0.3).translate((0, 0, z0)))
    check_sea(h, sea_z, x0 - 1, y0 - 10, x0 + L + 15, y0 + 12, "A1 scale bar")
    check_sea(h, sea_z, ax - 5, ay, ax + 5, ay + 22, "A1 north arrow")
    return parts


def key_shape(clear):
    pts = [(-15, -7), (0, -3.5), (15, -7), (15, 7), (0, 3.5), (-15, 7)]
    cs = poly_cs(pts)
    return cs.offset(-clear, m3.JoinType.Miter) if clear else cs


# ------------------------------------------------------------------ insets
def build_inset(cfg):
    name = cfg["name"]
    print(f"{name} inset: downloading / sampling terrain ...")
    clat, clon = cfg["center"]
    ce, cn = to_utm.transform(clon, clat)
    ce, cn = ce / 1000, cn / 1000
    map_h = TILE - INSET_STRIP
    e0 = ce - TILE / 2 * INSET_KM_PER_MM
    n0 = cn - map_h / 2 * INSET_KM_PER_MM
    nx = int(round(TILE / INSET_STEP)) + 1
    ny = int(round(TILE / INSET_STEP)) + 1
    step = TILE / (nx - 1)
    xs = np.arange(nx) * step
    ys = np.arange(ny) * step
    X, Y = np.meshgrid(xs, ys)
    E = (e0 + X * INSET_KM_PER_MM) * 1000
    N = (n0 + (Y - INSET_STRIP) * INSET_KM_PER_MM) * 1000
    lon, lat = to_geo.transform(E, N)
    dem = DEM(lon.min() - .01, lat.min() - .01, lon.max() + .01, lat.max() + .01, 13, smooth_px=0.4)
    elev = dem(lon, lat)
    inmap = Y >= INSET_STRIP
    datum = math.floor(elev[inmap].min() / 50.0) * 50.0
    h = BASE + 0.6 + (elev - datum) / INSET_M_PER_MM_Z
    h[~inmap] = BASE

    def mm(la, lo):
        e, n = to_utm.transform(lo, la)
        return ((e / 1000 - e0) / INSET_KM_PER_MM, (n / 1000 - n0) / INSET_KM_PER_MM + INSET_STRIP)

    pts = [mm(s[1], s[2]) for s in cfg["sites"]]
    pads = [flatten_pad(h, step, px, py, pad_radius(i, pts, 4.5)) for i, (px, py) in enumerate(pts)]

    adds, cuts = [], []
    for (px, py), z in zip(pts, pads):
        adds.append(peg(px, py, z))

    if cfg["trench"]:
        tp = [mm(la, lo) for la, lo in cfg["trench"]]
        seg = []
        for (ax, ay), (bx, by) in zip(tp[:-1], tp[1:]):
            L = math.hypot(bx - ax, by - ay)
            for t in np.linspace(0, 1, max(2, int(L / 1.5)) + 1):
                seg.append((ax + (bx - ax) * t, ay + (by - ay) * t))
        for (ax, ay), (bx, by) in zip(seg[:-1], seg[1:]):
            za = h[int(round(ay / step)), int(round(ax / step))] - 1.2
            zb = h[int(round(by / step)), int(round(bx / step))] - 1.2
            cuts.append(Manifold.hull(cyl(0.7, za, za + 40, ax, ay, 12) + cyl(0.7, zb, zb + 40, bx, by, 12)))

    cap = None
    if cfg["light_peak"]:
        _, la, lo = cfg["light_peak"]
        px, py = mm(la, lo)
        # find the true summit within 500 m of the given point
        r_px = int(5.0 / step)
        j0, i0 = int(round(py / step)), int(round(px / step))
        win = h[j0 - r_px:j0 + r_px + 1, i0 - r_px:i0 + r_px + 1]
        dj, di = np.unravel_index(np.argmax(win), win.shape)
        sj, si = j0 - r_px + dj, i0 - r_px + di
        sx, sy, sz = si * step, sj * step, float(h[sj, si])
        cut_z = sz - 100.0 / INSET_M_PER_MM_Z     # top 100 m of the mountain
        cap_r = 6.0
        cap_info = (sx, sy, cut_z, cap_r, sz)
        pts.append((sx, sy))

    # label strip: title + 5 km scale bar
    z0 = BASE - 0.3
    adds.append(text_cs(f"{name.upper()}  1 cm = 1 km", 6, 8, 5).extrude(EMBOSS + 0.3).translate((0, 0, z0)))
    bx0, L = 120.0, 5.0 / INSET_KM_PER_MM
    for i in range(5):
        hh = 3.0 if i % 2 == 0 else 1.6
        adds.append(Manifold.cube((L / 5, hh, EMBOSS + 0.3)).translate((bx0 + i * L / 5, 4 + (0 if i % 2 == 0 else 0.7), z0)))
    adds.append(Manifold.cube((L, 0.8, EMBOSS + 0.3)).translate((bx0, 5.1, z0)))
    adds.append(text_cs("0", 4.5, bx0 - 2.5, 3.6, "right").extrude(EMBOSS + 0.3).translate((0, 0, z0)))
    adds.append(text_cs("5 km", 4.5, bx0 + L + 2.5, 3.6).extrude(EMBOSS + 0.3).translate((0, 0, z0)))
    adds.append(text_cs("N^", 5, TILE - 8, TILE - 12, "right").extrude(EMBOSS + 0.3)
                .translate((0, 0, float(h[int((TILE - 10) / step), int((TILE - 12) / step)]) - 0.3)))

    letter = "M" if name == "Mecca" else "D"
    for cs in (text_cs(f"{name.upper()} INSET", 14, TILE / 2, TILE / 2, "center", mirror=True),
               text_cs("1:100,000", 7, TILE / 2, TILE / 2 - 14, "center", mirror=True)):
        cuts.append(cs.extrude(ENGRAVE + 1).translate((0, 0, -1)))

    solid = heightfield_solid(h, step)
    solid = solid + Manifold.batch_boolean(adds, m3.OpType.Add)
    solid = solid - Manifold.batch_boolean(cuts, m3.OpType.Add)
    if cfg["light_peak"]:
        sx, sy, cut_z, cap_r, sz = cap_info
        body = cyl(cap_r, cut_z, sz + 5, sx, sy, 48)
        cap = solid ^ body
        solid = solid - body
        solid = solid + cyl(1.0, cut_z - 0.5, cut_z + 1.0, sx, sy, 16)       # nub
        cap = cap - cyl(1.2, cut_z - 1, cut_z + 1.2, sx, sy, 16)              # socket
        cap = cap.translate((-sx, -sy, -cut_z))
        bb = cap.bounding_box()
        print(f"  Hira cap: {bb[3]-bb[0]:.1f} x {bb[4]-bb[1]:.1f} x {bb[5]-bb[2]:.1f} mm, summit {sz:.1f} mm")
    save_stl(solid, f"inset_{name.lower()}.stl")
    np.save(os.path.join(CACHE, f"inset_{name.lower()}_h.npy"), h)
    print(f"  datum {datum:.0f} m (ground at that height = {BASE+0.6:.1f} mm)")
    return h, step, pts, cap, datum


# ------------------------------------------------------------------ markers
def marker(kind, d):
    """A marker with a flat base and a socket underneath. d = base width (mm)."""
    r = d / 2
    if kind == "kaaba":
        m = Manifold.cube((d * 0.9, d * 0.9, d * 0.9)).translate((-d * 0.45, -d * 0.45, 0)).rotate((0, 0, 45))
    elif kind == "mosque":
        m = cyl(r, 0, r, 0, 0, 48) + Manifold.sphere(r * 0.95, 48).translate((0, 0, r))
        m = m + cyl(0.35, r * 1.9, r * 1.9 + 1.4, 0, 0, 12)
    elif kind == "light":
        m = cyl(r, 0, 2.5, 0, 0, 48) + cyl(r, 2.5, 2.5 + d, 0, 0, 48, r_top=0.3)
    elif kind == "battle":
        m = Manifold.cylinder(2.5, r, r, 8) + Manifold.cylinder(d * 1.2, r, 0.3, 8).translate((0, 0, 2.5))
    else:  # site
        m = Manifold.cylinder(d * 0.75, r, r, 6)
    return m - cyl(SOCKET_R, -1, SOCKET_H, 0, 0, 24)


def build_markers(cap):
    groups = {}
    for s in MAIN_SITES:
        groups.setdefault(s[3], []).append(4.6)
    for cfg in (MECCA_INSET, MEDINA_INSET):
        for s in cfg["sites"]:
            groups.setdefault(s[3], []).append(6.5)
    colour = {"kaaba": "black", "mosque": "green", "light": "white", "battle": "red", "site": "gold"}
    for kind, sizes in groups.items():
        parts = []
        sizes = sorted(sizes) + [sizes[0]]        # one spare of the smallest
        for i, d in enumerate(sizes):
            parts.append(marker(kind, d).translate(((i % 5) * 12, (i // 5) * 12, 0)))
        if kind == "light" and cap is not None:
            parts.append(cap.translate((-20, 0, 0)))
        save_stl(Manifold.batch_boolean(parts, m3.OpType.Add), f"markers_{colour[kind]}_{kind}.stl")


def build_keys():
    n = 2 * MAIN_ROWS * (MAIN_COLS - 1) + 2 * MAIN_COLS * (MAIN_ROWS - 1)
    parts = []
    for i in range(n + 2):
        parts.append(key_shape(KEY_CLEAR).extrude(KEY_THICK).translate(((i % 4) * 34, (i // 4) * 17, 0)))
    save_stl(Manifold.batch_boolean(parts, m3.OpType.Add), "joining_keys.stl")
    return n


# ------------------------------------------------------------------ legend
LEGEND = [
    ("BLACK cube", "Mecca - the Kaaba. Conquest of Mecca 8 AH / 630 CE"),
    ("WHITE peak", "Jabal al-Nour - Cave of Hira, first revelation 610 CE"),
    ("GREEN dome", "Medina - the Prophet's Mosque. Hijra 1 AH / 622 CE"),
    ("RED spire", "Badr 2 AH/624 - Uhud 3 AH/625 - Trench 5 AH/627"),
    ("", "Khaybar 7 AH/628 - Hunayn 8 AH/630 - Ta'if 8 AH/630"),
    ("GOLD hex", "Hudaybiyyah treaty 6 AH/628 - Cave of Thawr 622"),
    ("", "Quba, Qiblatayn, Mina, Muzdalifah, Arafat 10 AH/632"),
]


def build_legend():
    W, Hh, T = 200.0, 150.0, 2.4
    plate = Manifold.cube((W, Hh, T))
    adds = []
    z = T - 0.01

    def put(cs):
        adds.append(cs.extrude(EMBOSS).translate((0, 0, z)))

    put(text_cs("THE HIJAZ IN THE TIME OF THE PROPHET", 7.2, W / 2, Hh - 14, "center"))
    put(text_cs("peace be upon him  -  c. 570 - 632 CE", 4.6, W / 2, Hh - 22, "center", bold=False))
    y = Hh - 34
    for sym, txt in LEGEND:
        if sym:
            put(text_cs(sym, 4.2, 8, y))
        put(text_cs(txt, 4.2, 48, y, bold=False))
        y -= 8.5
    # main scale bar 100 km = 100 mm
    y = 30
    for i in range(10):
        hh = 3.0 if i % 2 == 0 else 1.6
        adds.append(Manifold.cube((10, hh, EMBOSS)).translate((8 + i * 10, y + (0 if i % 2 == 0 else 0.7), z)))
    adds.append(Manifold.cube((100, 0.8, EMBOSS)).translate((8, y + 1.1, z)))
    put(text_cs("MAIN MAP 0-100 km  (1 cm = 10 km)", 4.2, 8, y + 5))
    put(text_cs("height x10: 1 mm = 100 m", 4.0, 112, y, bold=False))
    y = 12
    for i in range(5):
        hh = 3.0 if i % 2 == 0 else 1.6
        adds.append(Manifold.cube((10, hh, EMBOSS)).translate((8 + i * 10, y + (0 if i % 2 == 0 else 0.7), z)))
    adds.append(Manifold.cube((50, 0.8, EMBOSS)).translate((8, y + 1.1, z)))
    put(text_cs("INSETS 0-5 km  (1 cm = 1 km)", 4.2, 8, y + 5))
    put(text_cs("height x2.5: 1 mm = 40 m", 4.0, 112, y, bold=False))
    save_stl(plate + Manifold.batch_boolean(adds, m3.OpType.Add), "legend_plaque.stl")


# ------------------------------------------------------------------ previews
def previews(main_h, main_pts, insets):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib.colors import LightSource
    os.makedirs(OUT_PNG, exist_ok=True)
    col = {"kaaba": "black", "mosque": "#1f8a3b", "light": "white", "battle": "#c62828", "site": "#d4a017"}

    def draw(ax, h, step, pts, sites, title):
        ls = LightSource(azdeg=315, altdeg=40)
        rgb = ls.shade(h, cmap=plt.get_cmap("copper"), vert_exag=3 / step, blend_mode="soft")
        ext = (0, (h.shape[1] - 1) * step, 0, (h.shape[0] - 1) * step)
        sea = h < BASE - SEA_DROP + 0.01
        rgb[sea, :3] = (0.35, 0.55, 0.75)
        ax.imshow(rgb, origin="lower", extent=ext)
        for (px, py), s in zip(pts, sites):
            ax.plot(px, py, "o", ms=7, mfc=col[s[3]], mec="k" if s[3] != "kaaba" else "w")
            off = {"Mecca (Kaaba)": (8, -12), "Jabal al-Nour (Hira)": (-118, 12), "Hudaybiyyah": (-62, -12),
                   "Hunayn": (6, 8)}.get(s[0], (6, 4))
            ax.annotate(s[0], (px, py), xytext=off, textcoords="offset points", fontsize=8,
                        color="k", bbox=dict(fc="w", alpha=.7, lw=0, pad=1))
        ax.set_title(title)
        ax.set_xlabel("mm")

    fig, ax = plt.subplots(figsize=(8, 11))
    draw(ax, main_h, MAIN_STEP, main_pts, MAIN_SITES, "Main map, 400 x 600 mm, 1 cm = 10 km")
    for c in range(1, MAIN_COLS):
        ax.axvline(c * TILE, color="k", lw=.8, ls="--")
    for r in range(1, MAIN_ROWS):
        ax.axhline(r * TILE, color="k", lw=.8, ls="--")
    for r in range(MAIN_ROWS):
        for c in range(MAIN_COLS):
            ax.text(c * TILE + 8, r * TILE + TILE - 14, f"{'AB'[c]}{r + 1}", fontsize=14, weight="bold", color="w")
    fig.tight_layout()
    fig.savefig(os.path.join(OUT_PNG, "main_map.png"), dpi=110)
    plt.close(fig)
    for cfg, (h, step, pts, _cap, _d) in insets:
        sites = list(cfg["sites"])
        if cfg["light_peak"]:
            sites.append((cfg["light_peak"][0], 0, 0, "light", "", False))
        fig, ax = plt.subplots(figsize=(8, 8))
        draw(ax, h, step, pts, sites, f"{cfg['name']} inset, 200 x 200 mm, 1 cm = 1 km")
        fig.tight_layout()
        fig.savefig(os.path.join(OUT_PNG, f"inset_{cfg['name'].lower()}.png"), dpi=110)
        plt.close(fig)


if __name__ == "__main__":
    os.makedirs(CACHE, exist_ok=True)
    main_h, main_pts = build_main()
    insets = []
    cap = None
    for cfg in (MECCA_INSET, MEDINA_INSET):
        res = build_inset(cfg)
        insets.append((cfg, res))
        if res[3] is not None:
            cap = res[3]
    build_markers(cap)
    n = build_keys()
    print(f"  {n} keys needed (+2 spares printed)")
    build_legend()
    previews(main_h, main_pts, insets)
    print("done")
