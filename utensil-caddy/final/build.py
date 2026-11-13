"""Dining-table utensil caddy - generator.

Front row: 3 pockets (forks, spoons, knives), 100 mm tall.
Back row: 2 tall pockets (spatulas/turners, ladles/whisks), 160 mm tall.
Icons are inlaid 0.6 mm into the walls as a second colour for the AMS.

Run: pip install manifold3d trimesh numpy ; python build.py
All sizes in mm. Change the constants below to resize.
"""
import numpy as np, trimesh, os
from manifold3d import CrossSection as CS, Manifold as M, JoinType

W = 240.0          # overall width (x)
D = 150.0          # overall depth (y)
FRONT_H = 100.0    # cutlery row height
BACK_H = 160.0     # cooking-utensil row height
FRONT_D = 70.0     # depth of cutlery row (outer, incl. front wall)
WALL = 1.6         # 4 perimeters at 0.4 mm
FLOOR = 2.4
R_OUT = 10.0       # outer corner radius
R_IN = 6.0         # pocket corner radius (easy to wipe clean)
INLAY = 0.6        # icon inlay depth
BACK_SPLIT = 0.5   # share of the back row width given to the left (spatula) pocket
FOOT_D, FOOT_DEPTH = 10.5, 1.0  # recesses for 10 mm rubber bumper feet

OUT = os.path.dirname(os.path.abspath(__file__))

def rrect(x0, y0, x1, y1, r):
    w, h = x1 - x0, y1 - y0
    r = min(r, w / 2 - 0.01, h / 2 - 0.01)
    return CS.square((w - 2 * r, h - 2 * r)).translate((x0 + r, y0 + r)).offset(r, JoinType.Round, circular_segments=48)

def circ(x, y, r):
    return CS.circle(r, 48).translate((x, y))

def hull(*parts):
    return CS.batch_hull(list(parts))

def box(x0, x1, y0, y1, z0, z1, r):
    return rrect(x0, y0, x1, y1, r).extrude(z1 - z0).translate((0, 0, z0))

# ---------- icons (2D, drawn ~60 mm tall, origin at bottom centre) ----------
def icon_fork():
    s = hull(circ(0, 4, 3.2), circ(0, 30, 2.0))
    s += hull(circ(0, 30, 2.0), rrect(-6.5, 37, 6.5, 41, 1))
    s += rrect(-6.5, 37, 6.5, 45, 2.5)
    for x in (-5.4, -1.8, 1.8, 5.4):
        s += rrect(x - 1.0, 42, x + 1.0, 60, 1.0)
    return s

def icon_spoon():
    s = hull(circ(0, 4, 3.2), circ(0, 32, 2.0))
    s += circ(0, 0, 1).scale((7.5, 12)).translate((0, 47))
    return s

def icon_knife():
    s = rrect(-3.2, 0, 3.2, 27, 3.0)
    pts = [(-3.0, 27), (3.0, 27), (3.0, 56), (2.0, 59.5), (0.5, 60)]
    # curved cutting edge on the left
    for t in np.linspace(1, 0, 12):
        pts.append((-3.0 - 1.5 * np.sin(np.pi * t), 27 + 33 * t * t))
    s += CS([pts[:5] + pts[5:]]).hull()
    return s

def icon_turner():
    s = hull(circ(0, 4, 3.2), circ(0, 28, 2.0))
    s += hull(circ(0, 28, 2.0), rrect(-4, 34, 4, 36, 1))
    head = rrect(-10, 34, 10, 60, 3)
    for x in (-5, 0, 5):
        head -= rrect(x - 1.1, 39, x + 1.1, 55, 1.1)
    return s + head

def icon_ladle():
    s = hull(circ(0, 58, 2.2), circ(0, 20, 2.0))
    s += circ(0, 11, 11) - rrect(-12, 11, 12, 30, 0.1)   # bowl (half disc)
    s += rrect(-11, 10, 11, 13, 1.5)                       # rim
    return s

def place_icon(cs, cx, cz, scale, y_face, into):
    """Extrude a 2D icon (x,z) into a wall whose face is at y=y_face.
    into=+1 cuts toward +y (front face), -1 toward -y."""
    cs = cs.scale((scale, scale)).translate((cx, cz - 30 * scale))
    m = cs.extrude(INLAY + 1.0)                      # along +z
    m = m.rotate((90, 0, 0))                         # z->-y, y->z
    # now occupies y in [-(INLAY+1), 0]
    if into > 0:
        m = m.translate((0, y_face + INLAY, 0))
    else:
        m = m.mirror((0, 1, 0)).translate((0, y_face - INLAY, 0))
    return m

# ---------- body ----------
# front block (cutlery height) + back block (tall), back block clipped to the rounded footprint
body = box(0, W, 0, D, 0, FRONT_H, R_OUT) + (box(0, W, FRONT_D - WALL, D + R_OUT, 0, BACK_H, 0.01) ^ box(0, W, 0, D, 0, BACK_H, R_OUT))

pockets = []
fw = (W - 4 * WALL) / 3
for i in range(3):
    x0 = WALL + i * (fw + WALL)
    pockets.append(box(x0, x0 + fw, WALL, FRONT_D - WALL, FLOOR, BACK_H + 1, R_IN))
bw = W - 3 * WALL
b1 = bw * BACK_SPLIT
pockets.append(box(WALL, WALL + b1, FRONT_D, D - WALL, FLOOR, BACK_H + 1, R_IN))
pockets.append(box(2 * WALL + b1, W - WALL, FRONT_D, D - WALL, FLOOR, BACK_H + 1, R_IN))
for p in pockets:
    body -= p

# rubber-feet recesses underneath
for fx in (18, W - 18):
    for fy in (18, D - 18):
        body -= M.cylinder(FOOT_DEPTH + 0.01, FOOT_D / 2, circular_segments=48).translate((fx, fy, -0.01))

# ---------- icons ----------
icons = M()
front_cz = FLOOR + (FRONT_H - FLOOR) / 2 + 2
for i, ic in enumerate((icon_fork, icon_spoon, icon_knife)):
    cx = WALL + i * (fw + WALL) + fw / 2
    icons += place_icon(ic(), cx, front_cz, 1.0, 0.0, +1)
# back icons on the exposed face of the divider above the cutlery row
back_cz = FRONT_H + (BACK_H - FRONT_H) / 2
for cx, ic in ((WALL + b1 / 2, icon_turner), (2 * WALL + b1 + (bw - b1) / 2, icon_ladle)):
    icons += place_icon(ic(), cx, back_cz, 0.75, FRONT_D - WALL, +1)

icons = icons ^ body            # only where it overlaps the wall
body_ams = body - icons

def to_tm(m):
    g = m.to_mesh()
    return trimesh.Trimesh(np.array(g.vert_properties)[:, :3], np.array(g.tri_verts), process=True)

def write_3mf(path, parts):
    """One object, several parts (Bambu Studio keeps them as one model; set filament per part)."""
    import zipfile
    objs, comps = [], []
    for i, (name, tm) in enumerate(parts, start=1):
        v = "".join(f'<vertex x="{a:.4f}" y="{b:.4f}" z="{c:.4f}"/>' for a, b, c in tm.vertices)
        t = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in tm.faces)
        objs.append(f'<object id="{i}" name="{name}" type="model"><mesh><vertices>{v}</vertices><triangles>{t}</triangles></mesh></object>')
        comps.append(f'<component objectid="{i}"/>')
    n = len(parts) + 1
    model = ('<?xml version="1.0" encoding="UTF-8"?><model unit="millimeter" xml:lang="en-US" '
             'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"><resources>' + "".join(objs) +
             f'<object id="{n}" name="utensil_caddy" type="model"><components>{"".join(comps)}</components></object>'
             f'</resources><build><item objectid="{n}" transform="1 0 0 0 1 0 0 0 1 8 53 0"/></build></model>')
    ct = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
          '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
          '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ct); z.writestr("_rels/.rels", rels); z.writestr("3D/3dmodel.model", model)

if __name__ == "__main__":
    tb, ti, ts = to_tm(body_ams), to_tm(icons), to_tm(body)
    tb.export(os.path.join(OUT, "caddy_body.stl"))
    ti.export(os.path.join(OUT, "caddy_icons.stl"))
    ts.export(os.path.join(OUT, "..", "single-colour", "caddy_single_colour.stl"))
    write_3mf(os.path.join(OUT, "utensil_caddy_AMS.3mf"), [("body", tb), ("icons", ti)])
    for n, t in (("body", tb), ("icons", ti), ("single", ts)):
        print(n, "watertight", t.is_watertight, "bounds", np.round(t.bounds, 1).tolist(), "vol cm3", round(t.volume / 1000, 1))
    print("pockets: cutlery %.1f x %.1f mm, %.0f deep; back %.1f / %.1f x %.1f mm, %.0f deep" %
          (fw, FRONT_D - 2 * WALL, FRONT_H - FLOOR, b1, bw - b1, D - WALL - FRONT_D, BACK_H - FLOOR))
