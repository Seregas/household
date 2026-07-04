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
    # увігнута галтель R2 → дотично на верх бортика
    pts += _arc_pts((P.WALL_REAR_Y + rc, zt + rc), rc,
                    (P.WALL_REAR_Y, zt + rc), (P.WALL_REAR_Y + rc, zt))
    # 04.07: БЕЗ клаптя — тор кутового револьва бортика в дотичній
    # площині Y86.5 збігається з прямим філетом смуги ТОЧНО, а клапоть
    # 0.5 за дотичною давав клин-обрив (137.7/87/7.8). T-стик дотичної
    # у STL лікує _heal-конвеєр експортера.
    pts += [(P.WALL_REAR_Y + rc, 0)]
    return sg.Polygon(pts).buffer(0)


def _profile_sketch():
    """Точний профіль (build123d, справжні дуги) у ЛОКАЛЬНІЙ площині XY
    (x=Y, y=Z) — вся 2D-алгебра локальна, у світ лише при екструзії
    (add() позиційованого скетча в інший скетч подвійно трансформує).
    Бік кожної дуги перевіряється площею проти shapely-еталона."""
    tv, ts, _ = shoulder_geometry()
    ts2, tv2, _ = corner_geometry()
    yf = P.BODY_FRONT_Y - 0.5
    zt = P.RIDGE_TOP_Z
    rc = P.REAR_COVE_R
    ref = _silhouette_shapely().area
    cands = []
    for s1 in (1, -1):
        for s2 in (1, -1):
            for s3 in (1, -1):
                try:
                    with BuildSketch() as sk:
                        with BuildLine():
                            Polyline((yf, 0), tv)
                            RadiusArc(tv, ts, s1 * P.WALL_SWOOP_R)
                            Line(ts, ts2)
                            RadiusArc(ts2, tv2, s2 * P.WALL_EDGE_CORNER_R)
                            Line(tv2, (P.WALL_REAR_Y, zt + rc))
                            RadiusArc((P.WALL_REAR_Y, zt + rc),
                                      (P.WALL_REAR_Y + rc, zt), s3 * rc)
                            Polyline((P.WALL_REAR_Y + rc, zt),
                                     (P.WALL_REAR_Y + rc, 0), (yf, 0))
                        make_face()
                    cands.append(sk.sketch)
                except Exception:
                    continue
    return min(cands, key=lambda s: abs(s.area - ref))


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
        with Locations((82.5, 15)):
            Rectangle(9.0, 30.0)
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
    y_hi = P.WALL_REAR_Y + P.REAR_COVE_R + 0.2

    def in_chain(e, zmin):
        c = e.center()
        if not (c.Z > zmin and yf_lo - 0.1 < c.Y < y_hi + 0.1):
            return False
        bb = e.bounding_box()
        # біля торців у ланцюзі лишаються ЛИШЕ поздовжні ребра силуету
        # (біжать у YZ, size.X≈0) — вертикальні торцеві та поперечні
        # (вздовж X: кут Y87/Z8, дотичне біля yf) валять філет цілком
        at_end = c.Y > y_hi - 0.7 or c.Y < yf_lo + 0.7
        return not (at_end and (bb.size.Z > 6.0 or bb.size.X > 1.0))

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
         and not (77.4 < e.center().Y < 78.6), True),
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
        for r in (rad, rad * 0.6, rad * 0.35):
            try:
                solid = solid.fillet(r, list(es))
                if r != rad:
                    print(f"  (i) fillet «{name}»: радіус {rad} → {r:.2f}")
                if name.startswith("кромка"):
                    done_main = True
                break
            except Exception as ex:
                if r == rad * 0.35:
                    print(f"  (!) fillet «{name}» не вдався навіть R{r:.2f}:", ex)

    # ── «ЗАКІНЧЕННЯ» (04.07): сегмент Y[рейл..дотична] вирізаємо і
    # заміняємо ЛОФТОМ з R2-гребенем у КОЖНОМУ 2D-профілі: філет тут
    # неможливий (R2-кулька по R2-кову = no-op), гострий кут давав
    # сходинку проти кутового револьва бортика (фідбек: «муляє»).
    # На Y86.5 профіль лофта = профіль револьва → стик точний.
    y0h, y1h = P.WALL_REAR_Y, P.WALL_REAR_Y + P.REAR_COVE_R
    x_in = x_outer + thickness_dir * P.BEAD_W
    cx = (x_outer + x_in) / 2
    with BuildPart() as cv:
        # карв ЗА торець (+1): різ по копланарній із торцем грані Y86.5
        # робив шелл невалідним (04.07)
        with Locations((cx, (y0h + y1h + 1.0) / 2, 5.5)):
            Box(P.BEAD_W + 0.4, y1h - y0h + 1.0, 13.0)
    solid = (solid - cv.part).fix()
    cyc, czc = y1h, P.RIDGE_TOP_Z + P.REAR_COVE_R      # центр кова (86.5, 10)
    with BuildPart() as heel:
        # старт на 1мм ПЕРЕД карвом: об'ємне перекриття з тілом смуги
        # (бутт-стик OCC «склеює», наступні булеві розклеюють у 2 соліди);
        # поховані секції ВТОПЛЕНІ на 0.4 — копланарні з гранями смуги
        # бічні/нижня грані лофта робили fuse невалідним (04.07)
        for y, ins in ((y0h - 1.0, 0.4), (y0h - 0.4, 0.4), (y0h, 0.0),
                       (y0h + 0.4, 0.0), (y0h + 0.8, 0.0),
                       (y0h + 1.2, 0.0), (y0h + 1.6, 0.0),
                       (y0h + 1.85, 0.0), (y1h, 0.0)):
            zt = czc - math.sqrt(max(P.REAR_COVE_R ** 2 - (y - cyc) ** 2,
                                     0.0)) - ins
            xo = x_outer + thickness_dir * ins
            xi = x_in - thickness_dir * ins
            with BuildSketch(Plane.XZ.offset(-y)) as sec:
                with BuildLine():
                    Polyline((xi, ins), (xo, ins), (xo, zt),
                             (xi, zt), (xi, ins))
                make_face()
                vs = [v for v in sec.vertices()
                      if abs(v.X - xo) < 0.01 and abs(v.Y - zt) < 0.01]
                fillet(vs, radius=P.CREST_R)
            # (профілі накопичуються як pending faces)
        loft()
    solid = (solid + heel.part).fix()
    return solid




def rear_ridge():
    """Задній бортик 5×5 (Z3..8): пряма ділянка = екструзія профілю з R2
    на зовнішньо-верхній вершині (2D!), кути = чверть-РЕВОЛЬВИ того ж
    профілю навколо центрів планових R5-дуг, кінці — приховані коробки
    в тілі стінок. БЕЗ 3D-філетів (вони лишали вироджені грані → діри STL).
    Внутрішнє верхнє ребро гостре — на нього дотично сідає ков стінки."""
    zb, zt = P.FRAME_T, P.RIDGE_TOP_Z
    y0, y1 = P.REAR_Y - P.BEAD_W, P.REAR_Y          # 86.5 .. 91.5
    cxl = P.WALL_L_X + P.REAR_CORNER_R              # -78.1 (центр лівої дуги)
    cxr = P.WALL_R_X - P.REAR_CORNER_R              # 132.9 (центр правої)

    def prof_sk():
        with BuildSketch() as s:
            with Locations(((y0 + y1) / 2, (zb + zt) / 2)):
                Rectangle(P.BEAD_W, P.BEAD_H)
            fillet(s.vertices().filter_by(
                lambda v: v.X > y1 - 0.01 and v.Y > zt - 0.01), radius=2.0)
        return s.sketch

    with BuildPart() as rp:
        # пряма ділянка між центрами дуг
        extrude(Plane.YZ.offset(cxl) * prof_sk(), amount=cxr - cxl)
        # кутові чверть-револьви (бік обертання — перевіркою габаритів)
        for cx, outward in ((cxl, -1), (cxr, +1)):
            base = Plane.YZ.offset(cx) * prof_sk()
            ax = Axis((cx, y0, 0), (0, 0, 1))
            r1 = revolve(base, axis=ax, revolution_arc=90)
            bb = r1.bounding_box()
            grew_ok = (outward < 0 and bb.min.X < cx - 1) or \
                      (outward > 0 and bb.max.X > cx + 1)
            if not grew_ok:
                r1 = revolve(base, axis=ax, revolution_arc=-90)
        # приховані кінцеві коробки в тілі стінок
        for x0, x1 in ((P.WALL_L_X, cxl), (cxr, P.WALL_R_X)):
            with Locations(((x0 + x1) / 2, (P.WALL_REAR_Y - 1 + y0) / 2,
                            (zb + zt) / 2)):
                Box(x1 - x0, y0 - (P.WALL_REAR_Y - 1), P.BEAD_H)
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
        with Locations(((-97.5 + 88.0) / 2, 45)):
            Rectangle(88.0 + 97.5, 70,
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
    # хвіст плити в зоні «закінчення» зрізаємо: нижня смуга плити (Z<10,
    # трим-бокс навмисно її не чіпає) там повнопрофільна — її ков 8.27
    # накривав гребінь лофта (04.07, четвертий винуватець сходинки)
    x_in2 = x_outer + thickness_dir * P.BEAD_W
    y0h = P.WALL_REAR_Y
    with BuildPart() as pcv:
        with Locations(((x_outer + x_in2) / 2,
                        (2 * y0h + P.REAR_COVE_R + 1.0) / 2, 5.5)):
            Box(P.BEAD_W + 0.4, P.REAR_COVE_R + 1.0, 13.0)
    slab = (wp.part - pcv.part).fix()
    return slab + _bead_band(x_outer, thickness_dir, prof)

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
    # з бортика зрізаємо зони «закінчення» (Y84.5..86.5 при стінках):
    # його передня коробка (від Y83.5) з гострим верхом Z8 стирчала над
    # гребенем лофта (04.07, п'ятий і останній винуватець сходинки);
    # кутові револьви (Y>86.5) НЕ чіпаємо
    ridge = rear_ridge()
    with BuildPart() as rcv:
        for xo, td in ((P.WALL_R_X, -1), (P.WALL_L_X, +1)):
            xc = xo + td * P.BEAD_W / 2
            with Locations((xc, (P.WALL_REAR_Y + P.WALL_REAR_Y
                                 + P.REAR_COVE_R) / 2, 5.5)):
                Box(P.BEAD_W + 0.4, P.REAR_COVE_R, 12.0)
    ridge = (ridge - rcv.part).fix()
    return left + right + ridge


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "walls")
