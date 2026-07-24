"""
io_insert.py — ЗМІННА I/O-ВСТАВКА (09.07, ідея користувача: універсальність).
Панель має апертуру 1:1 під сталевий щиток; порти конкретної плати ріжуться
в цій друкованій вставці. Зміна плати = передрук вставки, не корпусу.

24.07 РЕДИЗАЙН (примірка щитка+вставки на надрукованому корпусі):
  • Суцільний фальц/фланець ВИДАЛЕНІ — полиця з'їдала стінку апертури, де
    пупирки сталевого щитка мали тиснути. Тепер стінка апертури ПОВНА 3.0
    (у панелі), а вставка = ПЛИТА на всю товщину (апертура−0.2), тримається
    ДИСКРЕТНИМИ кріпленнями (2 язики знизу + 2 пружні пальці згори) у
    локальних кишенях панелі між пупирками щитка.
  • ПОЛЕ вставки ТОНШАЄ до 0.64 виїмкою З ЛИЦЯ (−99.4): у друці ROT_REAR
    порожнина зверху → поле друкується від стола БЕЗ мостів; кабельні
    обливки лягають у виїмку — «все як в оригінальній вставці».
  • 24.07 фідбек: повнотовщинна рамка ЛИШЕ по периметру вставки
    (INS_FIELD_RIM), навколо портів НЕ треба — тоншання до самих портів;
    поле знову з РОМБІЛЯМИ (наскрізна вентиляція, та сама ґратка/фаза
    s7, що на панелі — патерн продовжується; обідок 1.5 навколо портів
    лишається у ТОНКОМУ полі проти сліверів).

Тримання (схема користувача 24.07 ч.2):
  • НИЗ: 2 ЖОРСТКІ язики (8×1.8) у ЗАХОПНІ кишені (закриті −97.9/−96.3) —
    тримають в ОБИДВА боки Y;
  • ВЕРХ-тил: 2 ЖОРСТКІ зуби (INS_TAB_XC, тиловий шар, Z 49.9..51.5) у
    ніші З ТИЛУ панелі — дно ніші (−98.05) = стоп від ВИПАДІННЯ (−Y);
  • ВЕРХ-лице: 2 ПРУЖНІ наскрізні ЗУБЦІ (INS_HOOK_XC) на пальцях-балках
    (U-проріз, гнуться ВНИЗ = у площині шарів ROT_REAR) — проходять крізь
    апертуру, клацають у ніші-ЗАГЛИБЛЕННЯ НА ЛИЦІ панелі (зуб флаш з
    лицем); дно ніші (−98.1) = стоп від ПРОВАЛЮВАННЯ (+Y).
Установка КАЧАННЯМ: язики вниз у захопні кишені → докачати верх (жорсткі
зуби входять у тилові ніші; кромка апертури тисне рампу зубця, палець
прогинається вниз) → клац зубців у лицьові ніші. Виймання: плата знята →
зсередини притиснути обидва пальці вниз, качнути верх назад, підняти.
Порти (включно з TF — лише тут) — з P.IO_PORTS.
Запуск: .venv/bin/python cad/io_insert.py  → out/io_insert.step/stl
Друк — ТИЛОМ вниз (ROT_REAR): плита лягає на стіл, порожнина поля зверху.
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
    if geom.geom_type == 'Polygon':
        return [geom]
    return [g for g in geom.geoms if g.geom_type == 'Polygon']


def _plans():
    """2D-плани (X,Z): flange (тил, −96.4..−97.9), nose (лице, −97.9..−99.4),
    field (зона тоншання). Плита = апертура−0.2; язики/пальці = локальні
    виступи ЛИШЕ на тиловому шарі (у кишені панелі)."""
    aper = _rounded(sg.box(P.IO_X[0], P.IO_Z[0], P.IO_X[1], P.IO_Z[1]),
                    P.INS_APER_R)
    plate = aper.buffer(-P.INS_CLEAR, quad_segs=8)      # апертура −0.2
    ztop = P.IO_Z[1] - P.INS_CLEAR                       # верх плити 49.9
    ztop_lip = P.IO_Z[1] + P.INS_REBATE_W - P.INS_CLEAR  # язичок над апертурою 51.5

    tabs, tips, slits, fing_keep = [], [], [], []
    # нижні ЖОРСТКІ язики (виступ під нижню кромку апертури, у захопну
    # кишеню); верх боксу +1 У плиту — низ плити 5.5 (апертура−0.2), а не 5.3
    for xc in P.INS_TAB_XC:
        tabs.append(sg.box(xc - P.INS_TAB_W / 2,
                           P.IO_Z[0] - 1.4 - P.INS_TAB_H,
                           xc + P.INS_TAB_W / 2, P.IO_Z[0] + 1.0))
        # верхні ЖОРСТКІ зуби (ті ж X, лише тиловий шар): у ніші з тилу
        # панелі — дно ніші = стоп від випадіння назовні (−Y)
        tips.append(sg.box(xc - P.INS_TAB_W / 2, ztop,
                           xc + P.INS_TAB_W / 2, ztop_lip))
    # верхні ПРУЖНІ пальці-балки (несуть наскрізні зубці, що клацають у
    # ніші НА ЛИЦІ панелі): U-проріз = горизонтальний під балкою +
    # вертикальний на вільному кінці; вільний кінець НАЗОВНІ
    for xh in P.INS_HOOK_XC:
        sgn = -1 if xh < 0 else +1
        x_free = xh + sgn * (P.INS_HOOK_W / 2 + 0.25)   # 0.25 за край зубця
        x_anchor = x_free - sgn * P.INS_FING_L
        zf0 = ztop - P.INS_FING_H
        slits.append(sg.box(min(x_anchor, x_free + sgn * P.INS_SLIT_W),
                            zf0 - P.INS_SLIT_H,
                            max(x_anchor, x_free + sgn * P.INS_SLIT_W), zf0))
        slits.append(sg.box(min(x_free, x_free + sgn * P.INS_SLIT_W), zf0,
                            max(x_free, x_free + sgn * P.INS_SLIT_W),
                            ztop + 0.1))
        fing_keep.append(sg.box(min(x_anchor, x_free) - 1.0, zf0 - 1.0,
                                max(x_anchor, x_free) + 1.0, ztop + 0.1))

    ports = unary_union(ioports.port_polys())
    slitU = unary_union(slits)
    fingU = unary_union(fing_keep) if fing_keep else sg.Polygon()

    # ── rhombille (панельна ґратка/фаза s7 — патерн продовжує панель;
    # НЕ lattice.rhombille_holes: там стінковий RHOMB_S=8) ──
    s = P.PANEL_RHOMB_S
    dxl = math.sqrt(3) * s
    dyl = 1.5 * s
    ero = P.RHOMB_T / 2 + P.RHOMB_R
    _probe = sg.Polygon([(0, 0), (-s * math.cos(math.radians(30)), -s / 2),
                         (0, -s), (s * math.cos(math.radians(30)), -s / 2)])         .buffer(-ero).buffer(P.RHOMB_R, quad_segs=8)
    tip_inset = s * math.cos(math.radians(30)) - abs(_probe.bounds[0])
    cx0 = P.IO_X[0] - tip_inset
    cz0 = P.IO_Z[1] + P.PANEL_RIM + s / 2
    port_pads = ports.buffer(1.5)          # обідок 1.5 у ТОНКОМУ полі
    fing_pads = fingU.buffer(1.0)
    # патерн-зона на 0.5 углиб від рамки: кліп рівно по межі рамки давав
    # нуль-товщинну стінку виріз↔стінка виїмки поля (watertight=False)
    pat = plate.buffer(-(P.INS_FIELD_RIM + 0.5), quad_segs=8)         .difference(port_pads).difference(fing_pads)
    pb = pat.bounds
    rhomb = []
    for row in range(-int((cz0 - pb[1]) / dyl) - 2, 3):
        for col in range(-3, int((pb[2] - cx0) / dxl) + 3):
            hx = cx0 + col * dxl + (row % 2) * dxl / 2
            hz = cz0 + row * dyl
            V = [(hx + s * math.cos(math.radians(a)),
                  hz + s * math.sin(math.radians(a)))
                 for a in range(90, 450, 60)]
            for k in (0, 2, 4):
                rb = sg.Polygon([(hx, hz), V[k], V[k + 1], V[(k + 2) % 6]])
                if not rb.intersects(pat):
                    continue
                pk = rb.buffer(-ero).buffer(P.RHOMB_R, quad_segs=8)                        .intersection(pat)
                if rb.intersects(port_pads) or rb.intersects(fing_pads):
                    pk = pk.buffer(-0.35).buffer(0.35, quad_segs=8)
                for g in _polys(pk):
                    if g.area < 1.5 or g.buffer(-0.45).is_empty:
                        continue
                    rhomb.append(g)
    # «волосини»: стінки тонші 0.8 біля кіл портів → у сусідній виріз
    mat = pat.buffer(3.0).difference(unary_union(rhomb) if rhomb
                                     else sg.Polygon())
    hair = mat.difference(mat.buffer(-0.4).buffer(0.4, quad_segs=8))
    for c in _polys(hair):
        if c.area < 5.0 and c.intersects(pat):
            rhomb.append(c)
    rhombU = unary_union(rhomb) if rhomb else sg.Polygon()

    cut_all = ports.union(slitU).union(rhombU)   # ромбілі НАСКРІЗЬ (обидва шари)
    flange = unary_union([plate] + tabs + tips).difference(cut_all)
    nose = plate.difference(cut_all)
    # зона тоншання (виїмка з лиця): рамка ЛИШЕ по периметру — тоншання
    # доходить до самих країв портів (24.07 фідбек). Порти НЕ виключаємо:
    # вони вже наскрізні дірки (перекриття повітря нешкідливе), а
    # `.difference(ports)` давав стінку виїмки, збіжну з стінкою порт-
    # вирізу — два simplify() різних скетчів → сливери, watertight=False
    field = plate.buffer(-P.INS_FIELD_RIM, quad_segs=8).difference(fingU)
    return nose, flange, field


def _sketch_faces(sk_geom):
    """shapely → список готових Sketch-граней (алгебра-режим).
    ⚠️ Урок 24.07 (порти зникли!): Polygon() у ВИКЛИКАНІЙ функції при
    АКТИВНОМУ BuildSketch АВТО-ДОДАЄТЬСЯ у контекст (стек глобальний) —
    контури дірок доливались назад як ADD і вставка вийшла суцільною.
    Тому всі проміжні Polygon — з mode=Mode.PRIVATE; у build() add()-имо
    лише готові грані."""
    out = []
    for g in _polys(sk_geom):
        if g.area < 0.3:
            continue
        coords = list(g.exterior.simplify(0.02).coords)[:-1]
        if len(coords) < 3:
            continue
        f = Polygon(*coords, align=None, mode=Mode.PRIVATE)
        for ring in g.interiors:
            rp = sg.Polygon(ring)
            if rp.area < 0.5:
                continue
            rc = list(rp.exterior.simplify(0.02).coords)[:-1]
            if len(rc) < 3:
                continue
            f -= Polygon(*rc, align=None, mode=Mode.PRIVATE)
        out.append(f)
    return out


def build():
    nose_pl, flange_pl, field_pl = _plans()
    layers = ((flange_pl, 96.4, 1.5),    # тил −96.4…−97.9 (язики/пальці тут)
              (nose_pl, 97.9, 1.5))      # лице −97.9…−99.4
    with BuildPart() as ins:
        for plan, yoff, t in layers:
            with BuildSketch(Plane.XZ.offset(yoff)) as sk:
                for f in _sketch_faces(plan):
                    add(f)
            extrude(sk.sketch, amount=t)

        # ── ТОНШАННЯ ПОЛЯ: виїмка З ЛИЦЯ (−99.4) на глибину 3.0−0.64=2.36 →
        # лишається 0.64 біля тилу; у друці ROT_REAR порожнина зверху ──
        depth = P.INS_PLATE_T - P.INS_FIELD_T
        with BuildSketch(Plane.XZ.offset(99.4 - depth)) as fk:
            for f in _sketch_faces(field_pl):
                add(f)
        extrude(fk.sketch, amount=depth, mode=Mode.SUBTRACT)

        # ── НАСКРІЗНІ ЗУБЦІ на пальцях (клацають у ніші НА ЛИЦІ панелі):
        # YZ-профіль на балці; передня грань ФЛАШ з лицем (−99.4), рампа-кам
        # ~47° (низ спереду → верх ззаду: кромка апертури (−96.4, 50.1) при
        # качанні тисне рампу → палець прогинається вниз); задня грань
        # (−98.25) = стоп у дно ніші лиця; занурення 0.5 у балку ──
        ztop = P.IO_Z[1] - P.INS_CLEAR                   # верх плити 49.9
        yface = -99.4                                    # лице панелі
        yr = yface + P.INS_HOOK_LEN                      # тил зубця −98.25
        ztip = P.IO_Z[1] + P.INS_HOOK_ENG                # верх зубця 51.3
        for xh in P.INS_HOOK_XC:
            with BuildSketch(
                    Plane.YZ.offset(xh - P.INS_HOOK_W / 2)) as wk:
                with BuildLine():
                    Polyline((yface, ztop - 0.5),
                             (yface, ztip - 1.25),
                             (yr, ztip),
                             (yr, ztop - 0.5), close=True)
                make_face()
            extrude(wk.sketch, amount=P.INS_HOOK_W)
    return ins.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "io_insert")
