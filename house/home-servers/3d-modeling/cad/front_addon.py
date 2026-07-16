"""
front_addon.py — ЗНІМНІ ПАНЕЛІ-АДДОНИ правої зони (15.07, схема
користувача: замість вікна-з-фальцом панель РОЗРІЗАНА на всю висоту
X92..133.4; права секція = окрема повнорозмірна деталь):
  • fan    — гриль-ромбілі з тоншими ребрами 0.7 у колі лопатей + 4
             отвори ⌀3.2 (крок 32×32): Noctua 40мм гвинтиться до тилу
             аддона штатними самонарізами, ставиться РАЗОМ із ним;
  • grille — чиста решітка-ромбілі (продув без вентилятора);
  • blank  — глуха (тиха конфігурація / майбутня розмітка під порти).

Посадка ВЕРТИКАЛЬНА (згори вниз):
  • ВЕРХ: 2 Т-РЕБРА на тилі (шия 3.7 → flare 45° → голова 7.6) → Т-пази
    у бобишках брови; flare ребра збігається з flare паза = ласточкін
    хвіст (тримає вперед) і самонесучий друк лицем вниз;
  • НИЗ: 2 жорсткі ЯЗИКИ 8×2 (Z1.2..2.9) у пази передньої рами дна +
    1 пружний ПАЛЕЦЬ (U-прорізи, вільний кінець УНИЗУ = кромка плити)
    з бампом R0.8: низ круглий = рампа заходу по кромці рами, верх
    зрізаний флетом = уступ у кишеню рами (тримає від ПІДЙОМУ);
  • БОКИ: half-lap — панель лишає передню ламель у проліт, аддон лягає
    ЗЗАДУ своєю ламеллю (тяга вперед → упор, лицьової щілини нема).
Зняття: підважити низ (палець), підняти вгору (Т-ребра виходять з пазів).
Ромбілі — ТА САМА глобальна ґратка/фаза, що на панелі (патерн
продовжується через розріз).
Запуск: .venv/bin/python cad/front_addon.py →
        out/front_fan|front_grille|front_blank .step/stl
Аддон у координатах збірки; друк — лицем вниз.
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
    """2D-плани (X,Z): (плита, задня ламель) з вирізами варіанта."""
    px0 = P.ADP_X[0] + P.ADP_LAP_D + P.ADP_LAP_CLR      # 93.65
    px1 = P.ADP_X[1] - P.ADP_LAP_D - P.ADP_LAP_CLR      # 131.75
    lx0 = P.ADP_X[0] + P.ADP_LAP_CLR                    # 92.15
    lx1 = P.ADP_X[1] - P.ADP_LAP_CLR                    # 133.25
    plate = sg.box(px0, 0, px1, P.PANEL_H)
    lam = sg.box(lx0, 0, lx1, P.PANEL_H)

    # ── пружний палець: U-прорізи, вільний кінець унизу (Z0) ──
    xi0 = P.ADP_FING_XC - P.ADP_FING_W / 2              # 109.2
    xi1 = P.ADP_FING_XC + P.ADP_FING_W / 2              # 116.2
    slits = [sg.box(xi0 - P.INS_SLIT_W, -0.5, xi0, P.ADP_FING_L),
             sg.box(xi1, -0.5, xi1 + P.INS_SLIT_W, P.ADP_FING_L)]
    cut_all = list(slits)
    fing_pad = sg.box(xi0 - P.INS_SLIT_W - 1.5, 0,
                      xi1 + P.INS_SLIT_W + 1.5, P.ADP_FING_L + 1.5)

    # ── варіанти лиця ──
    screw_pads = sg.Polygon()
    blades = None
    if variant == 'fan':
        screw_pads = unary_union([sg.Point(
            P.FAN_CX + sx * P.FAN_SCREW_CC / 2,
            P.FAN_CZ + sz * P.FAN_SCREW_CC / 2)
            .buffer(P.FAN_SCREW_D / 2 + 2.0, 16)
            for sx in (-1, 1) for sz in (-1, 1)])
        blades = sg.Point(P.FAN_CX, P.FAN_CZ).buffer(18.0, 48)
        for sx in (-1, 1):     # наскрізні отвори ⌀3.2
            for sz in (-1, 1):
                cut_all.append(sg.Point(
                    P.FAN_CX + sx * P.FAN_SCREW_CC / 2,
                    P.FAN_CZ + sz * P.FAN_SCREW_CC / 2)
                    .buffer(P.FAN_SCREW_D / 2, 24))

    rhomb = []
    if variant != 'blank':
        # ── rhombille: ГЛОБАЛЬНА ґратка/фаза панелі (продовження) ──
        # поле: обідок 2 від країв плити, низ 5, верх 79.25 (вище — зона
        # Т-ребер 82.75+ і брова за плитою)
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
        field = sg.box(px0 + 2.0, 5.0, px1 - 2.0, 79.25) \
            .difference(fing_pad).difference(screw_pads)
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
                    if rb.intersects(fing_pad) or rb.intersects(screw_pads):
                        pk = pk.buffer(-0.35).buffer(0.35, quad_segs=8)
                    for g in _polys(pk):
                        if g.area < 1.5 or g.buffer(-0.45).is_empty:
                            continue
                        rhomb.append(g)
                    # коло лопатей: ширші прорізи (ребро гриля 0.7;
                    # межа круга сама проступає в патерні)
                    if blades is not None and rb.intersects(blades):
                        pk2 = rb.buffer(-(0.35 + P.RHOMB_R)) \
                                .buffer(P.RHOMB_R, quad_segs=8) \
                                .intersection(blades).intersection(field) \
                                .difference(screw_pads)
                        for g in _polys(pk2):
                            if g.area >= 1.5 and not g.buffer(-0.3).is_empty:
                                rhomb.append(g)
        # «волосини»: поріг 0.28 НИЖЧЕ ребра гриля 0.7 (урок c3a8236:
        # 0.8 з'їдав нетворк у колі лопатей → «зірочки»)
        mat = field.buffer(3.0).difference(unary_union(rhomb) if rhomb
                                           else sg.Polygon())
        hair = mat.difference(mat.buffer(-0.28).buffer(0.28, quad_segs=8))
        for c in _polys(hair):
            if c.area < 5.0 and c.intersects(field):
                rhomb.append(c)

    # closing 0.05 (урок 60f691d): межі pk/pk2 майже дотичні → «голки»
    cuts = unary_union(cut_all + rhomb) \
        .buffer(0.05, quad_segs=4).buffer(-0.05, quad_segs=4)
    return plate.difference(cuts), lam.difference(cuts)


def build(variant):
    plate_pl, lam_pl = _plans(variant)
    # шари (план, товщина); ⚠️ грані — ІНЛАЙНОМ (урок io_insert: helper
    # з BuildLine всередині не працює — скоуп-чутливість білдерів)
    layers = ((plate_pl, P.FRONT_PANEL_T),   # плита t3 (лице −99.4)
              (lam_pl, P.ADP_LAP_T))         # задня ламель half-lap:
    # у прольоті перекривається з плитою (жирний union), по боках —
    # крила, що лягають ЗЗАДУ на передні ламелі панелі
    with BuildPart() as ad:
        for plan, t in layers:
            with BuildSketch(Plane.XZ.offset(96.4)) as sk:
                for g0 in _polys(plan):
                    g = g0.simplify(0.02)    # полігонний (урок 60f691d)
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

        # ── Т-РЕБРА (2): шия → flare 45° → голова; хвіст 0.3 у плиту ──
        fy0, fy1 = P.ADP_TEE_FLARE_Y
        for xc in P.ADP_TEE_XC:
            with BuildSketch(Plane.XY.offset(P.ADP_TEE_Z0)) as st:
                with BuildLine():
                    Polyline((xc - P.ADP_NECK_HW, -96.7),
                             (xc - P.ADP_NECK_HW, fy0),
                             (xc - P.ADP_HEAD_HW, fy1),
                             (xc - P.ADP_HEAD_HW, P.ADP_HEAD_Y1),
                             (xc + P.ADP_HEAD_HW, P.ADP_HEAD_Y1),
                             (xc + P.ADP_HEAD_HW, fy1),
                             (xc + P.ADP_NECK_HW, fy0),
                             (xc + P.ADP_NECK_HW, -96.7), close=True)
                make_face()
            extrude(st.sketch, amount=P.PANEL_H - P.ADP_TEE_Z0)

        # ── ЯЗИКИ в раму дна (жорсткі, хвіст 0.3 у плиту) ──
        for xc in P.ADP_TON_XC:
            with Locations((xc, (-96.7 + P.BODY_FRONT_Y + P.ADP_TON_L) / 2,
                            (P.ADP_TON_Z[0] + P.ADP_TON_Z[1]) / 2)):
                Box(P.ADP_TON_W,
                    P.BODY_FRONT_Y + P.ADP_TON_L + 96.7,
                    P.ADP_TON_Z[1] - P.ADP_TON_Z[0])

        # ── БАМП пальця: циліндр R0.8 віссю по X на тилі (половина
        # втоплена в плиту = зварка); верх зрізаний флетом на BUMP_Z —
        # прямий уступ у кишеню рами, низ круглий — рампа заходу ──
        with Locations(Location((P.ADP_FING_XC, -96.4, P.ADP_BUMP_Z),
                                (0, 90, 0))):
            Cylinder(P.ADP_BUMP_R, P.ADP_BUMP_W)
        with Locations((P.ADP_FING_XC, (-96.4 + -95.5) / 2,
                        P.ADP_BUMP_Z + 0.5)):
            Box(P.ADP_BUMP_W + 0.2, -95.5 - -96.4, 1.0,
                mode=Mode.SUBTRACT)
    return ad.part


if __name__ == "__main__":
    for variant in ("fan", "grille", "blank"):
        part = build(variant)
        print(f"{variant}: valid {part.is_valid} | vol {part.volume:.1f}")
        save(part, f"front_{variant}")
