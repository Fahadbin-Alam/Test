#!/usr/bin/env python3
"""Lantern power ring generator (fan prop, own design).

Builds a chunky signet ring with a lantern emblem on the face, split into
three parts so a Bambu Lab P1S + AMS can print it in three colours:

  body   - band + head            (silver / grey)
  frame  - raised emblem outline  (gold)
  inlay  - bar inlays + domed gem (translucent or glow-in-the-dark green)

Everything is in millimetres. The finger hole runs along X and the face
points up (+Z), which is how it should sit on the build plate.

Usage:
  python3 build.py                 # US size 10 (default)
  python3 build.py --us-size 10.5  # any US size
  python3 build.py --clearance 0.2 # extra room in the hole
"""
import argparse
import os

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold, OpType

SEG = 160  # circle smoothness


def us_size_to_diameter(size):
    """Inner diameter in mm for a US/Canada ring size."""
    return 11.63 + 0.8128 * size


def box(x0, x1, y0, y1, z0, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def x_cylinder(radius, length):
    """Cylinder centred on the origin, axis along X."""
    return (Manifold.cylinder(length, radius, radius, SEG, True)
            .rotate([0, 90, 0]))


def rounded_rect(w, h, r):
    return (CrossSection.square([w - 2 * r, h - 2 * r], True)
            .offset(r, JoinType.Round, circular_segments=48))


def side_cracks(taper, bottom_w, head_w, r_out, zf, depth=0.45, seed=7):
    """Shallow cracked-stone grooves on both side walls of the band."""
    rng = np.random.default_rng(seed)
    segs = []

    def walk(y, z, ang, length, width, gen):
        for _ in range(int(length)):
            ang += rng.normal(0, 0.45)
            ny, nz = y + 1.1 * np.cos(ang), z + 1.1 * np.sin(ang)
            segs.append(CrossSection.batch_hull([
                CrossSection.circle(width / 2, 12).translate([-z, y]),
                CrossSection.circle(width / 2, 12).translate([-nz, ny])]))
            y, z = ny, nz
            if gen < 2 and rng.random() < 0.18:
                walk(y, z, ang + rng.choice([-1, 1]) * rng.uniform(0.6, 1.2),
                     length * 0.45, width * 0.75, gen + 1)

    r_in = r_out - 2.8
    n = 0
    while n < 22:  # start points on the side wall, not in the finger hole
        y0, z0 = rng.uniform(-13, 13), rng.uniform(-r_out, zf - 1.5)
        if np.hypot(y0, z0) < r_in + 0.6 or (z0 < 0 and np.hypot(y0, z0) > r_out):
            continue
        walk(y0, z0, rng.uniform(0, 2 * np.pi), rng.uniform(6, 14), 0.5, 0)
        n += 1
    pattern = CrossSection.batch_boolean(segs, OpType.Add)
    # 2D coords are (-Z, Y) so the rotation lands them on the YZ plane
    grooves = pattern.extrude(60).translate([0, 0, -30]).rotate([0, 90, 0])
    inner = Manifold.batch_hull([
        box(-bottom_w / 2 + depth, bottom_w / 2 - depth, -40, 40, -r_out - 1, -r_out - 0.99),
        box(-head_w / 2 + depth, head_w / 2 - depth, -40, 40, zf - 7.0, zf + 5),
    ])
    return grooves ^ (taper - inner)


def build(us_size, clearance):
    d = us_size_to_diameter(us_size) + clearance
    r_in = d / 2
    band = 2.8                  # band wall thickness under the finger
    r_out = r_in + band
    head_w, head_d = 20.0, 21.0  # face size: X (along finger) x Y
    zf = r_in + 5.0             # top of the grey face
    bottom_w = 6.5              # band width under the finger
    flat = 0.4                  # flat spot on the bottom for bed contact

    # --- body: hull of round band and rounded head block, then taper ---
    head = (rounded_rect(head_w, head_d, 1.5).extrude(6.0)
            .translate([0, 0, zf - 6.0]))
    shell = Manifold.batch_hull([x_cylinder(r_out, head_w), head])
    taper = Manifold.batch_hull([
        box(-bottom_w / 2, bottom_w / 2, -40, 40, -r_out - 1, -r_out - 0.99),
        box(-head_w / 2, head_w / 2, -40, 40, zf - 7.0, zf + 5),
    ])
    body = shell ^ taper
    body = body - side_cracks(taper, bottom_w, head_w, r_out, zf)
    body = body - x_cylinder(r_in, 60)
    body = body - box(-30, 30, -30, 30, -r_out - 5, -r_out + flat)

    # --- emblem (2D, face coordinates u = X, v = Y) ---
    line = 0.9
    bar_x = 9.0
    bar_v0, bar_v1 = 6.4, 9.8
    bar_out = rounded_rect(2 * bar_x, bar_v1 - bar_v0, 0.6)
    bar_in = bar_out.offset(-line, JoinType.Round, circular_segments=24)
    bar_c = (bar_v0 + bar_v1) / 2
    bars_out = bar_out.translate([0, bar_c]) + bar_out.translate([0, -bar_c])
    bars_in = bar_in.translate([0, bar_c]) + bar_in.translate([0, -bar_c])

    gem_r = 5.6
    ring_frame = (CrossSection.circle(gem_r + line, SEG)
                  - CrossSection.circle(gem_r, SEG))
    arc_r0, arc_r1 = gem_r + line + 0.8, gem_r + line + 0.8 + 1.1
    arcs = (CrossSection.circle(arc_r1, SEG) - CrossSection.circle(arc_r0, SEG))
    arcs = arcs ^ CrossSection.square([2 * arc_r1 + 2, 2 * (bar_v0 - 0.0)], True)
    arcs = arcs - CrossSection.square([3.0, 40], True)   # open top/bottom
    # border around the whole face
    border = (rounded_rect(head_w - 0.6, head_d - 0.6, 1.2)
              - rounded_rect(head_w - 0.6 - 2 * 0.8, head_d - 0.6 - 2 * 0.8, 0.5))

    frame_2d = (bars_out - bars_in) + ring_frame + arcs + border

    # --- frame: raised gold lines, keyed 0.6 mm into the body ---
    frame = frame_2d.extrude(2.0).translate([0, 0, zf - 0.6])

    # --- inlays: flat bars + domed centre gem ---
    bar_inlay = bars_in.extrude(2.2).translate([0, 0, zf - 1.2])
    sag = 1.1
    dome_top = zf + 2.0
    rs = (gem_r ** 2 + sag ** 2) / (2 * sag)
    gem = (CrossSection.circle(gem_r, SEG).extrude(4.0)
           .translate([0, 0, zf - 1.2]))
    gem = gem ^ Manifold.sphere(rs, SEG * 2).translate([0, 0, dome_top - rs])
    inlay = bar_inlay + gem

    body = body - frame - inlay
    return {"body": body, "frame": frame, "inlay": inlay}, d


def to_trimesh(m):
    mesh = m.to_mesh()
    return trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3],
                           faces=np.asarray(mesh.tri_verts), process=False)


def sizer(us_size, clearance):
    """Thin plain test band (3 mm tall) to check fit before the real print."""
    r = (us_size_to_diameter(us_size) + clearance) / 2
    return x_cylinder(r + 1.6, 3.0) - x_cylinder(r, 10)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--us-size", type=float, default=10.0)
    ap.add_argument("--clearance", type=float, default=0.15,
                    help="mm added to the inner diameter (FDM holes print small)")
    ap.add_argument("--out", default=os.path.join(os.path.dirname(__file__), "..", "stl"))
    a = ap.parse_args()

    tag = f"us{a.us_size:g}".replace(".", "_")
    out = os.path.abspath(os.path.join(a.out, tag))
    os.makedirs(out, exist_ok=True)

    parts, d = build(a.us_size, a.clearance)
    meshes = {}
    for name, m in parts.items():
        tm = to_trimesh(m)
        assert m.status().name == "NoError" and tm.is_watertight, name
        tm.export(os.path.join(out, f"ring_{tag}_{name}.stl"))
        meshes[name] = tm
        print(f"{name:6s} {tm.volume / 1000:6.2f} cm3  bounds {np.round(tm.bounds, 2).tolist()}")
    single = to_trimesh(parts["body"] + parts["frame"] + parts["inlay"])
    single.export(os.path.join(out, f"ring_{tag}_single_colour.stl"))

    sz = os.path.abspath(os.path.join(a.out, "size-test"))
    os.makedirs(sz, exist_ok=True)
    for s in (a.us_size - 0.5, a.us_size, a.us_size + 0.5):
        to_trimesh(sizer(s, a.clearance)).export(
            os.path.join(sz, f"size_test_us{s:g}".replace(".", "_") + ".stl"))
    print(f"US {a.us_size:g}: inner diameter {d:.2f} mm -> {out}")
    return meshes


if __name__ == "__main__":
    main()
