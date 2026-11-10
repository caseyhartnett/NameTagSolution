/*
    Studio NameTags — standalone two-color labels, millimeters of plastic.
    All bundled personal names are FICTIONAL common placeholders, not real people.

    OpenSCAD 2025.12.30 development build was tested. Enable textmetrics in
    Preferences > Features, or pass --enable=textmetrics on the command line.
    Width follows actual font metrics; letters NEVER shrink to fit a name.
    Read README.md for no-code GUI steps, pasted lists, JSON and CSV workflows.

    Export body and face as ONE aligned multi-material object. Both start at
    Z=0; artwork is mirrored for face-down printing. White body, black face;
    0.4 mm nozzle, 0.2 mm layers, PLA, no supports. No height-only color swap.
*/
use <fonts/LiberationSans-Bold.ttf>

/* [Input] */
// One name or complete phrase; spaces stay on ONE line
label_text = "John Smith";
// Optional second line; alternatively put one newline in label_text
second_line_text = "";
// Optional simple black pictogram on the second line
symbol = "none"; // [none, money_bag, smile, flower]
// Choose one Customizer label or an entry from pasted_labels below
input_source = "customizer"; // [customizer, pasted_list]
// Zero-based entry to select from pasted_labels
label_index = 0; // [0:1:999]

/* [Output] */
// Single printable label or a preview of the pasted list
mode = "single"; // [single, list_layout]
// Export the two printable parts separately; preview shows both colors
part = "preview"; // [preview, body, face]

/* [Physical Size] */
// Exact lettering size; width changes to fit the text (mm)
font_size_mm = 16.69; // [8:0.01:32]
// All complete labels have this height (mm)
height_mm = 50.8; // [20:0.1:100]
// Total plastic thickness (mm)
thickness_mm = 2; // [1.5:0.1:6]
// Black face thickness; the white backing is the remainder (mm)
face_thickness_mm = 0.4; // [0.4:0.1:2]
// Minimum horizontal border around the artwork (mm)
side_border_mm = 3.35135817527771; // [3:0.01:12]
// Minimum measured top/bottom artwork clearance (mm)
vertical_border_mm = 3; // [3:0.1:12]
// Grow each side of the lettering for sturdy printing (mm)
text_expansion_mm = 0.12; // [0.1:0.01:0.3]
// Zero = automatic width; positive = explicit exact reproduction width (mm)
width_override_mm = 0; // [0:0.1:244]
// Space between complete labels in list preview (mm)
gap_mm = 3; // [3:0.5:12]

/* [Hidden] */
// EDIT/PASTE THIS LIST. Strings are one-line phrases. Optional records are
// [first_line, second_line, symbol, width_override_mm]. Nothing is evaluated
// as code by the CSV converter. Choose input_source=pasted_list, label_index=N.
// FICTIONAL sample names; replace these with your own labels.
pasted_labels = ["John Smith", "Jane Doe", "Studio tools", ["Robert", "Brown", "none", 0]];
label_font = "Liberation Sans:style=Bold";
PRINT_BED_MM = 256;
BED_MARGIN_MM = 6;
FONT_ASCENDER_PER_SIZE = 1.006;
FONT_DESCENDER_PER_SIZE = 0.295;
BASELINE_PITCH_PER_SIZE = 1.3;
epsilon = 0.01;
smoothness = $preview ? 48 : 128;
metrics_probe = textmetrics("M", size = font_size_mm, font = label_font, halign = "center");
has_metrics = !is_undef(metrics_probe);
chosen_record = input_source == "pasted_list" && label_index >= 0 && label_index < len(pasted_labels)
    ? normalize_record(pasted_labels[label_index]) : normalize_record([label_text, second_line_text, symbol, width_override_mm]);
records = mode == "list_layout" ? [for (item = pasted_labels) normalize_record(item)] : [chosen_record];
widths_mm = has_metrics ? [for (record = records) record_width(record)] : [1];
positions_mm = has_metrics ? place_records(widths_mm) : [[0, 0]];

assert(has_metrics,
    "Enable textmetrics: OpenSCAD Preferences > Features > textmetrics, then reopen; CLI: --enable=textmetrics. Use a development build supporting this feature.");
assert(input_source == "customizer" || input_source == "pasted_list", "Unknown input source");
assert(mode == "single" || mode == "list_layout", "Unknown mode");
assert(part == "preview" || part == "body" || part == "face", "Unknown part");
assert(mode != "list_layout" || part == "preview", "List layout is preview-only; export single body/face pairs or use the Python plate builder");
assert(input_source != "pasted_list" || (label_index >= 0 && label_index < len(pasted_labels)), "label_index is outside pasted_labels");
assert(len(records) > 0 && height_mm > 0 && height_mm <= PRINT_BED_MM - 2 * BED_MARGIN_MM, "Invalid label height or empty list");
assert(font_size_mm > 0 && text_expansion_mm >= 0.1 && side_border_mm >= 3 && vertical_border_mm >= 3, "Keep sturdy lettering and >=3 mm borders");
assert(face_thickness_mm >= 0.4 && thickness_mm - face_thickness_mm >= 1.2, "Keep >=0.4 mm face and >=1.2 mm backing");
assert(gap_mm >= 3, "Keep >=3 mm between labels");
for (index = [0 : len(records) - 1]) {
    record = records[index];
    assert(is_string(record[0]) && len(record[0]) > 0, "Each label needs nonempty first-line text");
    assert(record[2] == "none" || record[2] == "money_bag" || record[2] == "smile" || record[2] == "flower", "Unknown symbol");
    assert(record[1] == "" || record[2] == "none", "Use a second text line OR pictogram, not both");
    assert(len(search("\n", record[0])) == 0 && len(search("\n", record[1])) == 0, "Only one or two text lines are supported");
    bounds = record_bounds(record);
    assert(bounds[0] >= -widths_mm[index] / 2 + side_border_mm - 0.025
        && bounds[2] <= widths_mm[index] / 2 - side_border_mm + 0.025,
        "Explicit width is too narrow for this font/name; use automatic width or increase it");
    assert(bounds[1] >= vertical_border_mm && bounds[3] <= height_mm - vertical_border_mm,
        "Artwork is too tall. Increase height or explicitly reduce font size; text is never silently shrunk");
    assert(widths_mm[index] <= PRINT_BED_MM - 2 * BED_MARGIN_MM,
        "Label exceeds usable bed width; split the phrase over two lines or explicitly choose a smaller font");
    assert(positions_mm[index][1] + height_mm <= PRINT_BED_MM - BED_MARGIN_MM,
        "Pasted list needs more than one plate; select one label or use the Python batch builder");
    echo(str("LABEL ", index, ": ", record[0], " / ", record[1], "; size ", widths_mm[index], " x ", height_mm,
        " x ", thickness_mm, " mm; font ", font_size_mm, " mm; ", label_font));
}

// ======================================================================
// FUNCTIONS AND GEOMETRY
// ======================================================================
function string_slice(value, start, count, index = 0) = index >= count ? ""
    : str(value[start + index], string_slice(value, start, count, index + 1));
function normalize_record(item) = let(raw = is_string(item) ? [item, "", "none", 0] : item,
    breaks = search("\n", raw[0])) len(breaks) == 0 ? raw
    : assert(len(breaks) == 1 && raw[1] == "", "Use one embedded newline OR second_line_text")
        [string_slice(raw[0], 0, breaks[0]), string_slice(raw[0], breaks[0] + 1, len(raw[0]) - breaks[0] - 1), raw[2], raw[3]];
function line_count(record) = record[1] == "" && record[2] == "none" ? 1 : 2;
function lower_baseline(record) = height_mm / 2 - font_size_mm
    * (FONT_ASCENDER_PER_SIZE + FONT_DESCENDER_PER_SIZE + (line_count(record) - 1) * BASELINE_PITCH_PER_SIZE) / 2
    + font_size_mm * FONT_DESCENDER_PER_SIZE;
function text_bounds(value, baseline) = let(metrics = textmetrics(value, size = font_size_mm,
    font = label_font, halign = "center")) [metrics.position.x - text_expansion_mm,
    baseline + metrics.position.y - text_expansion_mm,
    metrics.position.x + metrics.size.x + text_expansion_mm,
    baseline + metrics.position.y + metrics.size.y + text_expansion_mm];
function combine_bounds(a, b) = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])];
function symbol_bounds(record) = let(base = lower_baseline(record) + 0.42 * font_size_mm,
    extent = record[2] == "flower" ? 0.505 : record[2] == "smile" ? 0.48 : 0.45)
    [-extent * font_size_mm, base - extent * font_size_mm, extent * font_size_mm, base + extent * font_size_mm];
function record_bounds(record) = let(base = lower_baseline(record), first = text_bounds(record[0],
    base + (line_count(record) - 1) * BASELINE_PITCH_PER_SIZE * font_size_mm))
    record[1] != "" ? combine_bounds(first, text_bounds(record[1], base))
    : record[2] != "none" ? combine_bounds(first, symbol_bounds(record)) : first;
function record_width(record) = let(bounds = record_bounds(record)) record[3] > 0 ? record[3]
    : ceil((2 * (max(abs(bounds[0]), abs(bounds[2])) + side_border_mm) - 0.000001) * 10) / 10;
function place_records(widths, index = 0, x_mm = BED_MARGIN_MM, y_mm = BED_MARGIN_MM) = index >= len(widths) ? []
    : x_mm + widths[index] > PRINT_BED_MM - BED_MARGIN_MM && x_mm > BED_MARGIN_MM
        ? place_records(widths, index, BED_MARGIN_MM, y_mm + height_mm + gap_mm)
        : concat([[x_mm, y_mm]], place_records(widths, index + 1, x_mm + widths[index] + gap_mm, y_mm));

module sturdy_text(value) {
    offset(r = text_expansion_mm, $fn = smoothness)
        text(value, size = font_size_mm, font = label_font, halign = "center");
}

module symbol_2d(which) {
    if (which == "smile") {
        difference() {
            circle(r = 0.48, $fn = smoothness);
            circle(r = 0.37, $fn = smoothness);
        }
        for (eye_x = [-0.17, 0.17]) translate([eye_x, 0.14]) circle(r = 0.065, $fn = smoothness);
        intersection() {
            difference() {
                circle(r = 0.28, $fn = smoothness);
                circle(r = 0.17, $fn = smoothness);
            }
            translate([-0.35, -0.35]) square([0.7, 0.30]);
        }
    } else if (which == "flower") {
        difference() {
            union() {
                for (angle_deg = [0 : 72 : 288]) rotate(angle_deg) translate([0, 0.27]) circle(r = 0.235, $fn = smoothness);
                circle(r = 0.28, $fn = smoothness);
            }
            circle(r = 0.12, $fn = smoothness);
        }
    } else if (which == "money_bag") {
        difference() {
            union() {
                hull() {
                    translate([-0.17, -0.20]) circle(r = 0.23, $fn = smoothness);
                    translate([0.17, -0.20]) circle(r = 0.23, $fn = smoothness);
                    translate([0, 0.14]) circle(r = 0.18, $fn = smoothness);
                }
                polygon([[-0.16, 0.15], [-0.25, 0.45], [0.25, 0.45], [0.16, 0.15]]);
            }
            translate([0, -0.29]) text("$", size = 0.55, font = label_font, halign = "center");
        }
    }
}

module readable_art(record, width_mm) {
    translate([width_mm / 2, lower_baseline(record)]) {
        translate([0, (line_count(record) - 1) * BASELINE_PITCH_PER_SIZE * font_size_mm]) sturdy_text(record[0]);
        if (record[1] != "") sturdy_text(record[1]);
        if (record[2] != "none") translate([0, font_size_mm * 0.42])
            scale([font_size_mm, font_size_mm]) symbol_2d(record[2]);
    }
}
module print_art(record, width_mm) {
    translate([width_mm, 0]) mirror([1, 0]) readable_art(record, width_mm);
}
module body(record, width_mm) {
    difference() {
        cube([width_mm, height_mm, thickness_mm]);
        translate([0, 0, -epsilon]) linear_extrude(face_thickness_mm + epsilon) print_art(record, width_mm);
    }
}
module face(record, width_mm) {
    linear_extrude(face_thickness_mm) print_art(record, width_mm);
}

// ======================================================================
// RENDER — each single part is flat at Z=0, already in print orientation.
// ======================================================================
for (index = [0 : len(records) - 1])
    translate(mode == "single" ? [0, 0, 0] : [positions_mm[index][0], positions_mm[index][1], 0]) {
        if (part == "body" || part == "preview") color("White") body(records[index], widths_mm[index]);
        if (part == "face" || part == "preview") color("Black") face(records[index], widths_mm[index]);
    }
