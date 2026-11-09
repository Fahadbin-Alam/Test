"""Places marked on the map.

Coordinates are WGS84 decimal degrees (lat, lon). Most are well known and
accurate to a few hundred metres. Where a battlefield's exact spot is debated,
`approx=True` and the note says so; at the main map's scale (1 mm = 1 km) that
uncertainty is a few millimetres at most.

kind -> marker shape and colour (see README "Colour plan"):
  kaaba    black cube              the Kaaba / Masjid al-Haram
  mosque   green dome              the Prophet's Mosque
  light    white cone / white cap  Jabal al-Nour (Cave of Hira, first revelation)
  battle   red spire               battles and sieges
  site     gold hexagon            other events (treaty, Hijra, Hajj sites)
"""

# ---- Main map (1 cm = 10 km) -------------------------------------------------
MAIN_SITES = [
    # name, lat, lon, kind, event, approx
    ("Mecca (Kaaba)", 21.4225, 39.8262, "kaaba", "Birthplace of the Prophet, c. 570 CE; Conquest of Mecca, 8 AH / 630 CE", False),
    ("Jabal al-Nour (Hira)", 21.4576, 39.8593, "light", "First revelation in the Cave of Hira, 610 CE", False),
    ("Medina", 24.4672, 39.6112, "mosque", "Hijra 1 AH / 622 CE; Prophet's Mosque", False),
    ("Badr", 23.7333, 38.7667, "battle", "Battle of Badr, 2 AH / 624 CE", False),
    ("Hudaybiyyah", 21.4440, 39.6060, "site", "Treaty of Hudaybiyyah, 6 AH / 628 CE", False),
    ("Khaybar", 25.6994, 39.2918, "battle", "Battle of Khaybar, 7 AH / 628 CE", False),
    ("Hunayn", 21.5500, 40.0700, "battle", "Battle of Hunayn, 8 AH / 630 CE (valley, approx.)", True),
    ("Ta'if", 21.2703, 40.4158, "battle", "Siege of Ta'if, 8 AH / 630 CE", False),
]

# ---- Mecca inset (1 cm = 1 km) -----------------------------------------------
MECCA_INSET = dict(
    name="Mecca",
    center=(21.4050, 39.9050),   # chosen so the Haram and Arafat both fit
    sites=[
        ("Kaaba / Masjid al-Haram", 21.4225, 39.8262, "kaaba", "The Kaaba", False),
        ("Jabal Thawr", 21.3772, 39.8497, "site", "Cave of Thawr, start of the Hijra, 622 CE", False),
        ("Mina", 21.4133, 39.8933, "site", "Mina (Hajj)", False),
        ("Muzdalifah", 21.3947, 39.9172, "site", "Muzdalifah (Hajj)", False),
        ("Arafat (Jabal al-Rahmah)", 21.3549, 39.9841, "site", "Farewell Sermon, 10 AH / 632 CE", False),
    ],
    # Jabal al-Nour gets a separate white cap instead of a peg marker.
    light_peak=("Jabal al-Nour (Hira)", 21.4576, 39.8593),
    trench=None,
)

# ---- Medina inset (1 cm = 1 km) ----------------------------------------------
MEDINA_INSET = dict(
    name="Medina",
    center=(24.4800, 39.6000),
    sites=[
        ("Prophet's Mosque", 24.4672, 39.6112, "mosque", "Masjid an-Nabawi", False),
        ("Quba Mosque", 24.4393, 39.6173, "site", "First mosque, 1 AH / 622 CE", False),
        ("Masjid al-Qiblatayn", 24.4843, 39.5791, "site", "Change of qibla, 2 AH / 624 CE", False),
        ("Uhud", 24.5015, 39.6125, "battle", "Battle of Uhud, 3 AH / 625 CE (archers' hill)", False),
        ("The Trench", 24.4790, 39.5960, "battle", "Battle of the Trench, 5 AH / 627 CE (by Jabal Sal')", True),
    ],
    light_peak=None,
    # Approximate line of the trench across the open north side of the city,
    # between the western and eastern lava fields. Engraved as a groove.
    trench=[(24.4815, 39.5770), (24.4850, 39.5880), (24.4865, 39.6000),
            (24.4860, 39.6120), (24.4835, 39.6230)],
)
