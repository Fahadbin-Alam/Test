"""Fan-made Omnitrix-style wrist prop (classic style), built from scratch.

Run:  pip install manifold3d trimesh numpy
      python3 omnitrix/generator/build.py

All sizes are in millimetres. Change the WRIST settings below and re-run to
resize the cuff; every other part stays the same.
"""
import math
import os

import numpy as np
import trimesh
from manifold3d import CrossSection, JoinType, Manifold

OUT = os.path.join(os.path.dirname(__file__), "..", "stl")
SEG = 128

# ---------------- WRIST / CUFF SETTINGS ----------------
WRIST_INNER_W = 62.0   # inside width of the cuff, side to side (mm)
WRIST_INNER_H = 50.0   # inside height of the cuff, top to palm side (mm)
CUFF_WALL = 4.0        # band thickness
CUFF_WIDTH = 40.0      # band width along the arm
CUFF_GAP = 40.0        # opening on the palm side, to slide the wrist in
TEST_RING_WIDTH = 10.0

# ---------------- DIAL SETTINGS ----------------
CLEAR = 0.4            # sliding clearance between moving parts
CLICKS = 8             # detent positions per turn


def ring(r_out, r_in, h, seg=SEG):
    return Manifold.cylinder(h, r_out, r_out, seg) - Manifold.cylinder(h, r_in, r_in, seg).translate([0, 0, 0])


def sector(r_in, r_out, a0, a1, h, n=48):
    """Annular sector (angles in degrees) extruded to height h."""
    a = np.radians(np.linspace(a0, a1, n))
    outer = [(r_out * math.cos(t), r_out * math.sin(t)) for t in a]
    inner = [(r_in * math.cos(t), r_in * math.sin(t)) for t in a[::-1]]
    return CrossSection([outer + inner]).extrude(h)


def oval(a, b, n=SEG):
    t = np.linspace(0, 2 * math.pi, n, endpoint=False)
    return [(a * math.cos(x), b * math.sin(x)) for x in t]


def hourglass(scale=1.0):
    pts = [(-10, 11), (10, 11), (1.8, 0), (10, -11), (-10, -11), (-1.8, 0)]
    return [(x * scale, y * scale) for x, y in pts[::-1]]  # counter-clockwise


# ---------------- PARTS ----------------
# Z = 0 is the bottom of the watch body. Stack, bottom to top:
#   housing base 0-3, housing wall 3-14.3, dial flange 12-14, bezel 14.3-16.8,
#   dial top 22.
HOUSING_R = 30.0
WALL_IN = 26.6
FLANGE_R = WALL_IN - CLEAR          # 26.2
FLANGE_Z = 12.0
FLANGE_T = 2.0
WALL_TOP = FLANGE_Z + FLANGE_T + 0.3
DIAL_R = 22.0
BEZEL_IN = DIAL_R + CLEAR
DIAL_TOP = 22.0
TUBE_IN = 16.0
FACE_R = 19.0
FACE_T = 2.5
PIN_D = 3.0
PIN_X = 12.0


def housing():
    base = Manifold.cylinder(3, HOUSING_R, HOUSING_R, SEG)
    wall = ring(HOUSING_R, WALL_IN, WALL_TOP - 3).translate([0, 0, 3])
    support = ring(19.0, 17.0, FLANGE_Z - 3).translate([0, 0, 3])   # dial rests on this
    body = base + wall + support
    # click grooves on the inside of the wall
    for k in range(CLICKS):
        t = 2 * math.pi * k / CLICKS
        body -= Manifold.cylinder(WALL_TOP, 0.9, 0.9, 24).translate(
            [WALL_IN * math.cos(t), WALL_IN * math.sin(t), 3])
    # side slot for an on/off switch (fits a small 8x4 mm slide switch)
    body -= Manifold.cube([8, 8, 4], center=True).translate([HOUSING_R - 2, 0, 7])
    # pin holes in the base to locate the body on the cuff
    for x in (-PIN_X, PIN_X):
        body -= Manifold.cylinder(2.6, PIN_D / 2 + 0.15, PIN_D / 2 + 0.15, 32).translate([x, 0, -0.01])
    # decorative side blocks (the "clamps" that hold the body to the band)
    for s in (-1, 1):
        blk = Manifold.cube([12, 10, 8], center=True).translate([0, s * (HOUSING_R + 1), 4])
        groove = Manifold.cube([14, 1.2, 1.2], center=True).translate([0, s * (HOUSING_R + 2.5), 8])
        body += blk - groove
    return body


def dial():
    flange = ring(FLANGE_R, 12.0, FLANGE_T)
    # two flexing click tongues cut into the flange edge
    for base_a in (0, 180):
        flange -= sector(23.6, 24.4, base_a, base_a + 35, FLANGE_T + 1).translate([0, 0, -0.5])
        cut = Manifold.cube([3.5, 0.8, FLANGE_T + 1]).translate([23.4, -0.4, -0.5]).rotate([0, 0, base_a + 35])
        flange -= cut
        t = math.radians(base_a + 32)
        flange += Manifold.cylinder(FLANGE_T, 0.9, 0.9, 24).translate(
            [FLANGE_R * math.cos(t), FLANGE_R * math.sin(t), 0])
    top = DIAL_TOP - FLANGE_Z                 # dial height in its own coordinates
    tube = ring(DIAL_R, TUBE_IN, top - FLANGE_T).translate([0, 0, FLANGE_T])
    # recess for the face plate
    tube -= Manifold.cylinder(FACE_T + 0.01, FACE_R + 0.2, FACE_R + 0.2, SEG).translate([0, 0, top - FACE_T])
    body = flange + tube
    # grip grooves around the dial
    for k in range(24):
        t = 2 * math.pi * k / 24
        body -= Manifold.cube([1.6, 1.6, 7], center=True).rotate([0, 0, math.degrees(t) + 45]).translate(
            [DIAL_R * math.cos(t), DIAL_R * math.sin(t), top - 3.0])
    return body


def face():
    plate = Manifold.cylinder(FACE_T, FACE_R, FACE_R, SEG)
    win = CrossSection([hourglass()]).offset(0.15, JoinType.Miter).extrude(FACE_T + 2).translate([0, 0, -1])
    plate -= win
    # shallow ring line for detail
    plate -= ring(FACE_R - 1.5, FACE_R - 2.3, 0.6).translate([0, 0, FACE_T - 0.6])
    return plate


def hourglass_insert():
    lip = CrossSection([hourglass()]).offset(0.6, JoinType.Miter).extrude(0.8)
    core = CrossSection([hourglass()]).extrude(0.8 + FACE_T + 1.0)
    return lip + core


def bezel():
    b = ring(HOUSING_R, BEZEL_IN, 2.5)
    for k in range(4):   # four notches for style
        t = 45 + 90 * k
        b -= Manifold.cube([4, 3, 1.2], center=True).translate([HOUSING_R, 0, 2.5]).rotate([0, 0, t])
    return b


def cuff(width):
    a_in, b_in = WRIST_INNER_W / 2, WRIST_INNER_H / 2
    outer = CrossSection([oval(a_in + CUFF_WALL, b_in + CUFF_WALL)])
    inner = CrossSection([oval(a_in, b_in)])
    band = (outer - inner).extrude(width)
    # flat pad on top where the watch body sits
    top = b_in + CUFF_WALL
    pad = Manifold.cube([40, 5, width]).translate([-20, top - 2, 0])
    pad -= inner.extrude(width)
    band += pad
    # opening on the palm side
    band -= Manifold.cube([CUFF_GAP, 30, width + 2]).translate([-CUFF_GAP / 2, -b_in - 20, -1])
    # round the ends of the opening
    for s in (-1, 1):
        x = s * CUFF_GAP / 2
        y = -(b_in + CUFF_WALL / 2) * math.sqrt(max(0, 1 - (x / (a_in + CUFF_WALL / 2)) ** 2))
        band += Manifold.cylinder(width, CUFF_WALL / 2, CUFF_WALL / 2, 32).translate([x, y, 0])
    if width >= 20:
        # panel lines and pin holes
        for z in (6, width - 6):
            groove = (CrossSection([oval(a_in + CUFF_WALL + 1, b_in + CUFF_WALL + 1)])
                      - CrossSection([oval(a_in + CUFF_WALL - 0.6, b_in + CUFF_WALL - 0.6)])).extrude(1.0)
            band -= groove.translate([0, 0, z - 0.5])
        for x in (-PIN_X, PIN_X):
            hole = Manifold.cylinder(4, PIN_D / 2 + 0.15, PIN_D / 2 + 0.15, 32).rotate([-90, 0, 0])
            band -= hole.translate([x, top + 3 - 4 + 0.01, width / 2])
    return band


def pin():
    return Manifold.cylinder(6.0, PIN_D / 2 - 0.05, PIN_D / 2 - 0.05, 32)


def save(m, name):
    mesh = m.to_mesh()
    tm = trimesh.Trimesh(vertices=np.asarray(mesh.vert_properties)[:, :3], faces=np.asarray(mesh.tri_verts))
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, name + ".stl")
    tm.export(path)
    bb = tm.bounds
    print(f"{name:20s} {bb[1][0]-bb[0][0]:6.1f} x {bb[1][1]-bb[0][1]:6.1f} x {bb[1][2]-bb[0][2]:6.1f} mm  "
          f"watertight={tm.is_watertight}  vol={tm.volume/1000:.1f} cm3")
    return tm


PARTS = {
    "1_cuff": lambda: cuff(CUFF_WIDTH),
    "0_test_fit_ring": lambda: cuff(TEST_RING_WIDTH),
    "2_housing": housing,
    "3_dial": dial,
    "4_face": face,
    "5_hourglass_insert": hourglass_insert,
    "6_bezel": bezel,
    "7_pin_x2": pin,
}


def assembly():
    """Everything placed as worn, for the preview."""
    top = WRIST_INNER_H / 2 + CUFF_WALL + 3
    # the watch stack is built along +Z; lay it on the cuff top (+Y)
    lift = lambda m: m.rotate([-90, 0, 0]).translate([0, top, CUFF_WIDTH / 2])
    return {
        "cuff": cuff(CUFF_WIDTH),
        "housing": lift(housing()),
        "dial": lift(dial().translate([0, 0, FLANGE_Z])),
        "face": lift(face().translate([0, 0, DIAL_TOP - FACE_T])),
        "insert": lift(hourglass_insert().translate([0, 0, DIAL_TOP - FACE_T - 0.8])),
        "bezel": lift(bezel().translate([0, 0, WALL_TOP])),
    }


if __name__ == "__main__":
    for name, fn in PARTS.items():
        save(fn(), name)
