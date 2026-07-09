"""
io_insert.py — ЗМІННА I/O-ВСТАВКА (09.07, ідея користувача: універсальність).
Панель має апертуру 1:1 під сталевий щиток; порти конкретної плати ріжуться
в цій друкованій вставці. Зміна плати = передрук вставки, не корпусу.

Конструкція (все tool-less):
  • носик = апертура −0.2/бік, товщина 1.4 (лице −0.1 від лиця панелі);
  • фланець = апертура +1.4/бік, товщина 1.4, сидить у фальці панелі
    (глибина 1.5, полиця 1.6) — кабелі тиснуть вставку в панель, фланець
    упирається в дно фальца;
  • знизу 2 ЖОРСТКІ язички (8×1.8) у кишені фальца — пряме встромляння;
  • зверху 2 ПРУЖНІ пальці (U-проріз 9×2.5 у плиті) з язичком-підйомом
    на вільному кінці та півкруглим бампом R0.6: бамп тре по стелі
    фальца (натяг 0.35, ε≈1.6%) і клацає в кишеню панелі;
  • виймання: плата знята → притиснути обидва пальці згори з тилу.
Порти (включно з TF — лише тут, у панелі його нема) — з P.IO_PORTS.
Запуск: .venv/bin/python cad/io_insert.py  → out/io_insert.step/stl
Вставка в координатах збірки; друк — лицем вниз.
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


# (⚠️ урок: helper з BuildLine усередині НЕ працює — build123d
# скоуп-чутливий, об'єкти з викликаної функції не авто-додаються
# в білдер; тому грані будуються інлайном, як у front.py)
def _polys(geom):
    if geom.geom_type == 'Polygon':
        return [geom]
    return [g for g in geom.geoms if g.geom_type == 'Polygon']


def _plans():
    """2D-плани (X,Z): (nose, flange) з портами/прорізами вже вирізаними."""
    aper = _rounded(sg.box(P.IO_X[0], P.IO_Z[0], P.IO_X[1], P.IO_Z[1]),
                    P.INS_APER_R)
    nose = aper.buffer(-P.INS_CLEAR, quad_segs=8)
    flange = aper.buffer(P.INS_REBATE_W - P.INS_CLEAR, quad_segs=8)
    # нижні жорсткі язички — частина фланця
    for xc in P.INS_TAB_XC:
        flange = flange.union(sg.box(
            xc - P.INS_TAB_W / 2, P.IO_Z[0] - 1.4 - P.INS_TAB_H,
            xc + P.INS_TAB_W / 2, P.IO_Z[0]))

    # ── пружні пальці зверху: U-прорізи (крізь ОБИДВА шари) ──
    ztop_n = P.IO_Z[1] - P.INS_CLEAR          # верх носика 49.9
    ztop_f = P.IO_Z[1] + P.INS_REBATE_W - P.INS_CLEAR   # верх фланця 51.5
    slits, lip_gaps = [], []
    for xc, xd in zip(P.INS_TAB_XC, P.INS_DIMPLE_XC):
        sgn = -1 if xc < 0 else +1            # вільний кінець назовні
        x_anchor = xc - sgn * P.INS_FING_L / 2
        x_free = xc + sgn * P.INS_FING_L / 2
        zf0 = ztop_n - P.INS_FING_H           # низ пальця 47.4
        # горизонтальний проріз під пальцем + вертикальний на кінці
        slits.append(sg.box(min(x_anchor, x_free + sgn * P.INS_SLIT_W),
                            zf0 - P.INS_SLIT_W,
                            max(x_anchor, x_free + sgn * P.INS_SLIT_W), zf0))
        slits.append(sg.box(min(x_free, x_free + sgn * P.INS_SLIT_W), zf0,
                            max(x_free, x_free + sgn * P.INS_SLIT_W),
                            ztop_f + 0.1))
        # губа фланця над пальцем зрізається до верху носика, КРІМ
        # язичка-підйому (несе бамп) — він лишається до ztop_f
        tab0 = xd - P.INS_LIP_TAB_W / 2
        tab1 = xd + P.INS_LIP_TAB_W / 2
        span = sg.box(min(x_anchor, x_free), ztop_n,
                      max(x_anchor, x_free), ztop_f + 0.1)
        lip_gaps.append(span.difference(sg.box(tab0, ztop_n, tab1,
                                               ztop_f + 0.1)))

    ports = unary_union(ioports.port_polys())

    # ── rhombille (09.07 фідбек: «зникли ромбілі — ми ж для вентиляції») —
    # та сама ґратка/фаза, що була на панелі (s7, вершини кишень на лівій
    # межі апертури) → патерн вставки продовжує патерн панелі навколо ──
    s = P.PANEL_RHOMB_S
    dxl = math.sqrt(3) * s
    dyl = 1.5 * s
    ero = P.RHOMB_T / 2 + P.RHOMB_R
    _probe = sg.Polygon([(0, 0), (-s * math.cos(math.radians(30)), -s / 2),
                         (0, -s), (s * math.cos(math.radians(30)), -s / 2)])         .buffer(-ero).buffer(P.RHOMB_R, quad_segs=8)
    tip_inset = s * math.cos(math.radians(30)) - abs(_probe.bounds[0])
    cx0 = P.IO_X[0] - tip_inset
    cz0 = P.IO_Z[1] + P.PANEL_RIM + s / 2
    port_pads = ports.buffer(1.5)          # обідок 1.5 = 3-4 периметри
    fing_pads = unary_union(
        [g.buffer(1.5) for g in slits]
        + [sg.box(xd - P.INS_LIP_TAB_W / 2 - 1.5, ztop_n - 3.0,
                  xd + P.INS_LIP_TAB_W / 2 + 1.5, ztop_f + 1)
           for xd in P.INS_DIMPLE_XC])
    field = aper.buffer(-1.7, quad_segs=8)         .difference(port_pads).difference(fing_pads)
    fb = field.bounds
    rhomb = []
    for row in range(-int((cz0 - fb[1]) / dyl) - 2, 3):
        for col in range(-3, int((fb[2] - cx0) / dxl) + 3):
            hx = cx0 + col * dxl + (row % 2) * dxl / 2
            hz = cz0 + row * dyl
            V = [(hx + s * math.cos(math.radians(a)),
                  hz + s * math.sin(math.radians(a)))
                 for a in range(90, 450, 60)]
            for k in (0, 2, 4):
                rb = sg.Polygon([(hx, hz), V[k], V[k + 1], V[(k + 2) % 6]])
                if not rb.intersects(field):
                    continue
                pk = rb.buffer(-ero).buffer(P.RHOMB_R, quad_segs=8)                        .intersection(field)
                if rb.intersects(port_pads) or rb.intersects(fing_pads):
                    pk = pk.buffer(-0.35).buffer(0.35, quad_segs=8)
                for g in (pk.geoms if pk.geom_type != 'Polygon' else [pk]):
                    if g.geom_type != 'Polygon' or g.area < 1.5                             or g.buffer(-0.45).is_empty:
                        continue
                    rhomb.append(g)
    # «волосини»: стінки тонші 0.8 біля кіл портів → у сусідній виріз
    mat = field.buffer(3.0).difference(unary_union(rhomb) if rhomb
                                       else sg.Polygon())
    hair = mat.difference(mat.buffer(-0.4).buffer(0.4, quad_segs=8))
    for c in (hair.geoms if hair.geom_type != 'Polygon' else [hair]):
        if c.geom_type == 'Polygon' and c.area < 5.0                 and c.intersects(field):
            rhomb.append(c)

    cut_all = ports.union(unary_union(slits + rhomb))
    nose_pl = nose.difference(cut_all)
    flange_pl = flange.difference(cut_all).difference(
        unary_union(lip_gaps))
    return nose_pl, flange_pl


def build():
    nose_pl, flange_pl = _plans()
    layers = ((flange_pl, 96.5, P.INS_FLANGE_T),   # фланець −96.5…−97.9
              (nose_pl, 97.9, P.INS_NOSE_T))       # носик  −97.9…−99.3
    with BuildPart() as ins:
        for plan, yoff, t in layers:
            with BuildSketch(Plane.XZ.offset(yoff)) as sk:
                for g in _polys(plan):
                    with BuildLine():
                        Polyline(*list(g.exterior.simplify(0.02)
                                       .coords)[:-1], close=True)
                    make_face()
                    for ring in g.interiors:
                        rp = sg.Polygon(ring)
                        if rp.area < 0.5:
                            continue
                        with BuildLine():
                            Polyline(*list(rp.exterior.simplify(0.02)
                                           .coords)[:-1], close=True)
                        make_face(mode=Mode.SUBTRACT)
            extrude(sk.sketch, amount=t)
        # бампи на верхівках язичків: передня половина = півциліндр R0.6
        # (рампа заходу — тре по стелі фальца), задня зрізана вертикально
        # (прямий уступ у кишеню — тримає від виштовхування назад)
        ztop_f = P.IO_Z[1] + P.INS_REBATE_W - P.INS_CLEAR
        for xd in P.INS_DIMPLE_XC:
            with Locations(Location((xd, -97.35, ztop_f), (0, 90, 0))):
                Cylinder(P.INS_BUMP_R, P.INS_LIP_TAB_W)
            with Locations((xd, (-97.35 + -96.3) / 2, ztop_f + 0.36)):
                Box(P.INS_LIP_TAB_W + 0.2, -96.3 - -97.35, 0.7,
                    mode=Mode.SUBTRACT)
    return ins.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "io_insert")
