"""
make_bambu.py — збирає ГОТОВІ Bambu Studio проєкти (.3mf) з out/*.stl
з правильними параметрами друку для кожної деталі (10.07).

Bambu обмеження: один процес (висота шару) на проєкт → ТРИ файли:
  • out/print_tray.3mf  — корпус ЛИЦЕМ ВНИЗ, 0.24, без підтримок
  • out/print_block.3mf — SSD-блок дном вниз, 0.2, gyroid 13%
  • out/print_small.3mf — вставка I/O + LSI-защіпка лицем вниз, 0.16

База — Metadata/project_settings.config з NAS_tray-fast-petg.3mf
(робочий PETG-профіль користувача: температури/вентилятори/швидкості
філамента НЕ чіпаємо, правимо лише процесні ключі + different_settings_
to_system, інакше Bambu скидає значення до пресетів).

Запуск: .venv/bin/python cad/make_bambu.py [шлях-до-шаблону.3mf]
"""
import json
import sys
import zipfile
from pathlib import Path

import trimesh

HERE = Path(__file__).resolve().parent.parent
TEMPLATE = Path(sys.argv[1]) if len(sys.argv) > 1 \
    else HERE / "NAS_tray-fast-petg.3mf"

# поворот «лицем вниз»: x'=x, y'=-z, z'=y (панель y=-99.4 стає низом)
FACE_DOWN = (1, 0, 0, 0, 0, 1, 0, -1, 0)
IDENT = (1, 0, 0, 0, 1, 0, 0, 0, 1)

ROT_Z90 = (0, 1, 0, -1, 0, 0, 0, 0, 1)   # довга вісь блока по X

PLATE_STRIDE = 270.35   # крок пластин у світових координатах (з шаблону:
                        # build tx=398.35 при центрі пластини-2 = 128)

# проєкт = список ПЛАСТИН; пластина = список об'єктів
# (stl, назва, поворот, (dx,dy) від центру пластини, {per-object ключі})
PROJECTS = {
    # ОДИН ФАЙЛ, ТРИ ПЛАСТИНИ (10.07). ⚠️ КОМПРОМІС (Bambu): процес —
    # один на ПРОЄКТ, тому шар 0.2 для всіх пластин (корпус міг би
    # 0.24, дрібнота 0.16 — для цього лишаються окремі print_*.3mf)
    "print_all": dict(
        plates=[
            dict(name="Корпус (лицем вниз)", objects=[
                ("tray.stl", "NAS_tray", FACE_DOWN, (0.0, 0.0),
                 {"brim_type": "auto_brim", "brim_width": "5"})]),
            # 10.07: дрібнота РАЗОМ з блоком — origin третьої пластини
            # в Студії невідомий (grid-розкладка), а крок другої знято
            # з файлу користувача; блок центр, вставка спереду, защіпка
            # ззаду — все вміщається
            # 10.07: шар — ПООБ'ЄКТНО (глобальний 0.24 під корпус;
            # блок 0.2, дрібнота 0.16 своїми object-налаштуваннями)
            dict(name="SSD блок + вставка IO + защіпка LSI", objects=[
                ("ssd_block.stl", "SSD_block", IDENT, (0.0, 0.0),
                 {"layer_height": "0.2",
                  "sparse_infill_density": "13%",
                  "sparse_infill_pattern": "gyroid"}),
                ("io_insert.stl", "IO_insert", FACE_DOWN, (0.0, -93.0),
                 {"layer_height": "0.16", "outer_wall_speed": "50"}),
                ("lsi_clip.stl", "LSI_clip", FACE_DOWN, (0.0, 80.0),
                 {"layer_height": "0.16", "outer_wall_speed": "50"})]),
        ],
        over={"layer_height": "0.24", "wall_loops": "2",
              "sparse_infill_density": "10%",
              "sparse_infill_pattern": "grid",
              "brim_type": "no_brim"},
    ),
    "print_tray": dict(
        plates=[dict(name="Корпус (лицем вниз)", objects=[
            ("tray.stl", "NAS_tray", FACE_DOWN, (0.0, 0.0), {})])],
        over={"layer_height": "0.24", "wall_loops": "2",
              "sparse_infill_density": "10%",
              "sparse_infill_pattern": "grid"},
    ),
    "print_block": dict(
        plates=[dict(name="SSD блок (дном вниз)", objects=[
            ("ssd_block.stl", "SSD_block", IDENT, (0.0, 0.0), {})])],
        over={"layer_height": "0.2", "wall_loops": "2",
              "sparse_infill_density": "13%",
              "sparse_infill_pattern": "gyroid",
              "brim_type": "no_brim"},
    ),
    "print_small": dict(
        plates=[dict(name="Вставка IO + защіпка LSI", objects=[
            ("io_insert.stl", "IO_insert", FACE_DOWN, (-45.0, 0.0), {}),
            ("lsi_clip.stl", "LSI_clip", FACE_DOWN, (90.0, 0.0), {})])],
        over={"layer_height": "0.16", "wall_loops": "2",
              "outer_wall_speed": "50",
              "brim_type": "no_brim"},
    ),
}
# спільні процесні оверрайди (зазори защіпок у перших шарах, шов, мости)
COMMON = {"reduce_crossing_wall": "1",   # 10.07: travel об'їжджає
          # стіни — на висоті 213 сопло не чіпляє шви верхівки (головна
          # причина завалу високих друків; CoreXY стіл деталь не гойдає)
          "elefant_foot_compensation": "0.15",
          "precise_outer_wall": "1",
          "seam_position": "back",
          "bridge_speed": "28",
          "initial_layer_print_height": "0.2"}


def mesh_xml(m, obj_uuid, inner_id):
    v = "\n".join('    <vertex x="%.4f" y="%.4f" z="%.4f"/>' % tuple(p)
                  for p in m.vertices)
    t = "\n".join('    <triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f)
                  for f in m.faces)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <resources>
  <object id="{inner_id}" p:UUID="{obj_uuid}" type="model">
   <mesh>
   <vertices>
{v}
   </vertices>
   <triangles>
{t}
   </triangles>
   </mesh>
  </object>
 </resources>
 <build/>
</model>
'''


def apply_overrides(settings, over):
    s = json.loads(json.dumps(settings))          # deep copy
    changed = []
    for k, val in over.items():
        if k not in s:
            print(f"  (!) ключа {k} нема в шаблоні — пропущено")
            continue
        if isinstance(s[k], list):
            s[k] = [val] * len(s[k])
        else:
            s[k] = val
        changed.append(k)
    # different_settings_to_system[0] = процесні відхилення від пресета;
    # без цього Bambu мовчки скидає значення (урок сесії 09.07)
    diffs = s.get("different_settings_to_system", [""])
    have = set(diffs[0].split(";")) if diffs[0] else set()
    diffs[0] = ";".join(sorted(have | set(changed)))
    s["different_settings_to_system"] = diffs
    return s


def build_project(name, spec, tz, base_settings):
    center = 128.0
    objects, rels, model_parts = [], [], {}
    flat = [(pi, ob) for pi, plate in enumerate(spec["plates"])
            for ob in plate["objects"]]
    for i, (plate_i, (stl, oname, rot, (dx, dy), oset)) in enumerate(flat):
        m = trimesh.load(HERE / "out" / stl)
        oid = 2 + i
        inner = 100 + oid                     # id меша всередині файлу:
        u = f"0000000{oid}"                   # УНІКАЛЬНИЙ (10.07: чотири
        obj_uuid = f"{u}-61cb-4c03-9d28-80fed5dfa1dc"   # файли з id=1 —
        inner_uuid = f"00{oid}90000-81cb-4c03-9d28-80fed5dfa1dc"  # Студія
        comp_uuid = f"00{oid}90000-b206-40ff-9872-83e8017abed1"   # злила
        item_uuid = f"{u}-b1ec-4553-aec9-835e5b724bb4"  # всі в один меш)
        path = f"/3D/Objects/object_{inner}.model"
        # 10.07: поворот і позицію ЗАПІКАЄМО у вершини — Студія читала
        # матрицю item-а в іншій конвенції (row/column), корпус лягав
        # не тим боком і об'єкти з'їжджали з пластин; identity в item
        # не залежить від конвенції
        import numpy as np
        R = np.array(rot, float).reshape(3, 3)
        vv = m.vertices @ R
        lo, hi = vv.min(0), vv.max(0)
        shift = np.array([
            center + dx - (lo[0] + hi[0]) / 2 + PLATE_STRIDE * plate_i,
            center + dy - (lo[1] + hi[1]) / 2,
            -lo[2]])
        m = trimesh.Trimesh(vertices=vv + shift, faces=m.faces,
                            process=False)
        model_parts[path.lstrip("/")] = mesh_xml(m, inner_uuid, inner)
        tr = "1 0 0 0 1 0 0 0 1 0 0 0" 
        objects.append(dict(oid=oid, inner=inner, name=oname,
                            path=path, tr=tr,
                            faces=len(m.faces), obj_uuid=obj_uuid,
                            comp_uuid=comp_uuid, item_uuid=item_uuid,
                            oset=oset, plate=plate_i))
        rels.append(
            f'<Relationship Target="{path}" Id="rel-obj-{oid}" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/'
            '3dmodel"/>')

    res = "\n".join(
        f'''  <object id="{o["oid"]}" p:UUID="{o["obj_uuid"]}" type="model">
   <components>
    <component p:path="{o["path"]}" objectid="{o["inner"]}" p:UUID="{o["comp_uuid"]}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>
   </components>
  </object>''' for o in objects)
    items = "\n".join(
        f'''  <item objectid="{o["oid"]}" p:UUID="{o["item_uuid"]}" transform="{o["tr"]}" printable="1"/>'''
        for o in objects)
    root = f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="Application">BambuStudio-02.07.01.62</metadata>
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <metadata name="Title">{name}</metadata>
 <resources>
{res}
 </resources>
 <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">
{items}
 </build>
</model>
'''
    obj_meta = "\n".join(f'''  <object id="{o["oid"]}">
    <metadata key="name" value="{o["name"]}"/>
    <metadata key="extruder" value="1"/>
{"".join(chr(10).join(f'    <metadata key="{k}" value="{v}"/>' for k, v in o["oset"].items()) + chr(10) if o["oset"] else "")}
    <metadata face_count="{o["faces"]}"/>
    <part id="1" subtype="normal_part">
      <metadata key="name" value="{o["name"]}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="source_file" value="{o["name"]}.stl"/>
      <metadata key="source_object_id" value="0"/>
      <metadata key="source_volume_id" value="0"/>
      <mesh_stat face_count="{o["faces"]}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>
  </object>''' for o in objects)
    n_plates = len(spec["plates"])
    plates_meta = []
    for pi in range(n_plates):
        inst = "\n".join(f'''    <model_instance>
      <metadata key="object_id" value="{o["oid"]}"/>
      <metadata key="instance_id" value="0"/>
      <metadata key="identify_id" value="{o["oid"] * 100}"/>
    </model_instance>''' for o in objects if o["plate"] == pi)
        pname = spec["plates"][pi].get("name", "")
        plates_meta.append(f'''  <plate>
    <metadata key="plater_id" value="{pi + 1}"/>
    <metadata key="plater_name" value="{pname}"/>
    <metadata key="locked" value="false"/>
    <metadata key="filament_map_mode" value="Auto For Match"/>
    <metadata key="filament_maps" value="1"/>
    <metadata key="thumbnail_file" value="Metadata/plate_{pi + 1}.png"/>
{inst}
  </plate>''')
    plates_xml = "\n".join(plates_meta)
    asm = "\n".join(
        f'   <assemble_item object_id="{o["oid"]}" instance_id="0" '
        f'transform="{o["tr"]}" offset="0 0 0" />' for o in objects)
    model_cfg = f'''<?xml version="1.0" encoding="UTF-8"?>
<config>
{obj_meta}
{plates_xml}
  <assemble>
{asm}
  </assemble>
</config>
'''
    settings = apply_overrides(base_settings, {**COMMON, **spec["over"]})

    out = HERE / "out" / f"{name}.3mf"
    with zipfile.ZipFile(TEMPLATE) as z:
        keep = {n: z.read(n) for n in z.namelist()
                if n in ("[Content_Types].xml", "_rels/.rels",
                         "Metadata/cut_information.xml")}
        blanks = {suf: z.read(f"Metadata/{suf}_1.png")
                  for suf in ("plate", "plate_no_light", "top", "pick")}
        blank_small = z.read("Metadata/plate_1_small.png")
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for n, data in keep.items():
            z.writestr(n, data)
        import json as _json
        z.writestr("Metadata/filament_sequence.json", _json.dumps(
            {f"plate_{i + 1}": {"nozzle_sequence": [],
                                "optimal_assignment": [], "sequence": []}
             for i in range(n_plates)}))
        for i in range(n_plates):
            for suf in ("plate", "plate_no_light", "top", "pick"):
                z.writestr(f"Metadata/{suf}_{i + 1}.png", blanks[suf])
            z.writestr(f"Metadata/plate_{i + 1}_small.png", blank_small)
        z.writestr("3D/3dmodel.model", root)
        z.writestr("3D/_rels/3dmodel.model.rels",
                   '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                   '\n<Relationships xmlns="http://schemas.openxmlformats.'
                   'org/package/2006/relationships">\n'
                   + "\n".join(rels) + "\n</Relationships>")
        for pth, xml in model_parts.items():
            z.writestr(pth, xml)
        z.writestr("Metadata/model_settings.config", model_cfg)
        z.writestr("Metadata/project_settings.config",
                   json.dumps(settings, indent=4, ensure_ascii=False))
    print(f"  {out.name}: пластин {n_plates}, об'єктів {len(objects)}, шар {settings['layer_height']}")


if __name__ == "__main__":
    with zipfile.ZipFile(TEMPLATE) as z:
        base = json.loads(z.read("Metadata/project_settings.config"))
    for name, spec in PROJECTS.items():
        build_project(name, spec, None, base)
