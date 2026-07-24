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
    flange = unary_union([plate] + tabs + tips).difference(ports)         .difference(slitU)
    nose = plate.difference(ports).difference(slitU)
    # зона тоншання (виїмка з лиця): поле − обідок портів − край − пальці
    field = plate.buffer(-P.INS_FIELD_RIM, quad_segs=8)         .difference(ports.buffer(P.INS_FIELD_RIM))         .difference(unary_union(fing_keep) if fing_keep else sg.Polygon())
    return nose, flange, field


def _sketch_faces(sk_geom):
    """shapely → список готових Sketch-граней (алгебра-режим).
    Урок 09.07: BuildLine у ВИКЛИКАНІЙ функції не авто-додається у контекст
    білдера — тому будуємо Polygon-об'єкти явно, а в build() add()-имо їх."""
    out = []
    for g in _polys(sk_geom):
        if g.area < 0.3:
            continue
        coords = list(g.exterior.simplify(0.02).coords)[:-1]
        if len(coords) < 3:
            continue
        f = Polygon(*coords, align=None)
        for ring in g.interiors:
            rp = sg.Polygon(ring)
            if rp.area < 0.5:
                continue
            rc = list(rp.exterior.simplify(0.02).coords)[:-1]
            if len(rc) < 3:
                continue
            f -= Polygon(*rc, align=None)
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
