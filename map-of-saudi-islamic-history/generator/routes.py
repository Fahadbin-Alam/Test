"""Journeys of the Prophet, traced through the real terrain.

Nobody recorded the exact tracks, only the stations they passed. So each
route goes through its historical stations (sites.py) and, between them,
follows the path of least effort over the elevation model: the way a camel
caravan would go, along the wadis and over the lowest passes. Expect the line
to be right to within a few kilometres, which is a few millimetres on the
main map.
"""
import math

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter1d
from scipy.sparse import coo_matrix
from scipy.sparse.csgraph import dijkstra

# effort of one step = distance * (1 + SLOPE_K * slope + SLOPE_K2 * slope^2)
SLOPE_K, SLOPE_K2 = 30.0, 600.0


def _graph(elev_m, cell_km, blocked, extra=None, slope=(SLOPE_K, SLOPE_K2)):
    """8-connected grid graph whose edge weights are walking effort."""
    ny, nx = elev_m.shape
    idx = np.arange(nx * ny).reshape(ny, nx)
    ok = ~blocked
    mult = np.ones_like(elev_m) if extra is None else 1.0 + extra
    rows, cols, w = [], [], []
    for dj, di in ((0, 1), (1, 0), (1, 1), (1, -1)):
        j0, j1 = max(0, -dj), ny - max(0, dj)
        i0, i1 = max(0, -di), nx - max(0, di)
        a = idx[j0:j1, i0:i1]
        b = idx[j0 + dj:j1 + dj, i0 + di:i1 + di]
        ja, ia = np.unravel_index(a.ravel(), (ny, nx))
        jb, ib = np.unravel_index(b.ravel(), (ny, nx))
        good = ok[ja, ia] & ok[jb, ib]
        ja, ia, jb, ib = ja[good], ia[good], jb[good], ib[good]
        d = cell_km * math.hypot(dj, di)
        s = np.abs(elev_m[jb, ib] - elev_m[ja, ia]) / (d * 1000.0)
        cost = d * (1 + slope[0] * s + slope[1] * s * s) * 0.5 * (mult[ja, ia] + mult[jb, ib])
        a1, b1 = idx[ja, ia], idx[jb, ib]
        rows += [a1, b1]
        cols += [b1, a1]
        w += [cost, cost]
    rows, cols, w = np.concatenate(rows), np.concatenate(cols), np.concatenate(w)
    return coo_matrix((w, (rows, cols)), shape=(nx * ny, nx * ny)).tocsr()


def _nearest_ok(j, i, blocked):
    if not blocked[j, i]:
        return j, i
    jj, ii = np.nonzero(~blocked)
    k = np.argmin((jj - j) ** 2 + (ii - i) ** 2)
    return int(jj[k]), int(ii[k])


def trace(elev_m, step_mm, mm_per_km, blocked, waypoints_mm, extra=None, slope=(SLOPE_K, SLOPE_K2)):
    """Least-effort path through the given points (mm). Returns an (n, 2) array in mm."""
    ny, nx = elev_m.shape
    g = _graph(elev_m, step_mm / mm_per_km, blocked, extra, slope)
    out = []
    for (ax, ay), (bx, by) in zip(waypoints_mm[:-1], waypoints_mm[1:]):
        ja, ia = _nearest_ok(int(round(ay / step_mm)), int(round(ax / step_mm)), blocked)
        jb, ib = _nearest_ok(int(round(by / step_mm)), int(round(bx / step_mm)), blocked)
        s, t = ja * nx + ia, jb * nx + ib
        _, pred = dijkstra(g, indices=s, return_predecessors=True)
        path = [t]
        while path[-1] != s:
            p = pred[path[-1]]
            if p < 0:
                raise RuntimeError(f"no path between {waypoints_mm}")
            path.append(p)
        path = path[::-1]
        jj, ii = np.unravel_index(np.array(path), (ny, nx))
        seg = np.column_stack([ii * step_mm, jj * step_mm]).astype(float)
        seg[0], seg[-1] = (ax, ay), (bx, by)
        out.append(seg if not out else seg[1:])
    return np.vstack(out)


def smooth(p, sigma_mm, keep=()):
    """Resample to 0.5 mm and smooth, holding the ends and the given points still."""
    p = resample(p, 0.5)
    if len(p) < 5:
        return p
    sig = sigma_mm / 0.5
    q = np.column_stack([gaussian_filter1d(p[:, 0], sig, mode="nearest"),
                         gaussian_filter1d(p[:, 1], sig, mode="nearest")])
    # blend back to the exact points at the ends and at each kept station
    anchors = [0, len(p) - 1] + [int(np.argmin(np.hypot(*(p - k).T))) for k in keep]
    w = np.ones(len(p))
    s = np.arange(len(p))
    for a in anchors:
        w = np.minimum(w, np.clip(np.abs(s - a) / (3 * sig), 0, 1))
    return q * w[:, None] + p * (1 - w[:, None])


def resample(p, ds):
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(p, axis=0).T))]
    if d[-1] == 0:
        return p
    t = np.linspace(0, d[-1], max(2, int(d[-1] / ds) + 1))
    return np.column_stack([np.interp(t, d, p[:, 0]), np.interp(t, d, p[:, 1])])


def length(p):
    return float(np.sum(np.hypot(*np.diff(p, axis=0).T)))


def keep_away(shape, step_mm, lines=(), line_d=4.0, points=(), point_d=6.0, free=(), free_r=4.0):
    """Extra effort near other routes and markers, so a route runs beside them, not on them."""
    ys, xs = np.mgrid[0:shape[0], 0:shape[1]] * step_mm
    extra = np.zeros(shape)
    if lines:
        mask = np.zeros(shape, bool)
        for p in lines:
            q = resample(p, step_mm / 2)
            i = np.clip(np.round(q[:, 0] / step_mm).astype(int), 0, shape[1] - 1)
            j = np.clip(np.round(q[:, 1] / step_mm).astype(int), 0, shape[0] - 1)
            mask[j, i] = True
        d = distance_transform_edt(~mask) * step_mm
        extra = np.maximum(extra, np.where(d < line_d, 4.0 * (1 - d / line_d), 0.0))
    for (x, y) in points:
        d = np.hypot(xs - x, ys - y)
        extra = np.maximum(extra, np.where(d < point_d, 20.0 * (1 - d / point_d), 0.0))
    for (x, y) in free:
        extra[np.hypot(xs - x, ys - y) < free_r] = 0
    return extra


def exit_point(line, start, forward, inside):
    """Walk along `line` from the point nearest `start` until it leaves the area
    `inside(x, y)`; return the last point still inside."""
    k = int(np.argmin(np.hypot(*(line - np.asarray(start)).T)))
    rng = range(k, len(line)) if forward else range(k, -1, -1)
    last = line[k]
    for n in rng:
        if not inside(*line[n]):
            return np.asarray(last)
        last = line[n]
    return np.asarray(last)


def dashes(p, on, off):
    """Split a polyline into dashes `on` mm long with `off` mm gaps."""
    q = resample(p, 0.25)
    d = np.r_[0, np.cumsum(np.hypot(*np.diff(q, axis=0).T))]
    out, t = [], 0.0
    while t < d[-1]:
        sel = (d >= t) & (d <= t + on)
        if sel.sum() >= 2:
            out.append(q[sel])
        t += on + off
    return out
