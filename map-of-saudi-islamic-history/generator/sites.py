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
    ams_override={},
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
    # Multicolour version: the AMS has 4 slots and this tile needs white for
    # the Hijra, so Quba and Qiblatayn print white here instead of gold.
    ams_override={"Quba Mosque": "white", "Masjid al-Qiblatayn": "white"},
    # Approximate line of the trench across the open north side of the city,
    # between the western and eastern lava fields. Engraved as a groove.
    trench=[(24.4815, 39.5770), (24.4850, 39.5880), (24.4865, 39.6000),
            (24.4860, 39.6120), (24.4835, 39.6230)],
)

# ---- Journeys ----------------------------------------------------------------
# Stations named in the sira and on the old Medina-Mecca road. Nobody recorded
# the exact tracks and several of these spots are only known to within a few
# km, so every route is approximate. Between stations each route follows the
# easiest way through the real terrain (see routes.py).
STATIONS = {
    "Mecca": (21.4225, 39.8262),            # the Kaaba
    "Thawr": (21.3772, 39.8497),            # cave on Jabal Thawr
    "Medina": (24.4672, 39.6112),           # the Prophet's Mosque
    "Quba": (24.4393, 39.6173),
    "Dhul-Hulayfa": (24.4136, 39.5436),     # miqat of Medina (Abyar Ali)
    "al-Rawha": (24.07, 39.05),             # Wadi al-Safra (approx.)
    "al-Abwa": (23.15, 39.00),              # tomb of Amina (approx.)
    "al-Juhfa": (22.70, 39.14),             # miqat near Rabigh
    "Qudayd": (22.36, 39.33),               # tent of Umm Ma'bad (approx.)
    "Usfan": (21.92, 39.37),
    "Marr al-Zahran": (21.617, 39.700),     # Wadi Fatima, al-Jumum
    "Badr": (23.7333, 38.7667),
    "Khaybar": (25.6994, 39.2918),
    "Hudaybiyyah": (21.4440, 39.6060),
    "Hunayn": (21.5500, 40.0700),
    "Ta'if": (21.2703, 40.4158),
    "Uhud": (24.5015, 39.6125),
    "Mina": (21.4133, 39.8933),
    "Muzdalifah": (21.3947, 39.9172),
    "Arafat": (21.3549, 39.9841),
    # The Hijra kept off the main road and went down to the coast.
    "coast south of Usfan": (21.55, 39.27),
    "coast west of Usfan": (21.95, 39.20),
    "coast west of Qudayd": (22.36, 39.17),
    "al-Kharrar": (22.80, 39.07),            # near Rabigh (approx.)
}

# key, name, colour (AMS), date, stations. Red = the Prophet's marches and
# campaigns, white = the Hijra (printed as a dashed line).
ROUTES = [
    ("badr", "March to Badr", "red", "2 AH / 624 CE",
     ["Medina", "Dhul-Hulayfa", "al-Rawha", "Badr"]),
    ("khaybar", "March to Khaybar", "red", "7 AH / 628 CE",
     ["Medina", "Khaybar"]),
    ("hudaybiyyah", "Journey to Hudaybiyyah", "red", "6 AH / 628 CE",
     ["Medina", "Dhul-Hulayfa", "al-Rawha", "al-Abwa", "al-Juhfa", "Qudayd", "Usfan", "Hudaybiyyah"]),
    ("mecca", "Conquest of Mecca, and the Farewell Hajj", "red", "8 AH / 630 CE, 10 AH / 632 CE",
     ["Medina", "Dhul-Hulayfa", "al-Rawha", "al-Abwa", "al-Juhfa", "Qudayd", "Usfan", "Marr al-Zahran", "Mecca"]),
    ("hunayn", "Hunayn and the siege of Ta'if", "red", "8 AH / 630 CE",
     ["Mecca", "Hunayn", "Ta'if"]),
    ("hijra", "The Hijra", "white", "1 AH / 622 CE",
     ["Mecca", "Thawr", "coast south of Usfan", "coast west of Usfan", "coast west of Qudayd",
      "al-Kharrar", "Quba", "Medina"]),
]

# Close-up routes on the insets: main-map route key (or None), colour, stations,
# raised label, and a name for the ones that are only on the inset. "->" carries
# a main-map route on to the edge of the tile and "<-" brings one in from it;
# the label goes beside that end.
MECCA_INSET["routes"] = [
    ("hijra", "white", ["Mecca", "Thawr", "->"], "Hijra to Medina {hijra} km", None),
    (None, "gold", ["Mecca", "Mina", "Muzdalifah", "Arafat"], None,
     ("The Farewell Hajj: Mina, Muzdalifah, Arafat", "10 AH / 632 CE")),
]
MEDINA_INSET["routes"] = [
    ("mecca", "red", ["Medina", "Dhul-Hulayfa", "->"], "to Badr {badr} km, Mecca {mecca} km",
     ("The road to Badr and Mecca", "Badr 2 AH, Hudaybiyyah 6 AH, Conquest 8 AH, Farewell Hajj 10 AH")),
    ("khaybar", "red", ["Medina", "->"], "to Khaybar {khaybar} km", None),
    (None, "red", ["Medina", "Uhud"], None, ("March to Uhud", "3 AH / 625 CE")),
    ("hijra", "white", ["<-", "Quba", "Medina"], "Hijra from Mecca {hijra} km", None),
]
