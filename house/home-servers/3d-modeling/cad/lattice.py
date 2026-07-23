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
    """Вирізи-трикутники ІЗОГРІД (рівносторонні, сторона ISO_A) у полі
    field (u,v). Історія: 23.07 ч.1 — «ферма 45°» (стрейчені трикутники,
    нуль мостів); 23.07 ч.2 (фідбек «зроби нормальний ізогрід, на 3мм
    буде все добре») — канонічні рівносторонні.
    ОРІЄНТАЦІЯ ПІД ДРУК (u = модельний Y = вісь висоти FACE_DOWN):
    бази ЛИШЕ вздовж v (модельний Z = горизонталь друку) → діагоналі
    60° від бази = 30° від вертикалі друку (самонесучі); стелі вікон
    «вершиною вниз» = мости ~10мм (правило ≤12, стінка тепер 3.0).
    Бази вздовж u були б катастрофою: КОЖНА діагональ = навіс 60°.
    anchor_u/anchor_v — прив'язка ґратки (лівий/нижній край поля)."""
    a = P.ISO_A
    h = a * math.sqrt(3) / 2             # висота рівностороннього ряду
    ero = P.ISO_T / 2 + P.RHOMB_R
    fu0, fv0, fu1, fv1 = field.bounds
    nrow = int((fu1 - fu0) / h) + 3      # ряди вздовж u
    ncol = int((fv1 - fv0) / a) + 3      # трикутники вздовж v

    tris = []
    for row in range(-1, nrow + 1):
        u0 = anchor_u + row * h          # низ ряду (база «апекс-вгору»)
        stag = (row % 2) * a / 2         # стагер вершин через ряд
        for col in range(-1, ncol + 1):
            v0 = anchor_v + col * a + stag
            # «апекс до +u»: база на u0, вершина на u0+h
            tU = sg.Polygon([(u0, v0), (u0, v0 + a), (u0 + h, v0 + a / 2)])
            # комплементарний «апекс до −u»: база на u0+h
            tD = sg.Polygon([(u0 + h, v0 + a / 2), (u0 + h, v0 + 3 * a / 2),
                             (u0, v0 + a)])
            for tri in (tU, tD):
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
