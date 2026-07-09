"""
front.py — параметрична ФРОНТ-ПАНЕЛЬ 2U (рішення 2026-07-02):
  • плита 254 × 88.75 × 3 (Y[-99.4,-96.4]), верхні кути R5, низ прямий
  • I/O-апертура mini-ITX з оригіналу 1:1 (плата на тому ж датумі BOARD_Z)
  • кнопка ⌀12 @ (81.2, Z58) — нативний циліндр (справжнє коло у STEP)
  • слоти вушок 4+4 — дослівно з оригіналу (перевірена посадка Lab-RAX)
  • rhombille (tumbling blocks) ЛИШЕ над I/O; права зона суцільна (під
    майбутній виріз HBA за замірами користувача)
Запуск: .venv/bin/python cad/front.py
Панель у координатах збірки: план у (X,Z), екструзія по -Y від Y=-96.4.
"""
import math
from build123d import *
import shapely.geometry as sg
from shapely.ops import unary_union
import params as P
import ioports
from exporter import save


def _rounded(poly, r, qs=8):
    return poly.buffer(-r).buffer(r, quad_segs=qs)


def _polys(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    if geom.geom_type in ('MultiPolygon', 'GeometryCollection'):
        return [g for g in geom.geoms if g.geom_type == 'Polygon']
    return []


def plan_panel():
    """2D-розкладка панелі в (X,Z). Повертає полігон(и) з дірками-кільцями."""
    # ── контур: прямокутник, ВСІ 4 кути R2 ──
    outline = _rounded(sg.box(P.EAR_L_X, 0, P.EAR_R_X, P.PANEL_H),
                       P.PANEL_CORNER_R)

    holes = []
    # ── I/O: АПЕРТУРА 1:1 під щиток (09.07: порти переїхали у змінну
    # друковану ВСТАВКУ io_insert.py — універсальність під інші плати;
    # сталевий щиток теж сяде) ──
    aper = _rounded(sg.box(P.IO_X[0], P.IO_Z[0], P.IO_X[1], P.IO_Z[1]),
                    P.INS_APER_R)
    holes.append(aper)
    # ── слоти вушок (вертикальні стадіони) ──
    for xc in P.EAR_SLOT_XC:
        for z0, z1 in P.EAR_SLOT_Z:
            r = P.EAR_SLOT_W / 2
            holes.append(sg.LineString([(xc, z0 + r), (xc, z1 - r)])
                         .buffer(r, quad_segs=12))

    # ── rhombille: Г-подібне поле (скріншот 2026-07-02) ──
    # смуга над апертурою + права зона до низу; зліва від апертури суцільно;
    # правий край = дзеркало лівого краю апертури (симетричні відступи);
    # зверху/знизу відступ PANEL_EDGE_RIM
    er = P.PANEL_EDGE_RIM
    s = P.PANEL_RHOMB_S                # сторона ромба = сторона комірки
    dx = math.sqrt(3) * s              # крок ґратки pointy-top комірок
    dy = 1.5 * s
    ero = P.RHOMB_T / 2 + P.RHOMB_R
    # фаза ґратки (2026-07-02, ітерація 4):
    #  X: ВЕРШИНИ КИШЕНЬ цілих ромбиків рівно на лівій межі поля (=лінія
    #     апертури). Кишеня вужча за ромб (ребро з'їдає вершину на tip_inset).
    #  Z: нижня межа по «талії» нижніх ромбів → ряд трикутничків над портами
    _probe = sg.Polygon([(0, 0), (-s * math.cos(math.radians(30)), -s / 2),
                         (0, -s), (s * math.cos(math.radians(30)), -s / 2)]) \
        .buffer(-ero).buffer(P.RHOMB_R, quad_segs=8)
    tip_inset = s * math.cos(math.radians(30)) - abs(_probe.bounds[0])
    cx0 = P.IO_X[0] - tip_inset
    cz0 = P.IO_Z[1] + P.PANEL_RIM + P.PANEL_RHOMB_S / 2

    # межі правої зони ПРИВ'ЯЗАНІ до ґратки (2026-07-02: «зрівняти трикутники
    # з ромбиками»): лінія меж — за тим самим рецептом, що лівий край смуги
    # (вершини цілих ромбів на лінії, сусідній ряд — навпіл у трикутники).
    # Колонки ґратки що dx/2; ліва межа ≥ апертура+RIM, права ≤ FIELD_R_X.
    jL = math.ceil((P.IO_X[1] + P.PANEL_RIM - tip_inset - cx0) / (dx / 2))
    BL = cx0 + jL * dx / 2 + tip_inset          # ≈ 91.67
    jR = math.floor((P.FIELD_R_X + tip_inset - cx0) / (dx / 2))
    BR = cx0 + jR * dx / 2 - tip_inset          # ≈ 125.05

    # 08.07: поле = ВСЯ панель (апертури/окантовки більше нема) до BR
    # праворуч (за BR — суцільно під планку HBA, як і було); обідок 2.0
    # навколо кожного порту
    # зліва — до внутрішньої грані СМУГИ лівої стінки (-78.1): ромбілі
    # в зоні -80..-78.1 упирались у торець смуги (фідбек 08.07)
    # верх — до низу кова брови (09.07: кишені впирались у брову —
    # сліпі трикутники); брова: zb=PANEL_H-BROW_H, ków вниз на BROW_D
    field = sg.box(P.WALL_L_X + P.BEAD_W, er, BR,
                   P.PANEL_H - P.BROW_H - P.BROW_D - 0.5)
    # обідок апертури: фальц ззаду сягає +1.6, наскрізним кишеням
    # треба ще ≥1.5 суцільного — разом 3.2
    port_pads = aper.buffer(P.INS_REBATE_W + 1.6)
    field = field.difference(port_pads)
    bx, bz = P.BUTTON_XZ
    btn_pad = sg.Point(bx, bz).buffer(P.BUTTON_D / 2 + P.BUTTON_RIM, 32)
    field = field.difference(btn_pad)
    # суцільний пад за картою LSI (край карти + защіпка-виделка;
    # панель тут цільна — жорсткість зони)
    fz0, fz1 = P.LSI_FORK_Z
    field = field.difference(sg.box(
        P.LSI_X - P.LSI_SLOT_W / 2 - P.LSI_FORK_W - 2.0, fz0 - 2.0,
        P.LSI_X + P.LSI_SLOT_W / 2 + P.LSI_FORK_W + 2.0, fz1 + 1.0))
    # вентилятор: отвір НЕ ріжеться — ромбілі йдуть наскрізь (вбудований
    # гриль, 2026-07-03); суцільні пади лише навколо чотирьох кріплень
    for sx in (-1, 1):
        for sz in (-1, 1):
            field = field.difference(sg.Point(
                P.FAN_CX + sx * P.FAN_SCREW_CC / 2,
                P.FAN_CZ + sz * P.FAN_SCREW_CC / 2).buffer(
                P.FAN_SCREW_D / 2 + 2.0, 16))
    # коло лопатей вентилятора: гриль ріжеться і ПОЗА полем (права третина
    # вентилятора за межею BR інакше дме в глуху панель)
    blades = sg.Point(P.FAN_CX, P.FAN_CZ).buffer(18.0, 48)
    # пади гвинтів: кишеню, що ТОРКАЄТЬСЯ пада, не ріжемо взагалі (інакше
    # обкусані дуги «скруглення на прямій» у ребрах — фідбек 2026-07-03)
    screw_pads = unary_union([sg.Point(
        P.FAN_CX + sx * P.FAN_SCREW_CC / 2,
        P.FAN_CZ + sz * P.FAN_SCREW_CC / 2).buffer(P.FAN_SCREW_D / 2 + 2.0, 16)
        for sx in (-1, 1) for sz in (-1, 1)])
    fx0, fz0, fx1, fz1 = field.bounds
    ncol = int((fx1 - fx0) / dx) + 3
    nrow = int((max(fz1 - cz0, cz0 - fz0)) / dy) + 3
    rhomb = []
    for row in range(-nrow, nrow + 1):
        for col in range(-ncol, ncol + 1):
            hx = cx0 + col * dx + (row % 2) * dx / 2
            hz = cz0 + row * dy
            V = [(hx + s * math.cos(math.radians(a)),
                  hz + s * math.sin(math.radians(a)))
                 for a in range(90, 450, 60)]
            for k in (0, 2, 4):        # 3 ромби на комірку (tumbling blocks)
                rb = sg.Polygon([(hx, hz), V[k], V[k + 1], V[(k + 2) % 6]])
                if not (rb.intersects(field) or rb.intersects(blades)):
                    continue
                # пади гвинтів і обід кнопки НЕ вбивають ромб цілком
                # (лишались залиті плями/лінзи — фідбек 04.07 «напрошується
                # дорізка»): кишеня ріжеться, пад/обід вирізається з неї
                pk = rb.buffer(-ero).buffer(P.RHOMB_R, quad_segs=8) \
                       .intersection(field).difference(screw_pads) \
                       .difference(btn_pad).difference(port_pads)
                # хвости-щілини на межі з ободом/падами (фідбек 08.07:
                # 89.5/60.7 біля кнопки) — морф. opening знімає тонше 0.7
                if rb.intersects(btn_pad) or rb.intersects(port_pads):
                    pk = pk.buffer(-0.35).buffer(0.35, quad_segs=8)
                for g in _polys(pk):
                    # ріжемо й часткові шматки по краях (границя області має
                    # проглядатись); фільтр лише проти пилу: <1.5мм², вужчі ~0.7
                    if g.area < 1.5 or g.buffer(-0.45).is_empty:
                        continue
                    rhomb.append(g)
                # у колі лопатей вентилятора — ширші прорізи:
                # межа умовного круга сама проступає в патерні
                if rb.intersects(blades):
                    # ребро гриля 0.9: тонше з'їдає «волосяна» чистка (0.8)
                    # і воно хлипке для друку (урок: діра із зірочками)
                    pk2 = rb.buffer(-(0.45 + P.RHOMB_R)) \
                            .buffer(P.RHOMB_R, quad_segs=8) \
                            .intersection(blades).difference(screw_pads)
                    for g in _polys(pk2):
                        if g.area >= 1.5 and not g.buffer(-0.3).is_empty:
                            rhomb.append(g)

    # ── чистка «цигликів» (2026-07-02): обірвані фрагменти ребер, що висять
    # у злитих крайових вирізах і не з'єднані з рештою решітки, — вирізаємо.
    # Метод: скелет = (поле+обвідка − кишені) мінус морф. відкриття 0.65
    # (усе тонше 1.3мм); маленькі ІЗОЛЬОВАНІ компоненти скелета → в отвори.
    rhombU = unary_union(rhomb)
    ctx = field.union(blades).buffer(3.0).difference(rhombU)
    opened = ctx.buffer(-0.65).buffer(0.65, quad_segs=8)
    skinny = ctx.difference(opened)
    bricks = []
    for c in _polys(skinny):
        if c.area >= 10.0 or not c.intersects(field.union(blades)):
            continue
        # справжнє ребро тримається за товстий матеріал ≥2 кінцями;
        # «циглик» — висячий: ≤1 точка контакту
        contacts = len(_polys(c.buffer(0.05).intersection(opened)))
        if contacts <= 1:
            bricks.append(c)
    holes.extend(rhomb)
    holes.extend(bricks)

    # ── чистка «волосин» (2026-07-02): стінки матеріалу тонші ~0.6мм
    # (з'являлись між вирізами й ободком кнопки) — вливаються у сусідній виріз
    mat = field.union(blades).buffer(3.0).difference(unary_union(rhomb + bricks))
    hair = mat.difference(mat.buffer(-0.4).buffer(0.4, quad_segs=8))
    holes.extend([c for c in _polys(hair)
                  if c.area < 5.0 and c.intersects(field.union(blades))])

    # ── фінал: set_precision зносить мікро-зигзаги/самоперетини швів
    # (спрощення їх не брало — це топологія, не зайві точки); найбільша
    # компонента = панель, решта — острови, відпадають самі
    from shapely import set_precision
    solid = set_precision(outline.difference(unary_union(holes)), 0.01)
    comps = _polys(solid)
    return [max(comps, key=lambda c: c.area)]


def brow_part():
    """«Брова» жорсткості — полиця вздовж верху з тильного боку панелі.

    ⚠️ Урок: філети ПІСЛЯ union з копланарними гранями → segfault OCC.
    Тому всі радіуси закладені ДО union: профіль (Y,Z) із R1 на задніх
    ребрах і УВІГНУТИМ R1 (ков) у примиканні низу до тильної грані —
    2D-філетами вершин скетча; торці скруглені на окремій деталі.
    Хвіст профілю заходить у панель на 0.5мм (надійний union, невидимо).
    Стик із верхньою поверхнею панелі НЕ скруглюється — продовжує площину.
    """
    y0 = P.EAR_FLANGE_Y            # тильна грань панелі (-96.4)
    y1 = y0 + P.BROW_D             # задня грань брови
    zt = P.PANEL_H                 # верх (урівень з панеллю)
    zb = zt - P.BROW_H             # низ брови
    bwx0, bwx1 = P.BROW_X
    r = P.BROW_R
    with BuildPart() as bp:
        # профіль (2026-07-03 v2, «по внутрішній площині — увігнуте»):
        # нижня грань брови ЗНИКАЄ — вся спідня частина = ВЕЛИКИЙ ков-чверть
        # R=BROW_D від задньо-нижнього ребра дотично в панель (як намалював
        # користувач); хвіст пірнає в панель нижче кінця кова
        Rc = P.BROW_D                                # 5.0 — чверть на всю глибину
        expected = P.BROW_D * P.BROW_H + 0.5 * (P.BROW_H + Rc) \
            + (Rc * Rc - math.pi * Rc * Rc / 4)
        for arc_r in (Rc, -Rc):                      # бік дуги — перевіркою площі
            with BuildSketch(Plane.YZ.offset(bwx0)) as prof:
                with BuildLine():
                    Polyline((y0 - 0.5, zt), (y1, zt),   # верх (стик — без R)
                             (y1, zb))                   # задня грань до низу
                    RadiusArc((y1, zb), (y0, zb - Rc), arc_r)      # ков R5
                    Polyline((y0, zb - Rc), (y0 - 0.5, zb - Rc),   # хвіст
                             (y0 - 0.5, zt))
                make_face()
                fillet(prof.vertices().filter_by(
                    lambda v: abs(v.X - y1) < 1e-6 and v.Y > zt - 1e-6),
                    radius=r)                            # лише задній ВЕРХНІЙ кут
            if abs(prof.sketch.area - (expected
                    - (r * r - math.pi * r * r / 4))) < 0.15:
                break
        extrude(amount=bwx1 - bwx0)
        # торці «через впадину» (2026-07-03, правило ≤90°): у плані кінці
        # брови вливаються в панель увігнутими чвертями R5 (дотично до панелі)
        Rc = 5.0
        with BuildSketch(Plane.XY.offset(zb - 3)) as clip:
            with BuildLine():
                Polyline((bwx0, y0 - 1), (bwx0, y0))
                RadiusArc((bwx0, y0), (bwx0 + Rc, y1), Rc)
                Line((bwx0 + Rc, y1), (bwx1 - Rc, y1))
                RadiusArc((bwx1 - Rc, y1), (bwx1, y0), Rc)
                Polyline((bwx1, y0), (bwx1, y0 - 1), (bwx0, y0 - 1))
            make_face()
            # (R1 на стику дуга↔задня грань прибрано: баг 2D-філета вершин
            # build123d 0.11 — «Fillet algorithm failed» з коорд. поза моделлю)
        extrude(amount=P.BROW_H + 6, mode=Mode.INTERSECT)
    return bp.part


def build():
    panel_polys = plan_panel()

    with BuildPart() as fp:
        # план (X,Z) → площина XZ на Y=-96.4, екструзія 3мм у бік -Y
        with BuildSketch(Plane.XZ.offset(96.4)):
            for poly in panel_polys:
                with BuildLine():
                    Polyline(*list(poly.exterior.simplify(0.03).coords)[:-1],
                             close=True)
                make_face()
                for ring in poly.interiors:
                    rp = sg.Polygon(ring)
                    if abs(rp.area) < 0.8:
                        continue          # вироджене кільце — пил, не ріжемо
                    # 0.05: мікро-зигзаги швів вузькі↔широкі кишені гриля
                    rp = rp.simplify(0.05).buffer(0)
                    if rp.geom_type != 'Polygon' or rp.area < 0.8:
                        continue
                    coords = list(rp.exterior.coords)[:-1]
                    if len(coords) < 3:
                        continue
                    with BuildLine():
                        Polyline(*coords, close=True)
                    make_face(mode=Mode.SUBTRACT)
        extrude(amount=P.FRONT_PANEL_T)

        # ── фальц вставки (09.07): кишеня з ТИЛУ навколо апертури
        # (полиця +1.6, глибина 1.5 — лице лишає 1.5); внизу локально
        # глибші кишені під жорсткі язички вставки ──
        aperp = _rounded(sg.box(P.IO_X[0], P.IO_Z[0], P.IO_X[1], P.IO_Z[1]),
                         P.INS_APER_R)
        reb = aperp.buffer(P.INS_REBATE_W, quad_segs=8)
        for xc in P.INS_TAB_XC:
            reb = reb.union(sg.box(xc - P.INS_TAB_W / 2 - 0.3,
                                   P.IO_Z[0] - 1.4 - P.INS_TAB_H - 0.4,
                                   xc + P.INS_TAB_W / 2 + 0.3,
                                   P.IO_Z[0]))
        with BuildSketch(Plane.XZ.offset(96.3)) as rb:
            with BuildLine():
                Polyline(*list(reb.exterior.simplify(0.03).coords)[:-1],
                         close=True)
            make_face()
        extrude(rb.sketch, amount=P.INS_REBATE_D + 0.1, mode=Mode.SUBTRACT)
        # кишені бампів у СТЕЛІ фальца (пружні пальці вставки клацають
        # знизу вгору; стінка-поріг до тилу 0.4 — тримає від виштовхування
        # назад при встромлянні кабелів, доки порти не підіпруть)
        for xc in P.INS_DIMPLE_XC:
            with Locations((xc, -97.65, 51.85)):
                Box(P.INS_LIP_TAB_W + 1.0, 0.8, 0.9, mode=Mode.SUBTRACT)

        # кнопка ⌀12 — нативний циліндр (справжнє коло у STEP)
        bx, bz = P.BUTTON_XZ
        with Locations(Location((bx, -96.4 + 1, bz), (90, 0, 0))):
            Cylinder(P.BUTTON_D / 2, P.FRONT_PANEL_T + 2,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)

        # вентилятор: 4 кріплення ⌀3.2 (крок 32×32); отвору нема — гриль
        for sx in (-1, 1):
            for sz in (-1, 1):
                with Locations(Location(
                        (P.FAN_CX + sx * P.FAN_SCREW_CC / 2, -96.4 + 1,
                         P.FAN_CZ + sz * P.FAN_SCREW_CC / 2), (90, 0, 0))):
                    Cylinder(P.FAN_SCREW_D / 2, P.FRONT_PANEL_T + 2,
                             align=(Align.CENTER, Align.CENTER, Align.MIN),
                             mode=Mode.SUBTRACT)

        # ── «брова» жорсткості: готова деталь (радіуси вже в ній) ──
        add(brow_part())

        # ── LSI (09.07 в2, «замість вбудованої»): виделки на панелі
        # НЕМА — її роль виконує ЗНІМНА защіпка-виделка (lsi_clip.py),
        # що опускається ЗГОРИ в колодязь крізь брову ПІСЛЯ установки
        # плати: паз защіпки захоплює передній край карти LSI (верх на
        # LSI_BRK_TOP=80.75), барби клацають у кишені стінок колодязя ──
        with Locations((P.LSI_X, (-96.45 + -92.3) / 2, (78.0 + 89.75) / 2)):
            Box(2 * P.LSI_WELL_HW, -92.3 - -96.45, 89.75 - 78.0,
                mode=Mode.SUBTRACT)
        # кишені барбів у X-стінках колодязя (повний матеріал брови)
        for sx in (-1, 1):
            with Locations((P.LSI_X + sx * (P.LSI_WELL_HW + 0.25),
                            (-95.6 + -93.2) / 2, 86.95)):
                Box(0.5, -93.2 - -95.6, 2.1, mode=Mode.SUBTRACT)

    return fp.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "front")
