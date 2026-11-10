"""All names here are FICTIONAL common placeholders, not real-person records.

Run from this standalone folder: python -m unittest discover tests -v.
"""
from pathlib import Path
import json
import os
import sys
import tempfile
import unittest
import zipfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"tools"))
import nametags as nt
from plates import pack,validate_placements,transform


class DataTests(unittest.TestCase):
    def test_csv_rows_accents_duplicates_phrases_and_explicit_second_lines(self):
        with tempfile.TemporaryDirectory() as temporary:
            p=Path(temporary)/"names.csv"
            p.write_text("label,sample_data\nJohn Smith,FAKE_NAMES\nJohn Smith,FAKE_NAMES\nJos\u00e9 Smith,FAKE_NAMES\nStudio tools,FAKE_NAMES\n",encoding="utf-8-sig")
            document=nt.csv_document(p)
            values=list(document["parameterSets"].values())
            self.assertEqual(len(document["parameterSets"]),4)
            self.assertEqual(values[2]["label_text"],"Jos\u00e9 Smith")
            self.assertTrue(document["batch"]["fictional_sample_data"])
            self.assertEqual(document["batch"]["rows"][0]["sample_data"],"FAKE_NAMES")
            self.assertEqual(values[3]["label_text"],"Studio tools")
            self.assertEqual(values[3]["second_line_text"],"")
            self.assertEqual(list(nt.csv_document(p,True)["parameterSets"].values())[3]["second_line_text"],"tools")

    def test_symbols_are_explicit_and_unknown_symbols_fail(self):
        with tempfile.TemporaryDirectory() as temporary:
            p=Path(temporary)/"names.csv"
            p.write_text("First Name\nJohn Smith \U0001f4b0\n",encoding="utf-8")
            document=nt.csv_document(p)
            self.assertEqual(next(iter(document["parameterSets"].values()))["symbol"],"money_bag")
            self.assertFalse(document["batch"]["fictional_sample_data"])
            self.assertEqual(document["batch"]["rows"][0]["original"],"John Smith \U0001f4b0")
            with self.assertRaises(ValueError): nt.csv_document(p,emoji_policy="error")
            p.write_text("First Name\nOther \U0001f308\n",encoding="utf-8")
            with self.assertRaises(ValueError): nt.csv_document(p)

    def test_examples_are_marked_fictional_and_preserve_duplicates_and_unicode(self):
        examples=json.loads((ROOT/"examples/fake_names.json").read_text(encoding="utf-8"))
        self.assertEqual(examples,json.loads((ROOT/"name_tags.json").read_text(encoding="utf-8")))
        self.assertEqual(examples["parameterSets"]["row_006_jose_smith"]["label_text"],"Jos\u00e9 Smith")
        self.assertIn("FAKE_NAMES",(ROOT/"examples/fake_names.csv").read_text(encoding="utf-8"))
        self.assertTrue(examples["batch"]["fictional_sample_data"])
        self.assertEqual(len(nt.validate_document(examples)),12)
        self.assertEqual(sum(p["label_text"]=="John Smith" for p in examples["parameterSets"].values()),2)
        self.assertEqual(examples["parameterSets"]["row_008_kiln"]["second_line_text"],"Room")
        self.assertEqual(len(nt.csv_document(ROOT/"examples/fake_names.csv")["parameterSets"]),12)

    def test_packing_fits_every_row_once_and_keeps_material_transform(self):
        entries=[dict(id=str(i),width_mm=180,height_mm=50.8) for i in range(12)]
        plates=pack(entries,256,6,3,True)
        self.assertEqual([len(p) for p in plates],[5,5,2])
        validate_placements(plates,entries,256,6,3)
        rotated=next(p for plate in plates for p in plate if p["rotation_deg"]==90)
        m=transform(rotated)
        self.assertEqual(m[:9],[0,1,0,-1,0,0,0,0,1])
        self.assertEqual(m[-1],0)

    def test_ready_reprints_contain_only_marked_fictional_examples(self):
        with zipfile.ZipFile(ROOT/"reprints/fake_names_plates.zip") as archive:
            self.assertIsNone(archive.testzip())
            self.assertGreater(len([n for n in archive.namelist() if n.endswith(".3mf")]),0)
            self.assertIn("Fictional sample data",archive.read("README.md").decode("utf-8"))
            self.assertTrue(json.loads(archive.read("plates.json"))["fictional_sample_data"])


class ShareTests(unittest.TestCase):
    def test_package_excludes_local_build_data_and_caches(self):
        with tempfile.TemporaryDirectory() as temporary:
            archive_path=Path(temporary)/"share.zip"
            nt.package(archive_path)
            with zipfile.ZipFile(archive_path) as archive:
                self.assertIsNone(archive.testzip())
                names=archive.namelist()
            for required in ("NameTags/README.md","NameTags/name_tags.scad","NameTags/name_tags.json",
                    "NameTags/tools/nametags.py","NameTags/fonts/LiberationSans-Bold.ttf",
                    "NameTags/fonts/LICENSE.txt","NameTags/reprints/fake_names_plates.zip"):
                self.assertIn(required,names)
            self.assertEqual([n for n in names if "build/" in n or "output/" in n or "private/" in n
                or "__pycache__" in n or n.endswith(".pyc")],[])
            self.assertEqual([n for n in names if not n.startswith("NameTags/")],[])
            with self.assertRaises(FileExistsError): nt.package(archive_path)
            nt.package(archive_path,overwrite=True)

    def test_share_entries_are_stable_and_contain_no_local_output(self):
        entries=[name.as_posix() for name in nt.share_entries()]
        self.assertEqual(entries,sorted(entries))
        self.assertEqual(len(entries),len(set(entries)))
        self.assertFalse([e for e in entries if e.startswith(("build/","output/",".venv/"))])


class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try: cls.executable=nt.openscad_path()
        except FileNotFoundError as error: raise unittest.SkipTest(str(error))

    def test_native_json_and_common_font_auto_width(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            doc=dict(fileFormatVersion="1",parameterSets=dict(
                john_smith=dict(label_text="John Smith"),pat_lee=dict(label_text="Pat Lee"),phrase_long=dict(label_text="Studio tools"),
                phrase=dict(label_text="Studio tools"),newline=dict(label_text="Kiln\nRoom"),
                second=dict(label_text="Kiln",second_line_text="Room")))
            nt.save_json(base/"presets.json",doc)
            widths={}
            for key in doc["parameterSets"]:
                log=nt.render(self.executable,base/"presets.json",key,"body",base/f"{key}.stl")
                self.assertIn("font 16.69",log)
                _,report=nt.audit(base/f"{key}.stl")
                widths[key]=report["bounds_max_mm"][0]
            self.assertLess(widths["pat_lee"],widths["john_smith"])
            self.assertGreater(widths["phrase_long"],widths["john_smith"])
            self.assertAlmostEqual(widths["newline"],widths["second"],places=4)

    def test_pasted_list_and_height_width_guards(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            nt.render(self.executable,ROOT/"examples/fake_names.json","row_001_john_smith","body",base/"pasted.stl",
                defines=(("input_source","pasted_list"),("label_index",1)))
            _,report=nt.audit(base/"pasted.stl")
            self.assertGreater(report["bounds_max_mm"][0],0)
            nt.render(self.executable,ROOT/"examples/fake_names.json","row_001_john_smith","preview",base/"layout.png",png=True,
                defines=(("mode","list_layout"),))
            for key,params in (("wide",dict(label_text="John Smith",width_override_mm=10)),
                ("tall",dict(label_text="Kiln",second_line_text="Room",font_size_mm=30))):
                nt.save_json(base/"bad.json",dict(parameterSets={key:params}))
                with self.assertRaises(RuntimeError): nt.render(self.executable,base/"bad.json",key,"body",base/f"{key}.stl")
            with self.assertRaisesRegex(RuntimeError,"Enable textmetrics"):
                nt.render(self.executable,ROOT/"examples/fake_names.json","row_001_john_smith","body",base/"disabled.stl",enable_metrics=False)

    def test_two_material_batch_and_3mf_roundtrip(self):
        with tempfile.TemporaryDirectory() as temporary:
            output=nt.build(ROOT/"examples/fake_names.json",Path(temporary)/"batch",self.executable,workers=2)
            report=json.loads((output/"plates.json").read_text())
            self.assertEqual(report["label_count"],12)
            for plate in report["plates"]:
                self.assertEqual(plate["validation"]["lib3mf_warnings"],[])
                self.assertTrue(plate["validation"]["exact_stl_mesh_roundtrip"])
            self.assertTrue((output/"source/name_tags.scad").is_file())
            self.assertTrue((output/"source/fonts/LiberationSans-Bold.ttf").is_file())
            self.assertTrue((output/"source/examples/fake_names.json").is_file())
            with self.assertRaises(FileExistsError): nt.build(ROOT/"examples/fake_names.json",output,self.executable)

    def test_tall_label_contact_sheet_has_room_for_complete_height(self):
        from PIL import Image
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary)
            nt.save_json(base/"presets.json",dict(parameterSets=dict(tall=dict(label_text="Studio tools",height_mm=90))))
            output=nt.build(base/"presets.json",base/"batch",self.executable)
            with Image.open(output/"all_labels.png") as image:
                self.assertGreaterEqual(image.height,80+35+round(90*2.7))


if __name__=="__main__": unittest.main()
