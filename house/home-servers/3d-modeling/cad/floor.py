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
import params as P
from exporter import save

AMIN = (Align.CENTER, Align.CENTER, Align.MIN)

# прототип «пупирки»-лінзи (05.07): сплюснутий еліпсоїд, будується ПОЗА
# білдерами — Sphere()/scale() всередині BuildPart авто-додаються, а
# scale ще й з Mode.REPLACE (зжер усе дно, лишивши дві лінзи; урок!)
# півось по нормалі 0.85 (було 1.3): лінза пробивала 1.2-стінку
# наскрізь і горбилась із протилежного боку («дві пари пупирок»)
LENS = scale(Sphere(1.0), (0.85, 2.4, 2.4))


def interior_box():
    """Внутрішня межа несучої рами (XY)."""
    return (P.WALL_L_X + P.FRAME_W, P.BODY_FRONT_Y + P.FRAME_W,
            P.WALL_R_X - P.FRAME_W, P.REAR_Y - P.FRAME_W)


def _rounded(poly, r, qs=8):
    """Скруглення кутів полігона: erode→dilate (opening)."""
    return poly.buffer(-r).buffer(r, quad_segs=qs)


def _polys(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    if geom.geom_type in ('MultiPolygon', 'GeometryCollection'):
        return [g for g in geom.geoms if g.geom_type == 'Polygon']
    return []                                   # LineString/Point від дегенерацій


def plan_geometry():
    """2D-розкладка заповнення. Повертає (holes, crown_polys):
       holes — полігони наскрізних отворів у 2мм шарі (соти кліпнуті + острівці),
       crown_polys — полігони шару +1мм над зонами постаментів (з кишенями-дірками).
    """
    Rc = P.HEX_AF / math.sqrt(3)               # circumradius соти-отвору
    dx = P.HEX_AF + P.HEX_RIB                  # крок ґратки
    dy = dx * math.sin(math.radians(60))
    Rcell = dx / math.sqrt(3)                  # circumradius КОМІРКИ (соти+піврібра)
    x0, y0, x1, y1 = interior_box()
    interior = _rounded(sg.box(x0, y0, x1, y1), P.FRAME_CORNER_R)
    cx0, cy0 = (x0 + x1) / 2, (y0 + y1) / 2
    pads = unary_union([sg.Point(x, y).buffer(P.STANDOFF_PAD_D / 2, 48)
                        for x, y in P.STANDOFF_XY.values()])
    windows = unary_union([_rounded(sg.box(k['x'][0], k['y'][0], k['x'][1], k['y'][1]),
                                    P.RAM_WIN_R)
                           for k in P.RAM_KEEPOUT.values()])

    def hexp(cx, cy, R):
        return sg.Polygon([(cx + R * math.cos(math.radians(a)),
                            cy + R * math.sin(math.radians(a)))
                           for a in range(90, 450, 60)])

    # ── коридори вікно↔рама (зазор < GAP_FILL): суцільні 2мм, без нічого ──
    corridors = []
    for k in P.RAM_KEEPOUT.values():
        wx0, wx1 = k['x']; wy0, wy1 = k['y']
        if wx0 - x0 < P.RAM_WIN_GAP_FILL:
            corridors.append(sg.box(x0, wy0, wx0, wy1))
        if x1 - wx1 < P.RAM_WIN_GAP_FILL:
            corridors.append(sg.box(wx1, wy0, x1, wy1))
        if wy0 - y0 < P.RAM_WIN_GAP_FILL:
            corridors.append(sg.box(wx0, y0, wx1, wy0))
        if y1 - wy1 < P.RAM_WIN_GAP_FILL:
            corridors.append(sg.box(wx0, wy1, wx1, y1))
    corridors = unary_union(corridors) if corridors else sg.Polygon()

    # ── соти: розширена ґратка, кліп по interior та ободку RAM-вікон ──
    # Кліпнуті ФРАГМЕНТИ ближче STANDOFF_SOLID_R до постаменту лишаємо
    # суцільними (жорсткість); повні соти ріжемо завжди.
    allowed = interior.difference(windows.buffer(P.RAM_WIN_RIM))
    full_hex_area = _rounded(hexp(0, 0, Rc), P.HEX_CORNER_R).area
    holes = []
    ncol = int((x1 - x0) / dx) + 3
    nrow = int((y1 - y0) / dy) + 3
    cells = []                                  # центри комірок (для трикутників)
    for row in range(-nrow, nrow + 1):
        for col in range(-ncol, ncol + 1):
            hx = cx0 + col * dx + (row % 2) * dx / 2
            hy = cy0 + row * dy
            cells.append((hx, hy))
            h = hexp(hx, hy, Rc)
            if not h.intersects(interior):
                continue
            if h.intersects(pads):
                continue                        # зона постаменту — без сот
            hc = _rounded(h, P.HEX_CORNER_R).intersection(allowed)
            for g in _polys(hc):
                # відсікати крихти й щілини вужчі за ~1.2мм
                if g.area < 10.0 or g.buffer(-0.6).is_empty:
                    continue
                if g.intersects(corridors):
                    continue                    # коридор вікно↔рама → суцільний
                clipped = g.area < full_hex_area - 0.5
                if clipped and min(g.distance(sg.Point(x, y))
                                   for x, y in P.STANDOFF_XY.values()) \
                        < P.STANDOFF_SOLID_R:
                    continue                    # фрагмент біля постаменту → суцільний
                holes.append(g)

    # SSD-зона 05.07: підлога СУЦІЛЬНА — канал під дисками закритий знизу,
    # потік від вентилятора мусить іти вздовж дисків до кінця (раніше соти
    # «для обдуву знизу» — концепція потоку змінилась)
    (a0, a1), (b0, b1) = P.SSD_SLOT_X
    y0s = P.SSD_Y[0] + P.SSD_B_SHIFT - 2
    y1s = P.SSD_Y[1] + 2
    ssd_zone = sg.box(P.SSD_INNER_X[0] - 1.0, y0s, 135.2, y1s)
    holes = [h.difference(ssd_zone) for h in holes]
    holes = [g for h in holes for g in _polys(h)
             if g.area > 10.0 and not g.buffer(-0.6).is_empty]
    voids = unary_union([unary_union(holes), windows])
    solid = interior.difference(voids)

    # ── острівці (не тримаються ні рами, ні падів) → у порожнечу ──
    rim = interior.exterior.buffer(0.05)
    kept, islands = [], []
    for c in _polys(solid):
        (kept if (c.intersects(rim) or c.intersects(pads)) else islands).append(c)
    solid = unary_union(kept)
    holes.extend(islands)

    # ── зони постаментів: морф. відкриття прибирає 2мм-павутину ──
    opened = solid.buffer(-1.2).buffer(1.2, quad_segs=8)
    zone = unary_union([c for c in _polys(opened) if c.intersects(pads)])
    zone = zone.intersection(solid)
    # 05.07: SSD-зона — НЕ корона: суцільна підлога каналу зробила її
    # «зоною постаменту» для морф. відкриття, і наскрізний ізогрід
    # прорізав дно каналу (фідбек: «чи не буде уходити через дно?» — 
    # уходило б, 565мм² трикутників)
    zone = zone.difference(ssd_zone)
    # відступ від RAM-вікон: модуль сідає в вікно, шар +1мм не має тертись
    zone = zone.difference(windows.buffer(0.5))
    # коридори вікно↔рама — гладенькі 2мм: без корони й трикутників
    zone = zone.difference(corridors)

    # ── трикутні кишені (6 на комірку, R1), ребра TRI_RIB_W між ними ──
    inset = P.TRI_RIB_W / 2
    # 04.07: ізогрід НАСКРІЗНИЙ → суцільний комірець ⌀17 під колоною
    # (виривання гвинта) + обідок 2мм по межі зони (крайові ребра 3мм
    # заввишки не мають бути тонші 2)
    keep_r = P.STANDOFF_COLLAR_D / 2
    base_keep = unary_union([
        sg.Point(x, y).buffer(keep_r, 48)
        for x, y in P.STANDOFF_XY.values()])
    pocket_region = zone.buffer(-2.0).difference(base_keep)
    pockets = []
    for (hx, hy) in cells:
        cell_pts = [(hx + Rcell * math.cos(math.radians(a)),
                     hy + Rcell * math.sin(math.radians(a)))
                    for a in range(90, 450, 60)]
        for k in range(6):
            tri = sg.Polygon([(hx, hy), cell_pts[k], cell_pts[(k + 1) % 6]])
            if not tri.intersects(zone):
                continue
            pk = tri.buffer(-(inset + P.HEX_CORNER_R)) \
                    .buffer(P.HEX_CORNER_R, quad_segs=8) \
                    .intersection(pocket_region)
            for g in _polys(pk):
                if g.area > 2.0:
                    pockets.append(g)

    from shapely import set_precision
    crown = set_precision(zone.difference(unary_union(pockets)), 0.01)
    crown_polys = [g for g in _polys(crown) if g.area > 3.0]
    holes = [g for h in holes for g in _polys(set_precision(h, 0.01))
             if g.area > 1.0]
    return holes, crown_polys, pockets


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
    holes, crown_polys, tri_pockets = plan_geometry()
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

        # ── соти (кліпнуті) — наскрізь крізь заповнення ──
        with BuildSketch(Plane.XY.offset(-1)):
            for g in holes:
                with BuildLine():
                    Polyline(*list(g.exterior.coords)[:-1], close=True)
                make_face()
        extrude(amount=1 + P.INFILL_T + 0.5, mode=Mode.SUBTRACT)

        # ── вирізи під RAM-модулі (наскрізні вікна; кути R1) ──
        for k in P.RAM_KEEPOUT.values():
            wx0, wx1 = k['x']; wy0, wy1 = k['y']
            with BuildSketch(Plane.XY.offset(-1)):
                with Locations(((wx0 + wx1) / 2, (wy0 + wy1) / 2)):
                    RectangleRounded(wx1 - wx0, wy1 - wy0, radius=P.RAM_WIN_R)
            extrude(amount=1 + P.INFILL_T + 0.5, mode=Mode.SUBTRACT)

        # ── корона зон постаментів: шар +1мм з трикутними кишенями ──
        with BuildSketch(Plane.XY.offset(P.INFILL_T)):
            for poly in crown_polys:
                with BuildLine():
                    Polyline(*list(poly.exterior.coords)[:-1], close=True)
                make_face()
                for ring in poly.interiors:
                    rp = sg.Polygon(ring)
                    if abs(rp.area) < 0.8:
                        continue
                    rp = rp.simplify(0.02).buffer(0)
                    if rp.geom_type != 'Polygon' or rp.area < 0.8:
                        continue
                    with BuildLine():
                        Polyline(*list(rp.exterior.coords)[:-1], close=True)
                    make_face(mode=Mode.SUBTRACT)
        extrude(amount=P.TRI_RIB_H)

        # ── ізогрід НАСКРІЗНИЙ (04.07): ті ж трикутні кишені прорізаються
        # крізь 2мм заповнення → решітка 3мм на просвіт (жорсткість ×2.5
        # у згині проти суцільної двійки, обдув; комірці ⌀17 суцільні) ──
        with BuildSketch(Plane.XY.offset(-1)):
            for pk in tri_pockets:
                rp = pk.simplify(0.02).buffer(0)
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

        # ── рейки SSD: 3 трапеції вздовж Y (скошені боки = самозавід);
        # диски ПРИПІДНЯТІ на шпалах — під ними канал для повітря ──
        (a0, a1), (b0, b1) = P.SSD_SLOT_X
        y0s, y1s = P.SSD_Y
        # зовнішня рейка (при стінці) — ПОСТАМИ (повітря → ромбілі стінки),
        # середня і внутрішня — суцільні
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
                # x_dir=(-1,0,0): щоб локальний +y був ГЛОБАЛЬНИМ +Z
                # (з (1,0,0) профіль ріс ВНИЗ — дно сягало Z-14)
                with BuildSketch(Plane((cx, ry0, P.INFILL_T),
                                       x_dir=(-1, 0, 0),
                                       z_dir=(0, 1, 0))) as tz:
                    with BuildLine():
                        # прямі грані до GRIP (хват), вище — скіс-лійка
                        Polyline((-w / 2, 0), (w / 2, 0), (w / 2, hg),
                                 (t2, ht), (-t2, ht), (-w / 2, hg),
                                 (-w / 2, 0))
                    make_face()
                    # бульнос верхньої грані вздовж (фідбек 06.07);
                    # стінка 1.2 → максимум R0.55
                    fillet(tz.vertices().filter_by(
                        lambda v: v.Y > ht - 0.01), radius=0.55)
                extrude(tz.sketch, amount=ry1 - ry0)
        # передній упор-МІСТОК на рівні диска (Z10-18): знизу відкрито —
        # фронтальний вентилятор продуває канал під дисками наскрізь
        # (суцільна стінка блокувала повітря — фідбек 2026-07-03);
        # заразом зв'язує верхи трьох рейок спереду
        sy0, sy1 = P.SSD_STOP_Y
        # ванна під диском A (06.07, ідея користувача): рама тут 3мм і
        # дно каналу A було на 1 вище за канал B — знижуємо до 2 з
        # пологими S-переходами (косинус, 6мм) на в'їзді та виїзді;
        # заразом рампи/бобишки обох каналів стають ідентичними (база Z2)
        prof = [(-26.0, 3.05)]
        for k in range(1, 8):
            t = k / 8
            prof.append((-26.0 + 6.0 * t,
                         2.0 + 1.05 * (0.5 + 0.5 * math.cos(math.pi * t))))
        prof.append((-20.0, 2.0))
        prof.append((74.0, 2.0))
        for k in range(1, 8):
            t = k / 8
            prof.append((74.0 + 6.0 * t,
                         2.0 + 1.05 * (0.5 - 0.5 * math.cos(math.pi * t))))
        prof.append((80.0, 3.05))
        with BuildSketch(Plane.YZ.offset(127.0)) as bath:
            with BuildLine():
                Polyline(*prof, (80.0, 3.4), (-26.0, 3.4), prof[0])
            make_face()
        extrude(bath.sketch, amount=134.9 - 127.0, mode=Mode.SUBTRACT)
        # упори-панелі (05.07 v2): строго В МЕЖАХ свого слота (виступали
        # в сусідні: 125.16/-21 та 127.3/-26), якоряться в перегородці
        # (0.5 углиб) і в стінці/консоллю; кути R2; соти в ОБОХ
        for bx0, bx1, hx, ysh in ((126.4, 135.4, 130.9, 0.0),
                                  (118.3, 126.4, 121.7, P.SSD_B_SHIFT)):
            with BuildSketch(Plane.XZ.offset(-(sy0 + ysh))) as bp_:
                with Locations(((bx0 + bx1) / 2,
                                P.INFILL_T + P.SSD_LIFT + 4.0)):
                    RectangleRounded(bx1 - bx0, 8.0, radius=2.0)
                with Locations((hx, P.INFILL_T + P.SSD_LIFT + 4.0)):
                    RegularPolygon(4.8 / math.sqrt(3), 6,
                                   major_radius=True, rotation=90,
                                   mode=Mode.SUBTRACT)
            extrude(bp_.sketch, amount=-(sy1 - sy0))
        # постаменти-арки з отворами (05.07 v2, фідбек): як шпали —
        # вікно пропускає потік каналу; в палубі+дні наскрізний отвір
        # M3 (бічні отвори SFF-8201: 14.0/90.6 від торця з роз'ємом),
        # прикручування знизу; перед отвором — ЗАКРУГЛЕНИЙ трамплін
        for cx, y_rear in ((130.9, P.SSD_Y[1]),
                           (121.7, P.SSD_Y[1] + P.SSD_B_SHIFT)):
            for off in (14.0, 90.6):
                yb = y_rear - off
                # бокс 8.6 — втоплений 0.3 в обидві стінки каналу
                # (палуба-місток тримається за них торцями)
                with Locations((cx, yb, P.INFILL_T + P.SSD_LIFT / 2)):
                    Box(8.6, P.SSD_SLEEPER_W, P.SSD_LIFT)
                # вікно на ВСЮ ширину каналу (фідбек 06.07: бічні ніжки
                # біля вертикальних площин прибрані — більше повітря);
                # ВИНЯТОК — передній постамент B: зліва рейки нема
                # (вона від Y13), місток нема за що тримати → ніжки
                ww = 4.6 if (cx == 121.7 and yb < P.SSD_INNER_Y[0]) else 8.0
                with Locations((cx, yb, P.INFILL_T
                                + (P.SSD_LIFT - 2.0) / 2)):
                    Box(ww, P.SSD_SLEEPER_W + 2, P.SSD_LIFT - 2.0,
                        mode=Mode.SUBTRACT)
                # увігнутий трамплін (05.07 v3): 2мм, пологий (8.2),
                # на ВСЮ ширину каналу (щілина до рейки виглядала дірою),
                # від МІСЦЕВОГО рівня підлоги (слот A стоїть на РАМІ Z3 —
                # рампи A були поховані в ній на 1мм: «втричі коротший»);
                # не будується де канал відкритий (рейка від Y13)
                if cx == 130.9 or yb > P.SSD_INNER_Y[0]:
                    zb_f = 2.0        # обидва канали: дно Z2 (ванна 06.07)
                    rx0 = 126.8 if cx == 130.9 else 117.6
                    rx1 = 135.0 if cx == 130.9 else 125.8
                    R = (8.2 ** 2 + 2.0 ** 2) / (2 * 2.0)
                    arcp = [(yb - 12.0 + d, zb_f + R
                             - math.sqrt(R * R - d * d))
                            for d in [8.2 * k / 8 for k in range(9)]]
                    with BuildSketch(Plane.YZ.offset(rx0)) as ramp:
                        with BuildLine():
                            Polyline(*arcp, (yb - 3.8, zb_f - 0.5),
                                     (yb - 12.0, zb_f - 0.5),
                                     (yb - 12.0, zb_f))
                        make_face()
                    extrude(ramp.sketch, amount=rx1 - rx0)
                with Locations((cx, yb, -1)):
                    Cylinder(P.SSD_BOSS_HOLE / 2, P.SSD_LIFT + 4,
                             align=AMIN, mode=Mode.SUBTRACT)
        # (05.07: перфорація рейок ВИДАЛЕНА повністю — «треба суцільну
        # стінку»: канал під диском має бути герметичним з боків)
        # торці рейок заокруглені (фідбек 06.07 «Р2 на торцях»):
        # стінка 1.2 завтовшки → фізичний максимум R0.6, беремо 0.55
        for ex, ey in ((P.SSD_DIV_X, y0s + P.SSD_B_SHIFT - 4),
                       (P.SSD_DIV_X, P.SSD_RAIL_Y_END),
                       (P.SSD_INNER_X, P.SSD_INNER_Y[0]),
                       (P.SSD_INNER_X, P.SSD_INNER_Y[1])):
            try:
                es = tray.edges().filter_by(
                    lambda e: abs(e.center().Y - ey) < 0.05
                    and ex[0] - 0.05 < e.center().X < ex[1] + 0.05
                    and e.bounding_box().size.Z > 5)
                if es:
                    fillet(list(es), radius=0.55)
            except Exception as exn:
                print("  (!) торець рейки:", exn)
        # верхні кути торців рейок R2 у площині Y-Z (уточнення 06.07:
        # «гострий кут» = стик торця з верхівкою; бічний бульнос лишаємо)
        top_z = P.INFILL_T + P.SSD_RAIL_H
        for ex, ey in ((P.SSD_DIV_X, y0s + P.SSD_B_SHIFT - 4),
                       (P.SSD_DIV_X, P.SSD_RAIL_Y_END),
                       (P.SSD_INNER_X, P.SSD_INNER_Y[0]),
                       (P.SSD_INNER_X, P.SSD_INNER_Y[1])):
            try:
                es = tray.edges().filter_by(
                    lambda e: abs(e.center().Y - ey) < 0.6
                    and abs(e.center().Z - top_z) < 0.6
                    and ex[0] - 0.1 < e.center().X < ex[1] + 0.1)
                if es:
                    fillet(list(es), radius=2.0)
            except Exception as exn:
                print("  (!) верхній кут торця:", exn)
        # crush-«пупирки» = потовщення площини рейки (фідбек 05.07 v2):
        # не стовпчики, а гладкі напливи-лінзи на гранях слота — 3 на
        # підпорку (Z11.75/16.75/21.75), виступ 0.6, плавний перехід у
        # площину; повітря від кулера обтікає диск між лінзами
        # лише ПЕРЕГОРОДКА, обидві грані (рейкові «ні до чого» — геть);
        # пара по вертикалі × 3 позиції на грань
        lens_faces = (
            (P.SSD_DIV_X[1], +1, P.SSD_SLEEPER_Y),                # перег.→A
            (P.SSD_DIV_X[0], -1,
             tuple(y + P.SSD_B_SHIFT for y in P.SSD_SLEEPER_Y)))  # перег.→B
        for fx, din, stations in lens_faces:
            for sy in stations:
                for bz in (12.5, 20.5):
                    add(Location((fx - din * 0.25, sy, bz)) * LENS)
        # перфорація «сотами» містка-упору A (палуб більше нема)
        # ЯВНИЙ скетч! Безіменний extrude ковтав УСІ витеклі pending-грані
        # (профілі рейок/ванни/упорів/РАМП) і штампував кожну на -4:
        # фантомні різи (зрізана рампа B, виїмки Z1.5, підрізана база
        # перегородки). Урок 06.07: extrude ТІЛЬКИ з явним скетчем.
        with BuildSketch(Plane((130.0, -23.0, P.INFILL_T + P.SSD_LIFT + 4),
                               x_dir=(1, 0, 0), z_dir=(0, -1, 0))) as hx_sk:
            RegularPolygon(4.8 / math.sqrt(3), 6, major_radius=True,
                           rotation=90)
        extrude(hx_sk.sketch, amount=-4.0, mode=Mode.SUBTRACT)
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

    return tray.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "floor")
