"""
ssd_block.py — SSD-кошик ОКРЕМОЮ ДЕТАЛЛЮ (08.07, рішення користувача):
друк корпусу лицем вниз робив рейки недрукованими консолями → блок
друкується окремо дном вниз і прикручується до дна корпусу.

Конструкція (усе в СИСТЕМІ КОРПУСУ, щоб координати збігались зі стінкою):
  • база 2мм (Z2..4, футпринт SSD_BASE_X×SSD_BASE_Y, кути R2);
  • на базі — вся SSD-геометрія (перенесена з floor.py, «підлога» тепер
    SSD_BASE_TOP=4): рейки з бульносом, перегородка, упори-панелі з hex,
    підпорка, постаменти-містки з палубами, рампи, лінзи-пупирки,
    ромбілі рейок, торцеві філети;
  • кріплення: 3×M3 крізь базу (⌀3.4) у дно корпусу (самонаріз ⌀2.9);
    гвинти дисків M3 ідуть знизу крізь дно корпусу (⌀6.2 прохід) і базу
    (⌀6.2) до палуб (⌀3.4) — тримають диски, блок тримають власні гвинти.
  • канал A відкритий праворуч — закривається правою стінкою корпусу
    (диск A спирається на неї); база на 0.3 не доходить до стінки.

Розкладка 08.07 (п.7): канали 7.0 (слоти 5.8), пакет до стінки (зазор до
кулера LSI ~4.1), диски вдаль на +6 (задні кінці за краєм материнки).

Запуск: .venv/bin/python cad/ssd_block.py → out/ssd_block.step/.stl
"""
import math
from build123d import *
import shapely.geometry as sg
import params as P
import lattice
from exporter import save

AMIN = (Align.CENTER, Align.CENTER, Align.MIN)

# прототип «пупирки»-лінзи — ПОЗА білдерами (урок про Sphere/scale)
LENS = scale(Sphere(1.0), (0.85, 2.4, 2.4))


def build():
    z0 = P.SSD_BASE_TOP                    # «підлога» блока = 4.0
    (a0, a1), (b0, b1) = P.SSD_SLOT_X
    y0s, y1s = P.SSD_Y
    cxa = sum(P.SSD_CH_A) / 2              # 131.4, центр каналу A
    cxb = sum(P.SSD_CH_B) / 2              # 123.2, центр каналу B
    bx0f, bx1f = P.SSD_BASE_X
    by0f, by1f = P.SSD_BASE_Y

    with BuildPart() as blk:
        # ── СУЦІЛЬНИЙ НИЗ (10.07, фідбек: «продуву там і так немає —
        # скоби та лижі перекрили; суцільний з рідким заповненням
        # зекономить матеріал і час»): один слаб Z3..8 замість полозів
        # і тонкої бази-мостів — слайсер дає периметр+інфіл 10-15%
        # замість 100%-тонкостінок; стоїть на рамі (над підлогою 1мм).
        # 20.07: слаб від САМОГО переду (by0f=5.0); блок тримають ДВА
        # універсальні snap-fit зачепи (snap_clip.py) у Т-пазах слаба
        # (бічне вставлення) — SNAP_SSD_CELLS (122.8,Y11) і
        # (130.6,Y71), носи в протилежні боки ──
        with BuildSketch(Plane.XY.offset(P.SSD_SIT_Z)) as bs:
            with Locations(((bx0f + bx1f) / 2, (by0f + by1f) / 2)):
                RectangleRounded(bx1f - bx0f, by1f - by0f, radius=2.0)
        extrude(bs.sketch, amount=P.SSD_BASE_TOP - P.SSD_SIT_Z)
        # ── ЗРІЗ під ТРАМПЛІН бортика (13.07): в5.2 опустив низ слаба
        # до Z3 по всій довжині, а трамплін (walls.py: дуга Y98.5 Z3 →
        # Y110.5 Z8) на кінці слаба (107.8) сягає Z5.79 — колізія
        # 120мм³, блок не сідав. Повертаю задум в4: низ у зоні
        # трампліна Z6 («майже спирається», зазор 0.21 на кінці);
        # стеля зрізу при друку дном вниз = міст 9.5мм упоперек ──
        ys_tr = P.REAR_Y - P.BEAD_W + 2.0 - 12.0       # старт дуги 98.5
        with Locations(((bx0f + bx1f) / 2, (ys_tr - 0.1 + by1f + 1) / 2,
                        P.SSD_SIT_Z - 0.1)):
            Box(bx1f - bx0f + 2, by1f + 1 - (ys_tr - 0.1),
                6.0 - (P.SSD_SIT_Z - 0.1), align=AMIN, mode=Mode.SUBTRACT)

        # ── рейки: перегородка + внутрішня (профіль із лійкою, бульнос) ──
        rails = ((P.SSD_DIV_X[0], P.SSD_DIV_X[1],
                  ((y0s + P.SSD_B_SHIFT - 4, P.SSD_RAIL_Y_END),)),
                 (P.SSD_INNER_X[0], P.SSD_INNER_X[1],
                  ((P.SSD_INNER_Y[0], P.SSD_INNER_Y[1]),)))
        for rx0, rx1, runs in rails:
            cx = (rx0 + rx1) / 2
            w = rx1 - rx0
            hg, ht = P.SSD_RAIL_GRIP, P.SSD_RAIL_H
            t2 = P.SSD_RAIL_TOP / 2
            for ry0, ry1 in runs:
                with BuildSketch(Plane((cx, ry0, z0),
                                       x_dir=(-1, 0, 0),
                                       z_dir=(0, 1, 0))) as tz:
                    with BuildLine():
                        Polyline((-w / 2, 0), (w / 2, 0), (w / 2, hg),
                                 (t2, ht), (-t2, ht), (-w / 2, hg),
                                 (-w / 2, 0))
                    make_face()
                    fillet(tz.vertices().filter_by(
                        lambda v: v.Y > ht - 0.01), radius=0.55)
                extrude(tz.sketch, amount=ry1 - ry0)

        # ── ЛОЖА для SSD (09.07 v3): упор+постамент = єдина поверхня:
        # згори упор іде по торцю диска, ków R2.5 завертає ПІД диск і
        # переходить у палубу (верх 16 = низ диска) з отвором M3; ложа
        # втоплені торцями в суцільні стінки каналів (ніжок нема);
        # переднє/заднє ложе розділені — вентиляція під диском ──
        for ch, y0d, y1d in ((P.SSD_CH_A, P.SSD_Y[0], P.SSD_Y[1]),
                             (P.SSD_CH_B, P.SSD_Y[0] + P.SSD_B_SHIFT,
                              P.SSD_Y[1] + P.SSD_B_SHIFT)):
            fx0, fx1 = ch[0] - 0.3, min(ch[1] + 0.3, bx1f)
            for sgn, yd in ((+1, y0d), (-1, y1d)):
                # sgn=+1: переднє ложе (упор перед диском), -1: заднє
                # (в4.2: задні ложа ПОВЕРНУТО 1:1 — прибирати без
                # погодження було помилкою; опору дають похилі
                # продовження стінок каналів нижче)
                g = yd - sgn * 0.2            # грань упору (зазор 0.2)
                yo = g - sgn * P.SSD_FENCE_T  # зовнішня грань упору
                pe = yd + 13.4 if sgn > 0 else yd - 18.0
                with BuildSketch(Plane.YZ.offset(fx0)) as cr:
                    with BuildLine():
                        Polyline((yo, 14.0), (yo, 21.0),
                                 (g - sgn * 1.5, 21.0),
                                 (g, 19.5),          # завід-фаска
                                 (g, 18.5))
                        RadiusArc((g, 18.5), (g + sgn * 2.5, 16.0),
                                  -sgn * 2.5)        # ków під диск
                        Polyline((g + sgn * 2.5, 16.0), (pe, 16.0),
                                 (pe, 14.0), (yo, 14.0))
                    make_face()
                extrude(cr.sketch, amount=fx1 - fx0)
        # ── опори задніх лож (09.07 в4.2): база тепер закінчується на
        # 107.8 (суцільний бортик) — палуби/упори за нею тримають
        # ПРОДОВЖЕННЯ стінок каналів: низ 45° від (кінець рейок, 8.2)
        # до 13.5, далі рівно; над бортиком (верх 8) не торкаючись ──
        yA = P.SSD_Y[1] + 0.2 + P.SSD_FENCE_T + 0.1          # 117.5
        yB = P.SSD_Y[1] + P.SSD_B_SHIFT + 0.2 + P.SSD_FENCE_T + 0.1
        for (wx0, wx1), yend in ((P.SSD_INNER_X, yB),
                                 (P.SSD_DIV_X, yA),
                                 ((bx1f - 0.8, bx1f), yA)):
            ys = P.SSD_RAIL_Y_END - 0.1
            kink = ys + 13.5 - 8.2          # де 45°-схил сягає 13.5
            pts_ = [(ys, 8.2), (ys, 16.0), (yend, 16.0)]
            if kink < yend - 0.05:
                pts_ += [(yend, 13.5), (kink, 13.5)]
            else:                            # схил упирається в кінець
                pts_ += [(yend, 8.2 + (yend - ys))]
            with BuildSketch(Plane.YZ.offset(wx0)) as wex:
                with BuildLine():
                    Polyline(*pts_, close=True)
                make_face()
            extrude(wex.sketch, amount=wx1 - wx0)

        # права ТОНКА стінка лотка (канал A): своя, 0.8, до низу диска —
        # повітря не тікає з-під диска у зазор до стінки корпусу
        with Locations((bx1f - 0.4, (P.SSD_Y[0] - 2.0 + P.SSD_RAIL_Y_END)
                        / 2, z0)):
            Box(0.8, P.SSD_RAIL_Y_END - (P.SSD_Y[0] - 2.0), 16.0 - z0,
                align=AMIN)

        # ── постаменти-містки з палубами, рампи, отвори M3 ──
        for cx, ch, y_rear in ((cxa, P.SSD_CH_A, P.SSD_Y[1]),
                               (cxb, P.SSD_CH_B, P.SSD_Y[1] + P.SSD_B_SHIFT)):
            for off in (14.0, 90.6):
                yb = y_rear - off
                # (09.07 v3: бокси-палуби видалені — палуби тепер
                # частина ЛОЖ вище; рампи й отвори лишаються)
                # увігнутий трамплін перед отвором (2мм, пологий)
                if cx == cxa or yb > P.SSD_INNER_Y[0]:
                    rx0 = ch[0] - 0.1
                    rx1 = min(ch[1] + 0.1, bx1f)
                    R = (8.2 ** 2 + 2.0 ** 2) / (2 * 2.0)
                    arcp = [(yb - 12.0 + d, z0 + R
                             - math.sqrt(R * R - d * d))
                            for d in [8.2 * k / 8 for k in range(9)]]
                    with BuildSketch(Plane.YZ.offset(rx0)) as ramp:
                        with BuildLine():
                            Polyline(*arcp, (yb - 3.8, z0 - 0.5),
                                     (yb - 12.0, z0 - 0.5),
                                     (yb - 12.0, z0))
                        make_face()
                    extrude(ramp.sketch, amount=rx1 - rx0)
                # M3 наскрізь (палуба ⌀3.4) + прохід головки крізь базу
                with Locations((cx, yb, P.SSD_SIT_Z - 1)):
                    Cylinder(P.SSD_BOSS_HOLE / 2, P.SSD_LIFT + 6,
                             align=AMIN, mode=Mode.SUBTRACT)
                with Locations((cx, yb, P.SSD_SIT_Z - 1)):
                    Cylinder(P.SSD_HEAD_D / 2,
                             P.SSD_SKID_H + P.SSD_BASE_T + 2,
                             align=AMIN, mode=Mode.SUBTRACT)
                # ── C-паз у праву грань (21.07, друк №1): тунель ⌀6.2
                # каналу A закінчується на 134.5, грань блока 134.6 —
                # стінку 0.10 слайсер викидав, кромка виходила щербата.
                # Погоджено «розкрити свідомо»: тунель → C-подібний паз,
                # відкритий у праву грань, той самий Z-діапазон ──
                if cx == cxa:
                    with Locations(((cx + bx1f + 0.5) / 2, yb,
                                    P.SSD_SIT_Z - 1)):
                        Box(bx1f + 0.5 - cx, P.SSD_HEAD_D,
                            P.SSD_SKID_H + P.SSD_BASE_T + 2,
                            align=AMIN, mode=Mode.SUBTRACT)

        # ── торцеві філети рейок (бульнос вертикалей + R2 верхніх кутів) ──
        top_z = z0 + P.SSD_RAIL_H
        ends = ((P.SSD_DIV_X, y0s + P.SSD_B_SHIFT - 4),
                (P.SSD_DIV_X, P.SSD_RAIL_Y_END),
                (P.SSD_INNER_X, P.SSD_INNER_Y[0]),
                (P.SSD_INNER_X, P.SSD_INNER_Y[1]))
        # верхні кути торців: РОЛЛ-ЗРІЗ R2 (box−циліндр) замість
        # 3D-філета — верх рейки вже бульнос R0.55 зі смужкою 0.1,
        # філет по ньому вироджений (пореброво 0/3 на будь-якому R)
        for ex, ey in ends:
            sgn = 1 if ey < 50 else -1        # куди «в тіло» рейки
            with BuildPart(mode=Mode.PRIVATE) as roll:
                with Locations(((ex[0] + ex[1]) / 2,
                                ey + sgn * 1.0, top_z - 1.0)):
                    Box(ex[1] - ex[0] + 0.4, 2.1, 2.2)
                with Locations(((ex[0] + ex[1]) / 2,
                                ey + sgn * 2.0, top_z - 2.0)):
                    Cylinder(2.0, ex[1] - ex[0] + 0.6,
                             rotation=(0, 90, 0), mode=Mode.SUBTRACT)
            add(roll.part, mode=Mode.SUBTRACT)
        for ex, ey in ends:
            try:
                es = blk.edges().filter_by(
                    lambda e: abs(e.center().Y - ey) < 0.05
                    and ex[0] - 0.05 < e.center().X < ex[1] + 0.05
                    and e.bounding_box().size.Z > 5)
                if es:
                    fillet(list(es), radius=0.55)
            except Exception:
                okv = 0
                for e in es:
                    try:
                        fillet([e], radius=0.55)
                        okv += 1
                    except Exception:
                        pass
                print(f"  (i) торець рейки Y{ey}: пореброво {okv}/{len(es)}")



        # ── лінзи-пупирки (лише перегородка, обидві грані, 3 станції) ──
        lens_faces = (
            (P.SSD_DIV_X[1], +1, P.SSD_SLEEPER_Y),
            (P.SSD_DIV_X[0], -1,
             tuple(y + P.SSD_B_SHIFT for y in P.SSD_SLEEPER_Y)))
        for fx, din, stations in lens_faces:
            for sy in stations:
                for bz in (z0 + 10.5, z0 + 18.5):
                    add(Location((fx - din * 0.25, sy, bz)) * LENS)

        # ── ромбілі на рейках (наскрізь; keepout: лінзи/містки/упори) ──
        deck_ys = [P.SSD_Y[1] - o for o in (14.0, 90.6)] \
            + [P.SSD_Y[1] + P.SSD_B_SHIFT - o for o in (14.0, 90.6)]
        lens_ko = [sg.box(sy - 3.5, z0 + 7.0, sy + 3.5, z0 + 22.0)
                   for sy in list(P.SSD_SLEEPER_Y)
                   + [y + P.SSD_B_SHIFT for y in P.SSD_SLEEPER_Y]]
        deck_ko = [sg.box(yb - 4.6, P.SSD_SIT_Z, yb + 4.6, z0 + 9.0)
                   for yb in deck_ys]
        # keepout-и БОРТИКІВ-посадок (09.07: їхні стійки стоять упритул
        # до рейок — наскрізні ромбілі прошивали їх)
        fence_ys = (P.SSD_Y[0] - 0.2 - P.SSD_FENCE_T / 2,
                    P.SSD_Y[0] + P.SSD_B_SHIFT - 0.2 - P.SSD_FENCE_T / 2,
                    P.SSD_Y[1] + 0.2 + P.SSD_FENCE_T / 2,
                    P.SSD_Y[1] + P.SSD_B_SHIFT + 0.2 + P.SSD_FENCE_T / 2)
        stop_ko = [sg.box(yc - 2.0, P.SSD_SIT_Z, yc + 2.0,
                          P.SSD_FENCE_TOP + 1.0) for yc in fence_ys]
        # keepout переднього ЛОЖА диска B (19.07 фідбек: ромбіль
        # 127.17/12.06/11.83 пробивав палубу-посадку 126.06/11.60/15.75)
        cradleB_ko = sg.box(P.SSD_Y[0] + P.SSD_B_SHIFT - 2.0, P.SSD_SIT_Z,
                            P.SSD_Y[0] + P.SSD_B_SHIFT + 6.0, z0 + 9.0)
        rail_fields = (
            ((P.SSD_DIV_X[0], P.SSD_DIV_X[1]),
             sg.box(y0s + P.SSD_B_SHIFT - 2.0, z0 + 2.0,
                    P.SSD_RAIL_Y_END - 2.0, z0 + 22.0),
             lens_ko + deck_ko + stop_ko + [cradleB_ko]),
            ((P.SSD_INNER_X[0], P.SSD_INNER_X[1]),
             sg.box(P.SSD_INNER_Y[0] + 2.0, 17.0,
                    P.SSD_INNER_Y[1] - 2.0, z0 + 22.0),
             [sg.box(yb - 4.6, P.SSD_SIT_Z, yb + 4.6, z0 + 9.0)
              for yb in deck_ys] + stop_ko))
        for (rx0_, rx1_), rfield, kos in rail_fields:
            for ko in kos:
                rfield = rfield.difference(ko)
            rholes = lattice.rhombille_holes(rfield, rfield.bounds[0],
                                             rfield.bounds[1])
            if rholes:
                with BuildSketch(Plane.YZ.offset(rx0_ - 1.0)) as rl:
                    for g in rholes:
                        g = g.simplify(0.01).buffer(0)
                        if g.geom_type != 'Polygon' or g.area < 1.0:
                            continue
                        with BuildLine():
                            Polyline(*list(g.exterior.coords)[:-1],
                                     close=True)
                        make_face()
                extrude(rl.sketch, amount=(rx1_ - rx0_) + 2.0,
                        mode=Mode.SUBTRACT)

        # (08.07 друк №2: кишеня під плінтус видалена — плінтус у зоні
        # SSD прибраний з корпусу разом із дугою кромки)

        # ── ЖЕРТОВНІ МОСТИ під кільцем-опорою головок M3 (21.07, друк
        # №1: низ палуби (Z14) над тунелем ⌀6.2 — міст, нитки навколо
        # ⌀3.4 провисали й засмічували отвір; погоджено «вшити»):
        # плівка 2×0.2 (шар блока) під палубою, натягнута між стінками
        # каналу (короткий чистий міст 5.9/7.0, кінці врощені 0.5 у
        # стінки, верх — 0.2 у палубу); ⌀3.4 над плівкою відновлюється
        # ре-вирізом — гвинт пробиває лише плівку 0.4 по центру,
        # головка сідає на плівку (посадка −0.4 по Z, некритично) ──
        film_z = 14.0                        # низ палуби (ложа)
        film_t = 0.4                         # 2 шари по 0.2
        film_spans = (
            (cxa, (P.SSD_DIV_X[1] - 0.5, bx1f - 0.8 + 0.5),
             tuple(P.SSD_Y[1] - o for o in (14.0, 90.6))),
            (cxb, (P.SSD_INNER_X[1] - 0.5, P.SSD_DIV_X[0] + 0.5),
             tuple(P.SSD_Y[1] + P.SSD_B_SHIFT - o for o in (14.0, 90.6))))
        for fcx, (fx0, fx1), ybs in film_spans:
            for yb in ybs:
                with Locations(((fx0 + fx1) / 2, yb, film_z - film_t)):
                    Box(fx1 - fx0, 7.0, film_t + 0.2, align=AMIN)
                with Locations((fcx, yb, film_z)):
                    Cylinder(P.SSD_BOSS_HOLE / 2, 2.0, align=AMIN,
                             mode=Mode.SUBTRACT)

        # ── Т-ПАЗИ SNAP-FIT ЗАЧЕПІВ (20.07 в6.1 — фідбек: «crush
        # ненадійне; чому б просто не вставити збоку в посадкові
        # місця?»): зачеп ЗАСУВАЄТЬСЯ по X із ближньої грані слаба до
        # ГЛУХОГО УПОРУ (центрує на ccx). Утримання геометрією: вгору —
        # стеля паза, вниз — полиці, по Y — стінки (тертя, зазор
        # 0.08/бік), по X у зборі — нога в слоті дна; при знятому блоці
        # страхує ГОРБИК біля входу (клац при засуванні, стоп назад).
        # Щілина ноги ВІЛЬНА (±0.85): затиснута нога вкоротила б
        # пружну довжину 4.6→2.8 → ε≈8.6% > PETG ~7%.
        # Стеля паза = міст 5.56 у друці дном вниз (як була кишеня).
        # (в6.2: козирок передньої комірки ВИДАЛЕНО — вся снап-сітка
        # +3 по Y, ряд 11: стінка паза 3.22 від переду слаба, R2-кут
        # плану живе; «нашльопка» була некрасива — фідбек) ──
        for ccx, cry, _nose in P.SNAP_SSD_CELLS:
            entry = -1 if (ccx - bx0f) < (bx1f - ccx) else +1
            face = bx0f if entry < 0 else bx1f
            stop = ccx - entry * P.SNAP_CLIP_W / 2
            ox = face + entry * 1.0                  # виліт різу за грань
            cx0, cx1 = sorted((ox, stop))
            sz0, sz1 = P.SNAP_SLIDE_Z
            # широка частина (канал голови)
            with Locations(((cx0 + cx1) / 2, cry, sz0)):
                Box(cx1 - cx0, 2 * P.SNAP_SLIDE_HALF, sz1 - sz0,
                    align=AMIN, mode=Mode.SUBTRACT)
            # щілина ноги (наскрізь униз крізь слаб)
            with Locations(((cx0 + cx1) / 2, cry, P.SSD_SIT_Z - 0.5)):
                Box(cx1 - cx0, 2 * P.SNAP_SLIT_HALF,
                    sz0 - (P.SSD_SIT_Z - 0.5),
                    align=AMIN, mode=Mode.SUBTRACT)
            # горбик-стопор на +Y стінці біля входу: вертикальний
            # циліндр R0.4, виступ 0.25 у канал (натяг об голову 0.17,
            # кулачок = сам радіус); після посадки — позаду зачепа
            xb = ccx + entry * (P.SNAP_CLIP_W / 2 + P.SNAP_BUMP_R)
            yb = cry + P.SNAP_SLIDE_HALF + (P.SNAP_BUMP_R
                                            - P.SNAP_BUMP_OFF)
            with Locations((xb, yb, sz0)):
                Cylinder(P.SNAP_BUMP_R, sz1 - sz0, align=AMIN)

    return blk.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "ssd_block")
