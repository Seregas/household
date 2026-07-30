"""
floor.py — параметричне ДНО 2U board-tray (концепція 2026-07-02, ітерація 3):
  • несуча РАМА по периметру (FRAME_T=3мм, ширина FRAME_W=10, внутр. кути R1)
  • всередині — заповнення 2мм; соти (pointy-top, R1) КЛІПНУТІ межами площини
    та RAM-вікон — біля країв соти урізані, не пропущені
  • навколо постаментів — зони суцільної площини до найближчих сот, укриті
    шаром +1мм з трикутними кишенями R1 (6 трикутників на комірку ґратки)
  • ВИРІЗИ під RAM 35×75 (R1) за замірами від S3
  • постаменти: циліндр ⌀18×2 → конус ⌀8 @ Z7.55 (S3: перехід → ⌀9×5),
    фаска 0.5 зверху, наскрізні отвори ⌀4
Запуск: .venv/bin/python cad/floor.py
2D-розкладка рахується в shapely, переноситься в build123d полілініями.
"""
import math
from build123d import *
import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.affinity import translate
import params as P
import lattice
from exporter import save

AMIN = (Align.CENTER, Align.CENTER, Align.MIN)
SKIRT_N = 10          # сходинок 45°-спідниці крони (h = TRI_RIB_H/N = 0.1)

# (лінзи-пупирки переїхали в ssd_block.py разом з усією SSD-геометрією)


def interior_box():
    """Внутрішня межа несучої рами (XY)."""
    return (P.WALL_L_X + P.FRAME_W, P.BODY_FRONT_Y + P.FRAME_W,
            P.WALL_R_X - P.FRAME_W, P.REAR_Y - P.FRAME_W)


def _polys(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    if geom.geom_type in ('MultiPolygon', 'GeometryCollection'):
        return [g for g in geom.geoms if g.geom_type == 'Polygon']
    return []                                   # LineString/Point від дегенерацій


# plan_geometry ПЕРЕПИСАНО З НУЛЯ 30.07 (cell-first) і винесено у
# floorplan.py; стара морфологічна реалізація (610 рядків) — у git
# (чекпойнт f65a798).
from floorplan import plan_geometry


def standoff_part():
    """Еталонний постамент: колона ⌀9 Z0..8 з галтеллю R1 біля основи.
    Профіль-револьв (не 3D-філет, за уроком): основа r5.5 до верху корони (Z3),
    дуга R1 → колона r4.5 до Z8. Створюється ПОЗА BuildPart (урок про витік)."""
    r = P.STANDOFF_D / 2
    fr = P.STANDOFF_FIL_R
    zc = P.INFILL_T + P.TRI_RIB_H                # верх корони = 3.0
    with BuildPart() as so:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Polyline((0, 0), (r + fr, 0), (r + fr, zc))
                RadiusArc((r + fr, zc), (r, zc + fr), fr)
                Polyline((r, zc + fr), (r, P.STANDOFF_TOP_Z),
                         (0, P.STANDOFF_TOP_Z), (0, 0))
            make_face()
        revolve(axis=Axis.Z)
    return so.part


def build():
    holes, crown_polys, tri_pockets, skirt = plan_geometry()
    standoff = standoff_part()                   # еталон — поза BuildPart

    with BuildPart() as tray:
        # ── плита на повну висоту рами (3мм); задні кути R3 у 2D-контурі ──
        with BuildSketch(Plane.XY) as fs:
            with BuildLine():
                Polyline(*P.footprint()[:-1], close=True)
            make_face()
            rear_vs = fs.vertices().filter_by(
                lambda v: abs(v.Y - P.REAR_Y) < 1e-6)
            fillet(rear_vs, radius=P.REAR_CORNER_R)
        extrude(amount=P.FRAME_T)

        # ── опустити інтер'єр до 2мм (лишається несуча рама; внутр. кути R1) ──
        x0, y0, x1, y1 = interior_box()
        with BuildSketch(Plane.XY.offset(P.INFILL_T)):
            with Locations(((x0 + x1) / 2, (y0 + y1) / 2)):
                RectangleRounded(x1 - x0, y1 - y0, radius=P.FRAME_CORNER_R)
        extrude(amount=P.FRAME_T - P.INFILL_T + 1, mode=Mode.SUBTRACT)

        # (28.07, фікс п.4: різ сот ПЕРЕНЕСЕНО ПІСЛЯ крони — тепер він
        # наскрізний крізь неї і тримить flush-грань стінки соти; крона
        # в плані перекриває діри на 0.35, різ зрізає перекриття)

        # ── вирізи під RAM-модулі (наскрізні вікна; кути R1) ──
        for k in P.RAM_KEEPOUT.values():
            wx0, wx1 = k['x']; wy0, wy1 = k['y']
            with BuildSketch(Plane.XY.offset(-1)):
                with Locations(((wx0 + wx1) / 2, (wy0 + wy1) / 2)):
                    RectangleRounded(wx1 - wx0, wy1 - wy0, radius=P.RAM_WIN_R)
            extrude(amount=1 + P.INFILL_T + 0.5, mode=Mode.SUBTRACT)

        # ── корона зон постаментів: СПІДНИЦЯ 45° сходинками (28.07,
        # «всі переходи 2→3 мм — під 45°») — рівень i = футпринт,
        # звужений shapely-offset на i·h (h=0.1). Межі до мембрани
        # стають 45°-рампами; наскрізні різи сот/кишень нижче
        # відновлюють точні вертикальні стінки патерну. ──
        _h = P.TRI_RIB_H / SKIRT_N
        for i, level in enumerate(skirt):
            with BuildSketch(Plane.XY.offset(P.INFILL_T + i * _h)):
                for poly in level:
                    with BuildLine():
                        Polyline(*list(poly.exterior.coords)[:-1],
                                 close=True)
                    make_face()
                    for ring in poly.interiors:
                        rp = sg.Polygon(ring)
                        if abs(rp.area) < 0.8:
                            continue
                        rp = rp.simplify(0.02).buffer(0)
                        if rp.geom_type != 'Polygon' or rp.area < 0.8:
                            continue
                        with BuildLine():
                            Polyline(*list(rp.exterior.coords)[:-1],
                                     close=True)
                        make_face(mode=Mode.SUBTRACT)
            extrude(amount=_h)

        # ── соти (кліпнуті) — наскрізь крізь заповнення І крону ──
        # (28.07: перенесено ПІСЛЯ крони, глибина повна — крона в плані
        # перекриває діри на 0.35, цей різ зрізає перекриття → грань
        # стінки соти ОДНА на всі шари Z1..3, коінцидентних площин нема)
        with BuildSketch(Plane.XY.offset(-1)):
            for g in holes:
                with BuildLine():
                    Polyline(*list(g.exterior.coords)[:-1], close=True)
                make_face()
                # внутрішні кільця (напр. пад кріплення ЦІЛКОМ усередині
                # соти): без цього острів зникав — бонка висіла в повітрі
                for ring in g.interiors:
                    with BuildLine():
                        Polyline(*list(ring.coords)[:-1], close=True)
                    make_face(mode=Mode.SUBTRACT)
        extrude(amount=1 + P.INFILL_T + P.TRI_RIB_H + 0.5,
                mode=Mode.SUBTRACT)

        # ── ізогрід НАСКРІЗНИЙ (04.07): ті ж трикутні кишені прорізаються
        # крізь 2мм заповнення → решітка 3мм на просвіт (жорсткість ×2.5
        # у згині проти суцільної двійки, обдув; комірці ⌀17 суцільні) ──
        # (29.07, правило 1: різ ТОЧНИМИ coords, без simplify — chord
        # error 0.02 зсував межі кишень → ребра ізогріду 1.51-1.52)
        with BuildSketch(Plane.XY.offset(-1)):
            for pk in tri_pockets:
                rp = pk.buffer(0)
                if rp.geom_type != 'Polygon' or rp.area < 0.8:
                    continue
                with BuildLine():
                    Polyline(*list(rp.exterior.coords)[:-1], close=True)
                make_face()
        extrude(amount=1 + P.INFILL_T + P.TRI_RIB_H + 0.5,
                mode=Mode.SUBTRACT)

        # ── постаменти: 4 однакові колони ⌀9 з галтеллю R1 ──
        with Locations(*[(x, y, 0) for x, y in P.STANDOFF_XY.values()]):
            add(standoff)

        # ── зрізати частини постаментів, що нависають у RAM-вікна ──
        # (сегмент бази S3 + скибка конуса; кліренс до модуля був 0.06мм)
        for k in P.RAM_KEEPOUT.values():
            wx0, wx1 = k['x']; wy0, wy1 = k['y']
            with BuildSketch(Plane.XY.offset(-1)):
                with Locations(((wx0 + wx1) / 2, (wy0 + wy1) / 2)):
                    RectangleRounded(wx1 - wx0, wy1 - wy0, radius=P.RAM_WIN_R)
            extrude(amount=1 + P.FRAME_T + 1, mode=Mode.SUBTRACT)

        # ── СІТКА АДДОНІВ (20.07, snap-fit — cad/snap_kin.py): комірка =
        # СИМЕТРИЧНИЙ слот у мембрані (наскрізь) + ПІДМЕМБРАННА КИШЕНЯ
        # знизу Z0..LEDGE (1.4) — зуб зачепа чіпляється під мембрану і
        # ХОВАЄТЬСЯ В ТОВЩІ ДНА (знизу корпусу не видно, нижче Z0 нічого).
        # Кишеня відкрита вниз — крізь неї зуби притискаються при
        # зніманні. Друк лицем вниз: стінки вертикальні, без підтримок.
        with BuildSketch(Plane.XY.offset(-1)):
            with Locations(*[(cx, ry)
                             for cx in P.ANCHOR_COLS
                             for ry in P.ANCHOR_ROWS]):
                RectangleRounded(P.SNAP_SLOT_X, 2 * P.SNAP_SLOT_HALF,
                                 radius=P.SNAP_SLOT_R)
        extrude(amount=1 + P.FRAME_T + 1, mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(-1)):
            with Locations(*[(cx, ry)
                             for cx in P.ANCHOR_COLS
                             for ry in P.ANCHOR_ROWS]):
                RectangleRounded(P.SNAP_SLOT_X, 2 * P.SNAP_TOOTH_POCKET_Y,
                                 radius=0.8)
        extrude(amount=1 + P.SNAP_LEDGE_Z, mode=Mode.SUBTRACT)
        # (17.07 #3: пази язиків аддона в передній рамі + лійка-розхил
        # ВИДАЛЕНІ — язики тепер у площині ламелі аддона, у кишенях
        # смуги-обідка ПАНЕЛІ (front.py); рама дна суцільна)

        # ── наскрізні отвори ⌀4 ──
        for (x, y) in P.STANDOFF_XY.values():
            with Locations((x, y, -1)):
                Cylinder(P.STANDOFF_HOLE_D / 2, P.STANDOFF_TOP_Z + 2,
                         align=AMIN, mode=Mode.SUBTRACT)

        # ── фаска на верхньому зовнішньому ребрі постаментів ──
        top_rims = (tray.edges()
                    .filter_by(GeomType.CIRCLE)
                    .filter_by(lambda e: abs(e.arc_center.Z - P.STANDOFF_TOP_Z) < 1e-6
                               and e.radius > P.STANDOFF_HOLE_D / 2 + 0.5))
        chamfer(top_rims, length=P.STANDOFF_CHAMFER)

        # ── 20.07 (зонд probe_print): дозріз колон над RAM-вікнами ──
        # Різ вище (до Z4) лишав скибку колони S3 z4..7.55 НАД вікном B —
        # у друці лицем вниз вона стартувала ОСТРОВОМ у повітрі (6.5 мм²,
        # висота 167). Різ ПІСЛЯ фаски (chamfer хоче повне коло обода;
        # спроба «різ до фаски» валила chamfer на дузі+хорді). Проти
        # копланарності зі стінками старого різу (invalid-шелл, урок
        # 02.07): футпринт +0.1 назовні, низ Z3.5 — у повітрі вікна,
        # жодної спільної площини. Зачіпає ЛИШЕ колону (обідок/корона
        # закінчуються на Z3); кліренс до RAM-модуля стає на 0.1 більший.
        for k in P.RAM_KEEPOUT.values():
            wx0, wx1 = k['x']; wy0, wy1 = k['y']
            with BuildSketch(Plane.XY.offset(P.FRAME_T + 0.5)):
                with Locations(((wx0 + wx1) / 2, (wy0 + wy1) / 2)):
                    RectangleRounded(wx1 - wx0 + 0.2, wy1 - wy0 + 0.2,
                                     radius=P.RAM_WIN_R)
            extrude(amount=P.STANDOFF_TOP_Z - P.FRAME_T + 1,
                    mode=Mode.SUBTRACT)

        # ── 24.07: жертовні МЕМБРАНИ у RAM-вікнах + ФІНИ під колони ──
        # (друк №3: «провисають отвори під пам'ять» — у FACE_DOWN верхні
        # кромки вікон = мости 75/35мм. Після друку все викушується/
        # виламується. ДОДАВАТИ ПІСЛЯ всіх різів вікон (z≥3.5 їх не
        # чіпає) і після chamfer (не збити фільтр ребер).)
        # 24.07 ч.4 — ГОФРА («жорсткість у площині згину, не в
        # стискання»): мембрана MEM_T=0.5 хвиляста — синус середньої
        # лінії ±MEM_WAVE_A уздовж довгої осі вікна, конверт Z0.5..1.5
        # у товщі інфілу 2.0. Побудова: призма конверта (футпринт
        # membrane2d) ∩ хвиляста плита — бічні/нижні містки стають
        # хвилястими автоматично. Верхня кромка (стеля FACE_DOWN) без
        # прямих містків — ФІНИ-ПЛАВНИКИ кожні ~MEM_FLAG_PITCH (25.07,
        # раніше короткі косинки 45°): лезо MEM_FLAG_W, що виростає з
        # конверта гофри і за MEM_FLAG_RUN (~7°) вливається у повну
        # товщу інфілу, вросток 0.5 у тіло за кромкою. Прольоти стелі
        # ~11 → ~5.8 мм.
        zc = P.INFILL_T / 2                       # серединна площина 1.0
        env0 = zc - P.MEM_T / 2 - P.MEM_WAVE_A    # конверт гофри 0.5
        env1 = zc + P.MEM_T / 2 + P.MEM_WAVE_A    #               1.5
        for name, k in P.RAM_KEEPOUT.items():
            wx0, wx1 = k['x']; wy0, wy1 = k['y']
            mem = lattice.membrane2d(wx0, wy0, wx1, wy1, P.RAM_WIN_R,
                                     open_side='v1')
            # позиції фінів рахуємо ДО патерна — keep-смуги мають
            # збігтися з реальними (для B — після снапу на вісь S3)
            xs = lattice.flag_spots(wx0, wx1)
            if name == 'B':
                sx3 = P.STANDOFF_XY['S3'][0]
                i = min(range(len(xs)), key=lambda j: abs(xs[j] - sx3))
                xs[i] = sx3
            # 25.07 — дрібний ізогрід («Ізогрід дрібний», вибір
            # користувача): наскрізні трикутники з 2D-футпринта ДО
            # призми — наскрізність через prism ∩ wave автоматична.
            # keep: смуги під коренями фінів-плавників (лезо 0.8 має
            # виростати з суцільної мембрани, не з ребра патерна) і під
            # поясом вростка фіна S3 (вікно B).
            keep = [sg.box(u - 1.5, wy1 - P.MEM_FLAG_RUN - 1.0,
                           u + 1.5, wy1) for u in xs]
            if name == 'B':
                keep.append(sg.box(sx3 - 1.5, wy1 - 7.0,
                                   sx3 + 1.5, wy1))
            iso = lattice.mem_iso_holes(mem, keep)
            if iso:
                mem = mem.difference(unary_union(iso))
            with BuildSketch(Plane.XY.offset(env0),
                             mode=Mode.PRIVATE) as psk:
                for g in _polys(mem):
                    with BuildLine():
                        Polyline(*g.exterior.coords)
                    make_face()
                    for hg in g.interiors:
                        with BuildLine():
                            Polyline(*hg.coords)
                        make_face(mode=Mode.SUBTRACT)
            prism = extrude(psk.sketch, amount=env1 - env0,
                            mode=Mode.PRIVATE)

            along_x = (wx1 - wx0) >= (wy1 - wy0)  # A: по x; B: по y
            a0 = (wx0 if along_x else wy0) - 1.0
            a1 = (wx1 if along_x else wy1) + 1.0

            def zmid(a, a0=a0):
                return zc + P.MEM_WAVE_A * math.sin(
                    2 * math.pi * (a - a0) / P.MEM_WAVE_P)

            ns = int(math.ceil((a1 - a0) / 0.5))
            samp = [a0 + (a1 - a0) * i / ns for i in range(ns + 1)]
            top = [(a, zmid(a) + P.MEM_T / 2) for a in samp]
            bot = [(a, zmid(a) - P.MEM_T / 2) for a in reversed(samp)]
            if along_x:
                wpl = Plane.XZ.offset(-(wy1 + 1.0))   # площина y=wy1+1
                wamt = wy1 - wy0 + 2.0                # екструзія → wy0−1
            else:
                wpl = Plane.YZ.offset(wx0 - 1.0)
                wamt = wx1 - wx0 + 2.0
            with BuildSketch(wpl, mode=Mode.PRIVATE) as wsk:
                with BuildLine():
                    Polyline(*(top + bot + [top[0]]))
                make_face()
            wave = extrude(wsk.sketch, amount=wamt, mode=Mode.PRIVATE)
            add(prism & wave)

            # ФІНИ-плавники на верхній кромці (стеля вікна у FACE_DOWN);
            # для B найближча позиція → на вісь S3 (анкер фіна — його
            # шари вище краю ядра висіли б у повітрі).
            # 25.07: старт = ВЕСЬ конверт гофри (env0..env1) — фін
            # гарантовано зростається з мембраною, де б не була фаза
            # хвилі (для B хвиля йде вздовж y, тобто вздовж самого фіна);
            # далі перехід до повної товщі за MEM_FLAG_RUN (~7°) і
            # вросток 0.5 у тіло за кромкою.
            # (xs пораховано вище, до патерна — keep-смуги збігаються)
            y0f = wy1 - P.MEM_FLAG_RUN
            for u in xs:
                with BuildSketch(Plane.YZ.offset(u - P.MEM_FLAG_W / 2),
                                 mode=Mode.PRIVATE) as fk:
                    with BuildLine():
                        Polyline((y0f, env0), (y0f, env1),
                                 (wy1, P.INFILL_T),
                                 (wy1 + 0.5, P.INFILL_T),
                                 (wy1 + 0.5, 0.0),
                                 (wy1, 0.0),
                                 (y0f, env0))
                    make_face()
                add(extrude(fk.sketch, amount=P.MEM_FLAG_W,
                            mode=Mode.PRIVATE))

        # фіни S1/S2/S4 (collar-тип): лезо PED_FIN_T по X під нижньою
        # хордою колони (y=cy−4.5), верх з зазором PED_FIN_GAP; анкер —
        # вросток z2.5..3 у суцільний комірець ⌀17 (на x=cx±0.4 комірець
        # сягає y=cy±8.49); виїмка знизу обходить галтель-кільце
        # (кліренс ≥0.15 при z≈3.05); гіпотенуза 45° — ріст самонесучий
        rr = P.STANDOFF_D / 2
        for sname in ('S1', 'S2', 'S4'):
            cx, cy = P.STANDOFF_XY[sname]
            yt = cy - rr - P.PED_FIN_GAP             # верх = cy−4.65
            with BuildSketch(Plane.YZ.offset(cx - P.PED_FIN_T / 2)) as fsk:
                with BuildLine():
                    Polyline((cy - 8.4, 2.5), (cy - 8.4, 3.2),
                             (yt, 3.2 + (yt - (cy - 8.4))),   # 45° → 6.95
                             (yt, 4.6), (cy - 5.65, 3.6),
                             (cy - 5.65, 2.5), (cy - 8.4, 2.5))
                make_face()
            extrude(fsk.sketch, amount=P.PED_FIN_T)

        # фін S3 — membrane-тип: колона зрізана вікном B (грань зрізу
        # y=68.0, комірця під нею нема) → фін висить на гофро-мембрані:
        # пояс вростка = ПОВНИЙ конверт гофри ±0.1 (0.4..1.6 — ловить
        # хвилю на будь-якій фазі), ріст 45°, верх 0.15 під гранню
        # зрізу; шари вище краю ядра анкеряться в косинку на осі S3
        cx3 = P.STANDOFF_XY['S3'][0]
        yb = P.RAM_KEEPOUT['B']['y'][1] + 0.1 - P.PED_FIN_GAP   # 67.85
        fin_lo, fin_hi = env0 - 0.1, env1 + 0.1                 # 0.4..1.6
        with BuildSketch(Plane.YZ.offset(cx3 - P.PED_FIN_T / 2)) as f3k:
            with BuildLine():
                Polyline((yb - 5.6, fin_lo), (yb - 5.6, fin_hi),
                         (yb, fin_hi + 5.6), (yb, fin_lo),
                         (yb - 5.6, fin_lo))
            make_face()
        extrude(f3k.sketch, amount=P.PED_FIN_T)

    return tray.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "floor")
