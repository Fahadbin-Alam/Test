#!/usr/bin/env python3
"""Nightstand valet tray with an upright, wired phone dock.

One print, no supports. Open top. Layout seen from above (front is the
bottom of the picture):

    +-----------------+-------------+-----------+
    |  PHONE DOCK     |  EARBUDS    |  WATCH    |   back row
    |  (raised, with  |             |           |
    |   vented rest)  |             |           |
    +-----------------+---+---------+-----------+
    |  WALLET             |  KEYS                 |   front row
    +---------------------+-----------------------+

The phone stands in a slot, leaning back 12 degrees on a vented backrest.
A USB-C cable is pushed into a slit from the back of the dock, and its plug
sits in a pocket under the slot floor, so the phone drops onto the plug.

Run:  python3 build.py        (needs: pip install manifold3d numpy)
Edit the numbers in the PARAMETERS block to fit your phone, case and cable.
All sizes are in millimetres.
"""
import math
import os

import numpy as np
from manifold3d import CrossSection, JoinType, Manifold, OpType

# ----------------------------------------------------------------- PARAMETERS
# Phone. Defaults are for an OPPO Find N-series foldable, folded, in a slim
# case. Measure yours with the case on and change these three numbers.
PHONE_W = 76.0      # width of the phone + case (left to right)
PHONE_T = 12.0      # thickness of the folded phone + case
PHONE_FIT = 2.0     # extra room around the phone in the slot

# USB-C cable plug (the plastic part around the metal tip).
PLUG_W = 13.0       # plug body width
PLUG_T = 8.0        # plug body thickness
PLUG_LEN = 20.0     # plug body length, not counting the ~6.5 mm metal tip
CABLE_D = 4.5       # cable diameter (the slit is cut slightly wider)

# Tray.
TRAY_W, TRAY_D = 240.0, 190.0   # footprint (fits a 256 x 256 mm bed)
TRAY_H = 32.0                   # height of the tray walls
FLOOR = 3.0                     # floor thickness
WALL = 4.0                      # outer wall and divider thickness
CORNER_R = 10.0                 # outer corner radius
POCKET_R = 7.0                  # pocket corner radius
SCOOP = 4.0                     # chamfer at the bottom of each pocket

# Dock.
DOCK_W = 100.0       # width of the raised dock block (left side, back row)
DOCK_H = 48.0        # height of the dock block
SLOT_DEPTH = 14.0    # how deep the phone sits in its slot
LEAN = 12.0          # backward lean of the phone, degrees
REST_H = 105.0       # height of the backrest above the slot floor
REST_T = 5.0         # backrest thickness
SLOT_BACK_Y = 152.0  # y position of the slot's back face at the slot floor

# Front row / back row split.
FRONT_D = 95.0       # depth of the wallet and keys pockets
WALLET_W = 130.0     # wallet pocket width (keys get the rest)
EARBUDS_W = 66.0     # earbuds pocket width (watch gets the rest)

# Rubber feet: shallow recesses on the underside for 10 mm stick-on bumpers.
FOOT_D, FOOT_DEPTH = 10.6, 1.0
# ---------------------------------------------------------------------------

SEG = 64


def rrect(x0, y0, x1, y1, r):
    """Rounded rectangle cross-section from corner coordinates."""
    r = min(r, (x1 - x0) / 2 - 0.01, (y1 - y0) / 2 - 0.01)
    cs = CrossSection.square([x1 - x0 - 2 * r, y1 - y0 - 2 * r])
    cs = cs.translate([x0 + r, y0 + r])
    return cs.offset(r, JoinType.Round, circular_segments=SEG)


def slab(cs, z0, z1):
    return Manifold.extrude(cs, z1 - z0).translate([0, 0, z0])


def box(x0, y0, z0, x1, y1, z1):
    return Manifold.cube([x1 - x0, y1 - y0, z1 - z0]).translate([x0, y0, z0])


def pocket(x0, y0, x1, y1, top):
    """Pocket with rounded corners and a chamfered (scooped) bottom edge,
    cut from the floor up to above `top`."""
    full = slab(rrect(x0, y0, x1, y1, POCKET_R), FLOOR + SCOOP, top + 1)
    small = slab(rrect(x0 + SCOOP, y0 + SCOOP, x1 - SCOOP, y1 - SCOOP,
                       max(POCKET_R - SCOOP, 1)), FLOOR, FLOOR + 0.01)
    floor_band = slab(rrect(x0, y0, x1, y1, POCKET_R), FLOOR + SCOOP,
                      FLOOR + SCOOP + 0.01)
    return Manifold.batch_hull([small, floor_band]) + full


def leaned(m, pivot):
    """Tilt a part built in 'dock coordinates' (origin at the back edge of
    the slot floor, +z up the phone, -y toward the screen) back by LEAN and
    move it into place."""
    return m.rotate([-LEAN, 0, 0]).translate(pivot)


def build():
    x_mid = WALL + DOCK_W / 2 - WALL / 2         # dock centre line
    slot_floor = DOCK_H - SLOT_DEPTH
    pivot = [x_mid, SLOT_BACK_Y, slot_floor]
    slot_w = PHONE_W + PHONE_FIT
    slot_t = PHONE_T + PHONE_FIT

    # Body: tray + raised dock block.
    body = slab(rrect(0, 0, TRAY_W, TRAY_D, CORNER_R), 0, TRAY_H)
    back_y0 = WALL + FRONT_D + WALL
    body += slab(rrect(0, back_y0 - WALL, WALL + DOCK_W, TRAY_D, CORNER_R),
                 0, DOCK_H)

    # Backrest, leaning back, starting a little below the slot floor so it
    # is fused into the dock block.
    rest_w = slot_w + 2 * WALL
    rest = box(-rest_w / 2, 0, -SLOT_DEPTH, rest_w / 2, REST_T, REST_H)
    # Round the top corners of the backrest.
    r = 12.0
    top_round = (Manifold.cylinder(REST_T, r, circular_segments=SEG)
                 .rotate([-90, 0, 0]))
    corners = (top_round.translate([-rest_w / 2 + r, 0, REST_H - r])
               + top_round.translate([rest_w / 2 - r, 0, REST_H - r]))
    trim = (box(-rest_w / 2 - 1, -1, REST_H - r, -rest_w / 2 + r, REST_T + 1, REST_H + 1)
            + box(rest_w / 2 - r, -1, REST_H - r, rest_w / 2 + 1, REST_T + 1, REST_H + 1))
    rest = rest - trim + corners
    body += leaned(rest, pivot)

    # Pockets.
    x0, x1 = WALL, TRAY_W - WALL
    y0, y1 = WALL, WALL + FRONT_D
    cuts = [
        pocket(x0, y0, x0 + WALLET_W, y1, TRAY_H),                 # wallet
        pocket(x0 + WALLET_W + WALL, y0, x1, y1, TRAY_H),          # keys
    ]
    bx0 = WALL + DOCK_W + WALL
    by0, by1 = back_y0, TRAY_D - WALL
    cuts += [
        pocket(bx0, by0, bx0 + EARBUDS_W, by1, TRAY_H),            # earbuds
        pocket(bx0 + EARBUDS_W + WALL, by0, x1, by1, TRAY_H),      # watch
    ]

    # Phone slot (open at the top, runs up past the backrest top).
    slot = box(-slot_w / 2, -slot_t, 0, slot_w / 2, 0, REST_H + 40)
    # Plug pocket under the slot floor, centred on the phone's thickness.
    py = -PHONE_T / 2
    plug = box(-PLUG_W / 2 - 0.4, py - PLUG_T / 2 - 0.4, -PLUG_LEN,
               PLUG_W / 2 + 0.4, py + PLUG_T / 2 + 0.4, 0.5)
    # Cable slit: a thin cut straight down from the plug pocket and out of
    # the back and underside of the dock. Drop the plug in from the top,
    # press the cable into the slit, and it comes out at the back.
    s = CABLE_D / 2 + 0.4
    a = math.radians(LEAN)
    # Where the bottom of the (leaning) plug pocket ends up.
    pb_y = SLOT_BACK_Y + py * math.cos(a) - PLUG_LEN * math.sin(a)
    pb_z = slot_floor - py * math.sin(a) - PLUG_LEN * math.cos(a)
    slit = box(x_mid - s, pb_y - PLUG_T / 2, -1, x_mid + s, TRAY_D + 1, pb_z + 1)
    cuts.append(slit)
    # Air vents through the backrest, behind the phone (where it gets warm).
    vents = Manifold()
    n, vw = 5, 6.0
    span = slot_w - 20
    for i in range(n):
        cx = -span / 2 + i * span / (n - 1)
        v = (Manifold.extrude(rrect(cx - vw / 2, 18, cx + vw / 2, REST_H - 22, vw / 2), REST_T + 2)
             .rotate([90, 0, 0]).translate([0, REST_T + 1, 0]))
        vents += v
    cuts += [leaned(slot, pivot), leaned(plug, pivot),
             leaned(vents, pivot)]

    # Feet recesses.
    m = 18.0
    for fx, fy in [(m, m), (TRAY_W - m, m), (m, TRAY_D - m), (TRAY_W - m, TRAY_D - m)]:
        cuts.append(Manifold.cylinder(FOOT_DEPTH + 0.01, FOOT_D / 2,
                                      circular_segments=SEG)
                    .translate([fx, fy, -0.01]))

    return body - Manifold.batch_boolean(cuts, OpType.Add)


def write_stl(m, path):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].astype(np.float32)
    f = np.asarray(mesh.tri_verts)
    tri = v[f]
    nrm = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-12)
    rec = np.zeros(len(f), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
    rec["n"], rec["v"] = nrm, tri
    with open(path, "wb") as fh:
        fh.write(b"nightstand valet".ljust(80, b" "))
        fh.write(np.uint32(len(f)).tobytes())
        fh.write(rec.tobytes())


if __name__ == "__main__":
    here = os.path.dirname(os.path.abspath(__file__))
    out_dir = os.path.join(here, "..", "stl")
    os.makedirs(out_dir, exist_ok=True)
    part = build()
    assert part.status().name == "NoError", part.status()
    lo, hi = part.bounding_box()[:3], part.bounding_box()[3:]
    path = os.path.abspath(os.path.join(out_dir, "nightstand_valet.stl"))
    write_stl(part, path)
    print(f"wrote {path}")
    # Fit test: just the dock, to check the phone and plug before the big print.
    test = part ^ box(-1, WALL + FRONT_D - 1, -1, WALL + DOCK_W + 2, TRAY_D + 1, 300)
    write_stl(test, os.path.join(out_dir, "dock_fit_test.stl"))
    print("wrote dock_fit_test.stl, %d piece(s)" % len(test.decompose()))
    print("size  %.1f x %.1f x %.1f mm" % tuple(h - l for h, l in zip(hi, lo)))
    print("min   %.1f %.1f %.1f" % tuple(lo))
    print("volume %.0f cm^3, genus %d, decompose -> %d piece(s)"
          % (part.volume() / 1000, part.genus(), len(part.decompose())))
