#!/usr/bin/env python3
"""Architectural model of Masjid al-Haram and the Makkah Clock Tower.

    python haram.py      # writes ../stl/haram_model.stl and ../ams/haram_model.3mf

Every building is extruded from real footprints and heights (Overture Maps /
OpenStreetMap, saved in data/ by fetch_haram_data.py) at TRUE scale, so the
Clock Tower stands 601 m / 4000 = 150 mm tall. Streets are engraved into the
ground and the ground follows the real terrain.
"""
import json
import math
import os
import sys

import numpy as np
from shapely.geometry import shape, box, Polygon, MultiPolygon, LineString
import warnings
from shapely.ops import unary_union, transform as shp_transform
warnings.filterwarnings('ignore', category=DeprecationWarning)
from shapely.validation import make_valid

sys.path.insert(0, os.path.dirname(__file__))
import build  # noqa: E402
from build import Manifold, CrossSection, FillRule, m3, text_cs, cyl  # noqa: E402

DATA = os.path.join(os.path.dirname(__file__), "data")
SCALE = 4000.0                  # 1:4,000  ->  1 cm = 40 m
MM = 1000.0 / SCALE             # mm per metre (same vertically: no exaggeration)
W, STRIP = 240.0, 12.0          # tile width; flat label strip along the south edge
H = W                           # tile depth (model area is W x (H - STRIP))
CENTER = (21.4214, 39.8260)     # lat, lon of the model area's centre
BASE = 3.0                      # mm under the lowest ground
MIN_W = 0.8                     # mm, thinnest wall the printer can do (2 lines)
ROAD_DEPTH = 0.4
ROAD_W = {"motorway": 22, "trunk": 18, "primary": 15, "secondary": 12, "tertiary": 10,
          "residential": 7, "unclassified": 7, "service": 5, "living_street": 6, "pedestrian": 8, "unknown": 6}
STEP = 0.75                     # mm, terrain grid

ce, cn = build.to_utm.transform(CENTER[1], CENTER[0])
E0 = ce - W / 2 / MM
N0 = cn - (H - STRIP) / 2 / MM - STRIP / MM


def to_mm(x, y, z=None):
    e, n = build.to_utm.transform(x, y)
    return (np.asarray(e) - E0) * MM, (np.asarray(n) - N0) * MM


def polys(g):
    g = make_valid(g)
    if isinstance(g, Polygon):
        return [g] if not g.is_empty else []
    if hasattr(g, "geoms"):
        out = []
        for x in g.geoms:
            out += polys(x)
        return out
    return []


def cs_of(p):
    rings = [np.asarray(p.exterior.coords)[:-1]] + [np.asarray(r.coords)[:-1] for r in p.interiors]
    rings = [r for r in rings if len(r) >= 3]
    return CrossSection(rings, FillRule.EvenOdd)


def thicken(p):
    """Make sure no part is thinner than the nozzle can print."""
    r = p.minimum_rotated_rectangle
    xs, ys = r.exterior.coords.xy
    sides = [math.hypot(xs[i + 1] - xs[i], ys[i + 1] - ys[i]) for i in range(2)]
    if min(sides) < MIN_W:
        p = p.buffer((MIN_W - min(sides)) / 2 + 0.02, quad_segs=4)
    return p


def main():
    print("Haram model: terrain ...")
    nx = int(round(W / STEP)) + 1
    ny = int(round(H / STEP)) + 1
    xs, ys = np.arange(nx) * STEP, np.arange(ny) * STEP
    X, Y = np.meshgrid(xs, ys)
    lon, lat = build.to_geo.transform(E0 + X / MM, N0 + Y / MM)
    dem = build.DEM(lon.min() - .003, lat.min() - .003, lon.max() + .003, lat.max() + .003, 15, smooth_px=3.0)
    elev = dem(lon, lat)
    inmap = Y >= STRIP
    datum = float(elev[inmap].min())
    h = BASE + (elev - datum) * MM
    h[~inmap] = BASE
    print(f"  ground {datum:.0f}-{elev[inmap].max():.0f} m, relief {(elev[inmap].max() - datum) * MM:.1f} mm")

    def ground(px, py):
        i = np.clip(np.round(np.asarray(px) / STEP).astype(int), 0, nx - 1)
        j = np.clip(np.round(np.asarray(py) / STEP).astype(int), 0, ny - 1)
        return h[j, i]

    area = box(0, STRIP, W, H)

    # --------------------------------------------------------------- buildings
    fc = json.load(open(os.path.join(DATA, "haram_buildings.geojson")))["features"]
    proj = lambda g: shp_transform(lambda x, y, z=None: to_mm(x, y), g)
    feats = []
    for f in fc:
        g = proj(shape(f["geometry"]))
        if not g.intersects(area):
            continue
        feats.append((f["properties"], g))
    parts = [(p, g) for p, g in feats if p["part"]]
    parents = [(p, g) for p, g in feats if not p["part"] and p.get("has_parts")]
    kaaba = next(g for p, g in feats if p["name"] == "الكعبة" and not p["part"])
    haram = next(g for p, g in feats if p["name"] == "المسجد الحرام" and not p["part"])
    skip = set()
    for i, (p, g) in enumerate(feats):
        if not p["part"] and p.get("has_parts"):
            if any(g.buffer(0.5).contains(pg.representative_point()) for _, pg in parts):
                skip.add(i)

    def parent_of(g):
        pt = g.representative_point()
        for p, pg in parents:
            if pg.buffer(0.5).contains(pt):
                return pg
        return None

    solids = {"white": [], "black": [], "gold": []}
    n = 0
    for i, (p, g) in enumerate(feats):
        if i in skip:
            continue
        hgt = p["height"] or ((p["floors"] or 0) * 3.5) or 12.0
        mh = p["min_height"] or 0.0
        ref = parent_of(g) if p["part"] else g
        ref = ref if ref is not None else g
        rx, ry = ref.exterior.xy if isinstance(ref, Polygon) else ref.convex_hull.exterior.xy
        gz = float(np.min(ground(np.r_[rx, ref.centroid.x], np.r_[ry, ref.centroid.y])))
        z0 = gz + mh * MM if mh > 0 else 0.5
        z1 = gz + hgt * MM
        if z1 - z0 < 0.15:
            continue
        pt = g.representative_point()
        if kaaba.buffer(0.3).contains(pt):
            colour = "black"
        elif mh >= 572 or (p["part"] and mh >= 114 and haram.buffer(1).contains(pt)):
            colour = "gold"        # crescent of the Clock Tower and the minaret finials
        else:
            colour = "white"
        for q in polys(g.intersection(area)):
            q = thicken(q).intersection(area)
            for q2 in polys(q):
                if q2.area < 0.05:
                    continue
                solids[colour].append(cs_of(q2).extrude(z1 - z0).translate((0, 0, z0)))
                n += 1
    print(f"  {n} building solids")

    # ----------------------------------------------------------------- ground
    terrain = build.heightfield_solid(h, STEP)
    rc = json.load(open(os.path.join(DATA, "haram_roads.geojson")))["features"]
    lines = []
    for f in rc:
        p = f["properties"]
        if p["class"] not in ROAD_W or set(p["flags"]) & {"is_tunnel", "is_bridge"}:
            continue
        g = proj(shape(f["geometry"]))
        lines.append(g.buffer(ROAD_W[p["class"]] * MM / 2, cap_style=2, quad_segs=2))
    roads = unary_union(lines).intersection(area.buffer(-0.01))
    cuts = [cs_of(q).extrude(100).translate((0, 0, 0.5)) for q in polys(roads) if q.area > 0.05]
    if cuts:
        terrain = terrain - (Manifold.batch_boolean(cuts, m3.OpType.Add) - terrain.translate((0, 0, -ROAD_DEPTH)))

    # label strip: title + 100 m scale bar, and bottom engraving
    z0 = BASE - 0.3
    adds = [text_cs("MASJID AL-HARAM  &  MAKKAH CLOCK TOWER", 4.6, 6, 4.2).extrude(build.EMBOSS + 0.3).translate((0, 0, z0))]
    bx, L = 160.0, 100 * MM * 2            # 200 m bar
    for k in range(4):
        hh = 2.6 if k % 2 == 0 else 1.4
        adds.append(Manifold.cube((L / 4, hh, build.EMBOSS + 0.3)).translate((bx + k * L / 4, 4 + (0 if k % 2 == 0 else 0.6), z0)))
    adds.append(text_cs("0", 3.8, bx - 1.5, 3.8, "right").extrude(build.EMBOSS + 0.3).translate((0, 0, z0)))
    adds.append(text_cs("200 m", 3.8, bx + L + 1.5, 3.8).extrude(build.EMBOSS + 0.3).translate((0, 0, z0)))
    terrain = terrain + Manifold.batch_boolean(adds, m3.OpType.Add)
    eng = [text_cs("MASJID AL-HARAM", 14, W / 2, H / 2 + 6, "center", mirror=True),
           text_cs("1:4,000  -  1 cm = 40 m  -  true height", 6, W / 2, H / 2 - 8, "center", mirror=True),
           text_cs("N^ top edge", 6, W / 2, H / 2 - 20, "center", mirror=True)]
    terrain = terrain - Manifold.batch_boolean([c.extrude(build.ENGRAVE + 1).translate((0, 0, -1)) for c in eng], m3.OpType.Add)

    # ---------------------------------------------------------------- combine
    white = Manifold.batch_boolean(solids["white"], m3.OpType.Add)
    black = Manifold.batch_boolean(solids["black"], m3.OpType.Add) - white
    gold = Manifold.batch_boolean(solids["gold"], m3.OpType.Add) - white - black
    # white marble floor of the mataf (the open courtyard around the Kaaba)
    court = [Polygon(r) for g in polys(haram) for r in g.interiors if Polygon(r).contains(kaaba.centroid)]
    if court:
        prism = cs_of(court[0].buffer(0.4)).extrude(100).translate((0, 0, 0.5))
        floor = (terrain ^ prism) - terrain.translate((0, 0, -0.6))
        white = white + floor - black
        print(f"  mataf floor {court[0].area:.0f} mm2")
    bld = white + black + gold
    grey = terrain - bld
    full = grey + bld
    build.save_stl(full, "haram_model.stl")
    parts = [("grey", grey), ("white", white), ("black", black), ("gold", gold)]
    os.makedirs(os.path.join(build.OUT_AMS, "stl", "haram_model"), exist_ok=True)
    keep = build.OUT_STL
    build.OUT_STL = os.path.join(build.OUT_AMS, "stl", "haram_model")
    for f in os.listdir(build.OUT_STL):
        os.remove(os.path.join(build.OUT_STL, f))
    for i, (c, m) in enumerate(parts, 1):
        build.save_stl(m, f"haram_model_{i}_{c}.stl")
    build.OUT_STL = keep
    build.COLOUR_HEX.setdefault("grey", "#BDBDBD")
    build.write_3mf(os.path.join(build.OUT_AMS, "haram_model.3mf"), "haram_model", parts)
    np.save(os.path.join(build.CACHE, "haram_h.npy"), h)
    k = kaaba.centroid
    print(f"  Kaaba at {k.x:.1f}, {k.y:.1f} mm; datum {datum:.0f} m")


if __name__ == "__main__":
    main()
