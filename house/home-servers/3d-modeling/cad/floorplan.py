"""
floorplan.py — 2D-розкладка заповнення дна, ПЕРЕПИСАНА З НУЛЯ (29.07,
cell-first). Замість морфологічної пост-обробки старого plan_geometry()
(opening −1.2/+1.2 + десяток латок: frame_ring, кутова латка, _zh, band,
closing, «розгін», якірний/orphan-фільтри) кожна комірка ґратки
КЛАСИФІКУЄТЬСЯ:
    HOLE  — сота-отвір (повна або опущена механікою Б);
    CROWN — комірка зони корони (перетинає пади/снап-бокси, або її
            кліпнутий фрагмент біля постаменту < STANDOFF_SOLID_R);
    SOLID — гола 2мм мембрана (коридори, крихти, пояси вікон).
Зона корони = union КОМІРОК CROWN (гекси Rcell — Вороної ґратки, тайлять
площину точно) + buffer(HEX_RIB/2 + 0.1, mitre): межа корони ЗАВЖДИ йде
по стінках сот і лініях патерну (рішення користувача «По комірках
патерну»), а перекриття 0.1 у сусідні отвори малюється ПРЯМИМИ
сторонами — пінч-вершини гексів опиняються ВСЕРЕДИНІ отворів, тож
нон-маніфолд «пісочних годинників» зникає за побудовою (зайве в отворах
зрізає наскрізний різ сот у build() → flush-стінки).
Обідок кишень 2.0 — лише від ВІЛЬНИХ меж зони (де крона стоїть на голій
мембрані), не від стінок сот: ребро сота↔кишеня = штатні 0.75+0.75=1.5.
Кишені ізогріду — правило ПОЛОВИНИ (30.07, фідбек користувача): якщо
кліп (обідком free, падом, фестоном, трамплін-смугою) закриває БІЛЬШЕ
половини трикутника патерну — кишеня НЕ ріжеться (трикутник лишається
кроною); якщо половину або менше — ріжеться кліпнута кишеня (сліверси
тонші 0.9 відкидаються). WEDGE-спецкейс ніш біля рами видалено.
Спідниця крони ВИМКНЕНА (30.07, «не вирізай ізогрід знизу над
стільниками під друк — зробимо потім»): усі рівні = повний футпринт,
межі крони Z2..3 вертикальні; механізм 45°-сходинок — у git/floor.py.
НЕ перенесено свідомо (порожні механізми; реактивація — через git):
ISO_FILL_XY (залиті соти), CROWN_TRIM_XY/pocket_blunt (притуплення).
Інтерфейс 1:1 зі старим: plan_geometry() → (holes, crown_polys,
pockets, skirt).
"""
import math
import shapely.geometry as sg
from shapely import set_precision
from shapely.ops import unary_union
from shapely.affinity import translate
import params as P

SKIRT_N = 10          # сходинок 45°-спідниці крони (h = TRI_RIB_H/N = 0.1)
FILL_C = ((6, 4),)    # явні заливки комірок → 'C' (30.07 ч.2: «пустота у
                      # верхньому правому кутку, хоча нижче є гратка
                      # ізогріду — заповни і той кут також»)


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
    """Повертає (holes, crown_polys, pockets, skirt):
       holes — отвори сот у 2мм шарі, crown_polys — шар +1мм (крона),
       pockets — наскрізні кишені ізогріду, skirt — рівні 45°-спідниці."""
    Rc = P.HEX_AF / math.sqrt(3)               # circumradius соти-отвору
    dx = P.HEX_AF + P.HEX_RIB                  # крок ґратки
    dy = dx * math.sin(math.radians(60))
    Rcell = dx / math.sqrt(3)                  # circumradius КОМІРКИ (соти+піврібра)
    x0, y0, x1, y1 = interior_box()
    interior = _rounded(sg.box(x0, y0, x1, y1), P.FRAME_CORNER_R)
    # мікрофаза 0.11 X/Y — розбиває точні збіги стінок патерну з гранями
    # інших операторів (історія 08.07 / 24.07), функційно нейтральна
    cx0, cy0 = (x0 + x1) / 2 + 0.11, (y0 + y1) / 2 + 0.11
    # пади: постаменти ⌀24 + симетричні снап-бокси комірок сітки аддонів
    pads = unary_union(
        [sg.Point(x, y).buffer(P.STANDOFF_PAD_D / 2, 48)
         for x, y in P.STANDOFF_XY.values()]
        + [sg.box(cx - P.SNAP_SLOT_X / 2 - P.ANCHOR_PAD_RIM,
                  ry - P.SNAP_TOOTH_POCKET_Y - P.ANCHOR_PAD_RIM,
                  cx + P.SNAP_SLOT_X / 2 + P.ANCHOR_PAD_RIM,
                  ry + P.SNAP_TOOTH_POCKET_Y + P.ANCHOR_PAD_RIM)
           for cx in P.ANCHOR_COLS for ry in P.ANCHOR_ROWS])
    windows = unary_union([_rounded(sg.box(k['x'][0], k['y'][0],
                                           k['x'][1], k['y'][1]),
                                    P.RAM_WIN_R)
                           for k in P.RAM_KEEPOUT.values()])

    # flat-top гекс (24.07): у FACE_DOWN верх отвору = короткий міст,
    # бічні грані 60° від горизонталі — самонесучі
    def hexp(cx, cy, R):
        return sg.Polygon([(cx + R * math.cos(math.radians(a)),
                            cy + R * math.sin(math.radians(a)))
                           for a in range(60, 420, 60)])

    # ── коридори вікно↔рама (зазор < GAP_FILL): суцільні 2мм ──
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

    allowed = interior.difference(windows.buffer(P.RAM_WIN_RIM))
    full_hex_area = _rounded(hexp(0, 0, Rc), P.HEX_CORNER_R).area
    # смуга під трампліном бортика — суцільна (підошва дуги від 98.4)
    ramp_strip = sg.box(P.WALL_L_X + P.BEAD_W - 0.5, 98.4,
                        P.WALL_R_IN + 0.4, 104.0)

    # ── ПРОХІД ҐРАТКИ: класифікація комірок ──
    # (транспонована під flat-top: колонки по X крок dy, центри по Y
    # крок dx, стагер dx/2 через колонку)
    ncol = int((x1 - x0) / dy) + 3
    nrow = int((y1 - y0) / dx) + 3
    cells = []                                  # усі центри (для трикутників)
    cellmap = {}                                # (col,row) → запис комірки
    for row in range(-nrow, nrow + 1):
        for col in range(-ncol, ncol + 1):
            hx = cx0 + col * dy
            hy = cy0 + row * dx + (col % 2) * dx / 2
            cells.append((hx, hy))
            h = hexp(hx, hy, Rc)
            if not h.intersects(interior):
                continue
            if h.intersects(pads):
                # зона постаменту/снап-пада — крона, пів-комірки заборонені
                cellmap[(col, row)] = {'c': (hx, hy), 'cls': 'C', 'pad': True}
                continue
            hr = _rounded(h, P.HEX_CORNER_R)
            # механіка Б (27.07): сота під вікном, чий флет-топ пірнає у
            # пояс RIM+CLR, ОПУСКАЄТЬСЯ (∩ self-зсунута-вниз) — стеля
            # лишається власним флет-топом, отвір менший але живий
            ty = hy + Rc * math.sin(math.radians(60))
            for k in P.RAM_KEEPOUT.values():
                wx0, wx1 = k['x']; wy0 = k['y'][0]
                lim = wy0 - (P.RAM_WIN_RIM + P.FILL_RETREAT)
                if (hy < wy0 and ty > lim
                        and hx + Rc / 2 > wx0 - 1.5
                        and hx - Rc / 2 < wx1 + 1.5):
                    hr = hr.intersection(
                        translate(hr, yoff=-(ty - lim + 0.05)))
            hc = hr.intersection(allowed).difference(ramp_strip)
            kept, near = [], False
            for g in _polys(hc):
                if g.intersects(corridors):
                    continue                    # коридор → фрагмент суцільний
                crumb = g.area < 10.0 or g.buffer(-0.6).is_empty
                clipped = crumb or g.area < full_hex_area - 0.5
                if clipped and min(g.distance(sg.Point(px, py))
                                   for px, py in P.STANDOFF_XY.values()) \
                        < P.STANDOFF_SOLID_R:
                    near = True                 # кліпнутий біля постаменту
                    continue
                if crumb:
                    continue
                kept.append(g)
            if kept:
                cellmap[(col, row)] = {'c': (hx, hy), 'cls': 'H',
                                       'kept': kept}
            elif near:
                cellmap[(col, row)] = {'c': (hx, hy), 'cls': 'C',
                                       'pad': False}
            else:
                cellmap[(col, row)] = {'c': (hx, hy), 'cls': 'S'}

    # ── ПІВ-КОМІРКИ (30.07, схема користувача зі скріншота): вертикальний
    # стик «крона прямо над сотою» = стеля соти (міст у FACE_DOWN) несла б
    # ізогрід — нависання. Комірка-стик розрізається по вершинній
    # діагоналі ±60° через центр (= лінія патерну, ребра трикутників —
    # ділить 6 трикутників рівно 3+3): ВЕРХНЯ половина — ізогрід (стик
    # із кроною), НИЖНЯ — пів-сота; діагональ 30° від вертикалі друку —
    # самонесуча, «жодних нависань». Два випадки: (а) крона-«палець»
    # (≤2 сусідів-крон) над отвором → зрізати нижню половину («чорна
    # лінія»); (б) отвір із кроною прямо зверху → ПОВНИЙ ізогрід
    # («червоні кола»; фідбек 30.07 — нові додаємо повними, HALF лише
    # для зрізу пальця). Pad-комірка демотується лише якщо є діагональ,
    # де пів-отвір не чіпає pads (ізогрід-половина покриває пад).
    def _halfplane(px, py, ang, s, off=0.0):
        """Півплощина від лінії під кутом ang через (px,py); s — бік
           (нормаль (-sin,cos)·s), off — відступ бази у бік s."""
        ux, uy = math.cos(math.radians(ang)), math.sin(math.radians(ang))
        nx, ny = -uy * s, ux * s
        bx, by = px + nx * off, py + ny * off
        L = 40.0
        return sg.Polygon([(bx - ux * L, by - uy * L),
                           (bx + ux * L, by + uy * L),
                           (bx + (ux + nx) * L, by + (uy + ny) * L),
                           (bx + (nx - ux) * L, by + (ny - uy) * L)])

    def _nbrs(px, py):
        return [r for r in cellmap.values()
                if 0.1 < math.hypot(r['c'][0] - px, r['c'][1] - py)
                < dx + 0.5]

    # (а) демоції пальців — ПЕРШИМИ (щоб (б) не заливала соти під ними).
    # Pad-комірка демотується ЛИШЕ якщо її пів-отвір (нижня половина з
    # відступом 0.75) не чіпає pads — ізогрід-половина покриває пад.
    for (col, row), rec in list(cellmap.items()):
        if rec['cls'] != 'C':
            continue
        below = cellmap.get((col, row - 1))
        if not below or below['cls'] != 'H':
            continue
        if sum(1 for r in _nbrs(*rec['c']) if r['cls'] == 'C') > 2:
            continue                            # не «палець» — масив крони
        if rec.get('pad'):
            hx, hy = rec['c']
            ok = [(ang, s) for ang, s in ((60.0, 1), (120.0, -1))
                  if hexp(hx, hy, Rc).intersection(
                      _halfplane(hx, hy, ang, -s, P.TRI_RIB_W / 2))
                  .intersection(pads).is_empty]
            if not ok:
                continue                        # пад лізе в обидва пів-отвори
            rec['diag_ok'] = tuple(ok)
        rec['cls'] = 'HALF'
    # (б) заливки (фідбек 30.07: «ті, що додаємо нові, мають бути
    # повними») — сота з кроною ПРЯМО зверху → ПОВНИЙ ізогрід; зрізаний
    # лишається лише палець (а). Снапшот was_C — без каскаду вниз по
    # колонці (нижчі соти бачать СТАРІ класи, не щойно підвищені).
    was_C = {k for k, r in cellmap.items() if r['cls'] == 'C'}
    for (col, row), rec in cellmap.items():
        if rec['cls'] != 'H':
            continue
        if (col, row + 1) in was_C:
            rec['cls'] = 'C'
            rec['kept'] = []
    # (в) явні заливки FILL_C (кут при масиві ізогріду знизу/збоку)
    for key in FILL_C:
        rec = cellmap.get(key)
        if rec and rec['cls'] == 'H':
            rec['cls'] = 'C'
            rec['kept'] = []
    # (г) чорне коло 30.07 ч.2 («так само половину треба зробити»):
    # сота, що ЛИШИЛАСЬ 'H' під повною кроною ПІСЛЯ промоцій (б)/(в)
    # (снапшот was_C блокував каскад — це рівно соти під щойно-повними
    # ізогрідами) → HALF: верх пів-ізогрід під кроною, низ пів-сота.
    # Каскаду далі нема: під HALF крони на стелі соти немає.
    for (col, row), rec in cellmap.items():
        if rec['cls'] == 'H' \
                and cellmap.get((col, row + 1), {}).get('cls') == 'C':
            rec['cls'] = 'HALF'
    # діагональ (60°/120°) — скорингом суміжності ізогрідної половини з
    # сусідами-кронами; пів-отвір = гекс Rc ∩ півплощина соти з відступом
    # 0.75 від лінії → ребро пів-сота↔кишені = штатні 1.5 патерну
    for rec in cellmap.values():
        if rec['cls'] != 'HALF':
            continue
        hx, hy = rec['c']
        best = None
        # ізогрід — верхня половина; pad-комірка обмежена diag_ok
        for ang, s in rec.get('diag_ok', ((60.0, 1), (120.0, -1))):
            iso = hexp(hx, hy, Rcell).intersection(
                _halfplane(hx, hy, ang, s))
            score = sum(iso.buffer(0.2).intersection(
                            hexp(r['c'][0], r['c'][1], Rcell)).area
                        for r in _nbrs(hx, hy) if r['cls'] == 'C')
            if best is None or score > best[0]:
                best = (score, ang, s)
        rec['ang'], rec['side'] = best[1], best[2]
        hh = hexp(hx, hy, Rc).intersection(
            _halfplane(hx, hy, best[1], -best[2], P.TRI_RIB_W / 2))
        hh = _rounded(hh, P.HEX_CORNER_R) \
            .intersection(allowed).difference(ramp_strip)
        rec['kept'] = [g for g in _polys(hh)
                       if not g.intersects(corridors)
                       and g.area > 10.0 and not g.buffer(-0.6).is_empty]

    # ── збірка з cellmap: отвори + частини зони корони ──
    holes = []
    zone_parts = []
    for rec in cellmap.values():
        hx, hy = rec['c']
        if rec['cls'] in ('H', 'HALF'):
            holes.extend(rec.get('kept', []))
        if rec['cls'] == 'C':
            zone_parts.append(hexp(hx, hy, Rcell))
        elif rec['cls'] == 'HALF':
            zone_parts.append(hexp(hx, hy, Rcell).intersection(
                _halfplane(hx, hy, rec['ang'], rec['side'])))

    # ── острівці мембрани (не тримаються ні рами, ні падів) → у порожнечу ──
    voids = unary_union([unary_union(holes), windows])
    solid = interior.difference(voids)
    rim = interior.exterior.buffer(0.05)
    islands = [c for c in _polys(solid)
               if not (c.intersects(rim) or c.intersects(pads))]
    holes.extend(islands)

    # ── belt-трим: обідок RIM+CLR навколо вікон = чиста мембрана ──
    _clr = P.FILL_RETREAT
    _belt = windows.buffer(P.RAM_WIN_RIM + _clr)
    holes_fin = [g for h in holes for g in _polys(h.difference(_belt))
                 if g.area > 10.0 and not g.buffer(-0.6).is_empty]
    hu_fin = unary_union(holes_fin)

    # ── фестони-трапеції (28.07): смуга CLR над флет-топом кожної соти —
    # межа крони колінеарна діагональним стінкам 60° (лінія патерну) ──
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
        fy0 = ty - 1.5
        fy1 = min(ty + top_h, ty + (xr - xl) / 2 * _slope60 - 0.05)
        if fy1 <= ty - 0.1:
            continue
        f = sg.Polygon([
            (xl + (fy0 - ty) / _slope60, fy0),
            (xr - (fy0 - ty) / _slope60, fy0),
            (xr - (fy1 - ty) / _slope60, fy1),
            (xl + (fy1 - ty) / _slope60, fy1)]).buffer(0)
        fr = f.buffer(-0.6, quad_segs=8).buffer(0.6, quad_segs=8)
        fest.append(fr if not fr.is_empty else f)
    fest = unary_union(fest) if fest else sg.Polygon()

    # ── ЗОНА КОРОНИ: union комірок CROWN, межа по лініях патерну ──
    # Rcell-гекси тайлять площину точно → межа union іде серединою
    # ребра; buffer +(HEX_RIB/2 + 0.1) mitre зсуває її ПРЯМИМИ
    # сторонами на 0.1 УСЕРЕДИНУ сусідніх отворів (перекриття, flush
    # зрізає наскрізний різ сот у build()); у раму зона заходить на 2.0
    # (верх крони Z3 = верх рами, перекриття тоне в рамі)
    # (частини зони зібрані вище з cellmap: повні гекси C + верхні
    # половини HALF — діагональ теж отримує перекриття 0.1 у пів-отвір)
    # смуга під трампліном — КРОНА ЗА ОЗНАЧЕННЯМ (30.07, дефект №2:
    # комірки, з'їдені ramp_strip до крихт, ставали 'S', а в непарних
    # колонках верхній ряд узагалі поза cellmap → клаптики 2мм мембрани
    # між кроною і рамою; смуга суцільна 3мм, зливається із задньою рамою).
    # У zone_parts смуга ОПУЩЕНА на HEX_RIB нижче підошви (96.9): інакше
    # буферені межі смуги (98.4−0.85=97.55) і C-комірок останнього ряду
    # (96.41+0.85=97.26) розходяться на 0.29 → слівер-щілина 2мм мембрани
    # там, де верхній ряд ґратки 'S' (x≈123.5..129.9). Глибший старт
    # безпечний: claim нижче обрізає смугу по лініях патерну над живими
    # сотами. Змінну ramp_strip НЕ чіпати — вона в класифікації hc
    # і pocket_region (кишені кронами смуги не ріжуться).
    zone_parts.append(sg.box(P.WALL_L_X + P.BEAD_W - 0.5, 98.4 - P.HEX_RIB,
                             P.WALL_R_IN + 0.4, 104.0))
    zone = unary_union(zone_parts)
    zone = zone.buffer(P.HEX_RIB / 2 + 0.1, join_style='mitre')
    zone = zone.intersection(interior.buffer(2.0))
    # різи вільних меж (1:1 зі старого):
    # відступ від RAM-вікон — модуль сідає у вікно, +1мм не має тертись
    zone = zone.difference(windows.buffer(0.5))
    # пояси під вікнами: RIM+CLR — чиста 2мм мембрана (механіка Б)
    _bw = P.RAM_WIN_RIM + P.FILL_RETREAT + 0.6
    for k in P.RAM_KEEPOUT.values():
        kx0, kx1 = k['x']; ky0 = k['y'][0]
        zone = zone.difference(sg.box(kx0 - _bw, ky0 - _bw, kx1 + _bw, ky0))
    # смужка МІЖ RAM-вікнами (модулі прилягають, звисають до Z2.55)
    _ra, _rb = P.RAM_KEEPOUT["A"], P.RAM_KEEPOUT["B"]
    zone = zone.difference(sg.box(_rb["x"][1] - 0.2, _ra["y"][0],
                                  _ra["x"][0] + 0.2, _ra["y"][1]))
    # коридори вікно↔рама — гладенькі 2мм
    zone = zone.difference(corridors)
    # «СОТИ ЗАБИРАЮТЬ СВОЇ РЕБРА» (30.07, дефект №1: buffer +0.85 зони
    # накривав нижнє горизонтальне ребро отвору сусідньої H-соти цілком
    # → ребро ставало 3мм кроною; правила (б)/(г) покривали лише «C над
    # H», а «H над C» — ні). Claim = живі отвори H-комірок + буфер
    # HEX_RIB → межа крони лягає РІВНО на лінію патерну наступної
    # комірки (9.0+1.5 = 10.5 = край сусіднього отвору), ребро
    # кожної живої соти = 1.5 з усіх боків. HALF-пів-отвори НЕ клеймлять
    # (клейм відсунув би крону на 0.75 ЗА центр-лінію діагоналі замість
    # перекриття 0.1 — затверджений діагональний стик зруйнувався б).
    hex_ribs = unary_union([g for r in cellmap.values() if r['cls'] == 'H'
                            for g in r.get('kept', [])])
    zone = zone.difference(hex_ribs.buffer(P.HEX_RIB, quad_segs=8))
    # ramp_strip у зоні ЗА ОЗНАЧЕННЯМ (лише кишені його виключають)

    # ── кишені ізогріду ──
    inset = P.TRI_RIB_W / 2
    # суцільний комірець ⌀17 під колоною + снап-пади: кишені не ріжемо
    keep_r = P.STANDOFF_COLLAR_D / 2
    base_keep = unary_union(
        [sg.Point(x, y).buffer(keep_r, 48)
         for x, y in P.STANDOFF_XY.values()]
        + [sg.box(cx - P.SNAP_SLOT_X / 2 - P.ANCHOR_PAD_RIM,
                  ry - P.SNAP_TOOTH_POCKET_Y - P.ANCHOR_PAD_RIM,
                  cx + P.SNAP_SLOT_X / 2 + P.ANCHOR_PAD_RIM,
                  ry + P.SNAP_TOOTH_POCKET_Y + P.ANCHOR_PAD_RIM)
           for cx in P.ANCHOR_COLS for ry in P.ANCHOR_ROWS])
    # обідок 2.0 — лише від ВІЛЬНИХ меж зони (крона на голій мембрані:
    # вікна/пояси/коридори/межі до SOLID-комірок); межі вздовж стінок
    # сот (лежать 0.1 всередині отворів) — НЕ вільні → ребро
    # сота↔кишеня = штатні 1.5 патерну
    free = zone.boundary.intersection(interior.buffer(-0.05)) \
               .difference(hu_fin.buffer(0.2))
    pocket_region = zone.intersection(interior) \
                        .difference(free.buffer(2.0)) \
                        .difference(base_keep).difference(ramp_strip) \
                        .difference(fest)
    # кишеня — правило ПОЛОВИНИ (30.07, фідбек «повна або жодної не
    # влаштовує… якщо більше половини отвору закрите — не ріжемо, якщо
    # половина або менше — ріжемо»): кліп (обідком free, падом,
    # фестоном, трамплін-смугою) закриває >50% трикутника → крона;
    # інакше ріжеться КЛІПНУТА кишеня. Сліверси (фрагменти тонші 0.9
    # або < 2 мм²) відкидаються — фільтр-прецедент 17.07 ч.2 #4.
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
                    .buffer(P.HEX_CORNER_R, quad_segs=8)
            if pk.is_empty:
                continue
            cut = pk.intersection(pocket_region)
            if cut.area < 0.5 * pk.area:
                continue                        # >половини закрито → крона
            for g in _polys(cut):
                if g.area > 2.0 and not g.buffer(-0.45).is_empty:
                    pockets.append(set_precision(g, 0.01))

    # кишені під нижніми дотичними комірця ⌀17 — геть (вістря дуги
    # мусить мати повну опору в FACE_DOWN, 28.07)
    _tang = [sg.Point(x, y - keep_r) for x, y in P.STANDOFF_XY.values()]
    pockets = [p for p in pockets
               if all(t.distance(p) > 0.3 for t in _tang)]
    crown = set_precision(zone.difference(unary_union(pockets)), 0.01)

    # WEDGE-спецкейс «ніш ноги біля рами» ВИДАЛЕНО (30.07): нашарування
    # фіксів давало «дефектні вирізи» біля фронту (фідбек #2); тепер
    # зону біля рами покриває загальне правило «кишеня цілком або ніяк».
    # фестони ріжуть КРОНУ (не соти); комірці/снап-пади недоторкані
    crown = crown.difference(fest.difference(base_keep))

    crown_polys = [g for g in _polys(crown) if g.area > 3.0]
    # соти віддаються ЯК Є (belt-trimmed holes_fin)
    holes = [g for h in holes_fin for g in _polys(set_precision(h, 0.01))
             if g.area > 1.0]
    # ребра останнього ряду сот (y≈98.09) — без ізогріду (28.07)
    _no_iso = unary_union([sg.box(x - 4.5, 95.6, x + 4.5, 100.6)
                           for x in (-41.18, -6.98, 27.60, 62.14)])
    pockets = [p for p in pockets if not p.intersects(_no_iso)]

    # ── футпринт СПІДНИЦІ крони (45° сходинками, дирекційна) ──
    _cu = unary_union(crown_polys)
    fp = unary_union(crown_polys + pockets)
    fp = fp.union(fp.buffer(1.2, quad_segs=8).difference(interior))
    fp = fp.union(fp.buffer(1.2, quad_segs=8).intersection(hu_fin))
    # фестонні смуги вливаються у футпринт: рампа ВІД краю соти
    if not fest.is_empty:
        fp = fp.union(unary_union(
            [f for f in _polys(fest) if f.intersects(fp)]))
    fp = unary_union([g for g in _polys(set_precision(fp, 0.01))
                      if g.area > 3.0 and g.intersects(_cu)])
    # спідниця ВИМКНЕНА (30.07, вказівка користувача: «не вирізай
    # ізогрід знизу над стільниками під друк — зробимо потім»):
    # усі рівні = повний футпринт → крона Z2..3 з вертикальними межами.
    # Механізм дирекційних 45°-сходинок (translate-∩ + keep-зони J/
    # трамплін/фестони) — у git та старому floor.py.
    fp_polys = [g for g in _polys(set_precision(fp, 0.01)) if g.area > 3.0]
    skirt = [fp_polys for _ in range(SKIRT_N)]
    return holes, crown_polys, pockets, skirt
