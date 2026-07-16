"""
front_addon.py — ЗНІМНІ ПАНЕЛІ-АДДОНИ правої зони (15.07, схема
користувача; 16.07 — спрощення «КОВПАК»): панель розрізана вище
СМУГИ-обідка Z0..5 (X92..133.4), права секція = окрема деталь:
  • fan    — гриль-ромбілі з тоншими ребрами 0.7 у колі лопатей + 4
             отвори ⌀3.2 (крок 32×32): Noctua 40мм гвинтиться до тилу
             аддона штатними самонарізами, ставиться РАЗОМ із ним;
  • grille — чиста решітка-ромбілі (продув без вентилятора);
  • blank  — глуха (тиха конфігурація / майбутня розмітка під порти).

Посадка ВЕРТИКАЛЬНА (згори вниз), тримають 3 деталі (корпус → аддон →
ковпак lsi_clip.py):
  • НИЗ: сідло = верх смуги панелі (Z5); 2 жорсткі ЯЗИКИ у пази
    передньої рами дна з вертикальними CRUSH-РЕБРАМИ (натяг 0.1/бік —
    «щоб витягти вгору треба зусиль, само не випадає»);
  • БОКИ: half-lap — панель лишає передню ламель у проліт (повна
    висота, тримає і ВПЕРЕД), аддон лягає ЗЗАДУ своєю ламеллю;
  • ВЕРХ: НОТЧ у кромці біля розрізу — рука ковпака крізь канал у
    брові блокує підйом (люфт 0.1).
Зняття: зняти ковпак → підняти аддон угору (зусилля crush-ребер).
Ромбілі — ТА САМА глобальна ґратка/фаза, що на панелі (патерн
продовжується через розріз).
Запуск: .venv/bin/python cad/front_addon.py →
        out/front_fan|front_grille|front_blank .step/stl
Аддон у координатах збірки; друк — лицем вниз (⚠️ язики нижче Z5 =
2 мікро-острови: 2 цятки підтримки пензлем).
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
    # 16.07: низ = верх смуги-обідка панелі (сідло посадки)
    plate = sg.box(px0, P.ADP_STRIP_Z, px1, P.PANEL_H)
    lam = sg.box(lx0, P.ADP_STRIP_Z, lx1, P.PANEL_H)

    cut_all = []

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
        # поле: обідок 2 від країв плити, низ = кромка+2 (7.0), верх
        # 79.25 (вище — зона нотча/брови за плитою)
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
        field = sg.box(px0 + 2.0, P.ADP_STRIP_Z + 2.0, px1 - 2.0, 79.25) \
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
                    if rb.intersects(screw_pads):
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

        # ── ЯЗИКИ в раму дна (жорсткі): нижче смуги — відступ 0.2 від
        # її тилу −96.4 (не тре при посадці); вище смуги — РАЙЗЕР із
        # вкоріненням 0.3 у плиту (0.2 люфт над верхом смуги Z5) ──
        y1t = P.BODY_FRONT_Y + P.ADP_TON_L               # −94.4
        for xc in P.ADP_TON_XC:
            with Locations((xc, (P.BODY_FRONT_Y + 0.2 + y1t) / 2,
                            (P.ADP_TON_Z[0] + P.ADP_TON_Z[1]) / 2)):
                Box(P.ADP_TON_W, P.ADP_TON_L - 0.2,
                    P.ADP_TON_Z[1] - P.ADP_TON_Z[0])
            with Locations((xc, (-96.7 + y1t) / 2,
                            (P.ADP_STRIP_Z + 0.2 + P.ADP_TON_Z[1]) / 2)):
                Box(P.ADP_TON_W, y1t + 96.7,
                    P.ADP_TON_Z[1] - P.ADP_STRIP_Z - 0.2)
            # crush-ребра (вертикальні, як на рейках SSD): циліндр R0.5
            # з виступом 0.3 за X-грань → натяг 0.1/бік у пазу 8.4;
            # знизу конус-лійка (захід у паз без задирів)
            for sx in (-1, 1):
                rx = xc + sx * (P.ADP_TON_W / 2 + P.ADP_RIB_PROT
                                - P.ADP_RIB_R)
                with Locations((rx, -95.3, P.ADP_TON_Z[0] + 0.4)):
                    Cylinder(P.ADP_RIB_R,
                             P.FRAME_T - 0.1 - (P.ADP_TON_Z[0] + 0.4),
                             align=(Align.CENTER, Align.CENTER,
                                    Align.MIN))
                with Locations((rx, -95.3, P.ADP_TON_Z[0])):
                    Cone(0.1, P.ADP_RIB_R, 0.4,
                         align=(Align.CENTER, Align.CENTER, Align.MIN))

        # ── НОТЧ верхньої кромки біля розрізу: кишеня під РУКУ КОВПАКА
        # (lsi_clip.py) — блокує підйом (дно нотча 85.5, рука 85.6);
        # передня стінка 1.4 (лице ціле — ззовні нотч не видно);
        # відкритий угору і вліво (у розріз/канал брови) ──
        with Locations(((P.ADP_X[0] - 1 + P.ADP_NOTCH_X1) / 2,
                        (P.FRONT_Y + 1.4 + -96.3) / 2,
                        (P.ADP_NOTCH_Z0 + P.PANEL_H + 0.1) / 2)):
            Box(P.ADP_NOTCH_X1 - (P.ADP_X[0] - 1),
                -96.3 - (P.FRONT_Y + 1.4),
                P.PANEL_H + 0.1 - P.ADP_NOTCH_Z0, mode=Mode.SUBTRACT)
    return ad.part


if __name__ == "__main__":
    for variant in ("fan", "grille", "blank"):
        part = build(variant)
        print(f"{variant}: valid {part.is_valid} | vol {part.volume:.1f}")
        save(part, f"front_{variant}")
