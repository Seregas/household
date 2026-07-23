"""
lattice.py — спільний генератор rhombille-вирізів (tumbling blocks) для
панелі та стінок. Фазові прив'язки — за рецептами, узгодженими на панелі:
  • нижня межа поля проходить по «талії» нижніх ромбів → ряд трикутничків
  • вершини КИШЕНЬ цілих ромбів лягають на передню/ліву межу (tip_inset)
Чистки: «циглики» (висячі фрагменти ребер, contacts<=1) і «волосини»
(стінки матеріалу < ~0.6мм) вливаються у вирізи.
"""
import math
import shapely.geometry as sg
from shapely.ops import unary_union
import params as P


def _polys(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    if geom.geom_type in ('MultiPolygon', 'GeometryCollection'):
        return [g for g in geom.geoms if g.geom_type == 'Polygon']
    return []


def tip_inset():
    """Відступ вершини кишені від вершини ромба (ребро з'їдає кінчик)."""
    s = P.RHOMB_S
    ero = P.RHOMB_T / 2 + P.RHOMB_R
    probe = sg.Polygon([(0, 0), (-s * math.cos(math.radians(30)), -s / 2),
                        (0, -s), (s * math.cos(math.radians(30)), -s / 2)]) \
        .buffer(-ero).buffer(P.RHOMB_R, quad_segs=8)
    return s * math.cos(math.radians(30)) - abs(probe.bounds[0])


def _cleanup(field, holes):
    """Спільні чистки: «циглики» (висячі фрагменти ребер, contacts<=1)
    і «волосини» (стінки матеріалу < ~0.6мм) вливаються у вирізи."""
    holes = list(holes)
    holesU = unary_union(holes)
    ctx = field.buffer(3.0).difference(holesU)
    # «циглики»: тонкі висячі фрагменти ребер
    opened = ctx.buffer(-0.65).buffer(0.65, quad_segs=8)
    skinny = ctx.difference(opened)
    for c in _polys(skinny):
        if c.area >= 10.0 or not c.intersects(field):
            continue
        contacts = len(_polys(c.buffer(0.05).intersection(opened)))
        if contacts <= 1:
            holes.append(c)
    # «волосини»: стінки тонші ~0.6мм
    mat = field.buffer(3.0).difference(unary_union(holes))
    hair = mat.difference(mat.buffer(-0.4).buffer(0.4, quad_segs=8))
    holes.extend([c for c in _polys(hair)
                  if c.area < 5.0 and c.intersects(field)])
    return holes


def iso_holes(field, anchor_u, anchor_v):
    """Вирізи-трикутники «ферма» (стрейчений ізогрід) у полі field (u,v).
    23.07: заміна ромбілів на стінках — стелі ромбів у FACE_DOWN були
    міні-мостами в одну стінку (задирання кінців → сопло розхитує лезо).
    Геометрія під друк: ВЕРТИКАЛЬНІ ребра вздовж u (модельний Y = вісь
    друку FACE_DOWN → стоять вертикально) довжиною ISO_A; апекси на
    сусідніх колонках через ISO_W=ISO_A/2 → діагоналі РІВНО 45° (Δu=Δv)
    — жодного моста і жодного навісу >45°.
    anchor_u/anchor_v — прив'язка ґратки (лівий/нижній край поля)."""
    a = P.ISO_A
    w = P.ISO_W
    ero = P.ISO_T / 2 + P.RHOMB_R
    fu0, fv0, fu1, fv1 = field.bounds
    ncol = int((fv1 - fv0) / w) + 3
    nrow = int((fu1 - fu0) / a) + 3

    tris = []
    for col in range(-1, ncol + 1):
        v0 = anchor_v + col * w          # база колонки (вертикальна лінія)
        stag = (col % 2) * a / 2         # стагер вершин через колонку
        for row in range(-1, nrow + 1):
            u0 = anchor_u + row * a + stag
            # правий трикутник: база на v0, апекс на v0+w
            tR = sg.Polygon([(u0, v0), (u0 + a, v0), (u0 + a / 2, v0 + w)])
            # лівий (комплементарний): база на v0+w, апекс на v0
            tL = sg.Polygon([(u0 + a / 2, v0 + w), (u0 + 3 * a / 2, v0 + w),
                             (u0 + a, v0)])
            for tri in (tR, tL):
                if not tri.intersects(field):
                    continue
                pk = tri.buffer(-ero).buffer(P.RHOMB_R, quad_segs=8) \
                        .intersection(field)
                for g in _polys(pk):
                    if g.area < 1.5 or g.buffer(-0.45).is_empty:
                        continue
                    tris.append(g)
    return _cleanup(field, tris)


def rhombille_holes(field, anchor_u, anchor_v):
    """Вирізи-ромби у полі field (координати (u,v), pointy-top по v).
    anchor_u — лінія, на яку лягають вершини цілих ромбів (tip-align);
    anchor_v — нижня межа, по «талії» нижніх ромбів (ряд трикутничків).
    Повертає список shapely-полігонів (вирізи + чистки)."""
    s = P.RHOMB_S
    dx = math.sqrt(3) * s
    dy = 1.5 * s
    ero = P.RHOMB_T / 2 + P.RHOMB_R
    cu0 = anchor_u - tip_inset()
    cv0 = anchor_v + s / 2
    fu0, fv0, fu1, fv1 = field.bounds
    ncol = int((fu1 - fu0) / dx) + 3
    nrow = int((max(fv1 - cv0, cv0 - fv0)) / dy) + 3

    rhomb = []
    for row in range(-nrow, nrow + 1):
        for col in range(-ncol, ncol + 1):
            hu = cu0 + col * dx + (row % 2) * dx / 2
            hv = cv0 + row * dy
            V = [(hu + s * math.cos(math.radians(a)),
                  hv + s * math.sin(math.radians(a)))
                 for a in range(90, 450, 60)]
            for k in (0, 2, 4):
                rb = sg.Polygon([(hu, hv), V[k], V[k + 1], V[(k + 2) % 6]])
                if not rb.intersects(field):
                    continue
                pk = rb.buffer(-ero).buffer(P.RHOMB_R, quad_segs=8) \
                       .intersection(field)
                for g in _polys(pk):
                    if g.area < 1.5 or g.buffer(-0.45).is_empty:
                        continue
                    rhomb.append(g)

    return _cleanup(field, rhomb)
