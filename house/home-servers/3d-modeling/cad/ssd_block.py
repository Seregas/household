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
        # ── база на ПОЛОЗАХ (08.07): 3 лижі 3мм під рейками — продув
        # під базою (дно корпусу там соти); мости бази між полозами 6-7мм
        with BuildSketch(Plane.XY.offset(P.SSD_SIT_Z + P.SSD_SKID_H)) as bs:
            with Locations(((bx0f + bx1f) / 2, (by0f + by1f) / 2)):
                RectangleRounded(bx1f - bx0f, by1f - by0f, radius=2.0)
        extrude(bs.sketch, amount=P.SSD_BASE_T)
        for sk0, sk1 in ((bx0f, bx0f + 3.0),
                         (P.SSD_DIV_X[0] - 0.6, P.SSD_DIV_X[1] + 0.9),
                         (bx1f - 3.0, bx1f)):
            with BuildSketch(Plane.XY.offset(P.SSD_SIT_Z)) as sks:
                with Locations(((sk0 + sk1) / 2,
                                (by0f + P.SSD_SKID_Y1) / 2)):
                    RectangleRounded(sk1 - sk0, P.SSD_SKID_Y1 - by0f,
                                     radius=1.0)
            extrude(sks.sketch, amount=P.SSD_SKID_H + 0.1)
        # задній поперечний полоз — опора хвоста бази при друці
        with BuildSketch(Plane.XY.offset(P.SSD_SIT_Z)) as skr:
            with Locations(((bx0f + bx1f) / 2,
                            sum(P.SSD_SKID_REAR) / 2)):
                RectangleRounded(bx1f - bx0f,
                                 P.SSD_SKID_REAR[1] - P.SSD_SKID_REAR[0],
                                 radius=1.0)
        extrude(skr.sketch, amount=P.SSD_SKID_H + 0.1)

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
        rail_fields = (
            ((P.SSD_DIV_X[0], P.SSD_DIV_X[1]),
             sg.box(y0s + P.SSD_B_SHIFT - 2.0, z0 + 2.0,
                    P.SSD_RAIL_Y_END - 2.0, z0 + 22.0),
             lens_ko + deck_ko + stop_ko),
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

        # ── SNAPFIT (09.07, tool-less): передні ЯЗИКИ на полозах ──
        # язики в4.4-фінал (09.07: «вусики не вусики, а замкнені
        # навколо зачепів конструкції» — якорі/містки ГЕТЬ): відкрита
        # консоль від полоза вістрям уперед, припіднята 0.4 над рамою;
        # хід установки ВПЕРЕД (поклав позаду на 4 → зсунув уперед до
        # клацання → опустив зад, гачки клац). Верхівка: ГОРБИК R0.8
        # біля кінчика (натяг 0.15 лише при проході під дахом) заскакує
        # ЗА передню кромку даху = стоп назад (защіпка не витягне);
        # стоп уперед = зуби гачків у пазу; легкий клин до кореня —
        # дах дотискає блок до дна наприкінці ходу
        for xc in P.SNAP_TAB_XC:
            # ГОЛОВА лижі (09.07 тест-фідбек «пришив козі рукав»):
            # квадратний блок ширини язика накриває скруглений торець
            # лижі — язик виростає з рівної грані, силует суцільний
            with Locations((xc, (by0f - 0.1 + by0f + 6.0) / 2,
                            P.SSD_SIT_Z)):
                Box(P.SNAP_TAB_W, 6.1, P.SSD_SKID_H + 0.1, align=AMIN)
            with BuildSketch(Plane.YZ.offset(xc - P.SNAP_TAB_W / 2)) as tw:
                with BuildLine():
                    Polyline((P.SNAP_TAB_Y[0], P.SNAP_TAB_Z[0]),
                             (P.SNAP_TAB_Y[0], 5.1),
                             (2.4, 5.1),                 # западина
                             (by0f + 0.1, 5.5),          # клин-дотиск
                             (by0f + 0.1, P.SNAP_TAB_Z[0]),
                             close=True)
                make_face()
            extrude(tw.sketch, amount=P.SNAP_TAB_W)
            # горбик: півциліндр уздовж X у западині біля кінчика,
            # втоплений — верх 5.75 (дах 5.6 → натяг 0.15 при проході)
            with Locations(Location((xc, 1.85, 4.95), (0, 90, 0))):
                Cylinder(0.8, P.SNAP_TAB_W)

        # ── гачки v4 (09.07 вечір): два плеча з хвоста бази йдуть НАД
        # бортиком (Z8) назад; від кожного — горизонтальна пружна БАЛКА
        # вздовж X (схрещені, рознесені по Y/Z), на вільному кінці стопа
        # з зубом ВПЕРЕД у паз задньої грані бортика. Натяг тисне блок
        # назад = затискає язики у скобах. Згин балок — у площині шарів ──
        rear_f = P.REAR_Y                       # задня грань бортика 113.5
        for (ax0, ax1), (fx0_, fx1_), (lz0, lz1), by0_ in (
                (P.SNAP_ARM_L_X, P.SNAP_FOOT_R_X, P.SNAP_LAY_HI, 115.8),
                (P.SNAP_ARM_R_X, P.SNAP_FOOT_L_X, P.SNAP_LAY_LO, 114.4)):
            by1_ = by0_ + 1.1
            # колона на базі + рука назад над бортиком до балки
            cy0, cy1 = P.SNAP_HOOK_COL_Y
            with Locations(((ax0 + ax1) / 2, (cy0 + cy1) / 2,
                            P.SSD_BASE_TOP - 0.2)):
                Box(ax1 - ax0, cy1 - cy0, lz1 - (P.SSD_BASE_TOP - 0.2),
                    align=AMIN)
            with Locations(((ax0 + ax1) / 2, (cy0 + by1_) / 2, lz0)):
                Box(ax1 - ax0, by1_ - cy0, lz1 - lz0, align=AMIN)
            # балка вздовж X (пружна, товщина Y = SNAP_BEAM_T)
            bx0_, bx1_ = min(ax0, fx0_), max(ax1, fx1_)
            with Locations(((bx0_ + bx1_) / 2,
                            by0_ + P.SNAP_BEAM_T / 2, lz0)):
                Box(bx1_ - bx0_, P.SNAP_BEAM_T, lz1 - lz0, align=AMIN)
            # стопа: від балки вниз за задньою гранню, перед 113.45
            # (0.05 натягу на грань — прижим); зуб уперед у паз.
            # Ліва стопа Г-подібна: її лезо йде вниз ПОЗАДУ шару правої
            # балки (y≥115.6), а вперед до грані виступає лише НИЖЧЕ
            # цього шару (z≤9.6) — балки схрещені, не перетинаються
            if lz1 > 12.0:                     # лівий гачок (верхній шар)
                with Locations(((fx0_ + fx1_) / 2, (115.6 + by1_) / 2,
                                3.0)):
                    Box(fx1_ - fx0_, by1_ - 115.6, lz1 - 3.0, align=AMIN)
                with Locations(((fx0_ + fx1_) / 2,
                                (rear_f - 0.05 + by1_) / 2, 3.0)):
                    Box(fx1_ - fx0_, by1_ - (rear_f - 0.05), 9.6 - 3.0,
                        align=AMIN)
            else:                              # правий гачок — суцільна
                with Locations(((fx0_ + fx1_) / 2,
                                (rear_f - 0.05 + by1_) / 2, 3.0)):
                    Box(fx1_ - fx0_, by1_ - (rear_f - 0.05), lz1 - 3.0,
                        align=AMIN)
            with Locations(((fx0_ + fx1_) / 2,
                            (rear_f - 0.05 - P.SNAP_TOOTH_D
                             + rear_f - 0.05) / 2,
                            P.SNAP_RAIL_Z[0] + 0.2)):
                Box(fx1_ - fx0_, P.SNAP_TOOTH_D,
                    P.SNAP_RAIL_Z[1] - 0.2 - (P.SNAP_RAIL_Z[0] + 0.2),
                    align=AMIN)
            # ПОЛИЧКА (09.07): виступ стопи над гребенем бортика
            # (зазор 0.3): при підйомі заду сідає на бортик — вертикаль
            # тримає бортик, а не тонка балка (1×1.1 гнеться)
            with Locations(((fx0_ + fx1_) / 2, (112.25 + rear_f + 0.05)
                            / 2, 8.2)):
                Box(fx1_ - fx0_, rear_f + 0.05 - 112.25, 1.2, align=AMIN)
            # кулачок: клин знизу зуба (з'їзд по скругленню гребеня)
            tip = rear_f - 0.05 - P.SNAP_TOOTH_D
            with BuildSketch(Plane((0, 0, 0), x_dir=(0, 1, 0),
                                   z_dir=(1, 0, 0)).offset(fx0_ - 0.1))                     as cam:
                with BuildLine():
                    Polyline((tip - 0.01, P.SNAP_RAIL_Z[1] - 0.6),
                             (tip - 0.01, 2.9),
                             (rear_f + 0.01, 2.9),
                             (rear_f + 0.01, P.SNAP_RAIL_Z[0] + 0.1),
                             close=True)
                make_face()
            extrude(cam.sketch, amount=(fx1_ - fx0_) + 0.2,
                    mode=Mode.SUBTRACT)

    return blk.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "ssd_block")
