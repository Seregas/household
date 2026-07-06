"""
walls.py — параметричні БІЧНІ СТІНКИ + БОРТИКИ (етап 2, v4 — 2026-07-03):
  • плити 3мм: outer X=WALL_L_X / WALL_R_X; задня грань Y=84.5
  • силует (YZ): фронт-вертикаль → ОПУКЛЕ плече R5 («в інший бік») → нахил →
    R5-кут → задня вертикаль до Z10 → увігнута галтель R2 → верх заднього
    бортика (Z8, дотично) → низ
  • БОРТИК СТІНКИ: замкнена рамка BEAD_W=5 по всьому периметру силуету
    (перед, кромка, зад, НИЗ-плінтус), виліт BEAD_W по X усередину
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
    """УВІГНУТЕ плече R5 (2026-07-03 ФІНАЛ v3, правило v2: стик кромки з
    панеллю = внутрішній кут → впадина). «Горб» першої ітерації був не від
    силуету, а від пофрагментного філета гребеня (шви) — вилікувано one-shot."""
    k, c0, n = _slope()
    R = P.WALL_SWOOP_R
    # дотик на ЗАГЛИБЛЕНІЙ грані (yf=-96.9, клапоть у панелі): раніше
    # дотик на -96.4 давав сходинку 0.5 у силуеті — ланцюг філета гребеня
    # обривався на ній, лишаючи клин недоведеного скруглення біля панелі
    # (фідбек 2026-07-03: -82.01/-96.2/76.33 і симетрично)
    yf = P.BODY_FRONT_Y - 0.5
    cy = yf + R
    cz = k * cy + c0 + R * n             # центр ВИЩЕ прямої нахилу
    t_vert = (yf, cz)                    # дотик на вертикалі (z_start)
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
    zt = P.RIDGE_TOP_Z                    # 8.0
    rc = P.REAR_COVE_R                    # 2.0
    pts = [(yf, 0), tv]                   # дотик тепер на самій yf — без сходинки
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
    zt = P.RIDGE_TOP_Z
    rc = P.REAR_COVE_R
    ccv = (P.WALL_REAR_Y + rc, zt + rc)
    cpr = (P.WALL_REAR_Y + rc, zt - P.CREST_R)
    pA = (P.WALL_REAR_Y, zt + rc)
    pB = (P.WALL_REAR_Y + rc, zt)
    pC = (P.WALL_REAR_Y + rc + P.CREST_R, zt - P.CREST_R)
    s1 = _arc_side(tv, ts, cc1, P.WALL_SWOOP_R)
    s2 = _arc_side(ts2, tv2, cc2, P.WALL_EDGE_CORNER_R)
    s3 = _arc_side(pA, pB, ccv, rc)
    s4 = _arc_side(pB, pC, cpr, P.CREST_R)
    with BuildSketch() as sk:
        with BuildLine():
            Polyline((yf, 0), tv)
            RadiusArc(tv, ts, s1)
            Line(ts, ts2)
            RadiusArc(ts2, tv2, s2)
            Line(tv2, pA)
            RadiusArc(pA, pB, s3)
            RadiusArc(pB, pC, s4)
            Polyline(pC, (pC[0], 0), (yf, 0))
        make_face()
    return sk.sketch


def _bead_band(x_outer, thickness_dir, prof):
    """Бортик стінки: замкнена рамка BEAD_W по периметру силуету.
    Кільце — ТОЧНИМИ дугами (2D offset скетча, не полілінія), гребінь
    верхньої кромки скруглюється R2 standalone ДО union («псевдо-свіп»:
    справжній sweep тут самоперетинається — радіуси шляху < глибини профілю)."""
    with BuildSketch() as ring:
        add(prof)
        offset(amount=-P.BEAD_W, mode=Mode.SUBTRACT)
        # 04.07: діру кільця ззаду ЗАСИПАЄМО від Y78 — внутрішній кут
        # офсету біля закінчення був клубком дуг (шпильки/провали на
        # внутрішній грані, фідбек: 132.92/83.39/7.8)
        # 05.07: засипка ЛИШЕ плінтус-висотою (Z0..7) — повна давала
        # «прямокутник» на внутрішній грані (фідбек: 132.9/78.76/7.29,
        # «має бути продовження нижнього бортика»); зона вузла — повна
        with Locations((82.5, 3.5)):
            Rectangle(9.0, 7.0)
        with Locations((85.2, 15)):
            Rectangle(7.4, 30.0)
        add(prof, mode=Mode.INTERSECT)
    with BuildPart() as bp:
        extrude(Plane.YZ.offset(x_outer) * ring.sketch,
                amount=thickness_dir * P.BEAD_W)
    solid = bp.part
    # гребінь R2: лише ребра ВЕРХНЬОЇ кромки (плече→нахил→R5-кут);
    # передні (примикання до панелі) і задній рейл/плінтус — не чіпаємо
    S = _silhouette_shapely()
    bnd = S.exterior
    # 2026-07-03: ПОСЛІДОВНІ філети (усі разом одним викликом OCC валить,
    # хоч кожен сегмент окремо проходить — класика). Ков R1 (R1.5+ не дається
    # через кривину R2-кова); якщо не пройде — лишається гострим (у ніші).
    # 04.07: вікно ланцюга РОЗШИРЕНЕ до кінців силуету (yf..клапоть Y87) —
    # обрізане [-96.2..86.55] лишало клинці-сходинки недоведеного філета
    # біля панелі (137.49/-96.2/74.74) та на бортику (137.7/87/7.8).
    # Торці філета поховані (0.5 у панель / у бортик) → вибіг невидимий.
    # Вертикальні ребра НА торцях (передня/задня грані рамки) НЕ чіпаємо —
    # їх заокруглення прорізало б жолоб у стику з панеллю/бортиком.
    yf_lo = P.BODY_FRONT_Y - 0.6
    y_hi = P.WALL_REAR_Y + P.REAR_COVE_R + P.CREST_R + 0.2

    def in_chain(e, zmin):
        c = e.center()
        if not (c.Z > zmin and yf_lo - 0.1 < c.Y < y_hi + 0.1):
            return False
        bb = e.bounding_box()
        # біля торців у ланцюзі лишаються ЛИШЕ поздовжні ребра силуету
        # (біжать у YZ, size.X≈0) — вертикальні торцеві та поперечні
        # (вздовж X: кут Y87/Z8, дотичне біля yf) валять філет цілком
        at_end = c.Y > y_hi - 0.7 or c.Y < yf_lo + 0.7
        if bb.size.Z > 6.0 and at_end:
            return False                     # торцеві вертикалі
        if bb.size.X > 1.0 and (c.Y > y_hi - 0.4 or c.Y < yf_lo + 0.7):
            return False                     # поперечка лише на торці зла
        return True

    stages = [
        # єдиний ланцюг: кромка+рейл (+ков, де R2 на R2-кові — no-op:
        # кулька сідає в жолоб; справжнє вливання рейла в кутовий револьв
        # бортика = окремий бленд-вузол «закінчення», TODO)
        ("кромка+рейл+ков", P.CREST_R, lambda e: in_chain(e, 8.1)),
        ("кромка+рейл (fallback)", P.CREST_R, lambda e: in_chain(e, 9.9)),
        # внутрішній контур кільця (п.1 фідбеку 2026-07-03: «скруглення мало
        # піти далі»); кути засипки діри на Y78 — виключені (валять ланцюг)
        ("внутрішній контур", P.CREST_R,
         lambda e: in_chain(e, -1.0)
         and not (77.4 < e.center().Y < 78.6)
         and e.center().Y < 82.0, True),
        # внутрішні ребра ВУЗЛА (Y>82) свідомо гострі: і ланцюгом, і
        # ребро-за-ребром OCC лишає вибіги-щілини (116 Т-дефектів);
        # друк 0.2мм згладить (05.07)
    ]
    Sin = S.buffer(-P.BEAD_W)
    bnd_in = Sin.exterior if Sin.geom_type == 'Polygon' else None
    done_main = False
    for name, rad, cond, *inner in stages:
        if "fallback" in name and done_main:
            continue
        ref = bnd_in if inner else bnd
        if ref is None:
            continue
        es = solid.edges().filter_by(
            lambda e, cond=cond, ref=ref: cond(e)
            and ref.distance(sg.Point(e.center().Y, e.center().Z)) < 0.3)
        if not es:
            continue
        # сходинки радіуса: краще менший ков, ніж гостре ребро
        applied = False
        for r in (rad, rad * 0.6, rad * 0.35):
            try:
                solid = solid.fillet(r, list(es))
                if r != rad:
                    print(f"  (i) fillet «{name}»: радіус {rad} → {r:.2f}")
                applied = True
                break
            except Exception:
                continue
        if not applied:
            # 05.07: ребро за ребром — одне вироджене ребро не має
            # лишати ГОЛИМ увесь контур (п.2/п.3 фідбеку)
            okc = 0
            for e in es:
                for r in (rad, rad * 0.5):
                    try:
                        solid = solid.fillet(r, [e])
                        okc += 1
                        break
                    except Exception:
                        continue
            print(f"  (i) fillet «{name}»: пореброво {okc}/{len(es)}")
            applied = okc > 0
        if applied and name.startswith("кромка"):
            done_main = True

    return solid


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
        with BuildSketch(Plane.YZ.offset(P.WALL_L_X + P.BEAD_W)) as af:
            with BuildLine():
                Polyline((y0, zt_r - 2.0), (y0, zt_r),
                         (y0 + 2.0, zt_r))
                RadiusArc((y0 + 2.0, zt_r), (y0, zt_r - 2.0), -2.0)
            make_face()
        extrude(af.sketch,
                amount=(P.WALL_R_X - P.WALL_T)
                - (P.WALL_L_X + P.BEAD_W), mode=Mode.SUBTRACT)
        rear = rp.edges().filter_by(
            lambda e: abs(e.center().Z - zt_r) < 1e-6
            and e.center().Y > P.REAR_Y - P.BEAD_W + 1.0
            and P.WALL_L_X + 0.5 < e.center().X < P.WALL_R_X - 0.5)
        fillet(rear, radius=2.0)
    return rp.part


def wall_part(x_outer, thickness_dir, keepouts=()):
    """Стінка = плита (ТОЧНІ дуги: силует − трим під гребенем) + бортик
    (точні дуги) − rhombille (окремою SUBTRACT-екструзією; слаб на shapely
    давав T-стики з бортиком біля задньої галтелі → діри в STL).
    keepouts — shapely-зони без решітки."""
    prof = _profile_sketch()
    with BuildSketch() as ring_t:
        add(prof)
        offset(amount=-(P.CREST_R + 0.2), mode=Mode.SUBTRACT)
    with BuildSketch() as trim:
        add(ring_t.sketch)
        # трим до ЗА задню межу (+0.5): відступ -0.2 лишав шпильку-залишок
        # плити 0.2мм біля Y84.5 → щілина з філетованим бортиком (коорд.
        # користувача 137.53/84.41/26.58); спереду відступ лишається
        # 04.07: трим ДО фронту (-97.5, за поховану грань) — передня
        # смужка плити 0.7 на повну висоту стирчала крізь філет бортика
        # («полиця» Y-96.2, фідбек: 137.49/-96.2/74.74 і дзеркально)
        # ...і ДО ЗА задній кінець силуету (88): хвіст плити Y85..86.5
        # на повну висоту накривав гребінь лофта-«закінчення» (04.07)
        # 05.07: трим від Z7 (було Z10) — повнопрофільна смуга плити
        # нижче триму давала плато Z10 у вузлі (п.4: 137.67/82.77/10);
        # і до Y88.7 — хвостик плити за перекатом (п.1)
        # Z від 5.5: межа на Z7 проходила крізь тіло перекату (6..8) —
        # Т-контакт по лінії перетину (116 щілин, 05.07)
        with Locations(((-97.5 + 88.7) / 2, 42.75)):
            Rectangle(88.7 + 97.5, 74.5,
                      mode=Mode.INTERSECT)
    with BuildSketch() as slab_sk:
        add(prof)
        add(trim.sketch, mode=Mode.SUBTRACT)
    with BuildPart() as wp:
        extrude(Plane.YZ.offset(x_outer) * slab_sk.sketch,
                amount=thickness_dir * P.WALL_T)
        # rhombille: поле = силует мінус смуга бортика (5) з запасом 1
        S = _silhouette_shapely()
        field = S.buffer(-(P.BEAD_W + 1.0))
        for ko in keepouts:
            field = field.difference(ko)
        holes = lattice.rhombille_holes(field, field.bounds[0],
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
    wall = wp.part + _bead_band(x_outer, thickness_dir, prof)
    # (05.07: зріз кута видалено — з REAR_CORNER_R=3 дуга кута
    # дотична до грані стінки в кінці перекату, різати нічого)
    return wall

def build():
    # keepout-и решітки: виріз кулера (ліва), ніша вентилятора + місток (права)
    ko_cooler = sg.box(P.COOLER_CUT_Y[0], P.COOLER_CUT_Z[0],
                       P.COOLER_CUT_Y[1], P.COOLER_CUT_Z[1]).buffer(3.0)
    ko_fan = sg.box(P.BODY_FRONT_Y - 1, P.FAN_CZ - P.FAN_W / 2 - 0.3,
                    P.BODY_FRONT_Y + P.FAN_D + P.FAN_NOTCH_CLR + P.FAN_BRIDGE_T,
                    P.FAN_CZ + P.FAN_W / 2 + 0.3).buffer(3.0)
    left = wall_part(P.WALL_L_X, +1, keepouts=(ko_cooler,))
    right = wall_part(P.WALL_R_X, -1, keepouts=(ko_fan,))

    cy0, cy1 = P.COOLER_CUT_Y
    cz0, cz1 = P.COOLER_CUT_Z
    with BuildPart() as cut:
        with BuildSketch(Plane.YZ.offset(P.WALL_L_X - 1)):
            with Locations(((cy0 + cy1) / 2, (cz0 + cz1) / 2)):
                RectangleRounded(cy1 - cy0, cz1 - cz0, radius=P.COOLER_CUT_R)
        extrude(amount=P.WALL_T + P.BEAD_W + 2)
    left = (left - cut.part).fix()   # .fix() після вирізу: інакше fuse
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

    # проріз під тіло 40-мм вентилятора у ПРАВІЙ стінці: рамка проходить
    # крізь плиту (права грань вентилятора врівень із зовнішньою площиною);
    # бортик/рубчик природно огинають проріз зверху і знизу
    clr = P.FAN_NOTCH_CLR
    with BuildPart() as fcut:
        with BuildSketch(Plane.YZ.offset(P.WALL_R_X - P.WALL_T - P.BEAD_W - 1)):
            with Locations((P.BODY_FRONT_Y + P.FAN_D / 2 - 1, P.FAN_CZ)):
                # ПРЯМИЙ прямокутник: бічний профіль вентилятора (10×40)
                # гострокутний — R2 у ніші не давав рамці сісти (фідбек);
                # передня межа на 2 вперед: інакше від рубчика лишалась
                # мембрана 0.25, що глушила гриль (04.07: 134.56/-96.7)
                Rectangle(P.FAN_D + 2 * clr + 2, P.FAN_W + 2 * clr)
        extrude(amount=P.WALL_T + P.BEAD_W + 3)
    right = (right - fcut.part).fix()
    # вікно під диск A (05.07): внутрішній виступ смуги бортика (до X132.9)
    # перетинав диск, притиснутий до стінки (зовн. грань диска 134.3) —
    # виріз до площини плити у прольоті дисків. Зовнішній гребінь кромки,
    # плінтус (Z<8, під диском) і задній вузол — не чіпаються.
    # 06.07 (п.5): вікно вниз до плінтуса (Z5.2) і назад до вузла
    # (Y82.2) — «зайва площина» 132.9/80.7/6.25 під/за старим вікном
    # 06.07 v2: вікно ДО БОРТИКА (Y86.4) — зупинка на 82.2 лишала
    # сходинку-фаску в зоні вузла (фідбек «не усунуто»); смуга вздовж
    # диска і так усюди потоншена до 3 — вузол тепер теж, а звільнені
    # 2мм підхоплює ролл бортика (анти-філет продовжено до плити)
    # 06.07 v3: і НАСКРІЗЬ через хвіст смуги (перекат Y86.5..88.5) —
    # він стирчав поверх ролла бортика «зайвим закругленням» зі щілиною
    # 0.1 (134.06/86.86/7.74); бортик додається ПІСЛЯ і не ріжеться
    with BuildPart() as dcut:
        with Locations((133.7, (-24.0 + 89.5) / 2, (5.2 + 70.0) / 2)):
            Box(2.4, 89.5 - (-24.0), 70.0 - 5.2)
    right = (right - dcut.part).fix()
    # (06.07: ков уздовж дна вікна ДОДАВАВСЯ і ПРИБРАНИЙ — читався як
    # «незрозуміле підвищення рами» + давав клин біля заднього кута)

    # МІСТОК за вентилятором (2026-07-03): відновлює неперервність стінки
    # через проріз і приймає праву пару гвинтів (M3×16 наскрізь:
    # панель 3 + вентилятор 10 + зазор 0.3 + місток 3)
    zb0, zb1 = P.FAN_CZ - P.FAN_W / 2 - clr, P.FAN_CZ + P.FAN_W / 2 + clr
    by0 = P.BODY_FRONT_Y + P.FAN_D + clr
    with BuildPart() as br:
        with Locations(((P.WALL_R_X + P.FAN_CX + P.FAN_SCREW_CC / 2 - 2) / 2,
                        by0 + P.FAN_BRIDGE_T / 2, (zb0 + zb1) / 2)):
            Box(P.WALL_R_X - (P.FAN_CX + P.FAN_SCREW_CC / 2 - 2),
                P.FAN_BRIDGE_T, zb1 - zb0)
        for sz in (-1, 1):
            with Locations(Location((P.FAN_CX + P.FAN_SCREW_CC / 2,
                                     by0 + P.FAN_BRIDGE_T + 1,
                                     P.FAN_CZ + sz * P.FAN_SCREW_CC / 2),
                                    (90, 0, 0))):
                Cylinder(P.FAN_SCREW_TAP_D / 2, P.FAN_BRIDGE_T + 2,
                         align=(Align.CENTER, Align.CENTER, Align.MIN),
                         mode=Mode.SUBTRACT)
    right = right + br.part
    # ⚠️ впадину у стику рейл↔бортик НЕ робити post-fuse філетом —
    # SEGFAULT (клапоть копланарний бортику, патерн «брови»). TODO:
    # окреме бленд-тіло (свіп-ков уздовж стику) наступною ітерацією.
    total = left + right

    return total + rear_ridge()


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "walls")
