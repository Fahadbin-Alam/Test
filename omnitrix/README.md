# Omnitrix-style wrist prop (fan-made, chunky classic style)

A wearable, fan-made prop inspired by the classic Ben 10 watch, modelled from
scratch for personal use. Chunky white body with four angled pylons and green
light bars, a ridged dial that turns and clicks into 8 positions, and an
armoured black band with a green stripe. The body is hollow so a green LED can
be added later.

![assembled](images/assembled.png)
![exploded](images/exploded.png)

## Quick start: Bambu P1S + AMS

Open **`omnitrix_full_kit_AMS.3mf`** in Bambu Studio. Every part is already
laid out on one 256 x 256 mm plate and named with its colour. Load your AMS
with these filaments and check each part's filament:

| AMS slot | Filament | Parts |
|---|---|---|
| 1 | Black | cuff (top and bottom), bezel, face, pins |
| 2 | Green (translucent if you'll add an LED) | cuff stripe, hourglass, 4 light bars |
| 3 | White | housing |
| 4 | Grey / silver | dial, dial grip |

If Bambu Studio doesn't pick the colours up by itself, click each part in the
object list (they're named "(Black)", "(Green)" and so on) and set the filament
number. Then slice with the 0.20 mm Standard profile and print, no supports.

Print `stl/0_test_fit_ring.stl` on its own first to check the fit.

## Parts (`stl/`)

| File | Print in | Notes |
|---|---|---|
| `0_test_fit_ring.stl` | any | 10 mm slice of the cuff. Print this first (about 20 min) to check the fit. |
| `1_cuff.stl` | black + green | Armoured C-cuff, slides on from the palm side. Print standing up (as exported). The green stripe is a separate part in the 3MF, so the AMS prints it automatically (no pauses). |
| `2_housing.stl` | white / light grey | Watch body with the four pylons. Flat side down. |
| `3_dial.stl` | grey / silver | The turning part. Flat flange side down. |
| `3b_dial_grip.stl` | grey / silver | Ridged collar that goes on the dial after the bezel. |
| `4_face.stl` | black | Face plate with the hourglass window. |
| `5_hourglass_insert.stl` | green (translucent green if you'll add an LED) | Thin lip side down. |
| `6_bezel.stl` | black | Ring that traps the dial. |
| `7_pin_x2.stl` | any | Print 2. Locate the body on the cuff. |
| `8_light_bar_x4.stl` | green (translucent is best) | Print 4. Press into the pylon tops. |

## Size

Cuff inside: **62 x 50 mm oval** (about 17.6 cm around), 40 mm wide band,
40 mm opening. That fits a typical adult wrist of roughly 15.5 to 17.5 cm.
To resize, change `WRIST_INNER_W` / `WRIST_INNER_H` at the top of
`generator/build.py` and run it again.

## Print settings (PLA)

- 0.2 mm layers, 3 walls, 20% infill (cuff: 4 walls, 30% so it doesn't snap)
- No supports needed for any part
- PETG is better for the cuff if you have it, since it flexes instead of cracking

## Assembly

1. Push the hourglass insert into the face from the back (lip behind the face). A drop of glue holds it.
2. Glue the face into the top of the dial.
3. Drop the dial into the housing. The two little nubs on the flange click into the grooves in the wall.
4. Glue the bezel onto the top of the housing wall (glue only on the wall, keep it off the dial). The dial should turn freely and click.
5. Slide the grip collar down over the dial until it sits on the step, line its ridges up with the bezel notches, and glue it to the dial (not the bezel).
6. Press the 4 green light bars into the pylon slots.
7. Push the 2 pins into the cuff's top pad, then glue the housing onto the pins and pad.

## Optional light

The housing has a 34 mm wide cavity under the dial and an 8 x 4 mm slot in the
side for a small slide switch. A CR2032 coin cell holder, one 5 mm green LED, a
100 ohm resistor and a mini slide switch fit inside. The light shines up through the
translucent green hourglass.

## Rebuilding

```
pip install manifold3d trimesh numpy matplotlib
python3 generator/build.py     # writes stl/
python3 generator/preview.py   # writes images/
python3 generator/export_3mf.py  # writes omnitrix_full_kit_AMS.3mf
```
