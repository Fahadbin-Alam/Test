#!/usr/bin/env python3
"""Download building footprints, 3D building parts and roads around the Haram
from Overture Maps (which includes OpenStreetMap data) and save them as small
GeoJSON files in generator/data/. Only needed to refresh the data; haram.py
reads the saved files.

    pip install pyarrow shapely requests
    python fetch_haram_data.py
"""
import json, os, sys
import pyarrow as pa
import pyarrow.parquet as pq
import concurrent.futures as cf
from shapely import wkb
from shapely.geometry import mapping

sys.path.insert(0, os.path.dirname(__file__))
import overture  # noqa: E402

RELEASE = "2026-10-21.0"
BBOX = (39.818, 21.414, 39.834, 21.430)      # lon/lat, a bit bigger than the model
OUT = os.path.join(os.path.dirname(__file__), "data")


def fetch(typ):
    keys = overture.keys(typ, RELEASE)
    tabs = []
    with cf.ThreadPoolExecutor(24) as ex:
        for _k, rows, _n in ex.map(lambda k: overture.scan(k, BBOX), keys):
            tabs += rows
    return pa.concat_tables(tabs, promote_options="permissive").to_pylist()


def feats(rows, props):
    out = []
    for r in rows:
        g = wkb.loads(r["geometry"])
        p = {k: f(r) for k, f in props.items()}
        out.append({"type": "Feature", "geometry": mapping(g), "properties": p})
    return out


def name(r):
    return (r.get("names") or {}).get("primary")


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    common = {"name": name, "height": lambda r: r.get("height"), "min_height": lambda r: r.get("min_height"),
              "floors": lambda r: r.get("num_floors"), "class": lambda r: r.get("class")}
    b = fetch("theme=buildings/type=building")
    p = fetch("theme=buildings/type=building_part")
    fb = feats(b, {**common, "has_parts": lambda r: bool(r.get("has_parts")), "part": lambda r: False})
    fp = feats(p, {**common, "part": lambda r: True})
    s = fetch("theme=transportation/type=segment")

    def flags(r):
        out = set()
        for f in r.get("road_flags") or []:
            out.update(f.get("values") or [])
        return sorted(out)
    fs = feats([r for r in s if r.get("subtype") == "road"], {"class": lambda r: r.get("class"), "flags": flags})
    for fn, fc in (("haram_buildings.geojson", fb + fp), ("haram_roads.geojson", fs)):
        with open(os.path.join(OUT, fn), "w") as f:
            json.dump({"type": "FeatureCollection",
                       "attribution": "Overture Maps Foundation, incl. (c) OpenStreetMap contributors (ODbL)",
                       "features": fc}, f, separators=(",", ":"))
        print(fn, len(fc))
