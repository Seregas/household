"""
front_insert.py — ЗМІННІ ВСТАВКИ ФРОНТ-АПЕРТУРИ (14.07, ідея користувача:
«вентилятор аддоном» + змінні панелі правої зони). Панель має вікно
FAP_X × FAP_Z з фальцом; сюди стає одна зі вставок:
  • fan    — гриль-ромбілі з ширшими прорізами в колі лопатей + 4 отвори
             ⌀3.2 (крок 32×32): Noctua 40мм гвинтиться до вставки штатними
             самонарізами, ставиться/виймається РАЗОМ із нею (проходить
             крізь вікно 41.4×70.7);
  • grille — чиста решітка-ромбілі (продув без вентилятора);
  • blank  — глуха (тиха конфігурація / майбутня розмітка під порти).

Механізм = io_insert, ПОСИЛЕНИЙ (сюди тикають кабелі/пальці — «щоб
пальцем можна було впертись і не вилетіло»):
  • носик = апертура −0.2/бік t1.4 (лице −0.1 від лиця панелі);
  • фланець = апертура +1.4/бік t1.4 у фальці — натиск ВСЕРЕДИНУ тримає
    вся рамка фланця по периметру, не зачепи;
  • фланець ЗРІЗАНИЙ: зліва при z>72.7 по лінії апертури (канал
    LSI-защіпки — тіло+барби до X91.8), справа по 134.4 (вежа на 134.9);
  • знизу 2 ЖОРСТКІ язички 10×1.8 (ширші за io) у кишені фальца;
  • зверху 2 ПРУЖНІ пальці (проріз 12, язичок 6) з бампом R0.8 —
    зачеплення уступу ~0.5 (io 0.35), прямий уступ проти виштовхування;
  • виймання: зсередини (корпус відкритий згори) притиснути обидва
    пальці вниз і виштовхнути вставку вперед.
Ромбілі — ТА САМА глобальна ґратка/фаза, що на панелі (патерн
продовжується через обідок вікна).
Запуск: .venv/bin/python cad/front_insert.py →
        out/front_fan|front_grille|front_blank .step/stl
Вставки в координатах збірки; друк — лицем вниз.
"""
import math
from build123d import *
import shapely.geometry as sg
from shapely.ops import unary_union
import params as P
from exporter import save


def _rounded(poly, r, qs=8):
    return poly.buffer(-r).buffer(r, quad_segs=qs)


def _polys(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    return [g for g in geom.geoms if g.geom_type == 'Polygon']


def _plans(variant):
    """2D-плани (X,Z): (nose, flange) з вирізами варіанта."""
    aper = _rounded(sg.box(P.FAP_X[0], P.FAP_Z[0], P.FAP_X[1], P.FAP_Z[1]),
                    P.INS_APER_R)
    nose = aper.buffer(-P.INS_CLEAR, quad_segs=8)
    flange = aper.buffer(P.INS_REBATE_W - P.INS_CLEAR, quad_segs=8)
    # зрізи фланця (див. док-стрінг): защіпка зліва вгорі, вежа справа.
    # Зліва фланець зрізаний НИЖЧЕ за фальц панелі (clz−0.3 проти clz):
    # фальца лівіше апертури вище clz нема — фланець там впирався б у тіло
    clx, clz = P.FAP_CLIP_L
    flange = flange.difference(
        sg.box(clx - 10, clz - 0.3, clx + P.INS_CLEAR, P.PANEL_H)) \
        .intersection(sg.box(P.EAR_L_X, 0,
                             P.FAP_CLIP_RX - P.INS_CLEAR, P.PANEL_H))
    # нижні жорсткі язички — частина фланця
    for xc in P.FAP_TAB_XC:
        flange = flange.union(sg.box(
            xc - P.FAP_TAB_W / 2, P.FAP_Z[0] - 1.4 - P.INS_TAB_H,
            xc + P.FAP_TAB_W / 2, P.FAP_Z[0]))

    # ── пружні пальці зверху: U-прорізи (крізь ОБИДВА шари) ──
    ztop_n = P.FAP_Z[1] - P.INS_CLEAR                    # верх носика 75.8
    ztop_f = P.FAP_Z[1] + P.INS_REBATE_W - P.INS_CLEAR   # верх фланця 77.4
    cx_mid = (P.FAP_X[0] + P.FAP_X[1]) / 2
    slits, lip_gaps = [], []
    for xc, xd in zip(P.FAP_TAB_XC, P.FAP_DIMPLE_XC):
        sgn = -1 if xc < cx_mid else +1        # вільний кінець назовні
        x_anchor = xc - sgn * P.FAP_FING_L / 2
        x_free = xc + sgn * P.FAP_FING_L / 2
        zf0 = ztop_n - P.INS_FING_H            # низ пальця 73.3
        slits.append(sg.box(min(x_anchor, x_free + sgn * P.INS_SLIT_W),
                            zf0 - P.INS_SLIT_W,
                            max(x_anchor, x_free + sgn * P.INS_SLIT_W), zf0))
        slits.append(sg.box(min(x_free, x_free + sgn * P.INS_SLIT_W), zf0,
                            max(x_free, x_free + sgn * P.INS_SLIT_W),
                            ztop_f + 0.1))
        # губа фланця над пальцем зрізається до верху носика, КРІМ
        # язичка-підйому (несе бамп)
        tab0 = xd - P.FAP_LIP_TAB_W / 2
        tab1 = xd + P.FAP_LIP_TAB_W / 2
        span = sg.box(min(x_anchor, x_free), ztop_n,
                      max(x_anchor, x_free), ztop_f + 0.1)
        lip_gaps.append(span.difference(sg.box(tab0, ztop_n, tab1,
                                               ztop_f + 0.1)))

    cut_all = list(slits)
    fing_pads = unary_union(
        [g.buffer(1.5) for g in slits]
        + [sg.box(xd - P.FAP_LIP_TAB_W / 2 - 1.5, ztop_n - 3.0,
                  xd + P.FAP_LIP_TAB_W / 2 + 1.5, ztop_f + 1)
           for xd in P.FAP_DIMPLE_XC])

    # ── варіанти лиця ──
    screw_pads = sg.Polygon()
    blades = None
    if variant == 'fan':
        # пади кріплень: кишеню, що торкається пада, морфимо (як на панелі)
        screw_pads = unary_union([sg.Point(
            P.FAN_CX + sx * P.FAN_SCREW_CC / 2,
            P.FAN_CZ + sz * P.FAN_SCREW_CC / 2)
            .buffer(P.FAN_SCREW_D / 2 + 2.0, 16)
            for sx in (-1, 1) for sz in (-1, 1)])
        blades = sg.Point(P.FAN_CX, P.FAN_CZ).buffer(18.0, 48)
        for sx in (-1, 1):     # наскрізні отвори ⌀3.2 (обидва шари)
            for sz in (-1, 1):
                cut_all.append(sg.Point(
                    P.FAN_CX + sx * P.FAN_SCREW_CC / 2,
                    P.FAN_CZ + sz * P.FAN_SCREW_CC / 2)
                    .buffer(P.FAN_SCREW_D / 2, 24))

    rhomb = []
    if variant != 'blank':
        # ── rhombille: ГЛОБАЛЬНА ґратка/фаза панелі (продовження патерну) ──
        s = P.PANEL_RHOMB_S
        dxl = math.sqrt(3) * s
        dyl = 1.5 * s
        ero = P.RHOMB_T / 2 + P.RHOMB_R
        _probe = sg.Polygon(
            [(0, 0), (-s * math.cos(math.radians(30)), -s / 2),
             (0, -s), (s * math.cos(math.radians(30)), -s / 2)]) \
            .buffer(-ero).buffer(P.RHOMB_R, quad_segs=8)
        tip_inset = s * math.cos(math.radians(30)) - abs(_probe.bounds[0])
        cx0 = P.IO_X[0] - tip_inset
        cz0 = P.IO_Z[1] + P.PANEL_RIM + s / 2
        field = aper.buffer(-1.7, quad_segs=8).difference(fing_pads) \
                    .difference(screw_pads)
        fb = field.bounds
        for row in range(int((fb[1] - cz0) / dyl) - 2,
                         int((fb[3] - cz0) / dyl) + 3):
            for col in range(int((fb[0] - cx0) / dxl) - 2,
                             int((fb[2] - cx0) / dxl) + 3):
                hx = cx0 + col * dxl + (row % 2) * dxl / 2
                hz = cz0 + row * dyl
                V = [(hx + s * math.cos(math.radians(a)),
                      hz + s * math.sin(math.radians(a)))
                     for a in range(90, 450, 60)]
                for k in (0, 2, 4):
                    rb = sg.Polygon([(hx, hz), V[k], V[k + 1],
                                     V[(k + 2) % 6]])
                    if not rb.intersects(field):
                        continue
                    pk = rb.buffer(-ero).buffer(P.RHOMB_R, quad_segs=8) \
                           .intersection(field)
                    if rb.intersects(fing_pads) or rb.intersects(screw_pads):
                        pk = pk.buffer(-0.35).buffer(0.35, quad_segs=8)
                    for g in _polys(pk):
                        if g.area < 1.5 or g.buffer(-0.45).is_empty:
                            continue
                        rhomb.append(g)
                    # коло лопатей: ширші прорізи (ребро гриля 0.7 —
                    # фідбек 14.07 «тоншими в зоні кулера»; межа круга
                    # сама проступає в патерні, як було на панелі)
                    if blades is not None and rb.intersects(blades):
                        pk2 = rb.buffer(-(0.35 + P.RHOMB_R)) \
                                .buffer(P.RHOMB_R, quad_segs=8) \
                                .intersection(blades).intersection(field) \
                                .difference(screw_pads)
                        for g in _polys(pk2):
                            if g.area >= 1.5 and not g.buffer(-0.3).is_empty:
                                rhomb.append(g)
        # «волосини»: стінки тонші 0.56 → у сусідній виріз (поріг НИЖЧЕ
        # ребра гриля 0.7 — з 0.8 чистка з'їдала весь нетворк у колі
        # лопатей, лишаючи 21 острів-«зірочку» в центрах шестикутників)
        mat = field.buffer(3.0).difference(unary_union(rhomb) if rhomb
                                           else sg.Polygon())
        hair = mat.difference(mat.buffer(-0.28).buffer(0.28, quad_segs=8))
        for c in _polys(hair):
            if c.area < 5.0 and c.intersects(field):
                rhomb.append(c)

    # closing 0.05: межі pk і pk2 у колі лопатей майже дотичні → union
    # лишає «голки»-шипи (ширина ~0.001) — валідні для shapely, але OCC
    # не замикає wire; закриття заповнює шипи, кути кишень не чіпає
    cuts = unary_union(cut_all + rhomb) \
        .buffer(0.05, quad_segs=4).buffer(-0.05, quad_segs=4)
    nose_pl = nose.difference(cuts)
    flange_pl = flange.difference(cuts).difference(unary_union(lip_gaps))
    return nose_pl, flange_pl


def build(variant):
    nose_pl, flange_pl = _plans(variant)
    layers = ((flange_pl, 96.5, P.INS_FLANGE_T),   # фланець −96.5…−97.9
              (nose_pl, 97.9, P.INS_NOSE_T))       # носик  −97.9…−99.3
    with BuildPart() as ins:
        for plan, yoff, t in layers:
            with BuildSketch(Plane.XZ.offset(yoff)) as sk:
                for g0 in _polys(plan):
                    # симпліфай на рівні ПОЛІГОНА (preserve_topology) —
                    # simplify LineString-а самоперетинав зигзаг-межі
                    # union(pk, pk2) у колі лопатей → незамкнений wire
                    g = g0.simplify(0.02)
                    with BuildLine():
                        Polyline(*list(g.exterior.coords)[:-1], close=True)
                    make_face()
                    for ring in g.interiors:
                        rp = sg.Polygon(ring)
                        if rp.area < 0.5:
                            continue
                        with BuildLine():
                            Polyline(*list(rp.exterior.coords)[:-1],
                                     close=True)
                        make_face(mode=Mode.SUBTRACT)
            extrude(sk.sketch, amount=t)
        # бампи R0.8: передня половина = рампа заходу (тре по стелі
        # фальца), задня зрізана вертикально — прямий уступ у кишеню
        ztop_f = P.FAP_Z[1] + P.INS_REBATE_W - P.INS_CLEAR
        for xd in P.FAP_DIMPLE_XC:
            with Locations(Location((xd, -97.35, ztop_f), (0, 90, 0))):
                Cylinder(P.FAP_BUMP_R, P.FAP_LIP_TAB_W)
            with Locations((xd, (-97.35 + -96.3) / 2, ztop_f + 0.5)):
                Box(P.FAP_LIP_TAB_W + 0.2, -96.3 - -97.35, 1.0,
                    mode=Mode.SUBTRACT)
    return ins.part


if __name__ == "__main__":
    for variant in ("fan", "grille", "blank"):
        part = build(variant)
        print(f"{variant}: valid {part.is_valid} | vol {part.volume:.1f}")
        save(part, f"front_{variant}")
