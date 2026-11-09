# 3D printed stuff

Everything I design and print on my Bambu Lab P1S + AMS. The same layout is
used here on GitHub and in the `3D print` folder on my desktop.

## How the folders work

Every project gets its own folder, and every project folder looks the same:

```
<project>/
  README.md        what the project is and what's in each folder
  final/           the latest version: print from here
  old-versions/    earlier versions, kept for reference
    v1-<what-it-was>/
  <variant>/       one folder per alternative version (a colour, a size, a style)
  <extra-piece>/   a separate model that belongs to the project (e.g. a close-up)
```

Rules:

1. **`final/` is always the one to print.** It holds the newest files, the
   README with print settings, and the generator script that made them.
2. **When a new version replaces the final one,** move the old files into
   `old-versions/vN-<short-description>/` (for example
   `v1-no-distance-rings`), then put the new files in `final/`.
3. **A variant is an alternative you might also print,** not an older one:
   a different colour scheme, size or style. Name the folder after what makes
   it different, in lower case with dashes (`red`, `pink`, `single-colour`,
   `us10-5`). A variant folder holds only the files that differ from `final/`.
4. Folder names are lower case with dashes, so they work the same on Windows
   and on GitHub.
5. **An extra piece** (a separate model that goes with the project, like the
   Haram model next to the map) gets its own named folder too.
6. Empty folders keep a `.gitkeep` file so they show up on GitHub.

## Projects

| Folder | What it is | Variants | Old versions |
|---|---|---|---|
| [`hijaz-islamic-history-map/`](hijaz-islamic-history-map/) | Tiled relief map of the Hijaz in the time of the Prophet ﷺ | `single-colour-with-pegs`, extra piece `haram-clock-tower-model` | `v1-no-distance-rings` |
| [`omnitrix/`](omnitrix/) | Omnitrix-style wrist prop (15 cm wrist) | none yet | `v1-original-style`, `v2-chunky-17cm-wrist` |
| [`green-lantern-ring/`](green-lantern-ring/) | Lantern power ring, US 10 | `single-colour` | none yet |
| [`phone-valet-tray/`](phone-valet-tray/) | Nightstand valet tray with phone dock | none yet | none yet |
| [`printer-and-pc-upgrades/`](printer-and-pc-upgrades/) | Upgrades for the printer and PC | none yet | none yet |
