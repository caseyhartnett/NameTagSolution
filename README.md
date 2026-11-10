# Studio NameTags

A self-contained project for black-and-white shelf names, studio labels and
short phrases. Copy or share this entire `NameTags/` folder — everything except
the local `build/` scratch folder, which is where your own renders land (see
[Share or hand over this folder](#share-or-hand-over-this-folder)).

**All included names are fictional common placeholders, not a roster of real people.**

## Basic details

**The lettering stays the same size. The plastic width changes to fit the text.**

| Detail | Studio setting |
|---|---|
| Font | Bundled **Liberation Sans Bold**, **16.69 mm** font size |
| Label size | Variable width × **50.8 mm / 2 inches high** × **2 mm thick** |
| Colors | **White body, black lettering/artwork** |
| Face and backing | **0.4 mm black face** (two 0.2 mm layers) on a **1.6 mm white backing**; `face_thickness_mm` takes 0.4–2 mm, e.g. 0.8 for a heavier face |
| Orientation | **Face down**; artwork is already mirrored to read correctly after flipping |
| Print settings | **PLA, 0.4 mm nozzle, 0.2 mm layers, supports off** |
| Borders | About **3.35 mm at the sides**, at least **3 mm above/below** the artwork |
| Batch arrangement | **256 × 256 mm bed**, **6 mm edge clearance**, **3 mm gaps** |

For example, the fictional labels **John Smith** and **Jane Doe** have different
widths while retaining the same lettering size, height and thickness.

Both colors print within the first layers. Use a two-color printing workflow;
**one filament change at a single height cannot make this face.**

## What is included and what you need

| What you want to do | Use these files | What you need |
|---|---|---|
| **Print the fictional sample tags** | [Ready-to-open plate ZIP](reprints/fake_names_plates.zip) | Slicer and two-color printer. **No OpenSCAD or Python.** |
| **Make a new name or phrase** | [name_tags.scad](name_tags.scad), [name_tags.json](name_tags.json), bundled `fonts/` | OpenSCAD development build with **textmetrics**, then your slicer. **No Python.** |
| **Make many labels from CSV or JSON** | [examples/](examples/), [tools/nametags.py](tools/nametags.py), [requirements.txt](requirements.txt) | OpenSCAD, Python **3.10+** with the listed packages, then your slicer. |

Here is how the pieces connect:

```text
One label or JSON settings → SCAD builds the shape → body + face STLs → slicer → printer
CSV list → Python converts it to JSON, runs SCAD and packs plates → 3MF files → slicer → printer
```

**SCAD** defines the geometry. **JSON** saves the text and settings. **CSV** is
a convenient list of labels; OpenSCAD cannot read it directly. The **Python
tool** converts CSV, renders labels and arranges plates. Each **3MF** keeps a
label's white body and black face aligned for the slicer.

## Print the included fictional samples

1. Extract [fake_names_plates.zip](reprints/fake_names_plates.zip).
2. Open its numbered `.3mf` files separately in your slicer. Select your
   printer/profile and check that body = white and face = black.
3. Inspect the first layers, slice and print using the settings above.

The 12 sample rows include common fictional names, a duplicate John Smith, an
accented name, studio phrases and three pictograms. [Preview the samples](reprints/fake_names_preview.png).
The files contain models and arrangements, not G-code.

## Make one label in OpenSCAD

1. Use an OpenSCAD development build with **textmetrics**. In Preferences →
   Features, enable **textmetrics**, then reopen the file if needed.
2. Open [name_tags.scad](name_tags.scad). In the Customizer set
   `input_source = customizer`, `mode = single`, `part = preview`.
3. Enter **label_text** and leave **width_override_mm = 0** for automatic
   width. A phrase such as `Studio tools` stays on one line.
4. For two lines, fill **second_line_text**. Alternatively, JSON/SCAD strings
   can contain one `\n` newline. For a money bag, smile or flower, choose
   **symbol** and leave the second text line empty. Use these pictograms
   instead of pasting color emoji into the text field.
5. Press **F6** and inspect the result. If it is too wide or tall, use a second
   line, increase the height or deliberately reduce **font_size_mm**.
6. Set `part = body`, render and export an STL; repeat with `part = face`
   without changing the text/settings. Import both together as **one
   multi-material object**. Preserve their alignment and keep all black
   letters/islands in the black part. Assign white/black and print face down.

## Enter several labels without Python

### Paste a list into the SCAD file

Under `Hidden`, replace `pasted_labels` with your list:

```openscad
pasted_labels = [
    "John Smith", "Jane Doe", "Studio tools",
    ["Kiln", "Room", "none", 0],
    ["Robin Miller", "", "flower", 0]
];
```

A string is one label. The optional record is
`[first_line, second_line, symbol, width_override_mm]`; zero means automatic.
Choose `input_source = pasted_list` and **label_index**: 0 is the first entry,
1 the second, and so on. Export each selected body/face pair as above.
`mode = list_layout` previews the list on one bed; it is preview-only.

### Use saved JSON presets

The included **name_tags.json** matches the SCAD filename, so its example
presets appear in the Customizer. Choose a sample such as `row_001_john_smith`
or `row_007_studio_tools`, then export as above. Save your own settings through
the Customizer's preset controls.

To use another JSON collection, preserve your current JSON, put the new file
beside the SCAD with the **same base filename**, then reopen the SCAD.
[examples/fake_names.json](examples/fake_names.json) keeps the fictional sample
collection. Its metadata explicitly marks the names as fictional.

## Build CSV or JSON batches with Python

From the `NameTags/` folder, create a virtual environment:

```text
python -m venv .venv
```

Activate it: Windows PowerShell `.venv\Scripts\Activate.ps1`;
macOS/Linux `source .venv/bin/activate`. Then run:

```text
python -m pip install -r requirements.txt
python tools/nametags.py doctor
python tools/nametags.py csv examples/fake_names.csv --out build/my_labels.json
python tools/nametags.py build --presets build/my_labels.json --out build/my_labels
```

`doctor` checks OpenSCAD and the bundled font. The CSV command creates JSON;
the build command uses that JSON to produce STLs, previews and arranged 3MFs.
Open the numbered files in the output's `plates/` folder in your slicer.
The output also includes a compact `plates.zip` and a repeatable source copy.

A CSV can contain just a `label` column, or these columns:

```csv
label,line2,symbol
Studio tools,,none
Kiln,Room,none
Robin Miller,,flower
```

Optional fourth column `width_mm` sets an exact width; omit it for automatic
fitting. The original `First Name` header is also accepted. Duplicate names
remain separate tags, and Unicode such as José Smith is preserved. Known emoji map
to the three black pictograms; unknown symbols are rejected for review.

**To build the supplied fictional samples directly from JSON:**

```text
python tools/nametags.py build --presets examples/fake_names.json --out build/fake_names
```

The optional `sample_data` column marks every supplied CSV row `FAKE_NAMES`.
It is metadata, not printable text, and is preserved in the generated JSON.
For your own labels, remove that column or blank its values to remove the fake-data label.
See [examples/README.md](examples/README.md) for the fictional-data notice.

Add `--split-first-space` to the CSV command only if you want two lines, such
as `John` / `Smith`; ordinary phrases otherwise remain on one line. Existing
output paths are refused: choose a new folder for a revised build.

## Share or hand over this folder

Everything here is meant to survive the person who built it: the SCAD file, the
fictional sample data, the bundled font, the Python batch tool and its tests are
self-contained, so the folder can be copied to a USB stick, a studio drive or
another computer and used as-is.

`build/` is local scratch (rendered STLs, plates, logs). It is ignored by
`.gitignore` and never belongs in a hand-over, and it may hold a real studio
batch you built for yourself. Real rosters belong in `private/`, which is
ignored too — never in `examples/` or `name_tags.json`, which stay fictional.

Build a clean archive from this folder:

```text
python tools/nametags.py package --out ../name_tags_standalone.zip
python tools/nametags.py package --out ../name_tags_standalone.zip --overwrite
```

The archive always excludes `build/`, `private/`, `.venv/`, `__pycache__/` and
`*.pyc`, so local data can never be shared by accident. It prints the file
count, size and SHA-256, and extracts to a single `NameTags/` folder. Copying
the folder by hand is equally fine — just delete `build/` first.

Before handing it over, from this folder:

```text
python -m unittest discover tests      # packaging, data and render checks
python tools/nametags.py doctor        # OpenSCAD, bundled font, test geometry
```

What the next person needs: an OpenSCAD **development** build with
**textmetrics** for anything in the Customizer, Python **3.10+** with
`requirements.txt` installed only if they make batch plates, and a two-color
printer for the tags themselves. The font's SIL Open Font License travels in
`fonts/LICENSE.txt` with the bundled TTF.

`AGENTS.md` is written for an AI coding assistant that helps the next person:
it records the fixed settings, the commands, the rules and the checks, and it
needs nothing outside this folder. `CLAUDE.md` exists only to point Claude Code
at the same file. Keep both with the project.

## Notes

- Tested OpenSCAD: **2025.12.30 development build**. OpenSCAD 2021.01 lacks
  this workflow. Python commands enable textmetrics automatically. If needed,
  choose the executable with `python tools/nametags.py --openscad "/path/to/openscad" doctor`
  or the **OPENSCAD_PATH** environment variable.
- Widths round up to 0.1 mm. Leave **width_override_mm = 0** for new text; an
  explicit positive override must still fit the artwork.
- The bundled font is unmodified Liberation Sans Bold 2.00.1, with its
  [SIL Open Font License](fonts/LICENSE.txt). Changing fonts changes the result.
- Arranged files contain no printer profile, brim or purge-tower reservation.
  Verify your actual spool assignments and leave any extra space your printer needs.
- Run checks with `python -m unittest discover tests -v`. The standalone build
  was checked with the fictional sample set; physical printing remains untested.
