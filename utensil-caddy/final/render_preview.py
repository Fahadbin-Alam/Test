import sys, numpy as np, trimesh
from PIL import Image, ImageDraw, ImageFont
d = sys.argv[1]
parts = [(trimesh.load(f"{d}/caddy_body.stl"), np.array([236, 230, 218]) / 255),
         (trimesh.load(f"{d}/caddy_icons.stl"), np.array([40, 42, 48]) / 255)]
def render(el, az, S=900):
    a, e = np.radians(az), np.radians(el)
    fwd = np.array([-np.cos(e) * np.sin(a), np.cos(e) * np.cos(a), -np.sin(e)])  # camera looks along fwd
    right = np.cross(fwd, [0, 0, 1]); right /= np.linalg.norm(right); up = np.cross(right, fwd)
    c = np.array([120, 75, 80])
    allv = np.vstack([m.vertices for m, _ in parts]) - c
    sc = 0.9 * S / (2 * np.abs(np.c_[allv @ right, allv @ up]).max())
    zb = np.full((S, S), np.inf); img = np.ones((S, S, 3))
    L = np.array([-0.35, -0.75, 0.6]); L /= np.linalg.norm(L)
    for m, col in parts:
        v = m.vertices - c
        P = np.c_[S / 2 + (v @ right) * sc, S / 2 - (v @ up) * sc, v @ fwd]
        n = m.face_normals
        shade = 0.35 + 0.65 * np.clip(n @ L, 0, 1)
        for f, s in zip(m.faces, shade):
            if n[f[0] if False else 0] is None: pass
            t = P[f]
            x0, y0 = np.floor(t[:, :2].min(0)).astype(int); x1, y1 = np.ceil(t[:, :2].max(0)).astype(int)
            x0, y0 = max(x0, 0), max(y0, 0); x1, y1 = min(x1, S - 1), min(y1, S - 1)
            if x1 < x0 or y1 < y0: continue
            X, Y = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
            (ax, ay, az_), (bx, by, bz), (cx, cy, cz) = t
            den = (by - cy) * (ax - cx) + (cx - bx) * (ay - cy)
            if abs(den) < 1e-9: continue
            w0 = ((by - cy) * (X - cx) + (cx - bx) * (Y - cy)) / den
            w1 = ((cy - ay) * (X - cx) + (ax - cx) * (Y - cy)) / den
            w2 = 1 - w0 - w1
            ins = (w0 >= -1e-6) & (w1 >= -1e-6) & (w2 >= -1e-6)
            if not ins.any(): continue
            z = w0 * az_ + w1 * bz + w2 * cz
            sub = zb[y0:y1 + 1, x0:x1 + 1]
            ok = ins & (z < sub - 1e-4 * 0)
            sub[ok] = z[ok]
            img[y0:y1 + 1, x0:x1 + 1][ok] = col * s
    return Image.fromarray((img * 255).astype(np.uint8))
a = render(24, -35); b = render(38, 30)
W = a.width + b.width
out = Image.new("RGB", (W, a.height + 70), "white"); out.paste(a, (0, 70)); out.paste(b, (a.width, 70))
dr = ImageDraw.Draw(out)
try: f = ImageFont.truetype("DejaVuSans.ttf", 26)
except Exception: f = ImageFont.load_default()
dr.text((20, 20), "Utensil caddy  240 x 150 x 160 mm (9.4 x 5.9 x 6.3 in)   front: forks / spoons / knives   back: spatulas / ladles", fill="black", font=f)
out.save(f"{d}/preview.png")
