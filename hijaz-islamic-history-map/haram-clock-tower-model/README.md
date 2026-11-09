# Masjid al-Haram and the Makkah Clock Tower

An extra piece for the map project: a 240 x 240 mm city model at 1:4,000
(1 cm = 40 m), true heights, Clock Tower 150 mm tall.

| File | What it is |
|---|---|
| `haram_model.3mf` | **Print this** on the AMS: 1 light grey, 2 white, 3 black, 4 gold |
| `ams-parts/` | The same colours as separate STLs, if the 3MF colours don't load |
| `haram_model_one_piece.stl` | One piece, for a single colour (white or light grey) |
| `preview/` | Renders |

Print settings, data sources and how to rebuild it are in
[`../final/README.md`](../final/README.md#masjid-al-haram-and-the-makkah-clock-tower).
The generator (`haram.py`) lives in `../final/generator/` and writes into
`../final/ams/` and `../final/stl/`; move the new files here afterwards.
