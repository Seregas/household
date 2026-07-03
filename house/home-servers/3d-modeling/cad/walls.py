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
    cy = P.BODY_FRONT_Y + R
    cz = k * cy + c0 + R * n             # центр ВИЩЕ прямої нахилу
    t_vert = (P.BODY_FRONT_Y, cz)        # дотик на вертикалі (z_start)
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
    pts = [(yf, 0), (yf, tv[1]), tv]
    pts += _arc_pts(cc, P.WALL_SWOOP_R, tv, ts)
    pts.append(ts2)
    pts += _arc_pts(cc2, P.WALL_EDGE_CORNER_R, ts2, tv2)
    pts.append((P.WALL_REAR_Y, zt + rc))
    # увігнута галтель R2 → дотично на верх бортика
    pts += _arc_pts((P.WALL_REAR_Y + rc, zt + rc), rc,
                    (P.WALL_REAR_Y, zt + rc), (P.WALL_REAR_Y + rc, zt))
    # клапоть 0.5 ПОВЕРХ бортика за точкою дотику: без нього дотичні
    # поверхні (ков ↔ верх бортика) дають T-стики → діри в STL
    pts += [(P.WALL_REAR_Y + rc + 0.5, zt), (P.WALL_REAR_Y + rc + 0.5, 0)]
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
                            Polyline((yf, 0), (yf, tv[1]), tv)
                            RadiusArc(tv, ts, s1 * P.WALL_SWOOP_R)
                            Line(ts, ts2)
                            RadiusArc(ts2, tv2, s2 * P.WALL_EDGE_CORNER_R)
                            Line(tv2, (P.WALL_REAR_Y, zt + rc))
                            RadiusArc((P.WALL_REAR_Y, zt + rc),
                                      (P.WALL_REAR_Y + rc, zt), s3 * rc)
                            Polyline((P.WALL_REAR_Y + rc, zt),
                                     (P.WALL_REAR_Y + rc + 0.5, zt),
                                     (P.WALL_REAR_Y + rc + 0.5, 0), (yf, 0))
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
    stages = [
        # єдиний ланцюг ВКЛЮЧНО з ковом (точка 137.9/84.52/9.84 — нескруглений
        # низ рейла); якщо впаде — fallback нижче підхопить окремо
        ("кромка+рейл+ков", P.CREST_R,
         lambda c: c.Z > 8.1 and P.BODY_FRONT_Y + 0.2 < c.Y
         < P.WALL_REAR_Y + P.REAR_COVE_R + 0.05),
        ("кромка+рейл (fallback)", P.CREST_R,
         lambda c: c.Z > 9.9 and P.BODY_FRONT_Y + 0.2 < c.Y < P.WALL_REAR_Y + 0.1),
        # внутрішній контур кільця (п.1 фідбеку 2026-07-03: «скруглення мало
        # піти далі») — ребра вздовж внутрішньої межі бортика
        ("внутрішній контур", P.CREST_R,
         lambda c: c.Y > P.BODY_FRONT_Y + 0.2, True),
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
        try:
            es = solid.edges().filter_by(
                lambda e, cond=cond, ref=ref: cond(e.center())
                and ref.distance(sg.Point(e.center().Y, e.center().Z)) < 0.3)
            if es:
                solid = solid.fillet(rad, list(es))
                if name.startswith("кромка"):
                    done_main = True
        except Exception as ex:
            print(f"  (!) fillet «{name}» не вдався:", ex)
    return solid




def _cove_prism(origin, line_dir, nA, nB, length, R, e=0.3):
    """Стрічка-ков: чверть-заповнення внутрішнього кута вздовж прямої.
    origin — точка на лінії стику; nA/nB — одиничні напрямки ВЗДОВЖ граней
    від кута; line_dir — напрямок лінії; length — довжина."""
    import numpy as np
    nA = np.array(nA, float); nB = np.array(nB, float)
    d = np.array(line_dir, float); d /= np.linalg.norm(d)
    pl = Plane(origin=tuple(origin), x_dir=tuple(nA), z_dir=tuple(d))
    target = R * R * (1 - math.pi / 4)
    # весь профіль втоплено на e у кут: кінці дуги (дотичні до граней!)
    # ховаються всередину матеріалу, поверхня виходить трансверсально —
    # інакше дотична лінія (напр. Z7 на стінці) дає нон-маніфолдний STL.
    # e — глибина втоплення; сусіднім стрічкам давати РІЗНЕ e, інакше їхні
    # поховані кромки знову збігаються лінія-в-лінію (нон-маніфолд).
    for s in (R, -R):
        try:
            with BuildSketch(pl) as sk:
                with BuildLine():
                    Polyline((-e, -e), (R - e, -e))
                    RadiusArc((R - e, -e), (-e, R - e), s)
                    Line((-e, R - e), (-e, -e))
                make_face()
            if abs(sk.sketch.area - target) < 0.05:
                break
        except Exception:
            continue
    with BuildPart() as cp:
        extrude(sk.sketch, amount=length)
    return cp.part


def wall_coves(x_outer, tdir):
    """Кови R2 прямих примикань бортика (перша черга): плінтус (стінка↔верх,
    бік↔рама), рубчик (панель↔бік, стінка↔внутр. грань), рейл (стінка↔внутр.).
    Мітри в кутах — перетином сусідніх стрічок (union)."""
    R = P.COVE_R
    xin = x_outer + tdir * P.WALL_T          # внутрішня грань стінки
    xb = x_outer + tdir * P.BEAD_W           # внутрішня межа бортика
    zt_pl = P.BEAD_W                         # верх плінтуса (Z5)
    zfr = P.FRAME_T                          # верх рами (Z3)
    y_rib = P.BODY_FRONT_Y + P.BEAD_W        # внутр. грань рубчика (-91.4)
    y_rail = P.WALL_REAR_Y - P.BEAD_W        # внутр. межа рейла (79.5)
    parts = []
    # 1) плінтус-верх ↔ стінка (лінія вздовж Y на (xin, zt_pl))
    parts.append(_cove_prism((xin, y_rib - R, zt_pl), (0, 1, 0),
                             (tdir, 0, 0) and (0, 0, 1) or None, None, 0, R)
                 if False else
                 _cove_prism((xin, y_rib - R, zt_pl), (0, 1, 0),
                             (0, 0, 1), (tdir, 0, 0),
                             (y_rail + R) - (y_rib - R), R))
    # 2) плінтус-бік ↔ рама (лінія вздовж Y на (xb, zfr));
    # e=0.45 ≠ 0.3 — кромка стрічки 1 сідала точно на кромку 2 (BEAD_W-WALL_T=R)
    parts.append(_cove_prism((xb, y_rib - R, zfr), (0, 1, 0),
                             (0, 0, 1), (tdir, 0, 0),
                             (y_rail + R) - (y_rib - R), R, e=0.45))
    # 3) рубчик: бічна грань (xb) ↔ панель (лінія вздовж Z)
    parts.append(_cove_prism((xb, P.BODY_FRONT_Y, zfr), (0, 0, 1),
                             (0, 1, 0), (tdir, 0, 0), 60.0, R))
    # 4) рубчик: внутрішня грань (y_rib) ↔ стінка (вздовж Z)
    parts.append(_cove_prism((xin, y_rib, zt_pl - R), (0, 0, 1),
                             (0, 1, 0), (tdir, 0, 0), 58.0, R))
    # 5) рейл: внутрішня межа (y_rail) ↔ стінка (вздовж Z, до кромки);
    # старт утоплений на 0.6 у плінтус — дотична мітра давала діри STL
    parts.append(_cove_prism((xin, y_rail, zt_pl - R - 0.6), (0, 0, 1),
                             (0, -1, 0), (tdir, 0, 0), 16.6, R))
    out = parts[0]
    for q in parts[1:]:
        out = out + q
    return out


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
        with Locations(((P.BODY_FRONT_Y + 0.2 + P.WALL_REAR_Y + 0.5) / 2, 45)):
            Rectangle(P.WALL_REAR_Y + 0.5 - P.BODY_FRONT_Y - 0.2, 70,
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
    return wp.part + _bead_band(x_outer, thickness_dir, prof)

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
    left = left + wall_coves(P.WALL_L_X, +1)

    # проріз під тіло 40-мм вентилятора у ПРАВІЙ стінці: рамка проходить
    # крізь плиту (права грань вентилятора врівень із зовнішньою площиною);
    # бортик/рубчик природно огинають проріз зверху і знизу
    clr = P.FAN_NOTCH_CLR
    with BuildPart() as fcut:
        with BuildSketch(Plane.YZ.offset(P.WALL_R_X - P.WALL_T - P.BEAD_W - 1)):
            with Locations((P.BODY_FRONT_Y + P.FAN_D / 2, P.FAN_CZ)):
                # ПРЯМИЙ прямокутник: бічний профіль вентилятора (10×40)
                # гострокутний — R2 у ніші не давав рамці сісти (фідбек)
                Rectangle(P.FAN_D + 2 * clr, P.FAN_W + 2 * clr)
        extrude(amount=P.WALL_T + P.BEAD_W + 3)
    right = (right - fcut.part).fix()
    right = right + wall_coves(P.WALL_R_X, -1)

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
    return left + right + rear_ridge()


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "walls")
