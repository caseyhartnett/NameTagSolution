# AGENTS.md — Studio NameTags

Instructions for an AI agent helping someone make flat two-color shelf labels
with this folder. **This folder is self-contained on purpose:** it needs no other
project, repository, notes or context. Everything required is here, and nothing
outside this folder may be assumed, quoted or edited.

If this folder sits inside a larger design repository, that repository's own
instructions still rule for everything *outside* `NameTags/`. This file only
describes this project.

## What is being made

A flat label: a white plastic body with black lettering and an optional
pictogram flush in its face. Both materials start at Z=0 and print together as
one two-material object, face down, so all artwork is mirrored in the model and
reads correctly after flipping. Artwork is flush with the face — a filament
change at a single height cannot produce it; both colors share the first layers.

## Fixed studio settings

**The lettering stays the same size; the plastic width fits the text.** Width is
measured from real font metrics plus a side border. Never stretch, squeeze or
shrink the font to reach a width, and never "make it fit" by clipping.

| Detail | Value | Where |
|---|---|---|
| Font | Liberation Sans Bold, bundled | `fonts/`, `label_font` |
| Lettering size | 16.69 mm | `font_size_mm` |
| Height, all labels equal | 50.8 mm | `height_mm` |
| Total thickness | 2 mm | `thickness_mm` |
| Black face / white backing | 0.4 / 1.6 mm | `face_thickness_mm` |
| Lettering grown for print | 0.12 mm per side | `text_expansion_mm` |
| Borders | 3.35 mm sides, at least 3 mm top/bottom | `side_border_mm`, `vertical_border_mm` |
| Plate packing | 256 mm bed, 6 mm margin, 3 mm gaps | `tools/nametags.py` |
| Printing | PLA, 0.4 mm nozzle, 0.2 mm layers, supports off | — |

Changing any of these changes every label. Do it only when asked, and report the
old and new values.

## Layout

| Path | What it is |
|---|---|
| `name_tags.scad` | All the geometry. Source of truth; edit here, never the STLs. |
| `name_tags.json` | Customizer presets loaded automatically. Fictional samples only. |
| `fonts/` | Bundled font, its SIL OFL licence and `fonts.conf`. Never modify, rename or replace it. |
| `examples/` | Fictional CSV and JSON showing every supported field. |
| `reprints/` | Ready-to-open sample plates ZIP and preview for someone with no tools. |
| `tools/nametags.py` | CLI: `doctor`, `csv`, `build`, `package`. |
| `tools/mesh.py`, `tools/plates.py` | Mesh audit and plate packing behind `build`. |
| `tests/` | The checks that define "working". |
| `README.md` | Human-facing guide; keep it true when behaviour changes. |
| `build/`, `private/` | Git-ignored. Renders and logs; real names if any. |

All commands below run from this folder.

## Start every session here

```text
python tools/nametags.py doctor
python -m unittest discover tests
```

`doctor` prints the OpenSCAD version and then `OK: local font hash, textmetrics
feature, fictional John Smith test geometry and print orientation`. If it fails,
stop and fix the environment first: OpenSCAD is missing or too old, `textmetrics`
is unavailable, or the bundled font was altered. Its failure text says which.

## Three ways to serve a request

**1. "Just print some labels."** No OpenSCAD, no Python. Point them at
`reprints/fake_names_plates.zip`; each numbered `.3mf` is one plate, already
two-material. They choose their own printer profile and confirm body = white,
face = black.

**2. One label or phrase, no Python.** Open `name_tags.scad` with `textmetrics`
enabled (Preferences → Features; CLI `--enable=textmetrics`). Use `part =
preview` to look at it; export `part = body` and `part = face` separately with
identical text and settings, then import both as one multi-material object.

**3. Many labels from a list.**

```text
python -m pip install -r requirements.txt
python tools/nametags.py csv examples/fake_names.csv --out build/my_labels.json
python tools/nametags.py build --presets build/my_labels.json --out build/my_labels
```

Open `build/my_labels/plates/plate_NN.3mf`, one plate at a time. A build writes
`tags/<id>/` (body STL, face STL, front and bed PNGs, `validation.json`),
`plates/`, `plates.json`, `all_labels.png`, a `plates.zip`, and a `source/`
snapshot that can rebuild itself.

## Rules while doing it

- Text is one or two lines. A second text line **or** a pictogram, never both.
- Pictograms are only `none`, `money_bag`, `smile` and `flower`. A literal emoji
  is accepted by `csv` under the default `symbols` policy and maps to one of
  those; any other symbol character is rejected for review — ask, do not
  silently drop it.
- Width is automatic. `width_override_mm` exists for exact reproductions and is
  still checked against the glyphs; it can never be narrower than the text.
- A phrase too wide for the 244 mm usable bed, or too tall, gets split over two
  lines or shortened. Reducing `font_size_mm` breaks the common lettering size,
  so only do it when asked.
- CSV headers are exactly `First Name`, `label`, `label,line2,symbol` or
  `label,line2,symbol,width_mm`, plus one optional `sample_data` column holding
  `FAKE_NAMES`. Duplicate names stay separate labels; accents are preserved.
- Existing output is never overwritten: `csv --out` and `build --out` refuse an
  existing path. Build into a new folder rather than deleting the old one.
- Preset ids are lowercase `snake_case`. Presets may set only the parameters the
  tool allows and must keep `input_source = customizer` and `mode = single`.
- Vanilla OpenSCAD only: no extra libraries, no BOSL2, no other CAD kernel.
- Exports contain models and arrangements, never G-code or a printer profile.

## Before saying it is done

1. `python -m unittest discover tests` passes and `doctor` is OK.
2. Look at the images. `front.png` must read normally, `bed.png` must be
   mirrored, and `all_labels.png` plus each plate PNG must show every label
   complete, unclipped, with its border intact. Viewing the render is part of the
   check, not a formality.
3. Read `validation.json` and `plates.json`: every mesh watertight, flat at Z=0,
   inside 256 mm, with complementary body/face volumes. A clean render does not
   prove a watertight mesh.
4. Report: how many labels and plates, each label's size, the tallest and widest
   label, thickness and face depth, where the files are, which parts or presets
   were exported, and what is still unverified. Physical printing has never been
   tested here — say so instead of implying a trial.

## Data and privacy

Bundled sample data is fictional and marked as such in the CSV, JSON and code.
Keep it that way. Real rosters, real names and anything personal belong in
`private/` or `build/`, both git-ignored, and never in `examples/`,
`name_tags.json`, the README or a commit. When someone supplies a real list,
convert and build it under `private/` and leave the tracked samples untouched.

## Keeping the folder shareable

The whole point of this project is that another person can take it over:

```text
python tools/nametags.py package --out <path>.zip
```

The archive contains the shareable files only — `build/`, `private/`, `.venv/`,
`__pycache__` and `*.pyc` are always excluded — and it prints the file count,
size and SHA-256. If you change behaviour, update `README.md` and this file in
the same pass, then re-run the tests and `package` before handing it on.