"""
walls.py — параметричні БІЧНІ СТІНКИ + БОРТИКИ (етап 2, v4 — 2026-07-03):
  • плити 3мм: outer X=WALL_L_X / WALL_R_X; задня грань Y=84.5
  • силует (YZ): фронт-вертикаль → ОПУКЛЕ плече R5 («в інший бік») → нахил →
    R5-кут → задня вертикаль до Z10 → увігнута галтель R2 → верх заднього
    бортика (Z8, дотично) → низ
  • (історія) рамка-бортик BEAD_W=5 видалена 09.07 («нафіг його»);
    плінтус-смуги 5×5 видалені 10.07 (фідбек 133.10/-19.90 та -78.35/55.30)
  • ЗАДНІЙ БОРТИК: 5×5 по задній поверхні дна (Z3..8), R5-кути плану,
    верхні ребра R2 (standalone-філет ДО union)
  • гребінь бортика стінки R2 (post-union філет, try/except — OCC-ризик)
  • виріз під кулер — ліва стінка
Запуск: .venv/bin/python cad/walls.py
"""
import math
from build123d import *
import shapely.geometry as sg
import params as P
import lattice
from exporter import save


def _slope():
    y1, z1 = P.TOP_EDGE_FRONT
    y2, z2 = P.TOP_EDGE_REAR
    k = (z2 - z1) / (y2 - y1)
    c0 = z1 - k * y1
    n = math.hypot(k, 1.0)
    return k, c0, n


def shoulder_geometry():
    """13.07: «ВЕЖА» рами замість плеча R8 біля панелі — фронт стінки
    йде на ПОВНУ висоту панелі (PANEL_H) перші BROW_D мм по Y: панель +
    брова + вежі обох стінок = замкнена РАМА під важкі плати (Deep
    mini-ITX 208, задача користувача «з'єднаємо брову і бічні стінки»).
    Тил вежі = тил брови (EAR_FLANGE_Y+BROW_D=−91.4) — площини
    продовжуються; брова пірнає у вежі на 0.9 по X → об'ємний union у
    збірці (не дотичний!). Вниз від тилу вежі — ков R=WALL_SWOOP_R
    (внутрішній кут → впадина, правило v2) дотично в нахил кромки.
    (Історія: «плече R8» 03-13.07 — дотик на yf=-96.9 давав верх лише
    Z78.25, брова висіла в повітрі за 1.5мм НАД стінкою.)"""
    k, c0, n = _slope()
    R = P.WALL_SWOOP_R
    yr = P.EAR_FLANGE_Y + P.BROW_D       # тил вежі/брови (−91.4)
    cy = yr + R
    cz = k * cy + c0 + R * n             # центр ВИЩЕ прямої нахилу
    t_vert = (yr, cz)                    # дотик на ТИЛІ вежі (вертикаль)
    t_slope = (cy + R * k / n, cz - R / n)   # дотик на нахилі
    return t_vert, t_slope, (cy, cz)


def corner_geometry():
    """R5-кут профілю нахил↔задня вертикаль (Y=WALL_REAR_Y)."""
    k, c0, n = _slope()
    R = P.WALL_EDGE_CORNER_R
    cy = P.WALL_REAR_Y - R
    cz = k * cy + c0 - R * n
    t_slope = (cy - R * k / n, cz + R / n)
    t_vert = (P.WALL_REAR_Y, cz)
    return t_slope, t_vert, (cy, cz)


def _arc_pts(c, r, p0, p1, qs=24, prefer_short=True):
    """Точки дуги кола (центр c) від p0 до p1 (коротша гілка)."""
    a0 = math.atan2(p0[1] - c[1], p0[0] - c[0])
    a1 = math.atan2(p1[1] - c[1], p1[0] - c[0])
    da = a1 - a0
    while da > math.pi:
        da -= 2 * math.pi
    while da < -math.pi:
        da += 2 * math.pi
    return [(c[0] + r * math.cos(a0 + da * i / qs),
             c[1] + r * math.sin(a0 + da * i / qs)) for i in range(qs + 1)]


def _silhouette_shapely():
    """Силует стінки (Y,Z), дуги дискретизовані."""
    tv, ts, cc = shoulder_geometry()
    ts2, tv2, cc2 = corner_geometry()
    yf = P.BODY_FRONT_Y - 0.5
    yr = P.EAR_FLANGE_Y + P.BROW_D        # тил вежі (−91.4)
    zt = P.RIDGE_TOP_Z                    # 8.0
    rc = P.REAR_COVE_R                    # 2.0
    # 13.07 «вежа»: фронт на повну PANEL_H → горизонталь до тилу брови →
    # вертикаль вниз до дотику кова (tv) → ков у нахил.
    # 17.07 ч.3: задній верхній кут вежі скруглено R=BROW_R — рол вежі
    # = рол брови (той самий циліндр по X, центр (−92.4, 87.75)); був
    # гострий кант → кліф 0.66 на стику з роллом брови (135.7/-91.45)
    rB = P.BROW_R
    cT = (yr - rB, P.PANEL_H - rB)
    pts = [(yf, 0), (yf, P.PANEL_H), (yr - rB, P.PANEL_H)]
    pts += _arc_pts(cT, rB, (yr - rB, P.PANEL_H), (yr, P.PANEL_H - rB))
    pts.append(tv)
    pts += _arc_pts(cc, P.WALL_SWOOP_R, tv, ts)
    pts.append(ts2)
    pts += _arc_pts(cc2, P.WALL_EDGE_CORNER_R, ts2, tv2)
    pts.append((P.WALL_REAR_Y, zt + rc))
    # 04.07 v4: ков R4 (REAR_COVE_R) — філет R2 по ньому НЕ вироджується
    # (на відміну від R2-кова), тож ланцюг гребеня їде через увесь кут
    pts += _arc_pts((P.WALL_REAR_Y + rc, zt + rc), rc,
                    (P.WALL_REAR_Y, zt + rc), (P.WALL_REAR_Y + rc, zt))
    # 04.07: БЕЗ клаптя — тор кутового револьва бортика в дотичній
    # площині Y86.5 збігається з прямим філетом смуги ТОЧНО, а клапоть
    # 0.5 за дотичною давав клин-обрив (137.7/87/7.8). T-стик дотичної
    # у STL лікує _heal-конвеєр експортера.
    pts += [(P.WALL_REAR_Y + rc, 0)]
    return sg.Polygon(pts).buffer(0)


def _arc_side(p0, p1, cc, R):
    """Знак радіуса RadiusArc: серединою еталонної (коротшої) дуги.
    05.07: перебір комбінацій за площею ЗРАДИВ — ков і перекат ділили
    один знак, правильної комбінації не існувало, і «найближча площа»
    перевернула кут профілю в увігнутий (фідбек ×2!)."""
    a0 = math.atan2(p0[1] - cc[1], p0[0] - cc[0])
    a1 = math.atan2(p1[1] - cc[1], p1[0] - cc[0])
    da = a1 - a0
    while da > math.pi:
        da -= 2 * math.pi
    while da < -math.pi:
        da += 2 * math.pi
    am = a0 + da / 2
    M = (cc[0] + R * math.cos(am), cc[1] + R * math.sin(am))
    for s in (R, -R):
        try:
            with BuildLine() as t:
                RadiusArc(p0, p1, s)
            mid = t.line @ 0.5
            if (mid.X - M[0]) ** 2 + (mid.Y - M[1]) ** 2 < 0.05:
                return s
        except Exception:
            continue
    return R


def _profile_sketch():
    """Точний профіль стінки: знак КОЖНОЇ дуги — детерміновано."""
    tv, ts, cc1 = shoulder_geometry()
    ts2, tv2, cc2 = corner_geometry()
    yf = P.BODY_FRONT_Y - 0.5
    yr = P.EAR_FLANGE_Y + P.BROW_D        # тил вежі (−91.4)
    zt = P.RIDGE_TOP_Z
    rc = P.REAR_COVE_R
    ccv = (P.WALL_REAR_Y + rc, zt + rc)
    cpr = (P.WALL_REAR_Y + rc, zt - P.CREST_R)
    pA = (P.WALL_REAR_Y, zt + rc)
    pB = (P.WALL_REAR_Y + rc, zt)
    pC = (P.WALL_REAR_Y + rc + P.CREST_R, zt - P.CREST_R)
    # 17.07 ч.3: рол кута вежі R=BROW_R (був гострий, «кульку ставить
    # OCC» — але брова скруглена R1.0, кулька R1.2 давала кліф 0.66 на
    # стику; тепер рол вежі = рол брови, той самий циліндр по X)
    rB = P.BROW_R
    cT = (yr - rB, P.PANEL_H - rB)
    pT1 = (yr - rB, P.PANEL_H)
    pT2 = (yr, P.PANEL_H - rB)
    s1 = _arc_side(tv, ts, cc1, P.WALL_SWOOP_R)
    s2 = _arc_side(ts2, tv2, cc2, P.WALL_EDGE_CORNER_R)
    s3 = _arc_side(pA, pB, ccv, rc)
    s4 = _arc_side(pB, pC, cpr, P.CREST_R)
    sT = _arc_side(pT1, pT2, cT, rB)
    with BuildSketch() as sk:
        with BuildLine():
            Polyline((yf, 0), (yf, P.PANEL_H), pT1)
            RadiusArc(pT1, pT2, sT)
            Line(pT2, tv)
            RadiusArc(tv, ts, s1)
            Line(ts, ts2)
            RadiusArc(ts2, tv2, s2)
            Line(tv2, pA)
            RadiusArc(pA, pB, s3)
            RadiusArc(pB, pC, s4)
            Polyline(pC, (pC[0], 0), (yf, 0))
        make_face()
    return sk.sketch


def rear_ridge():
    """Задній бортик 5×5 (Z3..8), v2 05.07: ПЛАН-контур з R3-кутами
    (2D-філети вершин) + ОДИН ланцюг R2 по всій верхній петлі — кульки
    на переходах ставить сам OCC. Стара конструкція (профіль + чверть-
    револьви) неявно вимагала REAR_CORNER_R == BEAD_W: з R3 револьв
    вимахував на 2мм за стінку (bounds 139.9!)."""
    y0, y1 = P.REAR_Y - P.BEAD_W, P.REAR_Y
    with BuildPart() as rp:
        with BuildSketch(Plane.XY.offset(P.FRAME_T)) as pl:
            with BuildLine():
                # передня межа з проміжними вершинами: переднє верхнє
                # ребро ділиться на 3, щоб філет узяв лише середину
                Polyline((P.WALL_L_X, y0),
                         (P.WALL_L_X + P.BEAD_W, y0),
                         (P.WALL_R_X - P.BEAD_W, y0),
                         (P.WALL_R_X, y0),
                         (P.WALL_R_X, y1), (P.WALL_L_X, y1),
                         (P.WALL_L_X, y0))
            make_face()
            fillet(pl.vertices().filter_by(lambda v: v.Y > y1 - 0.01),
                   radius=P.REAR_CORNER_R)
        extrude(amount=P.BEAD_H)
        # два ланцюги: біля кутів верх звужується до 2мм (дуга R3 ↔
        # переднє ребро) — два R2 там не вміщаються; переднє скруглення
        # в зоні кутів і не потрібне (там перекат смуги стінки), тож
        # воно тільки у відкритій середині, з вибігами в тілі смуг
        zt_r = P.RIDGE_TOP_Z
        # передній перекат R2 — ВИРІЗОМ (анти-філет призма): 3D-філет
        # на передньому ребрі неможливий (сегментація зливається на
        # extrude, повне ребро колізує з дугами біля кутів); вибіги
        # призми поховані в смугах стінок
        # 06.07 (п.1): кінці рівно на гранях смуг (133.73/86.73/8 —
        # сходинка від вибігу +0.5 під перекатом)
        # асиметрично: справа ролл до ПЛИТИ (134.9 — смуга там потоншена
        # вікном диска), зліва до грані смуги (-78.1 — смуга повна, різ
        # крізь неї валив fuse лівої стінки)
        with BuildSketch(Plane.YZ.offset(P.WALL_L_X + P.WALL_T)) as af:
            with BuildLine():
                Polyline((y0, zt_r - 2.0), (y0, zt_r),
                         (y0 + 2.0, zt_r))
                RadiusArc((y0 + 2.0, zt_r), (y0, zt_r - 2.0), -2.0)
            make_face()
        extrude(af.sketch,
                amount=(P.WALL_R_X - P.WALL_T)
                - (P.WALL_L_X + P.WALL_T), mode=Mode.SUBTRACT)
        rear = rp.edges().filter_by(
            lambda e: abs(e.center().Z - zt_r) < 1e-6
            and e.center().Y > P.REAR_Y - P.BEAD_W + 1.0
            and P.WALL_L_X + 0.5 < e.center().X < P.WALL_R_X - 0.5)
        fillet(rear, radius=2.0)
    return rp.part


def wall_part(x_outer, thickness_dir, keepouts=()):
    """Стінка v2 (09.07, «нафіг бортик»): ПЛИТА повного силуету +
    rhombille + БУЛЬНОС R1.45 верхнього ланцюга (обома ребрами, смужка
    0.1 — як на рейках блока). Рамки-бортика більше нема: перед зрізали,
    ззаду обходили вузлом, у SSD-зоні вирізали — користувач: «нафіг».
    Плінтус і задній бортик — окремо в build()."""
    prof = _profile_sketch()
    with BuildPart() as wp:
        extrude(Plane.YZ.offset(x_outer) * prof,
                amount=thickness_dir * P.WALL_T)
        # ізогрід-«ферма» (23.07, було rhombille): поле = силует − 2.5
        # краю (бульнос їсть 1.45) − плінтус-зона знизу (Z<6)
        S = _silhouette_shapely()
        field = S.buffer(-2.5).difference(
            sg.box(S.bounds[0] - 1, -1, S.bounds[2] + 1, 6.0))
        for ko in keepouts:
            field = field.difference(ko)
        holes = lattice.iso_holes(field, field.bounds[0],
                                  field.bounds[1])
        if holes:
            with BuildSketch(Plane.YZ.offset(x_outer - thickness_dir)) as hs:
                for g in holes:
                    g = g.simplify(0.01).buffer(0)
                    if g.geom_type != 'Polygon' or g.area < 1.0:
                        continue
                    with BuildLine():
                        Polyline(*list(g.exterior.coords)[:-1], close=True)
                    make_face()
            extrude(hs.sketch, amount=thickness_dir * (P.WALL_T + 2),
                    mode=Mode.SUBTRACT)
    solid = wp.part
    # ── бульнос верхнього краю: ребра на зовнішньому силуеті, вище
    # плінтуса, БЕЗ вертикалей торців (перед похований у панелі, зад
    # вливається в бортик) і поперечних X-ребер ──
    S = _silhouette_shapely()
    bnd = S.exterior

    def in_top(e):
        c = e.center()
        bb = e.bounding_box()
        if c.Z < 4.0:
            return False
        if bb.size.Y < 0.05 and bb.size.Z > 3.0 \
                and (c.Y < -95.0 or c.Y > 100.0):
            return False                      # вертикалі торців (13.07:
            # ЛИШЕ фронт у панелі та зад — тил вежі Y−91.4 МАЄ бути в
            # ланцюзі, інакше обрив = клин)
        if bb.size.X > 1.0:
            return False                      # поперечки на торцях
        return bnd.distance(sg.Point(c.Y, c.Z)) < 0.3

    es = solid.edges().filter_by(in_top)
    applied = False
    r_full = (P.WALL_T - 0.1) / 2      # обома ребрами + смужка 0.1 (=1.2 @2.5)
    for r in (r_full, r_full * 0.83, 0.8):
        try:
            solid = solid.fillet(r, list(es))
            if r != r_full:
                print(f"  (i) бульнос кромки: радіус → {r}")
            applied = True
            break
        except Exception:
            continue
    if not applied:
        okc = 0
        for e in es:
            for r in (r_full, 0.8):
                try:
                    solid = solid.fillet(r, [e])
                    okc += 1
                    break
                except Exception:
                    continue
        print(f"  (i) бульнос кромки: пореброво {okc}/{len(es)}")
    return solid


def build():
    # keepout-и решітки: виріз кулера (ліва), ніша вентилятора + місток (права)
    # обідок кулера 2.0 — «такої ж ширини, як під модулі пам'яті»
    # (RAM_WIN_RIM=2.0; фідбек 08.07 — 3.0 виглядав товстим на s8)
    ko_cooler = sg.box(P.COOLER_CUT_Y[0], P.COOLER_CUT_Z[0],
                       P.COOLER_CUT_Y[1], P.COOLER_CUT_Z[1]).buffer(2.0)
    # (09.07: ko_fan ПРИБРАНО — ніші вентилятора в стінці більше нема,
    # вентилятор цілком усередині; ромбілі течуть по всій правій стінці)
    # 13.07: зона ВЕЖІ (вежа + ков R8) — суцільна, це каркас рами
    ko_tower = sg.box(-98.0, 66.0, -84.0, 90.0)
    left = wall_part(P.WALL_L_X, +1, keepouts=(ko_cooler, ko_tower))
    right = wall_part(P.WALL_R_X, -1, keepouts=(ko_tower,))

    cy0, cy1 = P.COOLER_CUT_Y
    cz0, cz1 = P.COOLER_CUT_Z
    with BuildPart() as cut:
        with BuildSketch(Plane.YZ.offset(P.WALL_L_X - 1)):
            with Locations(((cy0 + cy1) / 2, (cz0 + cz1) / 2)):
                RectangleRounded(cy1 - cy0, cz1 - cz0, radius=P.COOLER_CUT_R)
        extrude(amount=P.WALL_T + 2)
    left = (left - cut.part).fix()   # .fix() після вирізу: інакше fuse

    # ── жертовна МЕМБРАНА вирізу кулера (24.07, ідея користувача:
    # «заповнити отвір — жорсткість збережеться»): у FACE_DOWN стінка =
    # вертикальне лезо, виріз 85×15 розрізав його на 2 вільні стрічки →
    # розхитування і падіння якості (друк №3). Мембрана MEM_T у ЦЕНТРІ
    # товщі з'єднує береги на кожному шарі; перфорація по периметру —
    # після друку викушується. Містки анкеряться в суцільний обідок 2.0.
    mem2 = lattice.membrane2d(cy0, cz0, cy1, cz1, P.COOLER_CUT_R)
    with BuildPart() as memc:
        with BuildSketch(Plane.YZ.offset(
                P.WALL_L_X + P.WALL_T / 2 - P.MEM_T / 2)) as ms:
            for g in lattice._polys(mem2):
                with BuildLine():
                    Polyline(*g.exterior.coords)
                make_face()
        extrude(ms.sketch, amount=P.MEM_T)
    left = (left + memc.part).fix()
    if P.PRINT_RIBS:
        # жертовні перемички вирізу кулера: міст 85мм → 3 прольоти по ~28
        with BuildPart() as ribs:
            y0k, y1k = P.COOLER_CUT_Y
            for k in (0.25, 0.5, 0.75):
                with Locations((P.WALL_L_X + P.WALL_T / 2,
                                y0k + k * (y1k - y0k),
                                (P.COOLER_CUT_Z[0] + P.COOLER_CUT_Z[1]) / 2)):
                    Box(P.WALL_T, P.PRINT_RIB_W,
                        P.COOLER_CUT_Z[1] - P.COOLER_CUT_Z[0] + 1)
        left = left + ribs.part
                                     # мовчки викидає «крихкий» солід

    # (09.07: проріз під вентилятор ВИДАЛЕНИЙ — 40мм Noctua цілком
    # усередині; 14.07: гриль з панелі переїхав у ЗМІННУ фронт-вставку
    # 15.07: вставка → повнорозмірний аддон front_addon.py —
    # вентилятор гвинтиться до нього, не до корпусу)
    # (09.07: вікно під диск A ВИДАЛЕНЕ разом зі смугою бортика — воно
    # різало її виступ до X132.9; гола плита 134.9 дає диску 0.6 зазору)
    # (08.07 друк №2: дуга кромки вікна ВИДАЛЕНА разом із плінтусом у
    # зоні SSD — вікно тепер до дна, кромки не існує)
    # (06.07: ков уздовж дна вікна ДОДАВАВСЯ і ПРИБРАНИЙ — читався як
    # «незрозуміле підвищення рами» + давав клин біля заднього кута)

    # ⚠️ впадину у стику рейл↔бортик НЕ робити post-fuse філетом —
    # SEGFAULT (клапоть копланарний бортику, патерн «брови»). TODO:
    # окреме бленд-тіло (свіп-ков уздовж стику) наступною ітерацією.
    total = left + right

    # (10.07: ПЛІНТУС-смуги 5×5 ВИДАЛЕНІ ЗОВСІМ — фідбек координатами
    # 133.10/-19.90/4.53 (правий частковий) і -78.35/55.30/4.65 (лівий
    # повний); стінки внизу = гола плита 3мм, суцільна до Z6 під полем
    # ромбілів. Кишеня плінтуса в SSD-блоці видалена ще 08.07.)

    total = total + rear_ridge()
    # (09.07: чверть-оберт кута смуга×бортик ВИДАЛЕНИЙ — смуги нема;
    # бортик тепер стикується просто з плитами)

    # ── трамплін-підпора під задній бортик (08.07: для друку лицем
    # вниз бортик = консоль 5мм на останніх шарах; «не прямий клин, а
    # закруглений за правилами трамплінів») — увігнута дуга від дна
    # (Z2) до верхівки ролла бортика (y0r+2, Z8), кінцевий нахил ~45°;
    # хвіст втоплений 1мм у тіло бортика, торці 0.4 у смуги стінок
    # 08.07: старт із Z3 (рівень рами/ізогрідів — «в областях ізогрідів
    # можна з 3мм», і задній кінець спирається на задню раму)
    Lr, Hr = 12.0, 5.0
    Rr = (Lr * Lr + Hr * Hr) / (2 * Hr)
    ys_ = P.REAR_Y - P.BEAD_W + 2.0 - Lr          # старт дуги (98.5)
    # 24.07 (друк №3: «три нитки висіли» — кінцевий нахил дуги 45.2° на
    # межі правила 45°): дуга лише до d=Dr (y=107.8, z=5.789 — ОПОРА
    # БЛОКА 1:1: низ бази Z6 на y≤107.8 не рухається), далі ПРЯМА-січна
    # до тої самої верхівки (110.5, 8.0) — нахил 39.3° замість 45.2°.
    Dr = 9.3
    arcp = [(ys_ + d, 3.0 + Rr - math.sqrt(Rr * Rr - d * d))
            for d in [Dr * k / 8 for k in range(9)]]
    arcp.append((ys_ + Lr, 8.0))
    with BuildPart() as rmp:
        with BuildSketch(Plane.YZ.offset(P.WALL_L_X + P.WALL_T - 0.4)) as rs:
            with BuildLine():
                # низ 2.0: над сотами (ребра 2мм) трамплін спирається на
                # них, на рамі/ізогріді (3) втоплюється (фідбек 08.07)
                Polyline(*arcp,
                         (P.REAR_Y - P.BEAD_W + 3.0, 8.0),
                         (P.REAR_Y - P.BEAD_W + 3.0, 2.0),
                         (ys_, 2.0), (ys_, 3.0))
            make_face()
        # правий кінець 132.7 — ПЕРЕД чверть-тором кута (дотик тора з
        # верхом рампи давав 10 нон-маніфолд ребер); консоль бортика
        # 132.7..134.9 (2.2мм) друкується і так
        # правий кінець до плити (0.4 втоплення): чверть-тора кута
        # більше нема — обмеження знято (09.07)
        extrude(rs.sketch, amount=(P.WALL_R_IN + 0.4)
                - (P.WALL_L_X + P.WALL_T - 0.4))
    total = (total + rmp.part).fix()

    # (20.07: ПАЗ у задній грані бортика ВИДАЛЕНИЙ разом із Г-гачком —
    # аддони тепер тримають snap-fit зачепи в слотах дна; бортик
    # суцільний по всій довжині)

    # ── ЗНИЖЕННЯ бортика в зоні плати (13.07): RIDGE_TOP_Z=8.0 >
    # BOARD_Z=7.55 — довга плата (Deep mini-ITX 208) лягала б на бортик,
    # не на постаменти. Прогін зрізається до RIDGE_BOARD_Z=7.3; 20.07:
    # паза/гачків більше нема — зниження їде до RIDGE_LOW_X1=131.5,
    # правіше (кутовий револьв) і стики зі стінками лишаються Z8.
    # Різати ПІСЛЯ трампліна — його хвіст сягає Z8 усередині бортика і
    # теж підрізається. Нові кромки — R1.5.
    x0c = P.WALL_L_X + P.WALL_T
    x1c = P.RIDGE_LOW_X1
    with BuildPart() as lowr:
        with Locations(((x0c + x1c) / 2, (105.0 + P.REAR_Y + 1) / 2,
                        (P.RIDGE_BOARD_Z + 9.5) / 2)):
            Box(x1c - x0c, P.REAR_Y + 1 - 105.0,
                9.5 - P.RIDGE_BOARD_Z)
    total = (total - lowr.part).fix()
    es_l = total.edges().filter_by(
        lambda e: abs(e.center().Z - P.RIDGE_BOARD_Z) < 0.05
        and x0c + 0.5 < e.center().X < x1c - 0.5
        and e.bounding_box().size.X > 5)
    for r in (1.5, 1.0, 0.6):
        try:
            total = total.fillet(r, list(es_l))
            if r != 1.5:
                print(f"  (i) кромки зниженого бортика: радіус → {r}")
            break
        except Exception:
            continue

    return total


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "walls")
