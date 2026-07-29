"""
floor.py — параметричне ДНО 2U board-tray (концепція 2026-07-02, ітерація 3):
  • несуча РАМА по периметру (FRAME_T=3мм, ширина FRAME_W=10, внутр. кути R1)
  • всередині — заповнення 2мм; соти (pointy-top, R1) КЛІПНУТІ межами площини
    та RAM-вікон — біля країв соти урізані, не пропущені
  • навколо постаментів — зони суцільної площини до найближчих сот, укриті
    шаром +1мм з трикутними кишенями R1 (6 трикутників на комірку ґратки)
  • ВИРІЗИ під RAM 35×75 (R1) за замірами від S3
  • постаменти: циліндр ⌀18×2 → конус ⌀8 @ Z7.55 (S3: перехід → ⌀9×5),
    фаска 0.5 зверху, наскрізні отвори ⌀4
Запуск: .venv/bin/python cad/floor.py
2D-розкладка рахується в shapely, переноситься в build123d полілініями.
"""
import math
from build123d import *
import shapely.geometry as sg
from shapely.ops import unary_union
from shapely.affinity import translate
import params as P
import lattice
from exporter import save

AMIN = (Align.CENTER, Align.CENTER, Align.MIN)
SKIRT_N = 10          # сходинок 45°-спідниці крони (h = TRI_RIB_H/N = 0.1)
ORPHAN_MIN = 0.5      # мін. частка кишені в ЗАЛИТІЙ короні (фільтр сиріт)

# (лінзи-пупирки переїхали в ssd_block.py разом з усією SSD-геометрією)


def interior_box():
    """Внутрішня межа несучої рами (XY)."""
    return (P.WALL_L_X + P.FRAME_W, P.BODY_FRONT_Y + P.FRAME_W,
            P.WALL_R_X - P.FRAME_W, P.REAR_Y - P.FRAME_W)


def _rounded(poly, r, qs=8):
    """Скруглення кутів полігона: erode→dilate (opening)."""
    return poly.buffer(-r).buffer(r, quad_segs=qs)


def _polys(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    if geom.geom_type in ('MultiPolygon', 'GeometryCollection'):
        return [g for g in geom.geoms if g.geom_type == 'Polygon']
    return []                                   # LineString/Point від дегенерацій


def plan_geometry():
    """2D-розкладка заповнення. Повертає (holes, crown_polys):
       holes — полігони наскрізних отворів у 2мм шарі (соти кліпнуті + острівці),
       crown_polys — полігони шару +1мм над зонами постаментів (з кишенями-дірками).
    """
    Rc = P.HEX_AF / math.sqrt(3)               # circumradius соти-отвору
    dx = P.HEX_AF + P.HEX_RIB                  # крок ґратки
    dy = dx * math.sin(math.radians(60))
    Rcell = dx / math.sqrt(3)                  # circumradius КОМІРКИ (соти+піврібра)
    x0, y0, x1, y1 = interior_box()
    interior = _rounded(sg.box(x0, y0, x1, y1), P.FRAME_CORNER_R)
    # мікрофаза 0.11: після зсуву постаментів -5 (08.07) стінка суцільної
    # соти біля S4 збіглась із гранню іншого оператора (6 відкритих ребер
    # на X96.65) — зсув фази розбиває точні збіги, функційно нейтральний
    # 24.07 (flat-top): мікрофаза і по Y — горизонтальні грані сот збігались
    # із межею зони корони на y79.30 (6 відкритих ребер, x85.02/−64.12)
    cx0, cy0 = (x0 + x1) / 2 + 0.11, (y0 + y1) / 2 + 0.11
    # 20.07: СІТКА SNAP-FIT — симетричні пади комірок (слот + підмембранна
    # кишеня + обідок) у правій смузі, всі ряди × 2 колонки
    pads = unary_union(
        [sg.Point(x, y).buffer(P.STANDOFF_PAD_D / 2, 48)
         for x, y in P.STANDOFF_XY.values()]
        + [sg.box(cx - P.SNAP_SLOT_X / 2 - P.ANCHOR_PAD_RIM,
                  ry - P.SNAP_TOOTH_POCKET_Y - P.ANCHOR_PAD_RIM,
                  cx + P.SNAP_SLOT_X / 2 + P.ANCHOR_PAD_RIM,
                  ry + P.SNAP_TOOTH_POCKET_Y + P.ANCHOR_PAD_RIM)
           for cx in P.ANCHOR_COLS for ry in P.ANCHOR_ROWS])
    windows = unary_union([_rounded(sg.box(k['x'][0], k['y'][0], k['x'][1], k['y'][1]),
                                    P.RAM_WIN_R)
                           for k in P.RAM_KEEPOUT.values()])

    # 24.07 (фідбек): FLAT-TOP по Y — у друці FACE_DOWN (вісь друку = +Y
    # моделі) верх отвору = коротка ПЛОЩИНА-міст (~8-9мм ≤ правила 12),
    # бічні грані 60° від горизонталі = самонесучі. Pointy-top (кути
    # 90..450) давав стелі-навіси 60° від вертикалі — задирались.
    def hexp(cx, cy, R):
        return sg.Polygon([(cx + R * math.cos(math.radians(a)),
                            cy + R * math.sin(math.radians(a)))
                           for a in range(60, 420, 60)])

    # ── коридори вікно↔рама (зазор < GAP_FILL): суцільні 2мм, без нічого ──
    corridors = []
    for k in P.RAM_KEEPOUT.values():
        wx0, wx1 = k['x']; wy0, wy1 = k['y']
        if wx0 - x0 < P.RAM_WIN_GAP_FILL:
            corridors.append(sg.box(x0, wy0, wx0, wy1))
        if x1 - wx1 < P.RAM_WIN_GAP_FILL:
            corridors.append(sg.box(wx1, wy0, x1, wy1))
        if wy0 - y0 < P.RAM_WIN_GAP_FILL:
            corridors.append(sg.box(wx0, y0, wx1, wy0))
        if y1 - wy1 < P.RAM_WIN_GAP_FILL:
            corridors.append(sg.box(wx0, wy1, wx1, y1))
    corridors = unary_union(corridors) if corridors else sg.Polygon()

    # ── соти: розширена ґратка, кліп по interior та ободку RAM-вікон ──
    # Кліпнуті ФРАГМЕНТИ ближче STANDOFF_SOLID_R до постаменту лишаємо
    # суцільними (жорсткість); повні соти ріжемо завжди.
    allowed = interior.difference(windows.buffer(P.RAM_WIN_RIM))
    full_hex_area = _rounded(hexp(0, 0, Rc), P.HEX_CORNER_R).area
    # 17.07 (фідбек 86.43/92.82): точка на стінці двох сот — обидві
    # суміжні соти НЕ ріжуться, а заливаються ізогрідом (додаються в
    # зону корони нижче)
    iso_fill = unary_union([sg.Point(x, y).buffer(1.0)
                            for x, y in P.ISO_FILL_XY])
    iso_hexes = []
    holes = []
    # 24.07: ґратка ТРАНСПОНОВАНА під flat-top — колонки по X (крок dy),
    # у колонці центри по Y (крок dx), стагер dx/2 через колонку
    ncol = int((x1 - x0) / dy) + 3
    nrow = int((y1 - y0) / dx) + 3
    cells = []                                  # центри комірок (для трикутників)
    for row in range(-nrow, nrow + 1):
        for col in range(-ncol, ncol + 1):
            hx = cx0 + col * dy
            hy = cy0 + row * dx + (col % 2) * dx / 2
            cells.append((hx, hy))
            h = hexp(hx, hy, Rc)
            if not h.intersects(interior):
                continue
            if h.intersects(iso_fill):
                iso_hexes.append(_rounded(h, P.HEX_CORNER_R))
                continue                        # сота заливається ізогрідом
            if h.intersects(pads):
                continue                        # зона постаменту — без сот
            hr = _rounded(h, P.HEX_CORNER_R)
            # 27.07 (відкат заливок, механіка Б): сота ПІД вікном, чий верх
            # пірнає у пояс RIM+CLR, НЕ заливається і НЕ ріжеться хордою —
            # ОПУСКАЄТЬСЯ (h ∩ self-зсунута-вниз): стеля лишається ВЛАСНИМ
            # флет-топом ≤9.65 (міст ≤ правила 12), отвір менший але живий.
            # Умова по сегменту флет-топа (±1.5 запас на дуги кутів пояса);
            # соти ЗБОКУ вікон не чіпаємо — бічні трими пояса вертикальні,
            # друк-безпечні. Дуже глибокі під вікном → area<10 → суцільні.
            ty = hy + Rc * math.sin(math.radians(60))
            for k in P.RAM_KEEPOUT.values():
                wx0, wx1 = k['x']; wy0 = k['y'][0]
                lim = wy0 - (P.RAM_WIN_RIM + P.FILL_RETREAT)
                if (hy < wy0 and ty > lim
                        and hx + Rc / 2 > wx0 - 1.5
                        and hx - Rc / 2 < wx1 + 1.5):
                    hr = hr.intersection(
                        translate(hr, yoff=-(ty - lim + 0.05)))
            hc = hr.intersection(allowed)
            for g in _polys(hc):
                # відсікати крихти й щілини вужчі за ~1.2мм
                if g.area < 10.0 or g.buffer(-0.6).is_empty:
                    continue
                if g.intersects(corridors):
                    continue                    # коридор вікно↔рама → суцільний
                clipped = g.area < full_hex_area - 0.5
                if clipped and min(g.distance(sg.Point(x, y))
                                   for x, y in P.STANDOFF_XY.values()) \
                        < P.STANDOFF_SOLID_R:
                    continue                    # фрагмент біля постаменту → суцільний
                holes.append(g)

    # SSD живе ОКРЕМИМ блоком (ssd_block.py); 13.07: кріпиться до дна
    # СІТКОЮ (місток у ряду Y5 + гачок в5.2 за паз бортика) — у дні від
    # нього нічого власного. Соти скрізь — підсос знизу.
    # смуга ПІД ТРАМПЛІНОМ бортика — суцільна (соти лишали його підошву
    # над дірками: 36.9/100.9 — «має на чомусь стояти»); задня рама від
    # 103.5 і так суцільна
    # 10.07 (фідбек 121.3/99.72/2): суцільне — РІВНО від підошви
    # трампліна (старт дуги 98.5, перекриття 0.1), патерни впритул
    ramp_strip = sg.box(P.WALL_L_X + P.BEAD_W - 0.5, 98.4,
                        P.WALL_R_IN + 0.4, 104.0)
    holes = [h.difference(ramp_strip) for h in holes]
    holes = [g for h in holes for g in _polys(h)
             if g.area > 10.0 and not g.buffer(-0.6).is_empty]
    voids = unary_union([unary_union(holes), windows])
    solid = interior.difference(voids)

    # ── острівці (не тримаються ні рами, ні падів) → у порожнечу ──
    rim = interior.exterior.buffer(0.05)
    kept, islands = [], []
    for c in _polys(solid):
        (kept if (c.intersects(rim) or c.intersects(pads))
         else islands).append(c)
    solid = unary_union(kept)
    holes.extend(islands)

    # 27.07 (відкат 5b086a0, «поверни отвори в стільниках… мета була
    # полегшити конструкцію»): заливання сот СКАСОВАНО. Варіант А:
    # ріжемо КРОНУ, не соти. Соти лишаються цілі 1:1 (або ОПУЩЕНІ
    # механікою Б вище — під RAM-вікнами); крона відступає ФЕСТОНАМИ:
    # над флет-топом кожної соти з крони/стека вирізається смуга CLR —
    # між стелею соти (міст у FACE_DOWN) і 3мм-масивом завжди лишається
    # ≥1.5 смуга 2мм-мембрани, масив сідає на опору, а не на кромку
    # моста. Фестон = БОКС над сегментом флет-топа (union повних форм
    # сот з'їдав би ребра вздовж діагональних стінок 60°: перпендикуляр
    # 0.75 з ребра ~1.5); xs беруть і плечі скруглень кутів (y>ty−0.3).
    # Пропуски: задня трамплін-крона (ty>94 — фестон підрізав би
    # підошву трампліна 98.4+; там крона на короткій мембрані, як у
    # базлайні) та одноточкові верхи (<1.0 — самонесучі). Пояс вікон
    # RIM+CLR (d122383, «рівномірно ширший обідок») лишається 1:1.
    _clr = P.FILL_RETREAT
    _belt = windows.buffer(P.RAM_WIN_RIM + _clr)
    holes_fin = [g for h in holes for g in _polys(h.difference(_belt))
                 if g.area > 10.0 and not g.buffer(-0.6).is_empty]
    hu_fin = unary_union(holes_fin)
    # 28.07 (фідбек п.3 «зрізав нижню грань ізогріду… артефакти в усіх
    # закінченнях зліва та справа», 67.03/59.30): фестон-БОКС мав
    # вертикальні кінці посеред крони — клин-слівер до 60°-плеча соти +
    # язичок 0.4 крони НАД фестоном (риб 2.0 між стосованими сотами −
    # фестон 1.6). Тепер фестон = ТРАПЕЦІЯ: боки йдуть 60° усередину-
    # вгору ЧЕРЕЗ верхні кути флет-топа — колінеарні діагональним
    # стінкам соти (межа крони = лінія патерну, клина нема); якщо
    # просто над фестоном СТОСОВАНА сота — верх подовжується за її
    # дно (ty+2.6 > риб 2.0, зайве зріже сама сота) і язичок зникає.
    _slope60 = math.tan(math.radians(60.0))
    fest = []
    for h in holes_fin:
        ty = max(c[1] for c in h.exterior.coords)
        if ty > 94.0:
            continue                # задня трамплін-смуга — базлайн
        xs = [c[0] for c in h.exterior.coords if c[1] > ty - 0.3]
        if max(xs) - min(xs) < 1.0:
            continue                # одноточковий верх — самонесучий
        xl, xr = min(xs), max(xs)
        mx = (xl + xr) / 2
        probe = sg.box(mx - 0.6, ty + 0.1, mx + 0.6, ty + 2.6)
        top_h = 2.6 if hu_fin.intersects(probe) else _clr
        y0 = ty - 1.5
        y1 = min(ty + top_h, ty + (xr - xl) / 2 * _slope60 - 0.05)
        if y1 <= ty - 0.1:
            continue
        f = sg.Polygon([
            (xl + (y0 - ty) / _slope60, y0),
            (xr - (y0 - ty) / _slope60, y0),
            (xr - (y1 - ty) / _slope60, y1),
            (xl + (y1 - ty) / _slope60, y1)]).buffer(0)
        # 28.07 («нормальні закруглення на краях»): opening R0.6 —
        # верхні кути фестона заокруглені; низ подовжено В отвір соти
        # (ty−1.5, боки колінеарні стінкам 60° — трапеція сидить точно
        # на лініях патерну), щоб радіуси НИЖНІХ кутів потонули в
        # отворі й не лишали мікро-клаптів крони на верхніх кутах соти
        fr = f.buffer(-0.6, quad_segs=8).buffer(0.6, quad_segs=8)
        fest.append(fr if not fr.is_empty else f)
    fest = unary_union(fest) if fest else sg.Polygon()

    # ── зони постаментів: морф. відкриття прибирає 2мм-павутину ──
    opened = solid.buffer(-1.2).buffer(1.2, quad_segs=8)
    zone = unary_union([c for c in _polys(opened) if c.intersects(pads)])
    zone = zone.intersection(solid)
    # 08.07: межі зони втоплені 0.05 від стінок сот (зона з morph-opening
    # збігається з ними по побудові; на глибині 113.5 ретайлінг дав
    # коінцидентну стінку крона↔сота на X-71.1 → 6 відкритих ребер STL)
    zone = zone.buffer(-0.08)
    # 13.07 (фідбек 127.35/22.4/1.6): втоплення -0.08 відступало і від
    # РАМИ — канавка 0.08 до мембрани вздовж межі interior. Доліплюємо
    # крону в раму (перекриття ~0.4), лишаючи 0.08 від стінок сот
    frame_ring = sg.LineString(interior.exterior.coords).buffer(0.6)
    zone = zone.union(zone.buffer(0.5).intersection(frame_ring)
                      .difference(voids.buffer(0.08)))
    # зона SSD-блока без корони (полози мають стояти на рівному 2мм)
    # (08.07: crown-killer SSD-зони ВИДАЛЕНИЙ — блок на полозах стоїть
    # на рівні корони Z3, ізогрід під ним = опора + «залий ізогрідами»
    # п.3; герметичної підлоги каналів давно нема)
    # відступ від RAM-вікон: модуль сідає в вікно, шар +1мм не має тертись
    zone = zone.difference(windows.buffer(0.5))
    # 28.07 (фідбек п.2 «ти для чогось додав ізогрід знизу отвору під
    # рам. навіщо?»): незапитаний ПОБІЧНИЙ ефект механіки Б — morph-
    # відкриття захопило широку мембрану над ОПУЩЕНИМИ сотами і
    # поставило смугу крони з кишенями в поясі під вікном A. Пояс
    # RIM+CLR під вікнами — чиста 2мм мембрана (як і задумано
    # фестонами): зона ріжеться явно, обидва вікна.
    # 28.07 ч.2 (фідбек «ізогрід на куті вікна A — прибрати», фрагмент
    # 40..48/38..48): пояс був вузький по x (±1.5) — морф-клапоть за
    # правим краєм вікна лишався. Ширина поясу по x = та сама
    # RIM+CLR+0.6, що і вниз.
    _bw = P.RAM_WIN_RIM + P.FILL_RETREAT + 0.6
    for k in P.RAM_KEEPOUT.values():
        kx0, kx1 = k['x']; ky0 = k['y'][0]
        zone = zone.difference(sg.box(kx0 - _bw, ky0 - _bw, kx1 + _bw, ky0))
    # 08.07 (п.6): смужка МІЖ RAM-вікнами (модулі там прилягають один до
    # одного і звисають до Z2.55) — корону/ізогрід (3мм) тут НЕ робити,
    # лишається 2мм заливка; по всій глибині вікна A
    _ra, _rb = P.RAM_KEEPOUT["A"], P.RAM_KEEPOUT["B"]
    zone = zone.difference(sg.box(_rb["x"][1] - 0.2, _ra["y"][0],
                                  _ra["x"][0] + 0.2, _ra["y"][1]))
    # коридори вікно↔рама — гладенькі 2мм: без корони й трикутників
    zone = zone.difference(corridors)
    # 23.07 (скрін користувача, кут вікна A): межа корони має йти по
    # лінії заокруглення ободка, ізогрід ширший (покриває −39.9/75.18).
    # Смужка між вікнами (вище) різала до y1 вікна A, хоча вікно B
    # закінчується на y67.9 (модуля там уже нема), а morph opening
    # лишав у куті гачок-завиток. Доливаємо зону явно — кутова латка
    # до стандартного відступу 0.5 від вікон (як у решти зони).
    # 27.07 (фідбек −33.80/75.95/3.00): правий край латки −33.0 був
    # ДОВІЛЬНИЙ — таб корони стирчав 0.5 ЗА межу смужки між вікнами
    # (різ вище: _rb.x1−0.2) і обривався посеред мембрани прямокутною
    # сходинкою. Край латки = край смужки: межа корони — одна пряма.
    _corner = sg.box(-45.0, _rb["y"][1] + 0.2, _rb["x"][1] - 0.2, 79.0)
    zone = zone.union(solid.intersection(_corner)
                      .difference(windows.buffer(0.5))
                      .difference(voids.buffer(0.08)))
    # 27.07 (та сама точка): ПРАВІШЕ латки morph-межа зони блукала
    # коридором над вікном A — язик до x−33.6 з гачком + горбик до
    # y80 під стінкою соти, обрив посеред мембрани. Зріз по вертикалі
    # x = лівий край смужки: межа корони = продовження лінії смужки
    # вгору; низ сідає на дугу 0.5 кута вікна A, верх — на нижню
    # стінку соти (y≈79.6). Верх/право — literal з запасом (вище/правіше
    # корони там немає, ріже лише язик+горбик).
    zone = zone.difference(sg.box(_rb["x"][1] - 0.2, _ra["y"][1] - 1.0,
                                  -30.0, 81.0))
    # 17.07: залиті соти (ISO_FILL_XY) — у зону ізогріду; обідок 2мм по
    # межі дає сам pocket_region (zone.buffer(-2.0) нижче)
    if iso_hexes:
        zone = zone.union(unary_union(iso_hexes).intersection(solid))
    # 23.07 («прибери кругляшок»): замість заливати острів суцільним
    # колом R2 (видима латка) — ПРИТУПЛЮЄМО хвіст кишені малим колом:
    # верхівка кишені відступає від вертикального ребра, щілина 0.15
    # закривається і вістря корони зростається з ребром у КОЖНОМУ шарі
    # FACE_DOWN (підпора знизу через ребро). Кола ріжуться з кишень
    # нижче, у циклі (pocket_blunt).
    pocket_blunt = unary_union(
        [sg.Point(x, y).buffer(P.CROWN_TRIM_R, 32)
         for x, y in P.CROWN_TRIM_XY]) if P.CROWN_TRIM_XY else None

    # ── трикутні кишені (6 на комірку, R1), ребра TRI_RIB_W між ними ──
    inset = P.TRI_RIB_W / 2
    # 04.07: ізогрід НАСКРІЗНИЙ → суцільний комірець ⌀17 під колоною
    # (виривання гвинта) + обідок 2мм по межі зони (крайові ребра 3мм
    # заввишки не мають бути тонші 2)
    keep_r = P.STANDOFF_COLLAR_D / 2
    base_keep = unary_union(
        [sg.Point(x, y).buffer(keep_r, 48)
         for x, y in P.STANDOFF_XY.values()]
        # комірки snap-fit: кишені ізогріду тут НЕ ріжемо — пад
        # суцільний (мембрана над підмембранною кишенею і так 1.6)
        + [sg.box(cx - P.SNAP_SLOT_X / 2 - P.ANCHOR_PAD_RIM,
                  ry - P.SNAP_TOOTH_POCKET_Y - P.ANCHOR_PAD_RIM,
                  cx + P.SNAP_SLOT_X / 2 + P.ANCHOR_PAD_RIM,
                  ry + P.SNAP_TOOTH_POCKET_Y + P.ANCHOR_PAD_RIM)
           for cx in P.ANCHOR_COLS for ry in P.ANCHOR_ROWS])
    # 23.07 (друк №2, прогалини під трампліном ПОВЕРНУЛИСЬ): ramp_strip
    # різав лише СОТИ — наскрізні кишені корони-ізогріду він не чіпав, і
    # зсув ґратки 22.07 (крок 19.6→20.0) поставив кишені під підошву
    # дуги. Генеричний фікс: смуга виключається і з зони кишень.
    # 24.07 (фідбек «соти від рами −86.40, ізогрід від −84.82 —
    # несправедливо; по боках теж»): кишені мають іти ДО РАМИ, як соти.
    # buffer(−2.0) давав 2мм обідок і вздовж interior — розширюємо зону
    # ЗА межу interior (смуга ззовні) перед ерозією, потім кліпаємо
    # назад: обідок 2мм лишається лише вздовж вікон/коридорів/меж зони.
    # 29.07 (дефект 4, −72.62/−21.91): той самий обідок 2.0 виникав і
    # вздовж стінок СОТ (зонд: кишеня за 2.08 від стінки — дуга ерозії)
    # → розширюємо зону і В СОТИ: сота «продовжує» зону, як рама;
    # кишеня йде до стінки за патерном (ребро 1.5, зайве в отворі
    # зрізає наскрізний різ сот у build()).
    zone_ext = zone.union(zone.buffer(2.2).difference(interior)) \
                   .union(zone.buffer(2.2).intersection(hu_fin))
    # 29.07 (дефект 2, закон зв'язків): кліп 25.07 holes.buffer(0.5)
    # ВИДАЛЕНО — він лікував «висячий пластик» ребер над отворами, що
    # відтоді вилікуваний наскрізним різом сот 28.07 (flush-стінки);
    # а сам ламав патерн: ребро кишеня↔сота ставало 2.0 замість
    # штатних 0.75+0.75=1.5 (трикутники субдивідують ТІ САМІ комірки).
    # 27.07 (варіант А): фестони лишаються — інакше наскрізна
    # tri-кишеня могла б пробити 1.5-смугу мембрани над мостом соти
    pocket_region = zone_ext.buffer(-2.0).intersection(interior) \
                            .difference(base_keep).difference(ramp_strip) \
                            .difference(fest)
    pockets = []
    for (hx, hy) in cells:
        cell_pts = [(hx + Rcell * math.cos(math.radians(a)),
                     hy + Rcell * math.sin(math.radians(a)))
                    for a in range(60, 420, 60)]
        for k in range(6):
            tri = sg.Polygon([(hx, hy), cell_pts[k], cell_pts[(k + 1) % 6]])
            if not tri.intersects(zone):
                continue
            pk = tri.buffer(-(inset + P.HEX_CORNER_R)) \
                    .buffer(P.HEX_CORNER_R, quad_segs=8) \
                    .intersection(pocket_region)
            if pocket_blunt is not None:
                pk = pk.difference(pocket_blunt)
            for g in _polys(pk):
                # 17.07: + фільтр ширини — кишені-СЛІВЕРСИ (<0.9мм) біля
                # кутів анкерних падів лишали тонкі гачки корони
                # (фідбек 117.95/−33.38, 118.17/−17.12)
                if g.area > 2.0 and not g.buffer(-0.45).is_empty:
                    pockets.append(g)

    from shapely import set_precision
    # 24.07 (flat-top, 3 відкриті ребра @ (85.2, 79.41) z0..3): кишеня і
    # крона ділять межу (кліп по pocket_region), але крона снапилась
    # set_precision 0.01, а tri_pockets ішли в наскрізний різ НЕснапнуті
    # (79.410 vs 79.413) → сливер-стінка. Снапимо кишені ДО обох вживань.
    pockets = [g for p in pockets for g in _polys(set_precision(p, 0.01))
               if g.area > 2.0]
    # 28.07 (острів FACE_DOWN z162.84 @S4): нижня ДОТИЧНА комірця ⌀17
    # (cx, cy−keep_r) опинилась ПОСЕРЕД кишені (крок ґратки 19.5 після
    # HEX_RIB 1.5) → вістря дуги комірця стартувало в повітрі над
    # наскрізною кишенею. Генерично: кишені під дотичними видаляються
    # ДО crown — крона заповнює трикутник, вістря має повну опору.
    _tang = [sg.Point(x, y - keep_r) for x, y in P.STANDOFF_XY.values()]
    pockets = [p for p in pockets
               if all(t.distance(p) > 0.3 for t in _tang)]
    crown = set_precision(zone.difference(unary_union(pockets)), 0.01)
    # 27.07→28.07: нога ребра ізогріду біля рами — ПО ПАТЕРНУ
    # (WEDGE_LEG_PTS). Історія: фаска 32° (клин-слівер+кома+горбик) →
    # паралелограм 1.6 з вертикальними межами (5560922) знову лишав
    # слівер і смужку (фідбек 54.90/−85.25 «має бути 3.00» +
    # 55.43/−85.93 «має бути нічого»; точки на перп. 1.678 і 2.477 від
    # стінки соти). Правильна межа = offset HEX_RIB 2.0 від стінки —
    # стандартний риб патерну (1.678<2.0 ✓, 2.477>2.0 ✓). Нога =
    # hex.buffer(2.0) ∩ clip-бокс; перекриття в соту зрізає наскрізний
    # різ сот у build() → flush по стінці.
    if P.WEDGE_LEG_PTS:
        for (wx, wy) in P.WEDGE_LEG_PTS:
            s = -1.0 if wx < 0 else 1.0         # дзеркало за знаком X
            hexw = min(holes_fin,
                       key=lambda h: h.distance(sg.Point(wx, wy)))
            hb = hexw.buffer(P.HEX_RIB, quad_segs=16)
            xin = wx - s * (wy + 86.9) / math.tan(math.radians(60.0))
            # зовнішня межа кліпа = край hb на ВЕРХНІЙ кромці (y −79.8):
            # вертикаль wx±4.2 відтинала ногу від морф-крони (клин-щілина,
            # що звужувалась угорі до ~0.5) — тепер угорі щілина = 0
            # (морф-крона прилягає до кута ноги), донизу ніша розкривається
            # природним трикутником-кишенею по патерну.
            tl = hb.intersection(sg.LineString([(-200, -79.8),
                                                (200, -79.8)]))
            xs = [c[0]
                  for g in (tl.geoms if hasattr(tl, 'geoms') else [tl])
                  for c in g.coords]
            xout = max(xs) if s > 0 else min(xs)
            clip = sg.box(min(xin, xout), -86.9, max(xin, xout), -79.8)
            # верхівка клину-ніші сходилась РІВНО в точці дотику нога↔
            # стрічка крони → point-touch у плані = pinch-ребро в STL
            # (watertight=False). Opening R1: верхівка ніші заокруглюється
            # і відступає (як у сусідніх кишень патерну), нога з'єднана
            # зі стрічкою суцільною перемичкою.
            v = clip.difference(hb)
            vtop = v.buffer(-1.0, quad_segs=8).buffer(1.0, quad_segs=8)
            # низ ніші (y ≤ −84) лишається різким — opening лише верхівці
            niche = vtop.union(v.intersection(
                sg.box(clip.bounds[0], -86.9, clip.bounds[2], -84.0)))
            crown = crown.union(hb.intersection(clip)).difference(niche)
        crown = set_precision(crown, 0.01)
    # 27.07 (варіант А): фестони ріжуть КРОНУ (не соти) — комірці ⌀17 і
    # снап-пади (base_keep) недоторкані
    crown = crown.difference(fest.difference(base_keep))
    # 28.07 (фідбек п.4 «ізогрід накладений на верх стільників не
    # точно», −49.91/92.61): zone.buffer(−0.08) (фікс коінцидентних
    # стінок 08.07) давав видиму ПОЛИЧКУ 0.08 крони над стінкою соти.
    # Фікс: крона ПЕРЕКРИВАЄ діру на 0.35 (замість дотику) — а точну
    # грань стінки тримить НАСКРІЗНИЙ різ сот у build() (перенесений
    # ПІСЛЯ крони, повна глибина): одна спільна грань, різ
    # трансверсальний, коінцидентних площин нема. Inset −0.08 живе.
    # 28.07 ч.2: intersection з ГОЛИМ hu_fin додавав лише шматок
    # УСЕРЕДИНІ діри — канавка 0.08 (кромка зони ↔ стінка соти)
    # лишалась непокритою (union роз'єднаних шматків її не зшиває,
    # зонд −49.98..−49.89 @y92.61). Діри роздуто на 0.1 > 0.08 —
    # band накриває канавку наскрізно до стінки й за неї; зайве
    # всередині діри зрізає той самий наскрізний різ.
    crown = set_precision(
        crown.union(crown.buffer(0.35, quad_segs=8)
                    .intersection(hu_fin.buffer(0.1, quad_segs=8))),
        0.01)
    # 29.07 (дефект 1, «всі точки з'єднання ізогрід↔сота дефектні»):
    # у смузі стику J (1.6 уздовж стінок сот) — opening −0.65/+0.70:
    # «вусики» морф-межі R1.2 і 0.1-слівери band'а (все тонше 1.3)
    # зникають, кінці ребер отримують простий круглий торець R0.7
    # («просто закругли», без напливів по боках), а +0.05 перекриття
    # у стінку гарантує flush без щілини (зайве в отворі зрізає
    # наскрізний різ сот у build()). Поза J крона недоторкана; шов на
    # межі J ≤0.05 < сопло 0.4.
    _J = hu_fin.buffer(1.6, quad_segs=8)
    _opened = crown.buffer(-0.65, quad_segs=8).buffer(0.70, quad_segs=8)
    crown = set_precision(
        crown.difference(_J).union(_opened.intersection(_J)), 0.01)
    crown_polys = [g for g in _polys(crown) if g.area > 3.0]
    # 24.07 (фідбек «артефакт видалити −36.60/38.40/3.00») → 28.07
    # («какаха» −37.78/38.26): поріг area≥15 пропускав ізольовані
    # морф-клякси, щойно вони виростали за 15. Каркас тепер ЯКІРНИЙ:
    # компонент лишається, якщо тримається постаментів (pads) або
    # рами (rim); дрібне — лише впритул (≤2.0) до каркасу.
    _anch = [g for g in crown_polys
             if g.intersects(pads) or g.intersects(rim)]
    _anch_u = unary_union(_anch)
    crown_polys = _anch + [
        g for g in crown_polys
        if not (g.intersects(pads) or g.intersects(rim))
        and g.distance(_anch_u) <= 2.0]
    # 27.07 (варіант А): соти віддаються ЯК Є (belt-trimmed holes_fin
    # згори; заливок і стек-різів більше нема — історію 24.07 ч.5
    # «відступ сот» і 27.07 «сота цілком» замінили фестони крони +
    # механіка Б опускання сот під вікнами, див. коменти вище)
    holes = [g for h in holes_fin for g in _polys(set_precision(h, 0.01))
             if g.area > 1.0]
    # 28.07 (фідбек): ребра ОСТАННЬОГО ряду сот (y≈98.09) — БЕЗ ізогріду:
    # кишені, що зачіпають ці 4 ребра, видаляються (крона там суцільна,
    # мембрана під ними теж — наскрізний різ цих кишень не робиться)
    _no_iso = unary_union([sg.box(x - 4.5, 95.6, x + 4.5, 100.6)
                           for x in (-41.18, -6.98, 27.60, 62.14)])
    pockets = [p for p in pockets if not p.intersects(_no_iso)]
    # 28.07 (закон зв'язків): кишені-СИРОТИ — чия крона зрізана якірним
    # фільтром чи поясом RAM — видаляються (перфорувати нічого; їхній
    # наскрізний різ у стеку спідниці давав OCC invalid-тіло → падав
    # chamfer постаментів). Кишені = ДІРИ у crown_polys → порівнювати
    # із ЗАЛИТИМ контуром крони (лише exterior), не з самою кроною.
    _cu = unary_union(crown_polys)
    _cu_fill = unary_union([sg.Polygon(g.exterior) for g in crown_polys])
    pockets = [p for p in pockets
               if p.intersection(_cu_fill).area > ORPHAN_MIN * p.area]
    # 28.07 («всі переходи 2→3 мм по зет — під 45°»): футпринт СПІДНИЦІ
    # крони. Кишені ЗАЛИТІ (нахил їхніх інтеріорів роздув би вікна
    # вгорі — ребра 1.5 стали б лезами); розширення 1.2 (> нахил 1.0)
    # у РАМУ (difference(interior) — рампа тоне в суцільній рамі 0..3)
    # і в СОТИ (intersection(hu_fin) — наскрізний різ сот у build()
    # зрізає до flush-стінки). Голими лишаються ЛИШЕ межі до мембрани
    # (вікна/коридори/фестони/пояси) → саме там 45°-схил.
    fp = unary_union(crown_polys + pockets)
    fp = fp.union(fp.buffer(1.2, quad_segs=8).difference(interior))
    fp = fp.union(fp.buffer(1.2, quad_segs=8).intersection(hu_fin))
    # компоненти-СИРОТИ (кишені крон, видалених якірним фільтром) геть —
    # інакше висіли б крихтами Z2..3 у повітрі (їх все одно зрізав би
    # наскрізний різ, але OCC на них дає invalid-тіла)
    fp = unary_union([g for g in _polys(set_precision(fp, 0.01))
                      if g.area > 3.0 and g.intersects(_cu)])
    # 45° СХОДИНКАМИ h=TRI_RIB_H/SKIRT_N (справжній extrude(taper=45)
    # на цих контурах падає: OCC MakeOffset → Null TopoDS_Shape на
    # невипуклих мульти-кільцевих межах; сходинка 0.1 < сопло 0.4 і
    # < шар 0.24 — друк і вигляд = рампа).
    # 28.07 ч.2 (фідбек «подивись тепер відповідно до площин друку де
    # вони реально потрібні»): спідниця НЕ ізотропна (buffer(−i·h)
    # відступав з усіх боків), а ДИРЕКЦІЙНА — FACE_DOWN росте вздовж
    # +Y моделі, полиця 2→3 висить лише там, де крона ПОЧИНАЄТЬСЯ по
    # ходу друку: межі, що дивляться у −Y (старт зони), і північні
    # обідки внутрішніх вікон fp (матеріал відновлюється після діри).
    # Межі вздовж Y = вертикальні стінки друку, межі у +Y = верхівки
    # (матеріал закінчується) — там рампа зайва. Рівень i =
    # fp ∩ translate(fp, +i·h по Y): точка лишається ⇔ вона і її
    # сусідка на i·h нижче обидві у fp → південна межа відступає,
    # північні обідки дір автоматично, решта незмінна. Бонус: опорні
    # площини Z3 (пади під полози блока, кромки RAM) не звужуються
    # з трьох непотрібних боків.
    # втоплення 0.05 від стінок отворів: край сходинки, ДОТИЧНИЙ до
    # вертикальної стінки соти/ізогріду, давав у STL зліплені трикутники
    # (20 нон-маніфолд ребер @Z2.05/2.15) — відступ робить грані
    # трансверсальними; 0.05 < сопло 0.4, невидимо
    _hu_in = unary_union(holes).buffer(0.05, quad_segs=4)
    # 29.07 (дефекти 1г/3/5): зони-ВИКЛЮЧЕННЯ спідниці — там межа fp
    # у друці самонесуча, а сходинки лише псували патерн:
    #   • смуга J стиків крона↔сота (вертикальна стінка друку або
    #     30°-діагональ — градієнт «там, де його не має бути»);
    #   • ніші WEDGE_LEG біля фронту (схили 60° у плані = 30° від
    #     вертикалі; віяло 10 дуг давало «суцільний дефект»);
    #   • межа трамплін-смуги (перехід сот у бортик: стеля соти =
    #     міст-прецедент, губа 1мм — мікрополиця).
    # Спідниця ЛИШАЄТЬСЯ на межах до голої мембрани (пояси RAM,
    # вікна, коридори, фестони) — її справжня робота.
    _skeep = [_J]
    if P.WEDGE_LEG_PTS:
        _skeep += [sg.box(wx - 6.0, -87.4, wx + 6.0, -79.3)
                   for (wx, wy) in P.WEDGE_LEG_PTS]
    _skeep.append(ramp_strip.buffer(1.6, quad_segs=8))
    _skirt_keep = fp.intersection(unary_union(_skeep))
    skirt = []
    for i in range(SKIRT_N):
        d = i * P.TRI_RIB_H / SKIRT_N
        ft = fp.intersection(translate(fp, yoff=d)).union(_skirt_keep) \
            if i else fp
        ft = ft.difference(_hu_in)
        skirt.append([g for g in _polys(set_precision(ft, 0.01))
                      if g.area > 3.0])
    return holes, crown_polys, pockets, skirt


def standoff_part():
    """Еталонний постамент: колона ⌀9 Z0..8 з галтеллю R1 біля основи.
    Профіль-револьв (не 3D-філет, за уроком): основа r5.5 до верху корони (Z3),
    дуга R1 → колона r4.5 до Z8. Створюється ПОЗА BuildPart (урок про витік)."""
    r = P.STANDOFF_D / 2
    fr = P.STANDOFF_FIL_R
    zc = P.INFILL_T + P.TRI_RIB_H                # верх корони = 3.0
    with BuildPart() as so:
        with BuildSketch(Plane.XZ):
            with BuildLine():
                Polyline((0, 0), (r + fr, 0), (r + fr, zc))
                RadiusArc((r + fr, zc), (r, zc + fr), fr)
                Polyline((r, zc + fr), (r, P.STANDOFF_TOP_Z),
                         (0, P.STANDOFF_TOP_Z), (0, 0))
            make_face()
        revolve(axis=Axis.Z)
    return so.part


def build():
    holes, crown_polys, tri_pockets, skirt = plan_geometry()
    standoff = standoff_part()                   # еталон — поза BuildPart

    with BuildPart() as tray:
        # ── плита на повну висоту рами (3мм); задні кути R3 у 2D-контурі ──
        with BuildSketch(Plane.XY) as fs:
            with BuildLine():
                Polyline(*P.footprint()[:-1], close=True)
            make_face()
            rear_vs = fs.vertices().filter_by(
                lambda v: abs(v.Y - P.REAR_Y) < 1e-6)
            fillet(rear_vs, radius=P.REAR_CORNER_R)
        extrude(amount=P.FRAME_T)

        # ── опустити інтер'єр до 2мм (лишається несуча рама; внутр. кути R1) ──
        x0, y0, x1, y1 = interior_box()
        with BuildSketch(Plane.XY.offset(P.INFILL_T)):
            with Locations(((x0 + x1) / 2, (y0 + y1) / 2)):
                RectangleRounded(x1 - x0, y1 - y0, radius=P.FRAME_CORNER_R)
        extrude(amount=P.FRAME_T - P.INFILL_T + 1, mode=Mode.SUBTRACT)

        # (28.07, фікс п.4: різ сот ПЕРЕНЕСЕНО ПІСЛЯ крони — тепер він
        # наскрізний крізь неї і тримить flush-грань стінки соти; крона
        # в плані перекриває діри на 0.35, різ зрізає перекриття)

        # ── вирізи під RAM-модулі (наскрізні вікна; кути R1) ──
        for k in P.RAM_KEEPOUT.values():
            wx0, wx1 = k['x']; wy0, wy1 = k['y']
            with BuildSketch(Plane.XY.offset(-1)):
                with Locations(((wx0 + wx1) / 2, (wy0 + wy1) / 2)):
                    RectangleRounded(wx1 - wx0, wy1 - wy0, radius=P.RAM_WIN_R)
            extrude(amount=1 + P.INFILL_T + 0.5, mode=Mode.SUBTRACT)

        # ── корона зон постаментів: СПІДНИЦЯ 45° сходинками (28.07,
        # «всі переходи 2→3 мм — під 45°») — рівень i = футпринт,
        # звужений shapely-offset на i·h (h=0.1). Межі до мембрани
        # стають 45°-рампами; наскрізні різи сот/кишень нижче
        # відновлюють точні вертикальні стінки патерну. ──
        _h = P.TRI_RIB_H / SKIRT_N
        for i, level in enumerate(skirt):
            with BuildSketch(Plane.XY.offset(P.INFILL_T + i * _h)):
                for poly in level:
                    with BuildLine():
                        Polyline(*list(poly.exterior.coords)[:-1],
                                 close=True)
                    make_face()
                    for ring in poly.interiors:
                        rp = sg.Polygon(ring)
                        if abs(rp.area) < 0.8:
                            continue
                        rp = rp.simplify(0.02).buffer(0)
                        if rp.geom_type != 'Polygon' or rp.area < 0.8:
                            continue
                        with BuildLine():
                            Polyline(*list(rp.exterior.coords)[:-1],
                                     close=True)
                        make_face(mode=Mode.SUBTRACT)
            extrude(amount=_h)

        # ── соти (кліпнуті) — наскрізь крізь заповнення І крону ──
        # (28.07: перенесено ПІСЛЯ крони, глибина повна — крона в плані
        # перекриває діри на 0.35, цей різ зрізає перекриття → грань
        # стінки соти ОДНА на всі шари Z1..3, коінцидентних площин нема)
        with BuildSketch(Plane.XY.offset(-1)):
            for g in holes:
                with BuildLine():
                    Polyline(*list(g.exterior.coords)[:-1], close=True)
                make_face()
                # внутрішні кільця (напр. пад кріплення ЦІЛКОМ усередині
                # соти): без цього острів зникав — бонка висіла в повітрі
                for ring in g.interiors:
                    with BuildLine():
                        Polyline(*list(ring.coords)[:-1], close=True)
                    make_face(mode=Mode.SUBTRACT)
        extrude(amount=1 + P.INFILL_T + P.TRI_RIB_H + 0.5,
                mode=Mode.SUBTRACT)

        # ── ізогрід НАСКРІЗНИЙ (04.07): ті ж трикутні кишені прорізаються
        # крізь 2мм заповнення → решітка 3мм на просвіт (жорсткість ×2.5
        # у згині проти суцільної двійки, обдув; комірці ⌀17 суцільні) ──
        with BuildSketch(Plane.XY.offset(-1)):
            for pk in tri_pockets:
                rp = pk.simplify(0.02).buffer(0)
                if rp.geom_type != 'Polygon' or rp.area < 0.8:
                    continue
                with BuildLine():
                    Polyline(*list(rp.exterior.coords)[:-1], close=True)
                make_face()
        extrude(amount=1 + P.INFILL_T + P.TRI_RIB_H + 0.5,
                mode=Mode.SUBTRACT)

        # ── постаменти: 4 однакові колони ⌀9 з галтеллю R1 ──
        with Locations(*[(x, y, 0) for x, y in P.STANDOFF_XY.values()]):
            add(standoff)

        # ── зрізати частини постаментів, що нависають у RAM-вікна ──
        # (сегмент бази S3 + скибка конуса; кліренс до модуля був 0.06мм)
        for k in P.RAM_KEEPOUT.values():
            wx0, wx1 = k['x']; wy0, wy1 = k['y']
            with BuildSketch(Plane.XY.offset(-1)):
                with Locations(((wx0 + wx1) / 2, (wy0 + wy1) / 2)):
                    RectangleRounded(wx1 - wx0, wy1 - wy0, radius=P.RAM_WIN_R)
            extrude(amount=1 + P.FRAME_T + 1, mode=Mode.SUBTRACT)

        # ── СІТКА АДДОНІВ (20.07, snap-fit — cad/snap_kin.py): комірка =
        # СИМЕТРИЧНИЙ слот у мембрані (наскрізь) + ПІДМЕМБРАННА КИШЕНЯ
        # знизу Z0..LEDGE (1.4) — зуб зачепа чіпляється під мембрану і
        # ХОВАЄТЬСЯ В ТОВЩІ ДНА (знизу корпусу не видно, нижче Z0 нічого).
        # Кишеня відкрита вниз — крізь неї зуби притискаються при
        # зніманні. Друк лицем вниз: стінки вертикальні, без підтримок.
        with BuildSketch(Plane.XY.offset(-1)):
            with Locations(*[(cx, ry)
                             for cx in P.ANCHOR_COLS
                             for ry in P.ANCHOR_ROWS]):
                RectangleRounded(P.SNAP_SLOT_X, 2 * P.SNAP_SLOT_HALF,
                                 radius=P.SNAP_SLOT_R)
        extrude(amount=1 + P.FRAME_T + 1, mode=Mode.SUBTRACT)
        with BuildSketch(Plane.XY.offset(-1)):
            with Locations(*[(cx, ry)
                             for cx in P.ANCHOR_COLS
                             for ry in P.ANCHOR_ROWS]):
                RectangleRounded(P.SNAP_SLOT_X, 2 * P.SNAP_TOOTH_POCKET_Y,
                                 radius=0.8)
        extrude(amount=1 + P.SNAP_LEDGE_Z, mode=Mode.SUBTRACT)
        # (17.07 #3: пази язиків аддона в передній рамі + лійка-розхил
        # ВИДАЛЕНІ — язики тепер у площині ламелі аддона, у кишенях
        # смуги-обідка ПАНЕЛІ (front.py); рама дна суцільна)

        # ── наскрізні отвори ⌀4 ──
        for (x, y) in P.STANDOFF_XY.values():
            with Locations((x, y, -1)):
                Cylinder(P.STANDOFF_HOLE_D / 2, P.STANDOFF_TOP_Z + 2,
                         align=AMIN, mode=Mode.SUBTRACT)

        # ── фаска на верхньому зовнішньому ребрі постаментів ──
        top_rims = (tray.edges()
                    .filter_by(GeomType.CIRCLE)
                    .filter_by(lambda e: abs(e.arc_center.Z - P.STANDOFF_TOP_Z) < 1e-6
                               and e.radius > P.STANDOFF_HOLE_D / 2 + 0.5))
        chamfer(top_rims, length=P.STANDOFF_CHAMFER)

        # ── 20.07 (зонд probe_print): дозріз колон над RAM-вікнами ──
        # Різ вище (до Z4) лишав скибку колони S3 z4..7.55 НАД вікном B —
        # у друці лицем вниз вона стартувала ОСТРОВОМ у повітрі (6.5 мм²,
        # висота 167). Різ ПІСЛЯ фаски (chamfer хоче повне коло обода;
        # спроба «різ до фаски» валила chamfer на дузі+хорді). Проти
        # копланарності зі стінками старого різу (invalid-шелл, урок
        # 02.07): футпринт +0.1 назовні, низ Z3.5 — у повітрі вікна,
        # жодної спільної площини. Зачіпає ЛИШЕ колону (обідок/корона
        # закінчуються на Z3); кліренс до RAM-модуля стає на 0.1 більший.
        for k in P.RAM_KEEPOUT.values():
            wx0, wx1 = k['x']; wy0, wy1 = k['y']
            with BuildSketch(Plane.XY.offset(P.FRAME_T + 0.5)):
                with Locations(((wx0 + wx1) / 2, (wy0 + wy1) / 2)):
                    RectangleRounded(wx1 - wx0 + 0.2, wy1 - wy0 + 0.2,
                                     radius=P.RAM_WIN_R)
            extrude(amount=P.STANDOFF_TOP_Z - P.FRAME_T + 1,
                    mode=Mode.SUBTRACT)

        # ── 24.07: жертовні МЕМБРАНИ у RAM-вікнах + ФІНИ під колони ──
        # (друк №3: «провисають отвори під пам'ять» — у FACE_DOWN верхні
        # кромки вікон = мости 75/35мм. Після друку все викушується/
        # виламується. ДОДАВАТИ ПІСЛЯ всіх різів вікон (z≥3.5 їх не
        # чіпає) і після chamfer (не збити фільтр ребер).)
        # 24.07 ч.4 — ГОФРА («жорсткість у площині згину, не в
        # стискання»): мембрана MEM_T=0.5 хвиляста — синус середньої
        # лінії ±MEM_WAVE_A уздовж довгої осі вікна, конверт Z0.5..1.5
        # у товщі інфілу 2.0. Побудова: призма конверта (футпринт
        # membrane2d) ∩ хвиляста плита — бічні/нижні містки стають
        # хвилястими автоматично. Верхня кромка (стеля FACE_DOWN) без
        # прямих містків — ФІНИ-ПЛАВНИКИ кожні ~MEM_FLAG_PITCH (25.07,
        # раніше короткі косинки 45°): лезо MEM_FLAG_W, що виростає з
        # конверта гофри і за MEM_FLAG_RUN (~7°) вливається у повну
        # товщу інфілу, вросток 0.5 у тіло за кромкою. Прольоти стелі
        # ~11 → ~5.8 мм.
        zc = P.INFILL_T / 2                       # серединна площина 1.0
        env0 = zc - P.MEM_T / 2 - P.MEM_WAVE_A    # конверт гофри 0.5
        env1 = zc + P.MEM_T / 2 + P.MEM_WAVE_A    #               1.5
        for name, k in P.RAM_KEEPOUT.items():
            wx0, wx1 = k['x']; wy0, wy1 = k['y']
            mem = lattice.membrane2d(wx0, wy0, wx1, wy1, P.RAM_WIN_R,
                                     open_side='v1')
            # позиції фінів рахуємо ДО патерна — keep-смуги мають
            # збігтися з реальними (для B — після снапу на вісь S3)
            xs = lattice.flag_spots(wx0, wx1)
            if name == 'B':
                sx3 = P.STANDOFF_XY['S3'][0]
                i = min(range(len(xs)), key=lambda j: abs(xs[j] - sx3))
                xs[i] = sx3
            # 25.07 — дрібний ізогрід («Ізогрід дрібний», вибір
            # користувача): наскрізні трикутники з 2D-футпринта ДО
            # призми — наскрізність через prism ∩ wave автоматична.
            # keep: смуги під коренями фінів-плавників (лезо 0.8 має
            # виростати з суцільної мембрани, не з ребра патерна) і під
            # поясом вростка фіна S3 (вікно B).
            keep = [sg.box(u - 1.5, wy1 - P.MEM_FLAG_RUN - 1.0,
                           u + 1.5, wy1) for u in xs]
            if name == 'B':
                keep.append(sg.box(sx3 - 1.5, wy1 - 7.0,
                                   sx3 + 1.5, wy1))
            iso = lattice.mem_iso_holes(mem, keep)
            if iso:
                mem = mem.difference(unary_union(iso))
            with BuildSketch(Plane.XY.offset(env0),
                             mode=Mode.PRIVATE) as psk:
                for g in _polys(mem):
                    with BuildLine():
                        Polyline(*g.exterior.coords)
                    make_face()
                    for hg in g.interiors:
                        with BuildLine():
                            Polyline(*hg.coords)
                        make_face(mode=Mode.SUBTRACT)
            prism = extrude(psk.sketch, amount=env1 - env0,
                            mode=Mode.PRIVATE)

            along_x = (wx1 - wx0) >= (wy1 - wy0)  # A: по x; B: по y
            a0 = (wx0 if along_x else wy0) - 1.0
            a1 = (wx1 if along_x else wy1) + 1.0

            def zmid(a, a0=a0):
                return zc + P.MEM_WAVE_A * math.sin(
                    2 * math.pi * (a - a0) / P.MEM_WAVE_P)

            ns = int(math.ceil((a1 - a0) / 0.5))
            samp = [a0 + (a1 - a0) * i / ns for i in range(ns + 1)]
            top = [(a, zmid(a) + P.MEM_T / 2) for a in samp]
            bot = [(a, zmid(a) - P.MEM_T / 2) for a in reversed(samp)]
            if along_x:
                wpl = Plane.XZ.offset(-(wy1 + 1.0))   # площина y=wy1+1
                wamt = wy1 - wy0 + 2.0                # екструзія → wy0−1
            else:
                wpl = Plane.YZ.offset(wx0 - 1.0)
                wamt = wx1 - wx0 + 2.0
            with BuildSketch(wpl, mode=Mode.PRIVATE) as wsk:
                with BuildLine():
                    Polyline(*(top + bot + [top[0]]))
                make_face()
            wave = extrude(wsk.sketch, amount=wamt, mode=Mode.PRIVATE)
            add(prism & wave)

            # ФІНИ-плавники на верхній кромці (стеля вікна у FACE_DOWN);
            # для B найближча позиція → на вісь S3 (анкер фіна — його
            # шари вище краю ядра висіли б у повітрі).
            # 25.07: старт = ВЕСЬ конверт гофри (env0..env1) — фін
            # гарантовано зростається з мембраною, де б не була фаза
            # хвилі (для B хвиля йде вздовж y, тобто вздовж самого фіна);
            # далі перехід до повної товщі за MEM_FLAG_RUN (~7°) і
            # вросток 0.5 у тіло за кромкою.
            # (xs пораховано вище, до патерна — keep-смуги збігаються)
            y0f = wy1 - P.MEM_FLAG_RUN
            for u in xs:
                with BuildSketch(Plane.YZ.offset(u - P.MEM_FLAG_W / 2),
                                 mode=Mode.PRIVATE) as fk:
                    with BuildLine():
                        Polyline((y0f, env0), (y0f, env1),
                                 (wy1, P.INFILL_T),
                                 (wy1 + 0.5, P.INFILL_T),
                                 (wy1 + 0.5, 0.0),
                                 (wy1, 0.0),
                                 (y0f, env0))
                    make_face()
                add(extrude(fk.sketch, amount=P.MEM_FLAG_W,
                            mode=Mode.PRIVATE))

        # фіни S1/S2/S4 (collar-тип): лезо PED_FIN_T по X під нижньою
        # хордою колони (y=cy−4.5), верх з зазором PED_FIN_GAP; анкер —
        # вросток z2.5..3 у суцільний комірець ⌀17 (на x=cx±0.4 комірець
        # сягає y=cy±8.49); виїмка знизу обходить галтель-кільце
        # (кліренс ≥0.15 при z≈3.05); гіпотенуза 45° — ріст самонесучий
        rr = P.STANDOFF_D / 2
        for sname in ('S1', 'S2', 'S4'):
            cx, cy = P.STANDOFF_XY[sname]
            yt = cy - rr - P.PED_FIN_GAP             # верх = cy−4.65
            with BuildSketch(Plane.YZ.offset(cx - P.PED_FIN_T / 2)) as fsk:
                with BuildLine():
                    Polyline((cy - 8.4, 2.5), (cy - 8.4, 3.2),
                             (yt, 3.2 + (yt - (cy - 8.4))),   # 45° → 6.95
                             (yt, 4.6), (cy - 5.65, 3.6),
                             (cy - 5.65, 2.5), (cy - 8.4, 2.5))
                make_face()
            extrude(fsk.sketch, amount=P.PED_FIN_T)

        # фін S3 — membrane-тип: колона зрізана вікном B (грань зрізу
        # y=68.0, комірця під нею нема) → фін висить на гофро-мембрані:
        # пояс вростка = ПОВНИЙ конверт гофри ±0.1 (0.4..1.6 — ловить
        # хвилю на будь-якій фазі), ріст 45°, верх 0.15 під гранню
        # зрізу; шари вище краю ядра анкеряться в косинку на осі S3
        cx3 = P.STANDOFF_XY['S3'][0]
        yb = P.RAM_KEEPOUT['B']['y'][1] + 0.1 - P.PED_FIN_GAP   # 67.85
        fin_lo, fin_hi = env0 - 0.1, env1 + 0.1                 # 0.4..1.6
        with BuildSketch(Plane.YZ.offset(cx3 - P.PED_FIN_T / 2)) as f3k:
            with BuildLine():
                Polyline((yb - 5.6, fin_lo), (yb - 5.6, fin_hi),
                         (yb, fin_hi + 5.6), (yb, fin_lo),
                         (yb - 5.6, fin_lo))
            make_face()
        extrude(f3k.sketch, amount=P.PED_FIN_T)

    return tray.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "floor")
