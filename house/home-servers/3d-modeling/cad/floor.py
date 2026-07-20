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
import lattice
from exporter import save

AMIN = (Align.CENTER, Align.CENTER, Align.MIN)

# (лінзи-пупирки переїхали в ssd_block.py разом з усією SSD-геометрією)


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
    # мікрофаза 0.11: після зсуву постаментів -5 (08.07) стінка суцільної
    # соти біля S4 збіглась із гранню іншого оператора (6 відкритих ребер
    # на X96.65) — зсув фази розбиває точні збіги, функційно нейтральний
    cx0, cy0 = (x0 + x1) / 2 + 0.11, (y0 + y1) / 2
    # 20.07: СІТКА SNAP-FIT — симетричні пади комірок (слот + підмембранна
    # кишеня + обідок) у правій смузі, всі ряди × 2 колонки
    pads = unary_union(
        [sg.Point(x, y).buffer(P.STANDOFF_PAD_D / 2, 48)
         for x, y in P.STANDOFF_XY.values()]
        + [sg.box(cx - P.SNAP_SLOT_X / 2 - P.ANCHOR_PAD_RIM,
                  ry - P.SNAP_TOOTH_POCKET_Y - P.ANCHOR_PAD_RIM,
                  cx + P.SNAP_SLOT_X / 2 + P.ANCHOR_PAD_RIM,
                  ry + P.SNAP_TOOTH_POCKET_Y + P.ANCHOR_PAD_RIM)
           for cx in P.ANCHOR_COLS for ry in P.ANCHOR_ROWS])
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
    # 17.07 (фідбек 86.43/92.82): точка на стінці двох сот — обидві
    # суміжні соти НЕ ріжуться, а заливаються ізогрідом (додаються в
    # зону корони нижче)
    iso_fill = unary_union([sg.Point(x, y).buffer(1.0)
                            for x, y in P.ISO_FILL_XY])
    iso_hexes = []
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
            if h.intersects(iso_fill):
                iso_hexes.append(_rounded(h, P.HEX_CORNER_R))
                continue                        # сота заливається ізогрідом
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

    # SSD живе ОКРЕМИМ блоком (ssd_block.py); 13.07: кріпиться до дна
    # СІТКОЮ (місток у ряду Y5 + гачок в5.2 за паз бортика) — у дні від
    # нього нічого власного. Соти скрізь — підсос знизу.
    # смуга ПІД ТРАМПЛІНОМ бортика — суцільна (соти лишали його підошву
    # над дірками: 36.9/100.9 — «має на чомусь стояти»); задня рама від
    # 103.5 і так суцільна
    # 10.07 (фідбек 121.3/99.72/2): суцільне — РІВНО від підошви
    # трампліна (старт дуги 98.5, перекриття 0.1), патерни впритул
    ramp_strip = sg.box(P.WALL_L_X + P.BEAD_W - 0.5, 98.4,
                        P.WALL_R_IN + 0.4, 104.0)
    holes = [h.difference(ramp_strip) for h in holes]
    holes = [g for h in holes for g in _polys(h)
             if g.area > 10.0 and not g.buffer(-0.6).is_empty]
    voids = unary_union([unary_union(holes), windows])
    solid = interior.difference(voids)

    # ── острівці (не тримаються ні рами, ні падів) → у порожнечу ──
    rim = interior.exterior.buffer(0.05)
    kept, islands = [], []
    for c in _polys(solid):
        (kept if (c.intersects(rim) or c.intersects(pads))
         else islands).append(c)
    solid = unary_union(kept)
    holes.extend(islands)

    # ── зони постаментів: морф. відкриття прибирає 2мм-павутину ──
    opened = solid.buffer(-1.2).buffer(1.2, quad_segs=8)
    zone = unary_union([c for c in _polys(opened) if c.intersects(pads)])
    zone = zone.intersection(solid)
    # 08.07: межі зони втоплені 0.05 від стінок сот (зона з morph-opening
    # збігається з ними по побудові; на глибині 113.5 ретайлінг дав
    # коінцидентну стінку крона↔сота на X-71.1 → 6 відкритих ребер STL)
    zone = zone.buffer(-0.08)
    # 13.07 (фідбек 127.35/22.4/1.6): втоплення -0.08 відступало і від
    # РАМИ — канавка 0.08 до мембрани вздовж межі interior. Доліплюємо
    # крону в раму (перекриття ~0.4), лишаючи 0.08 від стінок сот
    frame_ring = sg.LineString(interior.exterior.coords).buffer(0.6)
    zone = zone.union(zone.buffer(0.5).intersection(frame_ring)
                      .difference(voids.buffer(0.08)))
    # зона SSD-блока без корони (полози мають стояти на рівному 2мм)
    # (08.07: crown-killer SSD-зони ВИДАЛЕНИЙ — блок на полозах стоїть
    # на рівні корони Z3, ізогрід під ним = опора + «залий ізогрідами»
    # п.3; герметичної підлоги каналів давно нема)
    # відступ від RAM-вікон: модуль сідає в вікно, шар +1мм не має тертись
    zone = zone.difference(windows.buffer(0.5))
    # 08.07 (п.6): смужка МІЖ RAM-вікнами (модулі там прилягають один до
    # одного і звисають до Z2.55) — корону/ізогрід (3мм) тут НЕ робити,
    # лишається 2мм заливка; по всій глибині вікна A
    _ra, _rb = P.RAM_KEEPOUT["A"], P.RAM_KEEPOUT["B"]
    zone = zone.difference(sg.box(_rb["x"][1] - 0.2, _ra["y"][0],
                                  _ra["x"][0] + 0.2, _ra["y"][1]))
    # коридори вікно↔рама — гладенькі 2мм: без корони й трикутників
    zone = zone.difference(corridors)
    # 17.07: залиті соти (ISO_FILL_XY) — у зону ізогріду; обідок 2мм по
    # межі дає сам pocket_region (zone.buffer(-2.0) нижче)
    if iso_hexes:
        zone = zone.union(unary_union(iso_hexes).intersection(solid))
    # 17.07: трим «дзьобиків» корони (клин сота↔рама звужується в
    # гостряк; фідбек ±60.75/−44.88, −86) — вбираємо вістря колом
    zone = zone.difference(unary_union(
        [sg.Point(x, y).buffer(P.CROWN_TRIM_R, 32)
         for x, y in P.CROWN_TRIM_XY]))

    # ── трикутні кишені (6 на комірку, R1), ребра TRI_RIB_W між ними ──
    inset = P.TRI_RIB_W / 2
    # 04.07: ізогрід НАСКРІЗНИЙ → суцільний комірець ⌀17 під колоною
    # (виривання гвинта) + обідок 2мм по межі зони (крайові ребра 3мм
    # заввишки не мають бути тонші 2)
    keep_r = P.STANDOFF_COLLAR_D / 2
    base_keep = unary_union(
        [sg.Point(x, y).buffer(keep_r, 48)
         for x, y in P.STANDOFF_XY.values()]
        # комірки snap-fit: кишені ізогріду тут НЕ ріжемо — пад
        # суцільний (мембрана над підмембранною кишенею і так 1.6)
        + [sg.box(cx - P.SNAP_SLOT_X / 2 - P.ANCHOR_PAD_RIM,
                  ry - P.SNAP_TOOTH_POCKET_Y - P.ANCHOR_PAD_RIM,
                  cx + P.SNAP_SLOT_X / 2 + P.ANCHOR_PAD_RIM,
                  ry + P.SNAP_TOOTH_POCKET_Y + P.ANCHOR_PAD_RIM)
           for cx in P.ANCHOR_COLS for ry in P.ANCHOR_ROWS])
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
                # 17.07: + фільтр ширини — кишені-СЛІВЕРСИ (<0.9мм) біля
                # кутів анкерних падів лишали тонкі гачки корони
                # (фідбек 117.95/−33.38, 118.17/−17.12)
                if g.area > 2.0 and not g.buffer(-0.45).is_empty:
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
                # внутрішні кільця (напр. пад кріплення ЦІЛКОМ усередині
                # соти): без цього острів зникав — бонка висіла в повітрі
                for ring in g.interiors:
                    with BuildLine():
                        Polyline(*list(ring.coords)[:-1], close=True)
                    make_face(mode=Mode.SUBTRACT)
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

    return tray.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "floor")
