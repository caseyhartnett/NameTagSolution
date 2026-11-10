"""Standalone CSV -> OpenSCAD presets -> checked two-material 3MF plates.

Run from this project's root; no parent repository or network service is used.
Bundled names are fictional common placeholders, not a roster of real people.
"""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from collections import Counter
import csv
import functools
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import unicodedata
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(Path(__file__).resolve().parent))
from mesh import read_triangles, measure
from plates import pack, write_plate

FONT_SHA256 = "d723d5a272970aedf296ef6fc628180df6074bce7769701ea9e0d222c052668c"
FAKE_NOTICE = "Fictional sample data; not a roster of real people."
SYMBOLS = {"\U0001f4b0":"money_bag","\U0001f642":"smile","\U0001f338":"flower"}
ALLOWED = {"label_text","second_line_text","symbol","input_source","label_index","mode","part",
    "font_size_mm","height_mm","thickness_mm","face_thickness_mm","side_border_mm",
    "vertical_border_mm","text_expansion_mm","width_override_mm","gap_mm"}


def save_json(path,value):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")


def openscad_path(explicit=None):
    supplied = explicit or os.environ.get("OPENSCAD_PATH")
    if supplied:
        path = Path(supplied).expanduser()
        if path.is_file(): return str(path.resolve())
        found = shutil.which(str(supplied))
        if found: return found
        raise FileNotFoundError(f"OpenSCAD executable not found: {supplied}")
    candidates = [shutil.which("openscad")]
    if os.name == "nt":
        program_files = Path(os.environ.get("ProgramFiles","C:/Program Files"))
        candidates = [str(program_files/folder/name) for folder in ("OpenSCAD (Nightly)","OpenSCAD")
            for name in ("openscad.com","openscad.exe")]+candidates
    else:
        candidates += ["/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD","/usr/local/bin/openscad","/usr/bin/openscad"]
    for candidate in candidates:
        if candidate and Path(candidate).is_file(): return candidate
    raise FileNotFoundError("Install an OpenSCAD development build supporting textmetrics; use --openscad PATH or OPENSCAD_PATH")


@functools.lru_cache(maxsize=4)
def backend_args(executable):
    result = subprocess.run([executable,"--help"],capture_output=True,text=True,timeout=30)
    return ["--backend=manifold"] if "--backend" in result.stdout+result.stderr else []


def render(executable,preset_path,preset_id,part,output,png=False,enable_metrics=True,defines=()):
    output = Path(output).resolve()
    output.parent.mkdir(parents=True,exist_ok=True)
    command = [executable,*(["--enable=textmetrics"] if enable_metrics else []),*backend_args(executable),
        "-o",str(output),"-p",str(Path(preset_path).resolve()),"-P",preset_id,"-D",f'part="{part}"']
    if png:
        command += ["--render","--autocenter","--viewall","--imgsize=1200,900","--colorscheme=Tomorrow"]
    else: command += ["--export-format=binstl"]
    for key,value in defines:
        command += ["-D",f"{key}={json.dumps(value,ensure_ascii=False)}"]
    command.append(str(ROOT/"name_tags.scad"))
    (ROOT/"build/font_cache").mkdir(parents=True,exist_ok=True)
    environment = dict(os.environ,FONTCONFIG_FILE=str(ROOT/"fonts/fonts.conf"))
    result = subprocess.run(command,cwd=ROOT,capture_output=True,text=True,encoding="utf-8",errors="replace",
        env=environment,timeout=600)
    log = result.stdout+result.stderr
    output.with_suffix(output.suffix+".log").write_text(log,encoding="utf-8")
    if result.returncode or re.search(r"^(WARNING|ERROR|DEPRECATED|Fontconfig error):",log,re.MULTILINE) or not output.is_file():
        raise RuntimeError("OpenSCAD render failed. A development build with textmetrics is required.\n"+log)
    return log


def slug(text):
    plain = unicodedata.normalize("NFKD",text).encode("ascii","ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+","_",plain).strip("_") or "label"


def csv_document(path,split_first_space=False,emoji_policy="symbols"):
    sets,rows,markers = {},[],[]
    with Path(path).open(encoding="utf-8-sig",newline="") as stream:
        reader=csv.DictReader(stream)
        headers=reader.fieldnames or []
        content_headers=[name for name in headers if name!="sample_data"]
        if len(set(headers))!=len(headers) or content_headers not in (["First Name"],["label"],["label","line2","symbol"],["label","line2","symbol","width_mm"]):
            raise ValueError("CSV header must be First Name, label, or label,line2,symbol[,width_mm]; optional sample_data marks FAKE_NAMES")
        for index,row in enumerate(reader,1):
            if None in row: raise ValueError(f"Extra CSV columns at data row {index}")
            marker=(row.get("sample_data") or "").strip()
            if marker not in ("","FAKE_NAMES"): raise ValueError(f"Unknown sample_data marker at row {index}")
            markers.append(marker)
            original=row.get("label",row.get("First Name"))
            if not isinstance(original,str) or not original.strip(): raise ValueError(f"Missing label at row {index}")
            text=original.strip()
            found=[SYMBOLS[c] for c in text if c in SYMBOLS]
            unsupported=[c for c in text if unicodedata.category(c).startswith("S") and c not in SYMBOLS]
            if unsupported: raise ValueError(f"Unreviewed symbols at row {index}: {unsupported}")
            if found and emoji_policy=="error": raise ValueError(f"Choose symbol handling for emoji at row {index}")
            text="".join(c for c in text if c not in SYMBOLS).strip()
            second=(row.get("line2") or "").strip()
            symbol=(row.get("symbol") or "none").strip()
            if found and emoji_policy=="symbols":
                if len(found)!=1 or symbol!="none": raise ValueError(f"Only one explicit pictogram is supported at row {index}")
                symbol=found[0]
            if split_first_space and not second and " " in text: text,second=text.split(" ",1)
            if not text or symbol not in ("none","money_bag","smile","flower") or (second and symbol!="none"):
                raise ValueError(f"Invalid text/second-line/symbol combination at row {index}")
            key=f"row_{index:03d}_{slug(original)}"
            params=dict(label_text=text,second_line_text=second,symbol=symbol)
            if row.get("width_mm"):
                width=float(row["width_mm"])
                if not math.isfinite(width) or not 0<width<=244: raise ValueError(f"Invalid width at row {index}")
                params["width_override_mm"]=width
            sets[key]=params
            rows.append(dict(id=key,original=original,**({"sample_data":marker} if marker else {})))
    if not sets: raise ValueError("CSV contains no labels")
    fictional=bool(markers) and all(marker=="FAKE_NAMES" for marker in markers)
    return dict(fileFormatVersion="1",parameterSets=sets,batch=dict(name=Path(path).stem,rows=rows,
        fictional_sample_data=fictional,**({"description":FAKE_NOTICE} if fictional else {}),
        line_policy="split_first_space" if split_first_space else "phrases_stay_on_one_line",emoji_policy=emoji_policy))


def validate_document(document):
    sets=document.get("parameterSets")
    if not isinstance(sets,dict) or not sets: raise ValueError("OpenSCAD JSON needs nonempty parameterSets")
    for key,params in sets.items():
        if not re.fullmatch(r"[a-z0-9]+(?:_[a-z0-9]+)*",key): raise ValueError("Preset IDs must be lowercase snake_case")
        if not isinstance(params,dict) or set(params)-ALLOWED: raise ValueError(f"Unknown parameters in {key}")
        if not isinstance(params.get("label_text"),str) or not params["label_text"].strip(): raise ValueError(f"Missing label_text in {key}")
        if params.get("input_source","customizer")!="customizer" or params.get("mode","single")!="single":
            raise ValueError("Batch presets must select single Customizer labels")
    return sets


def audit(path):
    triangles=read_triangles(Path(path))
    edges,directed=Counter(),Counter()
    for triangle in triangles:
        for a,b in zip(triangle,triangle[1:]+triangle[:1]):
            edges[tuple(sorted((a,b)))]+=1
            directed[(a,b)]+=1
    volume,area,low,high=measure(triangles)
    if not edges or any(n!=2 for n in edges.values()) or any(directed[(a,b)]!=directed[(b,a)] for a,b in edges) or volume<=0:
        raise ValueError(f"Non-watertight/reversed mesh: {path}")
    if abs(low[2])>1e-6 or any(v<0 or v>256 for v in low+high): raise ValueError(f"Invalid print orientation/bounds: {path}")
    return triangles,dict(triangles=len(triangles),volume_mm3=volume,bounds_min_mm=low,bounds_max_mm=high,
        nonmanifold_edges=0,inconsistent_edge_winding=0)


def face_image(meshes,width,height,reading=True,pitch=16):
    from PIL import Image,ImageDraw
    image=Image.new("RGB",(round(width*pitch),round(height*pitch)),"#dddddd")
    draw=ImageDraw.Draw(image)
    for triangles,color in meshes:
        for triangle in triangles:
            if all(p[2]==0 for p in triangle):
                draw.polygon([((width-x if reading else x)*pitch,(height-y)*pitch) for x,y,z in triangle],fill=color)
    return image


def build(presets,output,executable=None,workers=3,selected=None):
    executable=openscad_path(executable)
    source_document=json.loads(Path(presets).read_text(encoding="utf-8"))
    sets=validate_document(source_document)
    if selected:
        if selected not in sets: raise ValueError(f"Unknown preset: {selected}")
        sets={selected:sets[selected]}
    output=Path(output).resolve()
    if output.exists(): raise FileExistsError(f"Refusing existing output: {output}")
    output.mkdir(parents=True)
    document=dict(source_document,parameterSets=sets)
    fictional=bool(document.get("batch",{}).get("fictional_sample_data"))
    save_json(output/"presets.json",document)
    def one(item):
        key,params=item
        target=output/"tags"/key
        target.mkdir(parents=True)
        meshes=[];report={}
        for layer,color in (("body","white"),("face","black")):
            path=target/f"name_{layer}.stl"
            render(executable,output/"presets.json",key,layer,path)
            triangles,report[layer]=audit(path)
            meshes.append((triangles,color))
        width,height,thickness=report["body"]["bounds_max_mm"]
        low,high=report["face"]["bounds_min_mm"],report["face"]["bounds_max_mm"]
        if min(low[0],width-high[0],low[1],height-high[1])<2.95:
            raise ValueError(f"Artwork border is too small: {key}")
        if abs(high[2]-params.get("face_thickness_mm",.4))>1e-5: raise ValueError("Wrong face depth")
        error=sum(report[layer]["volume_mm3"] for layer in ("body","face"))-width*height*thickness
        if abs(error)>.02: raise ValueError(f"Materials do not complement full badge: {key}: {error}")
        report["complementary_volume_error_mm3"]=error
        save_json(target/"validation.json",report)
        face_image(meshes,width,height).save(target/"front.png")
        face_image(meshes,width,height,False).save(target/"bed.png")
        print(f"{key}: {width:.1f} x {height:.1f} x {thickness:.1f} mm",flush=True)
        return dict(id=key,label=params["label_text"],width_mm=round(width,4),height_mm=round(height,4),thickness_mm=round(thickness,4))
    with ThreadPoolExecutor(max_workers=workers) as executor:
        entries=list(executor.map(one,sets.items()))
    plates=pack(entries,256,6,3,True)
    plate_root=output/"plates";plate_root.mkdir()
    reports=[]
    from PIL import Image,ImageDraw,ImageFont
    for index,placements in enumerate(plates,1):
        stem=f"plate_{index:02d}"
        report=write_plate(plate_root/f"{stem}.3mf",placements,output/"tags")
        reports.append(dict(file=f"plates/{stem}.3mf",placements=placements,validation=report))
        image=Image.new("RGB",(1024,1084),"#d9dde2");draw=ImageDraw.Draw(image)
        prefix="FAKE SAMPLES | " if fictional else ""
        draw.text((15,15),f"{prefix}{stem} | BED VIEW | {len(placements)} labels | 256 mm bed",font=ImageFont.load_default(size=22),fill="black")
        for p in placements:
            with Image.open(output/"tags"/p["id"]/"bed.png") as badge:
                if p["rotation_deg"]: badge=badge.transpose(Image.Transpose.ROTATE_90)
                badge=badge.resize((round(p["width_mm"]*4),round(p["height_mm"]*4)),Image.Resampling.LANCZOS)
                image.paste(badge,(round(p["x_mm"]*4),60+round((256-p["y_mm"]-p["height_mm"])*4)))
        image.save(plate_root/f"{stem}.png")
    row_height=max(220,math.ceil(max(e["height_mm"] for e in entries)*2.7)+75)
    sheet=Image.new("RGB",(2100,80+row_height*math.ceil(len(entries)/3)),"#dddddd");draw=ImageDraw.Draw(sheet)
    title="FAKE SAMPLE NAMES - common physical scale" if fictional else "Readable fronts - common physical scale; width follows each name"
    draw.text((20,15),title,font=ImageFont.load_default(size=27),fill="black")
    for index,e in enumerate(entries):
        x,y=(index%3)*700+15,80+(index//3)*row_height
        draw.text((x,y),f"{e['id']} | {e['width_mm']:g} x {e['height_mm']:g} mm",font=ImageFont.load_default(size=17),fill="black")
        with Image.open(output/"tags"/e["id"]/"front.png") as badge:
            badge=badge.resize((round(e["width_mm"]*2.7),round(e["height_mm"]*2.7)),Image.Resampling.LANCZOS)
            sheet.paste(badge,(x,y+35))
    sheet.save(output/"all_labels.png")
    save_json(output/"plates.json",dict(label_count=len(entries),plate_count=len(plates),bed_mm=256,edge_margin_mm=6,
        fictional_sample_data=fictional,**({"sample_notice":FAKE_NOTICE} if fictional else {}),
        gap_mm=3,entries=entries,plates=reports))
    snapshot=output/"source";snapshot.mkdir()
    for name in ("name_tags.scad","README.md","requirements.txt"):
        shutil.copy2(ROOT/name,snapshot/name)
    shutil.copytree(ROOT/"fonts",snapshot/"fonts")
    shutil.copytree(ROOT/"examples",snapshot/"examples")
    shutil.copytree(ROOT/"tools",snapshot/"tools",ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy2(output/"presets.json",snapshot/"presets.json")
    shutil.copy2(output/"presets.json",snapshot/"name_tags.json")
    text=f"""# NameTags batch\n\n{len(entries)} labels on {len(plates)} arranged model 3MF plates.\nOpen numbered 3MF files separately. Each label is one assembly with white body\nand black face; preserve alignment and all black islands. Verify actual filament\nassignments. No printer profile, G-code, purge tower or brim space is included.\n6 mm bed margins and 3 mm gaps were checked; packing is a heuristic.\n\nPrint face-down, 0.4 mm nozzle, 0.2 mm layers, PLA, supports off. Both colors\nshare the first layers. No height-only color swap. `all_labels.png` shows fronts;\nplate PNGs show mirrored bed views. Exact mesh edges/winding, complementary\nvolumes, containment and all 3MF mesh coordinates were checked. lib3mf parsed\neach file without warnings. No physical or sliced-toolpath trial is claimed.\n\n`presets.json` records all input. `source/` is an independent build snapshot.\nFrom its root: `python tools/nametags.py build --presets presets.json --out build/rebuild`\n"""
    if document.get("batch",{}).get("fictional_sample_data"):
        text=text.replace("# NameTags batch\n\n", "# NameTags batch\n\n"+FAKE_NOTICE+"\n\n",1)
    (output/"README.md").write_text(text,encoding="utf-8")
    with zipfile.ZipFile(output/"plates.zip","w",zipfile.ZIP_DEFLATED) as archive:
        for name in ("README.md","plates.json","all_labels.png"):
            archive.write(output/name,name)
        for path in sorted(plate_root.iterdir()): archive.write(path,path.relative_to(output).as_posix())
    return output


SHARE_ROOT = "NameTags"
SHARE_EXCLUDED_DIRS = {"build", "output", "private", ".venv", "__pycache__"}
SHARE_EXCLUDED_NAMES = {".DS_Store"}


def share_entries(root=None):
    """Shareable files in stable order; local build output and caches are never included."""
    source = Path(root or ROOT)
    entries = []
    paths = sorted(source.rglob("*"), key=lambda path: path.relative_to(source).as_posix())
    for path in paths:
        if not path.is_file():
            continue
        relative = path.relative_to(source)
        if any(part in SHARE_EXCLUDED_DIRS for part in relative.parts[:-1]):
            continue
        if relative.name in SHARE_EXCLUDED_NAMES or relative.suffix in (".pyc", ".pyo"):
            continue
        entries.append(relative)
    return entries


def package(out, overwrite=False):
    """Zip this project for sharing. Local build/ data is excluded by construction."""
    destination = Path(out).expanduser().resolve()
    if destination.suffix.lower() != ".zip":
        raise ValueError(f"Choose a .zip destination: {destination}")
    if destination.exists() and not overwrite:
        raise FileExistsError(f"Refusing existing archive: {destination}")
    try:
        inside = destination.relative_to(ROOT)
    except ValueError:
        inside = None
    entries = [name for name in share_entries() if inside is None or name != inside]
    if not entries or Path("name_tags.scad") not in entries:
        raise ValueError(f"Not a NameTags project folder: {ROOT}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_name(destination.name + ".part")
    with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in entries:
            archive.write(ROOT / name, f"{SHARE_ROOT}/{name.as_posix()}")
    partial.replace(destination)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    size = destination.stat().st_size
    print(f"{len(entries)} files, {size / 1e6:.1f} MB")
    print(destination)
    print(f"sha256 {digest}")
    for skipped in sorted(SHARE_EXCLUDED_DIRS):
        if (ROOT / skipped).is_dir():
            print(f"excluded local folder: {skipped}/")
    return destination


def doctor(executable=None):
    executable=openscad_path(executable)
    font=ROOT/"fonts/LiberationSans-Bold.ttf"
    if hashlib.sha256(font.read_bytes()).hexdigest()!=FONT_SHA256: raise ValueError("Bundled font differs from the tested unmodified Liberation Sans Bold font")
    result=subprocess.run([executable,"--version"],capture_output=True,text=True,timeout=30)
    print((result.stdout+result.stderr).strip())
    target=ROOT/"build/doctor";target.mkdir(parents=True,exist_ok=True)
    render(executable,ROOT/"examples/fake_names.json","row_001_john_smith","face",target/"john_smith_face.stl")
    _,report=audit(target/"john_smith_face.stl")
    expected=(4.466876,19.120396,129.120651,36.382519)
    actual=(*report["bounds_min_mm"][:2],*report["bounds_max_mm"][:2])
    if any(abs(a-b)>.025 for a,b in zip(actual,expected)): raise ValueError(f"Font/render fingerprint differs: {actual}")
    print("OK: local font hash, textmetrics feature, fictional John Smith test geometry and print orientation")


def main():
    if hasattr(sys.stdout,"reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--openscad",help="OpenSCAD executable; also accepts OPENSCAD_PATH environment variable")
    sub=parser.add_subparsers(dest="command",required=True)
    sub.add_parser("doctor",help="Check local font, OpenSCAD and fictional test-label geometry")
    converter=sub.add_parser("csv",help="Convert CSV into normal OpenSCAD Customizer JSON presets")
    converter.add_argument("input",type=Path);converter.add_argument("--out",required=True,type=Path)
    converter.add_argument("--split-first-space",action="store_true",help="Split text into two lines at its first space; default keeps full phrases")
    converter.add_argument("--emoji-policy",choices=("symbols","names_only","error"),default="symbols")
    builder=sub.add_parser("build",help="Render checked STLs, readable previews and arranged 3MF plates")
    builder.add_argument("--presets",required=True,type=Path);builder.add_argument("--out",required=True,type=Path)
    builder.add_argument("--preset",help="Build just one named preset")
    builder.add_argument("--workers",type=int,choices=range(1,5),default=3)
    packer=sub.add_parser("package",help="Zip this project for sharing; local build/ output is excluded")
    packer.add_argument("--out",required=True,type=Path,help="Destination .zip, normally outside this folder")
    packer.add_argument("--overwrite",action="store_true",help="Replace an existing archive")
    args=parser.parse_args()
    if args.command=="doctor": doctor(args.openscad)
    elif args.command=="csv":
        if args.out.exists(): raise FileExistsError(f"Refusing existing presets: {args.out}")
        save_json(args.out,csv_document(args.input,args.split_first_space,args.emoji_policy))
        print(args.out)
    elif args.command=="package": package(args.out,args.overwrite)
    else: print(build(args.presets,args.out,args.openscad,args.workers,args.preset))


if __name__=="__main__": main()
