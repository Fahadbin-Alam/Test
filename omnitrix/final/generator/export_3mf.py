"""Write a ready-to-slice 3MF for a Bambu P1S + AMS (256 x 256 mm bed).

Every part is its own object, laid out on one plate and tagged with its colour.
The cuff is one object made of three parts (black / green stripe / black) so the
AMS prints the stripe with no pauses. Colours use the standard 3MF material
table; parts are also named by colour in case the slicer asks you to map them.
"""
import os
import sys
import zipfile
from xml.sax.saxutils import escape

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
import build  # noqa: E402

COLOURS = {"Black": "#1A1A1AFF", "Green": "#2FD34AFF", "White": "#F2F2F2FF", "Grey": "#8D929BFF"}
CNAMES = list(COLOURS)


def split_cuff():
    c = build.cuff(build.CUFF_WIDTH)
    z0, z1 = build.STRIPE
    lo = c.trim_by_plane([0, 0, -1], -z0)
    mid = c.trim_by_plane([0, 0, 1], z0).trim_by_plane([0, 0, -1], -z1)
    hi = c.trim_by_plane([0, 0, 1], z1)
    return [("cuff_lower (Black)", lo, "Black"), ("cuff_stripe (Green)", mid, "Green"),
            ("cuff_upper (Black)", hi, "Black")]


# (object name, [(part name, manifold, colour)], (x, y) centre on the plate in mm)
def plate():
    b = build
    bars = [b.light_bar().translate([x, 0, 0]) for x in (0, 5, 10, 15)]
    return [
        ("Cuff", split_cuff(), (58, 60)),
        ("Housing (White)", [("housing", b.housing(), "White")], (175, 60)),
        ("Dial (Grey)", [("dial", b.dial(), "Grey")], (45, 160)),
        ("Dial grip (Grey)", [("dial_grip", b.dial_grip(), "Grey")], (110, 210)),
        ("Bezel (Black)", [("bezel", b.bezel(), "Black")], (120, 140)),
        ("Face (Black)", [("face", b.face(), "Black")], (195, 150)),
        ("Hourglass (Green)", [("hourglass", b.hourglass_insert(), "Green")], (200, 205)),
        ("Light bars x4 (Green)", [("bar%d" % i, m, "Green") for i, m in enumerate(bars)], (40, 225)),
        ("Pins x2 (Black)", [("pin1", b.pin(), "Black"), ("pin2", b.pin().translate([6, 0, 0]), "Black")], (160, 235)),
    ]


def mesh_xml(m, centre_xy, offset_xy):
    mesh = m.to_mesh()
    v = np.asarray(mesh.vert_properties)[:, :3].copy()
    v[:, 0] += centre_xy[0] - offset_xy[0]
    v[:, 1] += centre_xy[1] - offset_xy[1]
    t = np.asarray(mesh.tri_verts)
    verts = "".join(f'<vertex x="{x:.4f}" y="{y:.4f}" z="{z:.4f}"/>' for x, y, z in v)
    tris = "".join(f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in t)
    return f"<mesh><vertices>{verts}</vertices><triangles>{tris}</triangles></mesh>"


def write(path):
    objs, items, nid = [], [], 2
    for oname, parts, xy in plate():
        # centre the whole object (all its parts) on its plate spot, sitting on z = 0
        allv = np.concatenate([np.asarray(p.to_mesh().vert_properties)[:, :3] for _, p, _ in parts])
        off = ((allv[:, 0].min() + allv[:, 0].max()) / 2, (allv[:, 1].min() + allv[:, 1].max()) / 2)
        zmin = allv[:, 2].min()
        comp_ids = []
        for pname, m, col in parts:
            m = m.translate([0, 0, -zmin])
            objs.append(f'<object id="{nid}" name="{escape(pname)}" type="model" pid="1" '
                        f'pindex="{CNAMES.index(col)}">{mesh_xml(m, xy, off)}</object>')
            comp_ids.append(nid); nid += 1
        comps = "".join(f'<component objectid="{i}"/>' for i in comp_ids)
        objs.append(f'<object id="{nid}" name="{escape(oname)}" type="model"><components>{comps}</components></object>')
        items.append(f'<item objectid="{nid}"/>'); nid += 1
    mats = "".join(f'<base name="{n}" displaycolor="{c}"/>' for n, c in COLOURS.items())
    model = ('<?xml version="1.0" encoding="UTF-8"?>'
             '<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
             '<metadata name="Title">Omnitrix-style prop, full kit</metadata>'
             f'<resources><basematerials id="1">{mats}</basematerials>{"".join(objs)}</resources>'
             f'<build>{"".join(items)}</build></model>')
    ctypes = ('<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
              '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
              '<Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/></Types>')
    rels = ('<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/></Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml", ctypes)
        z.writestr("_rels/.rels", rels)
        z.writestr("3D/3dmodel.model", model)
    print("wrote", os.path.abspath(path))


if __name__ == "__main__":
    write(os.path.join(os.path.dirname(__file__), "..", "omnitrix_full_kit_AMS.3mf"))
