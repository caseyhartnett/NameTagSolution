# Fictional examples

**Fictional sample data; not a roster of real people.** Names such as John
Smith, Jane Doe, Mary Jones and Robert Brown are common placeholders. Any
resemblance to a person is incidental. The studio labels are also examples.

- `fake_names.csv` contains 12 sample rows. Every row has
  `sample_data = FAKE_NAMES` inside the CSV itself. This is metadata and does
  not print on a tag. The optional column is understood by the converter.
- `fake_names.json` contains the matching OpenSCAD presets and explicitly
  marks `fictional_sample_data: true`. `../name_tags.json` is the same data,
  named for automatic loading by the OpenSCAD Customizer.
- The duplicate John Smith row demonstrates keeping two separate tags.
- José Smith demonstrates an accented character. The three pictograms,
  a two-line studio label and a one-line phrase exercise the other inputs.

Replace these samples with your own labels when building your own set. Remove
the optional `sample_data` column (or blank its values) so your own labels are
not marked as fictional in the output.
