"""Portable plate packing and exact, two-material 3MF assemblies."""
import math
import xml.etree.ElementTree as ET
import zipfile
from mesh import read_triangles
NS="http://schemas.microsoft.com/3dmanufacturing/core/2015/02"
ET.register_namespace("",NS)

def intersects(a, b):
    return a[0] < b[0]+b[2]-1e-7 and b[0] < a[0]+a[2]-1e-7 and a[1] < b[1]+b[3]-1e-7 and b[1] < a[1]+a[3]-1e-7


def pack(entries, bed_mm=256, margin_mm=5, gap_mm=3, allow_rotation=True):
    """Deterministic MaxRects best-short-side-fit; try several input orders."""
    if bed_mm <= 0 or margin_mm < 0 or gap_mm < 0 or 2 * margin_mm >= bed_mm:
        raise ValueError("Invalid plate clearance settings")
    usable = bed_mm - 2 * margin_mm
    if len({entry["id"] for entry in entries}) != len(entries):
        raise ValueError("Duplicate batch IDs")
    for entry in entries:
        if min(entry["width_mm"], entry["height_mm"]) <= 0 or max(entry["width_mm"], entry["height_mm"]) > usable:
            raise ValueError(f"Badge does not fit usable plate: {entry['id']}")
    def attempt(ordered):
        plates = []
        for entry in ordered:
            choices = []
            for index, plate in enumerate(plates):
                for free in plate["free"]:
                    for angle in ((0, 90) if allow_rotation else (0,)):
                        width, height = (entry["width_mm"], entry["height_mm"])[::(-1 if angle else 1)]
                        width += gap_mm
                        height += gap_mm
                        if width <= free[2]+1e-7 and height <= free[3]+1e-7:
                            choices.append((min(free[2]-width, free[3]-height), max(free[2]-width, free[3]-height),
                                index, free[1], free[0], angle, width, height))
            if not choices:
                plates.append(dict(free=[(margin_mm, margin_mm, usable+gap_mm, usable+gap_mm)], placements=[]))
                plate_index = len(plates)-1
                angle = 0
                x_mm = y_mm = margin_mm
                width, height = entry["width_mm"]+gap_mm, entry["height_mm"]+gap_mm
            else:
                _, _, plate_index, y_mm, x_mm, angle, width, height = min(choices)
            plate = plates[plate_index]
            used = (x_mm, y_mm, width, height)
            split = []
            for free in plate["free"]:
                if not intersects(free, used):
                    split.append(free)
                    continue
                fx, fy, fw, fh = free
                if fx < x_mm: split.append((fx, fy, x_mm-fx, fh))
                if x_mm+width < fx+fw: split.append((x_mm+width, fy, fx+fw-x_mm-width, fh))
                if fy < y_mm: split.append((fx, fy, fw, y_mm-fy))
                if y_mm+height < fy+fh: split.append((fx, y_mm+height, fw, fy+fh-y_mm-height))
            plate["free"] = [a for i, a in enumerate(split) if not any(i != j and a != b
                and a[0] >= b[0] and a[1] >= b[1] and a[0]+a[2] <= b[0]+b[2]+1e-7
                and a[1]+a[3] <= b[1]+b[3]+1e-7 for j, b in enumerate(split))]
            plate["placements"].append(dict(id=entry["id"], x_mm=x_mm, y_mm=y_mm, rotation_deg=angle,
                width_mm=width-gap_mm, height_mm=height-gap_mm))
        return [plate["placements"] for plate in plates]
    orders = [entries, sorted(entries, key=lambda e: (-e["width_mm"]*e["height_mm"], e["id"])),
        sorted(entries, key=lambda e: (-e["width_mm"], e["id"])), sorted(entries, key=lambda e: (e["width_mm"], e["id"]))]
    plates = min((attempt(order) for order in orders), key=len)
    validate_placements(plates, entries, bed_mm, margin_mm, gap_mm)
    return plates


def validate_placements(plates, entries, bed_mm, margin_mm, gap_mm):
    seen = []
    by_id = {entry["id"]: entry for entry in entries}
    for plate in plates:
        for index, p in enumerate(plate):
            seen.append(p["id"])
            original = by_id[p["id"]]
            expected = (original["width_mm"], original["height_mm"])[::(-1 if p["rotation_deg"] else 1)]
            assert all(abs(a-b) < 1e-6 for a,b in zip(expected, (p["width_mm"], p["height_mm"])))
            assert margin_mm-1e-6 <= p["x_mm"] and margin_mm-1e-6 <= p["y_mm"]
            assert p["x_mm"]+p["width_mm"] <= bed_mm-margin_mm+1e-6
            assert p["y_mm"]+p["height_mm"] <= bed_mm-margin_mm+1e-6
            for other in plate[index+1:]:
                assert not intersects((p["x_mm"],p["y_mm"],p["width_mm"]+gap_mm,p["height_mm"]+gap_mm),
                    (other["x_mm"],other["y_mm"],other["width_mm"]+gap_mm,other["height_mm"]+gap_mm))
    assert sorted(seen) == sorted(by_id), "Lost or duplicated CSV rows in packing"


def transform(placement):
    if placement["rotation_deg"] == 90:
        return [0, 1, 0, -1, 0, 0, 0, 0, 1, placement["x_mm"]+placement["width_mm"], placement["y_mm"], 0]
    return [1, 0, 0, 0, 1, 0, 0, 0, 1, placement["x_mm"], placement["y_mm"], 0]


def write_plate(path, placements, people_root):
    model = ET.Element("model", xmlns=NS, unit="millimeter", attrib={"xml:lang": "en-US"})
    resources = ET.SubElement(model, "resources")
    colors = ET.SubElement(resources, "basematerials", id="1")
    for name, color in (("White body", "#FFFFFFFF"), ("Black name face", "#000000FF")):
        ET.SubElement(colors, "base", name=name, displaycolor=color)
    config = ET.Element("config")
    build = ET.SubElement(model, "build")
    expected = []
    for index, placement in enumerate(placements):
        first_id = 2+index*3
        parent_id = first_id+2
        assembly_config = ET.SubElement(config, "object", id=str(parent_id))
        ET.SubElement(assembly_config, "metadata", key="name", value=placement["id"])
        for offset, layer in enumerate(("body", "face")):
            source = people_root / placement["id"] / f"name_{layer}.stl"
            triangles = read_triangles(source)
            obj = ET.SubElement(resources, "object", id=str(first_id+offset), type="model",
                name=f"{placement['id']} / {layer}", pid="1", pindex=str(offset))
            mesh = ET.SubElement(obj, "mesh")
            vertices = ET.SubElement(mesh, "vertices")
            faces = ET.SubElement(mesh, "triangles")
            indices = {}
            for triangle in triangles:
                for vertex in triangle:
                    if vertex not in indices:
                        indices[vertex] = len(indices)
                        ET.SubElement(vertices, "vertex", **dict(zip("xyz",map(repr,vertex))))
                ET.SubElement(faces, "triangle", **{f"v{i+1}": str(indices[v]) for i,v in enumerate(triangle)})
            part = ET.SubElement(assembly_config, "part", id=str(first_id+offset), subtype="normal_part")
            ET.SubElement(part, "metadata", key="name", value=("White body" if not offset else "Black name face"))
            ET.SubElement(part, "metadata", key="extruder", value=str(offset+1))
            expected.append((first_id+offset, source))
        assembly = ET.SubElement(resources, "object", id=str(parent_id), type="model", name=placement["id"])
        components = ET.SubElement(assembly, "components")
        for object_id in (first_id, first_id+1):
            ET.SubElement(components, "component", objectid=str(object_id))
        ET.SubElement(build, "item", objectid=str(parent_id), transform=" ".join(map(str,transform(placement))))
    types = '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types"><Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/><Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/><Default Extension="config" ContentType="application/xml"/></Types>'
    rels = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rel0" Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel" Target="/3D/3dmodel.model"/></Relationships>'
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as package:
        package.writestr("[Content_Types].xml", types)
        package.writestr("_rels/.rels", rels)
        package.writestr("3D/3dmodel.model", ET.tostring(model, encoding="utf-8", xml_declaration=True))
        package.writestr("Metadata/model_settings.config", ET.tostring(config, encoding="utf-8", xml_declaration=True))
    return validate_plate(path, placements, expected)


def validate_plate(path, placements, expected):
    ns = {"m": NS}
    with zipfile.ZipFile(path) as package:
        assert package.testzip() is None
        model = ET.fromstring(package.read("3D/3dmodel.model"))
        assert model.attrib["unit"] == "millimeter"
        for object_id, source in expected:
            obj = model.find(f"m:resources/m:object[@id='{object_id}']", ns)
            vertices = [tuple(float(v.attrib[c]) for c in "xyz") for v in obj.findall("m:mesh/m:vertices/m:vertex", ns)]
            triangles = [tuple(vertices[int(t.attrib[c])] for c in ("v1","v2","v3")) for t in obj.findall("m:mesh/m:triangles/m:triangle", ns)]
            assert triangles == read_triangles(source), "3MF changed original material coordinates"
        items = model.findall("m:build/m:item",ns)
        assert len(items) == len(placements)
        for index, (item, placement) in enumerate(zip(items, placements)):
            assert list(map(float,item.attrib["transform"].split())) == transform(placement)
            obj = model.find(f"m:resources/m:object[@id='{item.attrib['objectid']}']",ns)
            assert [int(c.attrib["objectid"]) for c in obj.findall("m:components/m:component",ns)] == [2+index*3,3+index*3]
        config = ET.fromstring(package.read("Metadata/model_settings.config"))
        assert len(config.findall("object")) == len(placements)
        for obj in config.findall("object"):
            assert [p.find("metadata[@key='extruder']").attrib["value"] for p in obj.findall("part")] == ["1","2"]
    # Independent standards parser, including the actual build transforms.
    import lib3mf
    wrapper = lib3mf.get_wrapper()
    parsed = wrapper.CreateModel()
    reader = parsed.QueryReader("3mf")
    reader.ReadFromFile(str(path.resolve()))
    warnings = [reader.GetWarning(i) for i in range(reader.GetWarningCount())]
    if warnings:
        raise ValueError(f"lib3mf warnings: {warnings}")
    iterator = parsed.GetBuildItems()
    count = 0
    while iterator.MoveNext():
        count += 1
    assert count == len(placements)
    return dict(assemblies=count, material_meshes=len(expected), exact_stl_mesh_roundtrip=True,
        lib3mf_warnings=warnings, logical_filament_slots=[1,2], printer_profile=False)


