"""
front_addon.py — ЗНІМНІ ПАНЕЛІ-АДДОНИ правої зони (15.07, схема
користувача; 17.07 — в3 «ОБОДОК+КОВПАК-ЛЕЗО»): панель розрізана МІЖ
смугою-обідком Z0..5 і верхнім ободком Z81.9 (X92..133.4), права
секція = окрема деталь:
  • fan    — гриль-ромбілі з тоншими ребрами 0.7 у колі лопатей + 4
             отвори ⌀3.2 (крок 32×32): Noctua 40мм гвинтиться до тилу
             аддона штатними самонарізами, ставиться РАЗОМ із ним;
  • grille — чиста решітка-ромбілі (продув без вентилятора);
  • blank  — глуха (тиха конфігурація / майбутня розмітка під порти).

Верх аддона = суцільна РАМКА 79.25..81.75 (поле ромбілів до 79.25 —
той самий рівень, що на панелі, «рамка вбудовується чітко по 79.25»).
Тримають (корпус → аддон → ковпак addon_clip.py):
  • НИЗ: сідло = верх смуги панелі (Z5); 2 ЯЗИКИ В ПЛОЩИНІ ламелі
    (17.07 #3, «як у вікні з портами») у КИШЕНІ смуги-обідка з
    вертикальними CRUSH-РЕБРАМИ (натяг 0.1/бік — «щоб витягти вгору
    треба зусиль, само не випадає»);
  • БОКИ: half-lap — панель лишає передню ламель у проліт (тримає і
    ВПЕРЕД), аддон лягає ЗЗАДУ своєю ламеллю;
  • ВЕРХ: КОВПАК-БАЛКА опускається в наскрізний розріз брови ЗА рамку
    (зазор 0.05) — тримає від вдавлення; підйом блокує ободок (0.15).
УСТАНОВКА КАЧАННЯМ (вертикально під ободок не пролазить): верх назад
~6° (кромка пірнає під брову за ободок), язики в пази, верх уперед;
фаска ADP_CHAMF верхнього ЗАДНЬОГО ребра рамки дає прохід повз ободок.
Зняття: витягти ковпак → качнути верх назад → підняти.
Ромбілі — ТА САМА глобальна ґратка/фаза, що на панелі (патерн
продовжується через розріз).
Запуск: .venv/bin/python cad/front_addon.py →
        out/front_fan|front_grille|front_blank .step/stl
Аддон у координатах збірки; друк — лицем вниз БЕЗ підтримок (язики в
шарі ламелі = елевовані консолі h1.55, як таби io_insert).
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
    # 16.07: низ = верх смуги-обідка панелі (сідло посадки); 17.07 в3:
    # верх = РАМКА до ADP_TOP_Z (вище — ободок корпусу, зазор 0.15)
    plate = sg.box(px0, P.ADP_STRIP_Z, px1, P.ADP_TOP_Z)
    # ламель: 17.07 (фідбек 132.86/92.99 −97.95 z81.4) — КРИЛА half-lap
    # ідуть ДО ВЕРХУ рамки як і ядро; фаска-клин у build() зріже свій
    # кут, а попереду клина лишиться губа 0.45×1.0 — суцільно
    # прикріплена по всій довжині, не сліверс
    lam = sg.box(lx0, P.ADP_STRIP_Z, lx1, P.ADP_TOP_Z)
    # ЯЗИКИ (17.07 #3, «як у вікні з портами»): продовження ламельного
    # шару ВНИЗ у кишені смуги-обідка панелі — в площині плити, без
    # виступів по Y (старі виступи 99.64/−95.19/1.00 вимагали підтримок;
    # тепер елевована консоль h1.55 — прецедент табів io_insert)
    for xc in P.ADP_TON_XC:
        lam = lam.union(sg.box(xc - P.ADP_TON_W / 2, P.ADP_TON_Z0,
                               xc + P.ADP_TON_W / 2, P.ADP_STRIP_Z + 0.2))

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
        # 79.25 — рівень поля панелі (вище — суцільна РАМКА до ADP_TOP_Z)
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
    lx0 = P.ADP_X[0] + P.ADP_LAP_CLR                    # 92.15
    lx1 = P.ADP_X[1] - P.ADP_LAP_CLR                    # 133.25
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

        # ── ЯЗИКИ (17.07 #3) — уже В ПЛАНІ ламелі (вниз у кишені
        # смуги-обідка панелі); тут лише CRUSH-РЕБРА і СКІС.
        # Ребра вертикальні на X-гранях (гладяться при посадці, як на
        # рейках SSD): R0.5, виступ 0.3 за грань → натяг 0.1/бік у
        # кишені 8.4; знизу конус-лійка. По Y — цілком у товщі ламелі
        # (центр −97.125, кишеня −98.0..−96.4) ──
        ymid = P.BODY_FRONT_Y - P.ADP_LAP_T / 2          # −97.125
        for xc in P.ADP_TON_XC:
            for sx in (-1, 1):
                rx = xc + sx * (P.ADP_TON_W / 2 + P.ADP_RIB_PROT
                                - P.ADP_RIB_R)
                with Locations((rx, ymid, P.ADP_TON_Z0 + 0.4)):
                    Cylinder(P.ADP_RIB_R,
                             P.ADP_STRIP_Z - 0.1 - (P.ADP_TON_Z0 + 0.4),
                             align=(Align.CENTER, Align.CENTER,
                                    Align.MIN))
                with Locations((rx, ymid, P.ADP_TON_Z0)):
                    Cone(0.1, P.ADP_RIB_R, 0.4,
                         align=(Align.CENTER, Align.CENTER, Align.MIN))
        # скіс ПЕРЕДНЬОЇ грані язиків знизу (кінематика качання: нижні
        # точки язика їдуть вперед на (5−z)·sinθ — нижче GRIP_Z грань
        # відкинута назад, вище повна товщина = робочий ЗАЧЕП за
        # полицею кишені. 24.07: GRIP 3.8→3.0 (зачеп 1.2→2.0, фідбек
        # «ненадійно тримається»); фінальний нахил качання 6°→4°
        # (на z3.0 зсув при 4° = 0.14 < зазору 0.15) ──
        yF = P.BODY_FRONT_Y - P.ADP_LAP_T                # −97.85
        wx0 = P.ADP_TON_XC[0] - P.ADP_TON_W / 2 - 0.5
        wx1 = P.ADP_TON_XC[-1] + P.ADP_TON_W / 2 + 0.5
        with BuildSketch(Plane.YZ.offset(wx0)) as tch:
            with BuildLine():
                Polyline((yF - 0.1, P.ADP_TON_GRIP_Z),
                         (yF - 0.1, P.ADP_TON_Z0 - 0.3),
                         (yF + 0.45, P.ADP_TON_Z0 - 0.3), close=True)
            make_face()
        extrude(tch.sketch, amount=wx1 - wx0, mode=Mode.SUBTRACT)

        # ── ФАСКА-КЛИН 45° верхнього ЗАДНЬОГО ребра рамки: дає прохід
        # повз ободок при установці КАЧАННЯМ (~6°; радіус фаскованого
        # кута від півота язика 76.76 < 76.9 до ребра ободка, передній
        # верхній кут при нахилі 81.81 < 81.9). Гіпотенуза через
        # (−96.4, top−chamf) і (−96.4−chamf, top) ──
        yb = P.BODY_FRONT_Y                      # тил рамки −96.4
        with BuildSketch(Plane.YZ.offset(lx0 - 1)) as ch:
            with BuildLine():
                Polyline((yb + 0.5, P.ADP_TOP_Z - P.ADP_CHAMF - 0.5),
                         (yb - P.ADP_CHAMF - 0.5, P.ADP_TOP_Z + 0.5),
                         (yb + 0.5, P.ADP_TOP_Z + 0.5), close=True)
            make_face()
        extrude(ch.sketch, amount=lx1 - lx0 + 2, mode=Mode.SUBTRACT)
    return ad.part


if __name__ == "__main__":
    for variant in ("fan", "grille", "blank"):
        part = build(variant)
        print(f"{variant}: valid {part.is_valid} | vol {part.volume:.1f}")
        save(part, f"front_{variant}")
