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
                g = yd - sgn * 0.2            # грань упору (зазор 0.2)
                yo = g - sgn * P.SSD_FENCE_T  # зовнішня грань упору
                pe = yd + sgn * 13.2          # кінець палуби (за отвором)
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
            # проріз під гачок у задньому упорі B
            if ch is P.SSD_CH_B:
                with Locations((P.SNAP_LATCH_XC, y1d + 1.1,
                                (14.0 + 21.0) / 2)):
                    Box(P.SNAP_ARM_W + 2.4, P.SSD_FENCE_T + 3.0,
                        21.0 - 14.0 + 2, mode=Mode.SUBTRACT)
        # права ТОНКА стінка лотка (канал A): своя, 0.8, до низу диска —
        # повітря не тікає з-під диска у зазор до стінки корпусу
        with Locations((bx1f - 0.4, (P.SSD_Y[0] - 2.0 + P.SSD_Y[1]
                                     + 2.0) / 2, z0)):
            Box(0.8, P.SSD_Y[1] + 2.0 - (P.SSD_Y[0] - 2.0), 16.0 - z0,
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
        for ex, ey in ends:
            try:
                es = blk.edges().filter_by(
                    lambda e: abs(e.center().Y - ey) < 0.05
                    and ex[0] - 0.05 < e.center().X < ex[1] + 0.05
                    and e.bounding_box().size.Z > 5)
                if es:
                    fillet(list(es), radius=0.55)
            except Exception as exn:
                print("  (!) торець рейки:", exn)
        for ex, ey in ends:
            es = blk.edges().filter_by(
                lambda e: abs(e.center().Y - ey) < 0.6
                and abs(e.center().Z - top_z) < 0.6
                and ex[0] - 0.1 < e.center().X < ex[1] + 0.1)
            if not es:
                continue
            # сходинки радіуса (09.07 п.7: R2 падав — кут «губився»)
            for rr in (2.0, 1.2, 0.7):
                try:
                    fillet(list(es), radius=rr)
                    if rr != 2.0:
                        print(f"  (i) верхній кут торця: R{rr}")
                    break
                except Exception:
                    continue
            else:
                # пореброво (09.07 п.7: зрощений з ложем торець — ланцюг
                # не береться цілком)
                okd = 0
                for e in es:
                    for rr in (2.0, 1.0, 0.6):
                        try:
                            fillet([e], radius=rr)
                            okd += 1
                            break
                        except Exception:
                            continue
                print(f"  (i) верхній кут торця: пореброво {okd}/{len(es)}")

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
        for xc in P.SNAP_TAB_XC:
            with Locations((xc, (P.SNAP_TAB_Y[0] + by0f) / 2,
                            P.SNAP_TAB_Z[0])):
                Box(P.SNAP_TAB_W, by0f - P.SNAP_TAB_Y[0] + 0.1,
                    P.SNAP_TAB_Z[1] - P.SNAP_TAB_Z[0], align=AMIN)
        # ── задній пружний ГАЧОК: стовп на хвості бази → балка вперед →
        # язичок вниз перед хвостом, зуб у паз планки корпусу ──
        aw2 = P.SNAP_ARM_W / 2
        ax = P.SNAP_LATCH_XC
        # проріз у базі під язичок (гнеться назад до 2.2)
        with Locations((ax, (P.SNAP_ARM_Y0 - 0.4 + 114.6) / 2,
                        P.SSD_SIT_Z + P.SSD_SKID_H - 0.5)):
            Box(P.SNAP_ARM_W + 1.0, 114.6 - (P.SNAP_ARM_Y0 - 0.4),
                P.SSD_BASE_T + 1.5, mode=Mode.SUBTRACT)
        # стовп (жорсткий) на хвості бази
        with Locations((ax, (114.8 + 117.2) / 2, z0)):
            Box(P.SNAP_ARM_W, 117.2 - 114.8, 20.0 - z0, align=AMIN)
        # балка вперед на Z18.2..20
        with Locations((ax, (P.SNAP_ARM_Y0 + 117.2) / 2, 18.2)):
            Box(P.SNAP_ARM_W, 117.2 - P.SNAP_ARM_Y0, 1.8, align=AMIN)
        # язичок вниз (пружна частина, L~14.7)
        with Locations((ax, P.SNAP_ARM_Y0 + P.SNAP_ARM_T / 2, 3.5)):
            Box(P.SNAP_ARM_W, P.SNAP_ARM_T, 18.2 - 3.5 + 0.1, align=AMIN)
        # зуб уперед: похила нижня грань (заходить по планці), полиця
        # зверху в паз
        with BuildSketch(Plane((ax - aw2, 0, 0), x_dir=(0, 1, 0),
                               z_dir=(1, 0, 0))) as th:
            with BuildLine():
                Polyline((P.SNAP_TOOTH_TIP, 4.9),
                         (P.SNAP_ARM_Y0 + 0.01, 4.9),
                         (P.SNAP_ARM_Y0 + 0.01, 3.5),
                         (P.SNAP_TOOTH_TIP, 4.4),
                         (P.SNAP_TOOTH_TIP, 4.9))
            make_face()
        extrude(th.sketch, amount=P.SNAP_ARM_W)
        # педалька-виступ для пальця (тягнути назад)
        with Locations((ax, P.SNAP_ARM_Y0 + P.SNAP_ARM_T + 1.0, 4.5)):
            Box(P.SNAP_ARM_W, 2.0, 1.8)

    return blk.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "ssd_block")
