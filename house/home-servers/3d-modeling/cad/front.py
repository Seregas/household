"""
front.py — параметрична ФРОНТ-ПАНЕЛЬ 2U (рішення 2026-07-02):
  • плита 254 × 88.75 × 3 (Y[-99.4,-96.4]), верхні кути R5, низ прямий
  • I/O-апертура mini-ITX з оригіналу 1:1 (плата на тому ж датумі BOARD_Z)
  • кнопка ⌀12 @ (81.2, Z58) — нативний циліндр (справжнє коло у STEP)
  • слоти вушок 4+4 — дослівно з оригіналу (перевірена посадка Lab-RAX)
  • rhombille (tumbling blocks) між бічними смугами 21мм
  • права зона X92..133.4 РОЗРІЗАНА між смугою-обідком Z0..5 і верхнім
    ОБОДКОМ Z81.9..верх (17.07 в3) — знімний аддон front_addon.py;
    посадка: сідло = верх смуги, ламельні язики у КИШЕНІ смуги (#3),
    half-lap по боках; від вдавлення вгорі тримає КОВПАК-БАЛКА
    (addon_clip.py) у наскрізному розрізі брови, ЗА рамкою аддона
    (Y-стоп — зуб балки в надрізі правої брови)
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
    # ── РОЗРІЗ правої зони (15.07): права секція стала знімним
    # повнорозмірним АДДОНОМ (front_addon.py: fan/grille/blank);
    # вікно-з-фальцом 14.07 ВИДАЛЕНО. 16.07: розріз ВИЩЕ СМУГИ-обідка
    # (Z0..5 лишається в панелі — сідло аддона, фідбек «залишити смугу»).
    # 17.07 в3: розріз НИЖЧЕ ОБОДКА (ADP_RIM_Z0..верх лишається в панелі
    # — «ободок навколо панелі залишиться», плита t3 + брова = рама).
    # Half-lap ламелі по боках розрізу додаються 3D у build() ──
    holes.append(sg.box(P.ADP_X[0], P.ADP_STRIP_Z, P.ADP_X[1],
                        P.ADP_RIM_Z0))
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


    # 08.07: поле = ВСЯ панель (апертури/окантовки більше нема) до BR
    # праворуч (за BR — суцільно під планку HBA, як і було); обідок 2.0
    # навколо кожного порту
    # 09.07: «для загальної симетрії — суцільні смуги по бокам панелі
    # на 21 мм зліва і справа» (вушка/монтажні слоти в них і так
    # лишаються отворами); верх — до низу кова брови (кишені впирались
    # у брову). 15.07: права межа поля = 2мм обідка до РОЗРІЗУ (ромбілі
    # правої зони тепер в аддоні; права смуга панелі 133.4..154.4 —
    # суцільна, як і була: EAR_R_X−21 = ADP_X[1])
    field = sg.box(P.EAR_L_X + 21.0, er, P.ADP_X[0] - 2.0,
                   P.PANEL_H - P.BROW_H - P.BROW_D - 0.5)
    # обідок апертури: фальц ззаду сягає +1.6, наскрізним кишеням
    # треба ще ≥1.5 суцільного — разом 3.2
    port_pads = aper.buffer(P.INS_REBATE_W + 1.6)
    field = field.difference(port_pads)
    bx, bz = P.BUTTON_XZ
    btn_pad = sg.Point(bx, bz).buffer(P.BUTTON_D / 2 + P.BUTTON_RIM, 32)
    field = field.difference(btn_pad)
    # (09.07: суцільний пад під LSI ПРИБРАНО разом із вбудованою
    # виделкою — защіпка-виделка знімна, край карти панелі не торкається
    # (упор у перемичці защіпки за 2мм від тилу) → ромбілі як скрізь)
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
                if not rb.intersects(field):
                    continue
                # обід кнопки/апертур НЕ вбивають ромб цілком
                # (лишались залиті плями/лінзи — фідбек 04.07 «напрошується
                # дорізка»): кишеня ріжеться, обід вирізається з неї
                pk = rb.buffer(-ero).buffer(P.RHOMB_R, quad_segs=8) \
                       .intersection(field) \
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

    # ── чистка «цигликів» (2026-07-02): обірвані фрагменти ребер, що висять
    # у злитих крайових вирізах і не з'єднані з рештою решітки, — вирізаємо.
    # Метод: скелет = (поле+обвідка − кишені) мінус морф. відкриття 0.65
    # (усе тонше 1.3мм); маленькі ІЗОЛЬОВАНІ компоненти скелета → в отвори.
    rhombU = unary_union(rhomb)
    ctx = field.buffer(3.0).difference(rhombU)
    opened = ctx.buffer(-0.65).buffer(0.65, quad_segs=8)
    skinny = ctx.difference(opened)
    bricks = []
    for c in _polys(skinny):
        if c.area >= 10.0 or not c.intersects(field):
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
    mat = field.buffer(3.0).difference(unary_union(rhomb + bricks))
    hair = mat.difference(mat.buffer(-0.4).buffer(0.4, quad_segs=8))
    holes.extend([c for c in _polys(hair)
                  if c.area < 5.0 and c.intersects(field)])

    # ── фінал: set_precision зносить мікро-зигзаги/самоперетини швів
    # (спрощення їх не брало — це топологія, не зайві точки).
    # 16.07: смуга-обідок Z0..5 знову з'єднує ліву панель і праву смугу
    # (план — одна компонента); фільтр 50мм² лишається проти пилу
    from shapely import set_precision
    solid = set_precision(outline.difference(unary_union(holes)), 0.01)
    return [c for c in _polys(solid) if c.area > 50.0]


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
        # ── 17.07 ч.3 (фідбек 135.51/−91.56/88.59 «неякісна стиковка»):
        # хвіст пірнання 0.9 закінчувався ПОСЕРЕД кутового філета R1.2
        # вежі — квадратний край стирчав за дугу (сходинка 0.3 згори),
        # а спроба зрізати хвіст тим самим циліндром відкривала шахту
        # філетного вирізу під ним. СИЛУЕТ-рішення: хвіст іде НАСКРІЗЬ
        # через кут до ЗОВНІШНЬОЇ дотичної бульноса (BROW_X 136.2/−81.4
        # — задня площина −91.4 там дотично переходить у зовнішню дугу);
        # внутрішній філет вежі ховається ПІД бровою (стовп заокруглю-
        # ється вгору в підбрів'я), сходинки і шахти нема. ──
        # ТОРЦІ (14.07, фідбек «брова має плавно переходити в бічну
        # стінку»): дуги R5 на кінцях ВИДАЛЕНІ ЦІЛКОМ — спадок до-вежевої
        # ери, коли брова закінчувалась у повітрі. Тепер тил вежі = тил
        # брови (−91.4, площини продовжуються), тож повний профіль просто
        # пірнає у вежу 0.9 по X (об'ємний union у збірці) — стик
        # копланарний, невидимий. Будь-яка дуга тут (навіть дотична з
        # втопленням) виринала з-під грані вежі під кутом → клин-щілина.
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

        # (15.07: фальц ФРОНТ-АПЕРТУРИ з кишенями ВИДАЛЕНО — права зона
        # тепер повнорозмірний аддон з розрізом панелі, див. нижче)

        # кнопка ⌀12 — нативний циліндр (справжнє коло у STEP)
        bx, bz = P.BUTTON_XZ
        with Locations(Location((bx, -96.4 + 1, bz), (90, 0, 0))):
            Cylinder(P.BUTTON_D / 2, P.FRONT_PANEL_T + 2,
                     align=(Align.CENTER, Align.CENTER, Align.MIN),
                     mode=Mode.SUBTRACT)

        # (кріплення вентилятора ⌀3.2 — в аддоні front_addon.py;
        # вентилятор гвинтиться до тилу аддона, не до панелі)

        # ── «брова» жорсткості: готова деталь (радіуси вже в ній) ──
        add(brow_part())

        # ── зачистка ПІД ОБОДКОМ у прольоті (17.07 в3): нижче низу
        # ободка (ADP_RIM_Z0) плити в прольоті нема — хвіст профілю
        # брови 0.5 (−96.9) і низ кова R5 (до 79.75) висіли б у повітрі
        # за аддоном і заважали б качанню при установці. Зрізаємо ВСЕ за
        # прольотом нижче ободка (до −91.0, повз тил брови −91.4 не
        # треба — кова там уже нема). Вище ADP_RIM_Z0 брова/ков цілі й
        # злиті з плитою ободка ──
        ax0, ax1 = P.ADP_X
        with Locations(((ax0 + ax1) / 2, (-99.5 + -91.0) / 2,
                        (79.0 + P.ADP_RIM_Z0) / 2)):
            Box(ax1 - ax0, -91.0 - -99.5, P.ADP_RIM_Z0 - 79.0,
                mode=Mode.SUBTRACT)

        # ── КИШЕНІ ЯЗИКІВ у СМУЗІ-ОБІДКУ (17.07 #3: язики аддона тепер
        # В ПЛОЩИНІ ламелі, як таби io_insert — друк без підтримок;
        # пази рами дна + лійка ВИДАЛЕНІ з floor.py): виїмка з тилу
        # смуги, відкрита назад (−96.4) і догори (Z5); попереду
        # лишається полиця лиця 1.4 (тил полиці −98.0, перед язика
        # −97.85 → зазор 0.15, як у half-lap) ──
        ypk = P.BODY_FRONT_Y - P.ADP_LAP_T - P.ADP_LAP_CLR   # −98.0
        for xc in P.ADP_TON_XC:
            pw = P.ADP_TON_W + 2 * P.ADP_SLOT_CLR            # 8.4
            zp0 = P.ADP_TON_Z0 - P.ADP_SLOT_CLR              # 2.4
            with Locations((xc, (ypk + -96.0) / 2, (zp0 + 6.0) / 2)):
                Box(pw, -96.0 - ypk, 6.0 - zp0, mode=Mode.SUBTRACT)

        # ── LSI (09.07 в2, «замість вбудованої»): виделки на панелі
        # НЕМА — її роль виконує ЗНІМНИЙ КОВПАК (addon_clip.py), що
        # опускається ЗГОРИ в колодязь крізь брову ПІСЛЯ установки
        # плати: паз ковпака захоплює передній край карти LSI (верх на
        # LSI_BRK_TOP=80.75), лівий барб клацає у кишеню лівої стінки.
        # 17.07 «повний розріз»: колодязь ДО РОЗРІЗУ x92 (смужка
        # 91.6..92 геть — фідбек 92.00/−93.96/80.91) і НАСКРІЗЬ по
        # глибині брови (до −91.0, повз тил −91.4) ──
        with Locations(((P.LSI_X - P.LSI_WELL_HW + P.ADP_X[0]) / 2,
                        (-96.45 + -91.0) / 2, (78.0 + 89.75) / 2)):
            Box(P.ADP_X[0] - (P.LSI_X - P.LSI_WELL_HW),
                -91.0 - -96.45, 89.75 - 78.0, mode=Mode.SUBTRACT)
        # ── ПАЗ КОВПАКА-БАЛКИ (17.07 «повний розріз», підтверджено):
        # брова у прольоті РОЗРІЗАНА НАСКРІЗЬ по глибині (y−96.4..−91.0,
        # x92..133.4 = до розрізу), відкрито згори; лишається лише
        # плита-ободок t3 спереду. Балка кліпа на повну глибину брови
        # відновлює хорду П-рами. Мостоопори в3 ВИДАЛЕНІ — брови над
        # пазом більше нема, мостити нічого (друк лицем вниз чистий) ──
        with Locations(((P.ADP_X[0] + P.ADP_X[1]) / 2,
                        (-96.4 + -91.0) / 2, (81.5 + 89.75) / 2)):
            Box(P.ADP_X[1] - P.ADP_X[0], -91.0 - -96.4,
                89.75 - 81.5, mode=Mode.SUBTRACT)
        # ── НАДРІЗ під ЗУБ балки у ПРАВІЙ брові (Y-стоп вдавлення:
        # наскрізний паз задньої стінки не має — зуб t1.4 за розрізом
        # тисне в задню стінку надрізу −94.8, товща 3.4 підперта вежею;
        # права межа різу 135.2 — у зоні вежі (x≥134.9), у збірці вежа
        # стає правою стінкою. Друк: блок стінки над надрізом — консоль
        # 1.5мм першого шару (якорі x134.9 і z81.5) — друкована ──
        with Locations(((P.ADP_X[1] + 135.2) / 2,
                        (-96.4 + -96.4 + P.CAP_SLOT_D) / 2,
                        (81.5 + 89.75) / 2)):
            Box(135.2 - P.ADP_X[1], P.CAP_SLOT_D,
                89.75 - 81.5, mode=Mode.SUBTRACT)
        # кишеня барба у ЛІВІЙ X-стінці колодязя (ретенція ковпака =
        # лівий барб + crush-ребро зуба в стінку надрізу; стінки кишені
        # ±0.2 по Y — вторинний Y-стоп тіла)
        with Locations((P.LSI_X - (P.LSI_WELL_HW + 0.25),
                        (-95.6 + -93.2) / 2, 86.95)):
            Box(0.5, -93.2 - -95.6, 2.1, mode=Mode.SUBTRACT)

        # ── half-lap ЛАМЕЛІ по боках розрізу (15.07, ДОДАЮТЬСЯ
        # ОСТАННІМИ — щоб зрізи брови/каналів їх не чіпали): панель
        # лишає ПЕРЕДНІ полиці у проліт (лице y−99.4, t=LAP_T) до низу
        # ободка (+0.3 жирного union у нього); аддон лягає ззаду своєю
        # ламеллю — тяга вперед → упор, лицьова щілина закрита ──
        for x0, x1 in ((ax0 - 0.3, ax0 + P.ADP_LAP_D),
                       (ax1 - P.ADP_LAP_D, ax1 + 0.3)):
            with Locations(((x0 + x1) / 2, -99.4 + P.ADP_LAP_T / 2,
                            (P.ADP_RIM_Z0 + 0.3) / 2)):
                Box(x1 - x0, P.ADP_LAP_T, P.ADP_RIM_Z0 + 0.3)

    return fp.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "front")
