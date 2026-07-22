"""
make_bambu.py — збирає ГОТОВІ Bambu Studio проєкти (.3mf) з out/*.stl
з правильними параметрами друку для кожної деталі (10.07).

Bambu обмеження: один процес (висота шару) на проєкт → файли:
  • out/print_all.3mf   — ОДИН файл, 3 пластини (пооб'єктний шар)
  • out/print_tray.3mf  — корпус ЛИЦЕМ ВНИЗ, 0.24, без підтримок
  • out/print_block.3mf — SSD-блок дном вниз, 0.2, gyroid 13%
  • out/print_test.3mf  — ТЕСТ №4 snap-fit (20.07): test_tray стоячи +
    test_block + 2 зачепи, бойові орієнтації/шари
  • out/print_clips.3mf — ЛИШЕ 2 зачепи (в6.3, передрук інтерфейсної
    деталі: слот дна і Т-паз блока — старі), 0.16 + brim 3
  • out/print_small.3mf — вставка I/O лицем вниз + КОВПАК LSI задньою
    гранню вниз (16.07), 0.16

База — Metadata/project_settings.config з NAS_tray-ams-petg.3mf
(21.07: свіжий сейв користувача ПІСЛЯ установки AMS —
extruder_ams_count '1#0|4#1'; робочий PETG-профіль: температури/
вентилятори/швидкості філамента НЕ чіпаємо, правимо лише процесні
ключі + different_settings_to_system, інакше Bambu скидає значення
до пресетів).

21.07 (поки друкується тест №6):
  • ЗМІННИЙ ШАР — Metadata/layer_heights_profile.txt: банди 0.12 на
    висотах посадкових кромок (корпус: 6 рядів снап-сітки; блок: Т-пази);
  • МОДИФІКАТОР «повільний верх» корпусу (modifier_part-куб, z'≥165:
    outer 50 / inner 80) — менше трясе тонкі плити на верхніх шарах;
  • travel_acceleration 6000→4000 у проєктах з корпусом;
  • wall_generator=arachne (користувач перемкнув у Студії, сейв
    підтвердив — не відкочуємо генерований файлом).

22.07 (після друку шматка дна):
  • АНТИ-СТРІНГ у всі проєкти (apply_anti_string): 245° + ретракція
    1.2 (wipe вже був) — волосінь пережила сушку 38→11% і 250°;
  • МОДИФІКАТОР «повільне дно» корпусу (MOD_FLOOR, zmodel −1..11):
    у FACE_DOWN плита дна = вертикальний слаб, стінки сот = леза 2 мм,
    «площина рухається за головкою» → outer 40 / inner 60;
  • _mod тепер список (кілька modifier_part на об'єкт).

Запуск: .venv/bin/python cad/make_bambu.py [шлях-до-шаблону.3mf]
"""
import json
import sys
import zipfile
from pathlib import Path

import trimesh

import params as P     # cad/ у sys.path при запуску python cad/make_bambu.py

HERE = Path(__file__).resolve().parent.parent
TEMPLATE = Path(sys.argv[1]) if len(sys.argv) > 1 \
    else HERE / "NAS_tray-ams-petg.3mf"

# поворот «лицем вниз»: x'=x, y'=-z, z'=y (панель y=-99.4 стає низом)
FACE_DOWN = (1, 0, 0, 0, 0, 1, 0, -1, 0)
IDENT = (1, 0, 0, 0, 1, 0, 0, 0, 1)

ROT_Z90 = (0, 1, 0, -1, 0, 0, 0, 0, 1)   # довга вісь блока по X
# snap-зачеп сітки НА БОЦІ (X-гранню вниз): x'=-z, y'=y, z'=x — весь
# зачеп = YZ-профіль, кожен шар ідентичний; згин ноги-пружини по Y
# У ПЛОЩИНІ шарів (snap_clip.py, 20.07)
ROT_Y90 = (0, 0, 1, 0, 1, 0, -1, 0, 0)

# КОВПАК LSI (17.07 в3) — знову FACE_DOWN лицем (y−96.35) вниз:
# тіло і лезо копланарні спереду, лежать на столі; пронг гнеться по X
# = у площині шарів (ROT_REAR ери «руки» в2 видалено: лезо на −94.95
# висіло б островом 2.5 над столом)

# ФРОНТ-АДДОН ТИЛОМ ВНИЗ (21.07, фідбек «покласти на протилежну
# площину, щоб убрати нависання»): x'=x, y'=z, z'=−y — тил ламелі
# (y−97.85) стає низом. План плити ⊆ план ламелі (плита 93.65..131.75
# всередині ламелі 92.15..133.25, той самий Z-діапазон і вирізи) →
# ламель+язики+крила друкуються ПЕРШИМИ на столі, плита повністю
# спирається на них — елевовані консолі h1.55 ери FACE_DOWN зникають.
# Нові навіси тривіальні: crush-ребра язиків біля стола (конус-лійка
# знизу), фаска-клин 45° самонесуча. Косметика: лице стає ВЕРХНЬОЮ
# поверхнею (top-шари, не гладке від стола) — див. пам'ятку.
ROT_REAR = (1, 0, 0, 0, 0, -1, 0, 1, 0)

PLATE_STRIDE = 270.35   # крок пластин (знято з сейвів користувача)


def plate_origin(i):
    """Сітка пластин Studio 02.07: 2 колонки; другий ряд СПЕРЕДУ (-Y).
    Знято з сейва користувача 10.07: плита 2 = (+270.35, 0),
    плита 3 = (0, -270.35)."""
    return (PLATE_STRIDE * (i % 2), -PLATE_STRIDE * (i // 2))


# ── 21.07: ЗМІННИЙ ШАР — height ranges ──────────────────────────────────
# Банди тонкого шару 0.12 на висотах ПОСАДКОВИХ КРОМОК — точність зубів/
# полиць зачепів без здорожчання всього друку. Механізм: Metadata/
# layer_config_ranges.xml (знято 1:1 із сейва користувача з одним
# height-range модифікатором; «мій» layer_heights_profile.txt Студія
# ігнорувала). object id у файлі = 1-based ПОРЯДОК об'єкта в
# 3dmodel.model (семпл: XML-ids 2/4/6/8, range id=1 на першому).
# spans_rz — у «повернутому» домені (координата, що стає віссю Z друку:
# model-Y для FACE_DOWN, model-Z для IDENT); у build_project
# конвертується відніманням lo[2] (низ деталі → стіл).
# Корпус: усі 6 рядів снап-сітки (дно друкується РАЗ — майбутні аддони
# стануть у будь-який ряд); слот ±1.15 + кишеня ±2.0 → півширина 2.2.
# + постаменти плати (21.07): лежачі циліндри ⌀9 з отвором ⌀4 —
# тонкий шар кругліше веде отвір (хват M3) і нижню дугу-навіс;
# півширина 4.7 покриває ⌀9. Y-центри: S2 −83.1, S1 −60.4, S3/S4 71.9.
# МОСТИ ВИКЛЮЧЕНІ (probe_zones 21.07): верхні кромки RAM-вікон
# (A y74.9 проліт 74, B y67.9 проліт 34 + на нього сідає база S3)
# мають мостити на 0.24 — тонка нитка 0.12 провисає; band ріжеться.
_BRIDGE_EXCL = [(w["y"][1] - 0.2, w["y"][1] + 1.2)
                for w in P.RAM_KEEPOUT.values()]


def _cut_spans(spans, excl):
    """Відняти виключення (мости) від спанів тонкого шару."""
    out = []
    for a, b in spans:
        segs = [(a, b)]
        for ea, eb in excl:
            segs = [s for lo, hi in segs
                    for s in ((lo, min(hi, ea)), (max(lo, eb), hi))
                    if s[1] - s[0] > 0.3]
        out += segs
    return out


VLH_TRAY = {"fine": 0.12,
            "spans_rz": _cut_spans(
                [(r - 2.2, r + 2.2) for r in P.ANCHOR_ROWS] +
                [(y - 4.7, y + 4.7) for y in sorted(
                    {xy[1] for xy in P.STANDOFF_XY.values()})],
                _BRIDGE_EXCL)}
# Блок: зона Т-пазів (полиці Z5.9, стеля 7.35, верх слаба 8; люфти
# 0.1/0.15 порівнянні з квантуванням шару 0.2 → тонкий шар критичний)
VLH_BLOCK = {"fine": 0.12, "spans_rz": [(5.2, 8.2)]}
# Модифікатор «повільний верх» корпусу: вище z'=165 (останні ~48 мм
# друку) периметри повільніше — важіль високої деталі великий, тонкі
# плити стінок гойдаються, шви верхівки чистіші
MOD_TOP = {"name": "slow_top", "z0": 165.0,
           "set": {"outer_wall_speed": "50", "inner_wall_speed": "80"}}
# 22.07: «повільне дно» — у FACE_DOWN плита дна (модельний Z0..8: мембрана
# +соти+корона+трамплін) = вертикальний слаб, стінки сот — тонкі леза
# 2 мм, «площина рухається за головкою» (друк шматка дна: шершаві
# стінки). Бокс у МОДЕЛЬНИХ координатах (zmodel), обертається разом з
# деталлю; лише швидкості периметрів (fan — філаментний, per-modifier
# не буває)
MOD_FLOOR = {"name": "slow_floor", "zmodel": (-1.0, 11.0),
             "set": {"outer_wall_speed": "40", "inner_wall_speed": "60"}}


def vlh_ranges(idx, spans, fine, height):
    """<object> для Metadata/layer_config_ranges.xml: height-range
    модифікатори одного об'єкта (idx = 1-based порядок у 3dmodel.model);
    формат 1:1 із сейва Студії."""
    merged = []                             # злиття перекритих спанів
    for a, b in sorted(spans):              # (ряд 71 ∩ постаменти 71.9)
        a = max(a, 0.4)                     # перші шари не чіпаємо
        b = min(b, height - 0.01)
        if b <= a:
            continue
        if merged and a <= merged[-1][1] + 0.01:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    rngs = []
    for a, b in merged:
        rngs.append(f'''  <range min_z="{a:.4f}" max_z="{b:.4f}">
   <option opt_key="extruder">0</option>
   <option opt_key="layer_height">{fine}</option>
  </range>''')
    if not rngs:
        return None
    return f' <object id="{idx}">\n' + "\n".join(rngs) + "\n </object>"


# проєкт = список ПЛАСТИН; пластина = список об'єктів
# (stl, назва, поворот, (dx,dy) від центру пластини, {per-object ключі})
PROJECTS = {
    # ОДИН ФАЙЛ, ТРИ ПЛАСТИНИ (10.07): глобальний шар 0.24 (корпус),
    # блок/дрібнота — ПООБ'ЄКТНІ layer_height (підтверджено сейвом)
    "print_all": dict(
        plates=[
            dict(name="Корпус (лицем вниз)", objects=[
                ("tray.stl", "NAS_tray", FACE_DOWN, (0.0, 0.0),
                 {"brim_type": "auto_brim", "brim_width": "5",
                  "_vlh": VLH_TRAY, "_mod": [MOD_TOP, MOD_FLOOR]})]),
            # шар — ПООБ'ЄКТНО (глобальний 0.24 під корпус); пластину
            # перерозкладено 15.07: панель-аддон 41×89 (лицем вниз) не
            # вміщалась на місці старої вставки 41×71
            dict(name="Вставка IO + защіпки", objects=[
                ("io_insert.stl", "IO_insert", FACE_DOWN, (0.0, 72.0),
                 {"layer_height": "0.16", "outer_wall_speed": "50"}),
                ("addon_clip.stl", "Addon_clip", FACE_DOWN, (10.0, -53.0),
                 {"layer_height": "0.16", "outer_wall_speed": "50"}),
                # 20.07: snap-зачепи сітки (2 шт на SSD-блок; на боці
                # + brim — деталь 5.2×5.9×7.2, площа опори мала)
                ("snap_clip.stl", "Snap_clip_1", ROT_Y90,
                 (50.0, -53.0),
                 {"layer_height": "0.16", "outer_wall_speed": "50",
                  "brim_type": "auto_brim", "brim_width": "3"}),
                ("snap_clip.stl", "Snap_clip_2", ROT_Y90,
                 (65.0, -53.0),
                 {"layer_height": "0.16", "outer_wall_speed": "50",
                  "brim_type": "auto_brim", "brim_width": "3"}),
                # 15.07: панель-аддон правої зони з вентилятором
                # (гвинтиться до тилу аддона); grille/blank — окремі
                # out/front_grille|front_blank.stl, ті ж параметри
                # 21.07: ТИЛОМ вниз (ROT_REAR) — консолі язиків геть
                ("front_fan.stl", "Front_fan", ROT_REAR, (-58.0, -53.0),
                 {"layer_height": "0.16", "outer_wall_speed": "50"})]),
            dict(name="SSD блок", objects=[
                ("ssd_block.stl", "SSD_block", IDENT, (0.0, 0.0),
                 {"layer_height": "0.2",
                  "sparse_infill_density": "13%",
                  "sparse_infill_pattern": "gyroid",
                  "_vlh": VLH_BLOCK})]),
        ],
        # travel 6000→4000 (21.07): на 213 мм висоти ривки переміщень
        # гойдають корпус — травель повільніше, друк-швидкості ті самі
        over={"layer_height": "0.24", "wall_loops": "2",
              "sparse_infill_density": "8%",
              "sparse_infill_pattern": "grid",
              "brim_type": "no_brim",
              "default_acceleration": "6000",
              "travel_acceleration": "4000"},
    ),
    "print_tray": dict(
        plates=[dict(name="Корпус (лицем вниз)", objects=[
            ("tray.stl", "NAS_tray", FACE_DOWN, (0.0, 0.0),
             {"_vlh": VLH_TRAY, "_mod": [MOD_TOP, MOD_FLOOR]})])],
        over={"layer_height": "0.24", "wall_loops": "2",
              "sparse_infill_density": "8%",
              "sparse_infill_pattern": "grid",
              "default_acceleration": "6000",
              "travel_acceleration": "4000"},
    ),
    "print_block": dict(
        plates=[dict(name="SSD блок (дном вниз)", objects=[
            ("ssd_block.stl", "SSD_block", IDENT, (0.0, 0.0),
             {"_vlh": VLH_BLOCK})])],
        over={"layer_height": "0.2", "wall_loops": "2",
              "sparse_infill_density": "13%",
              "sparse_infill_pattern": "gyroid",
              "brim_type": "no_brim"},
    ),
    # 20.07: ТЕСТ №4 snap-fit (test_latch.py) — шматки в БОЙОВИХ
    # орієнтаціях і з бойовими параметрами шару (інакше тест бреше про
    # зазори): test_tray СТОЯЧИ на передньому торці = FACE_DOWN (та сама
    # орієнтація слотів/кишень, що в корпусі лицем вниз, 0.24 + brim 5);
    # test_block дном вниз 0.2 gyroid; зачепи на боці 0.16 + brim 3
    "print_test": dict(
        plates=[
            dict(name="Тест дна (стоячи, як корпус)", objects=[
                ("test_tray.stl", "Test_tray", FACE_DOWN, (0.0, 0.0),
                 {"brim_type": "auto_brim", "brim_width": "5"})]),
            dict(name="Тест блока + зачепи", objects=[
                ("test_block.stl", "Test_block", IDENT, (0.0, 0.0),
                 {"layer_height": "0.2",
                  "sparse_infill_density": "13%",
                  "sparse_infill_pattern": "gyroid"}),
                ("snap_clip.stl", "Snap_clip_1", ROT_Y90, (25.0, -10.0),
                 {"layer_height": "0.16", "outer_wall_speed": "50",
                  "brim_type": "auto_brim", "brim_width": "3"}),
                ("snap_clip.stl", "Snap_clip_2", ROT_Y90, (25.0, 10.0),
                 {"layer_height": "0.16", "outer_wall_speed": "50",
                  "brim_type": "auto_brim", "brim_width": "3"})]),
        ],
        over={"layer_height": "0.24", "wall_loops": "2",
              "sparse_infill_density": "8%",
              "sparse_infill_pattern": "grid",
              "brim_type": "no_brim",
              "default_acceleration": "6000",
              "travel_acceleration": "6000"},
    ),
    # 20.07 в6.3: міні-проєкт для передруку ЛИШЕ зачепів (клин-дотиск) —
    # модульність в дії: слот дна і Т-паз блока вже надруковані, міняється
    # лише інтерфейсна деталь
    "print_clips": dict(
        plates=[dict(name="2 зачепи (на боці)", objects=[
            ("snap_clip.stl", "Snap_clip_1", ROT_Y90, (-8.0, 0.0),
             {"brim_type": "auto_brim", "brim_width": "3"}),
            ("snap_clip.stl", "Snap_clip_2", ROT_Y90, (8.0, 0.0),
             {"brim_type": "auto_brim", "brim_width": "3"})])],
        over={"layer_height": "0.16", "wall_loops": "2",
              "outer_wall_speed": "50",
              "brim_type": "no_brim"},
    ),
    "print_small": dict(
        plates=[dict(name="Вставка IO + защіпки", objects=[
            ("io_insert.stl", "IO_insert", FACE_DOWN, (-45.0, 0.0), {}),
            ("addon_clip.stl", "Addon_clip", FACE_DOWN, (90.0, 0.0), {}),
            ("snap_clip.stl", "Snap_clip_1", ROT_Y90, (45.0, 40.0),
             {"brim_type": "auto_brim", "brim_width": "3"}),
            ("snap_clip.stl", "Snap_clip_2", ROT_Y90, (60.0, 40.0),
             {"brim_type": "auto_brim", "brim_width": "3"}),
            ("front_fan.stl", "Front_fan", ROT_REAR,
             (-45.0, 74.0), {})])],
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
          # 21.07: Арахне — користувач перемкнув у Студії (сейв
          # підтвердив), тест №6 друкувався ним; не відкочуємо
          "wall_generator": "arachne",
          "initial_layer_print_height": "0.2"}


def mesh_xml(meshes):
    """XML файлу object_NNN.model. meshes = [(inner_id, uuid, mesh), …] —
    21.07: кілька <object> в одному файлі (mesh деталі + куб-модифікатор)."""
    objs = []
    for inner_id, obj_uuid, m in meshes:
        v = "\n".join('    <vertex x="%.4f" y="%.4f" z="%.4f"/>' % tuple(p)
                      for p in m.vertices)
        t = "\n".join('    <triangle v1="%d" v2="%d" v3="%d"/>' % tuple(f)
                      for f in m.faces)
        objs.append(f'''  <object id="{inner_id}" p:UUID="{obj_uuid}" type="model">
   <mesh>
   <vertices>
{v}
   </vertices>
   <triangles>
{t}
   </triangles>
   </mesh>
  </object>''')
    body = "\n".join(objs)
    return f'''<?xml version="1.0" encoding="UTF-8"?>
<model unit="millimeter" xml:lang="en-US" xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" requiredextensions="p">
 <metadata name="BambuStudio:3mfVersion">1</metadata>
 <resources>
{body}
 </resources>
 <build/>
</model>
'''


def apply_anti_string(s):
    """22.07: анти-стрінг у ВСІ проєкти (вибір користувача після друку
    шматка дна — волосінь лишилась ПІСЛЯ сушки в AMS 38→11% і 250°):
      • nozzle_temperature 255→245 (＋initial_layer) — філаментні ключі,
        diffs-слот [1] (свідомий виняток із правила «філамент не
        чіпаємо», з дозволу користувача);
      • retraction_length 0.8→1.2 — принтерний ключ, diffs-слот [2];
        міняємо ЛИШЕ записи '0.8' (решта '2' — інші конфігурації сопла);
      • wipe у шаблоні ВЖЕ '1' (wipe_distance 2) — нічого не робимо.
    different_settings_to_system = [process, filament, printer]
    (1 філамент у шаблоні)."""
    ch_fil, ch_prn = [], []
    for k in ("nozzle_temperature", "nozzle_temperature_initial_layer"):
        s[k] = ["245"] * len(s[k])
        ch_fil.append(k)
    s["retraction_length"] = ["1.2" if v == "0.8" else v
                              for v in s["retraction_length"]]
    ch_prn.append("retraction_length")
    diffs = s["different_settings_to_system"]
    for idx, ch in ((1, ch_fil), (2, ch_prn)):
        have = set(diffs[idx].split(";")) if diffs[idx] else set()
        diffs[idx] = ";".join(sorted(have | set(ch)))
    return s


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
    vlh_lines = []
    for i, (plate_i, (stl, oname, rot, (dx, dy), oset)) in enumerate(flat):
        oset = dict(oset)               # 21.07: службові ключі — геть
        vlh = oset.pop("_vlh", None)    # з per-object metadata
        mods = oset.pop("_mod", None)   # 22.07: один mod або список
        if isinstance(mods, dict):
            mods = [mods]
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
        mb0, mb1 = m.bounds             # 22.07: модельні межі ДО повороту
        vv = m.vertices @ R
        lo, hi = vv.min(0), vv.max(0)
        px, py = plate_origin(plate_i)
        shift = np.array([
            center + dx - (lo[0] + hi[0]) / 2 + px,
            center + dy - (lo[1] + hi[1]) / 2 + py,
            -lo[2]])
        m = trimesh.Trimesh(vertices=vv + shift, faces=m.faces,
                            process=False)
        meshes = [(inner, inner_uuid, m)]
        mod_parts = []
        for j, mod in enumerate(mods or []):
            # куб-модифікатор поверх деталі — лише швидкості, без
            # окремого об'єкта на пластині. Два режими (22.07):
            #  • z0 — від висоти друку z0 до верху («повільний верх»);
            #  • zmodel — Z-діапазон у МОДЕЛЬНИХ координатах, куб
            #    обертається тим самим R + shift, що й деталь
            #    («повільне дно»: плита дна у FACE_DOWN = верт. слаб)
            if "zmodel" in mod:
                z0m, z1m = mod["zmodel"]
                ext = (mb1[0] - mb0[0] + 10.0, mb1[1] - mb0[1] + 10.0,
                       z1m - z0m)
                cube = trimesh.creation.box(extents=ext)
                cube.apply_translation([(mb0[0] + mb1[0]) / 2,
                                        (mb0[1] + mb1[1]) / 2,
                                        (z0m + z1m) / 2])
                cube = trimesh.Trimesh(vertices=cube.vertices @ R + shift,
                                       faces=cube.faces, process=False)
            else:
                b0, b1 = m.bounds
                ext = (b1[0] - b0[0] + 10.0, b1[1] - b0[1] + 10.0,
                       b1[2] + 5.0 - mod["z0"])
                cube = trimesh.creation.box(extents=ext)
                cube.apply_translation([(b0[0] + b1[0]) / 2,
                                        (b0[1] + b1[1]) / 2,
                                        mod["z0"] + ext[2] / 2])
            mod_part = dict(
                inner=inner + 500 + 10 * j,
                uuid=f"00{oid}9{1 + j}000-81cb-4c03-9d28-80fed5dfa1dc",
                comp_uuid=f"00{oid}9{1 + j}000-b206-40ff-9872-83e8017abed1",
                name=mod["name"], set=mod["set"], faces=len(cube.faces))
            meshes.append((mod_part["inner"], mod_part["uuid"], cube))
            mod_parts.append(mod_part)
        model_parts[path.lstrip("/")] = mesh_xml(meshes)
        if vlh is not None:
            # банди тонкого шару; висоти — у координатах друку деталі
            spans = [(a - lo[2], b - lo[2]) for a, b in vlh["spans_rz"]]
            blk = vlh_ranges(i + 1, spans, vlh["fine"], hi[2] - lo[2])
            if blk:
                vlh_lines.append(blk)
        tr = "1 0 0 0 1 0 0 0 1 0 0 0"
        objects.append(dict(oid=oid, inner=inner, name=oname,
                            path=path, tr=tr,
                            faces=len(m.faces), obj_uuid=obj_uuid,
                            comp_uuid=comp_uuid, item_uuid=item_uuid,
                            oset=oset, plate=plate_i, mods=mod_parts))
        rels.append(
            f'<Relationship Target="{path}" Id="rel-obj-{oid}" '
            'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/'
            '3dmodel"/>')

    def comps(o):
        c = [f'    <component p:path="{o["path"]}" objectid="{o["inner"]}"'
             f' p:UUID="{o["comp_uuid"]}" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>']
        for mp in o["mods"]:
            c.append(f'    <component p:path="{o["path"]}"'
                     f' objectid="{mp["inner"]}"'
                     f' p:UUID="{mp["comp_uuid"]}"'
                     ' transform="1 0 0 0 1 0 0 0 1 0 0 0"/>')
        return "\n".join(c)

    res = "\n".join(
        f'''  <object id="{o["oid"]}" p:UUID="{o["obj_uuid"]}" type="model">
   <components>
{comps(o)}
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
    def parts_meta(o):
        # part id = id МЕША в об'єкт-файлі (objectid компонента) — так
        # матчить Студія (сейв користувача: parts 1/3/5/7 = inner ids);
        # з "1"/"2" куб-модифікатор не матчився → ставав normal_part
        p = [f'''    <part id="{o["inner"]}" subtype="normal_part">
      <metadata key="name" value="{o["name"]}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
      <metadata key="source_file" value="{o["name"]}.stl"/>
      <metadata key="source_object_id" value="0"/>
      <metadata key="source_volume_id" value="0"/>
      <mesh_stat face_count="{o["faces"]}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>''']
        for mp in o["mods"]:
            # 21.07: modifier_part — невідомі ключі part-metadata Студія
            # кладе у volume config (підтверджено сейвом користувача:
            # per-object scalar overrides працюють так само)
            mset = "\n".join(f'      <metadata key="{k}" value="{v}"/>'
                             for k, v in mp["set"].items())
            p.append(f'''    <part id="{mp["inner"]}" subtype="modifier_part">
      <metadata key="name" value="{mp["name"]}"/>
      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>
{mset}
      <mesh_stat face_count="{mp["faces"]}" edges_fixed="0" degenerate_facets="0" facets_removed="0" facets_reversed="0" backwards_edges="0"/>
    </part>''')
        return "\n".join(p)

    obj_meta = "\n".join(f'''  <object id="{o["oid"]}">
    <metadata key="name" value="{o["name"]}"/>
    <metadata key="extruder" value="1"/>
{"".join(chr(10).join(f'    <metadata key="{k}" value="{v}"/>' for k, v in o["oset"].items()) + chr(10) if o["oset"] else "")}
    <metadata face_count="{o["faces"]}"/>
{parts_meta(o)}
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
    settings = apply_anti_string(
        apply_overrides(base_settings, {**COMMON, **spec["over"]}))

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
        if vlh_lines:
            # 21.07: height-range модифікатори (формат сейва Студії)
            z.writestr("Metadata/layer_config_ranges.xml",
                       '<?xml version="1.0" encoding="utf-8"?>\n'
                       '<objects>\n' + "\n".join(vlh_lines)
                       + "\n</objects>")
    extras = []
    if vlh_lines:
        extras.append(f"vlh×{len(vlh_lines)}")
    mod_names = [mp["name"] for o in objects for mp in o["mods"]]
    if mod_names:
        extras.append("mod " + "+".join(mod_names))
    print(f"  {out.name}: пластин {n_plates}, об'єктів {len(objects)}, "
          f"шар {settings['layer_height']}"
          + (f" [{', '.join(extras)}]" if extras else ""))


if __name__ == "__main__":
    with zipfile.ZipFile(TEMPLATE) as z:
        base = json.loads(z.read("Metadata/project_settings.config"))
    for name, spec in PROJECTS.items():
        build_project(name, spec, None, base)
