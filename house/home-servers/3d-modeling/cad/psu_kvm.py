"""
psu_kvm.py — 1U юніт «Flex-БЖ + JetKVM» для 10" Lab-RAX (254×44.45, глибина 52).

Компонування (узгоджено 2026-07-13):
  • БЖ ВПРИТУЛ ВЛІВО: тунель-комір з flex-atx-psu-single (ДРУКОВАНИЙ еталон,
    ENP-7660B сів): внутр. 82.3×41.5, стінки 1.7/1.475, глибина труби 49.
    Без гвинтів (тертя коміра, як у референсі). Розʼєм IEC зліва, кулер справа.
  • JetKVM ВПРИТУЛ ВПРАВО: колиска jetkvm-«Module Short Left Mount» 1:1,
    ПОВЕРНУТА на 180° (Rx180: left-mount → right-mount, безель вперед,
    фланець зі слотами до правої стійки).
  • Вушка/слоти Lab-RAX — з params.py (крок звірений, друкований на tray),
    для 1U — перші три пари слотів.
  • Полегшення: rhombille s7/t1.2 (lattice.py) — стінки тунелю + середина панелі.

Координати: X 0..254 (право глядача +), Y 0..44.45 (вгору), Z: фронт 0,
тіло вглиб −Z (глядач дивиться з +Z). Друк лицем на стіл.

Запуск: .venv/bin/python cad/psu_kvm.py → out/psu_kvm.stl
"""
import numpy as np
import trimesh
import shapely.geometry as sg
import shapely.affinity as sa
from shapely.ops import unary_union
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from lattice import rhombille_holes

DIR = os.path.dirname(__file__)
OUT = os.path.join(DIR, "..", "out")
KVM_REF = os.path.join(DIR, "..", "references",
                       "jetkvm-obj_1_1x Module Short Left Mount.stl")
PSU_REF = os.path.join(DIR, "..", "references", "flex-atx-psu-single.stl")

# ── габарити юніта ──────────────────────────────────────────────────────
W, H = 254.0, 44.45          # по вушках × 1U
PANEL_T = 3.0                # фронт-плита
BODY_X0, BODY_X1 = 16.5, 237.5   # тіло 221 (просвіт Lab-RAX 222.25, як tray)
CORNER_R = 2.0

# вушка Lab-RAX (звірено з params.py tray: центр слота 8.0 від краю, W 6.6)
EAR_SLOT_XC = (8.0, W - 8.0)
EAR_SLOT_W = 6.6
EAR_SLOT_Y = [(2.7, 12.5), (15.6, 28.4), (31.1, 40.9)]   # перші 3 пари (1U)

# ── тунель БЖ (еталон: комір flex-single, внутр. 82.3×41.5, глибина 49) ─
PSU_IN_W, PSU_IN_H = 82.3, 41.5
PSU_WALL_S = 1.7                      # бічні стінки (з еталона)
PSU_DEPTH = 49.0                      # глибина труби (з еталона)
PSU_X0 = BODY_X0                      # впритул вліво
PSU_OUT_W = PSU_IN_W + 2 * PSU_WALL_S     # 85.7
PSU_X1 = PSU_X0 + PSU_OUT_W               # 102.2
PSU_IY0 = (H - PSU_IN_H) / 2              # 1.475 (верх/низ стінки)
PSU_Z0, PSU_Z1 = -PANEL_T - PSU_DEPTH, -PANEL_T   # -52..-3
# губа лиця (з еталона): вікно 77.1×38 + 4 болтові отвори Ø4 (болти лиця
# Flex: пара біля IEC + нижній ряд) + кліренси; глибина губи 1.0
PSU_LIP_T = 1.0
PSU_REF_ROT = 42.602                  # еталон повернуто у площині (друк-розкладка)
PSU_REF_LUM = (17.2, 1.2, 99.5, 42.7)  # просвіт коміра у випрямленому еталоні

# ── колиска JetKVM (референс 87.19×44.45×33.16, безель Z0..3.2) ─────────
KVM_W, KVM_D = 87.19, 33.16
KVM_X1 = BODY_X1                      # впритул вправо
KVM_X0 = KVM_X1 - KVM_W               # 150.31

# ── полегшення ──────────────────────────────────────────────────────────
FRAME = 4.0                # рамки полів
EPS = 1.0


def _polys(geom):
    if geom.is_empty:
        return []
    if geom.geom_type == 'Polygon':
        return [geom]
    return [g for g in geom.geoms if g.geom_type == 'Polygon']


def _stadium(xc, y0, y1, w):
    """Вертикальний слот-стадіон (заокруглені кінці)."""
    return sg.LineString([(xc, y0 + w / 2), (xc, y1 - w / 2)]).buffer(w / 2)


def _prism(poly, z0, z1):
    p = trimesh.creation.extrude_polygon(poly, z1 - z0)
    p.apply_translation([0, 0, z0])
    return p


def psu_window():
    """Вікно-губа БЖ 1:1 з друкованого еталона (переріз лиця z=LIP/2):
    рамка-губа з отворами Ø4 під болти лиця Flex + кліренси головок.
    Мапінг = flipY випрямленого кадру. Орієнтацію дав КОРИСТУВАЧ
    скріншотом FreeCAD (вид «Знизу» = погляд на лице, деталь у файлі
    лежить лицем униз): вушко зліва, ряд з 4 отворів уздовж ВЕРХНЬОЇ
    кромки вікна, один отвір справа внизу."""
    ref = trimesh.load(PSU_REF, force='mesh')
    ref.apply_translation(-ref.bounds[0])
    ref.apply_transform(trimesh.transformations.rotation_matrix(
        np.radians(PSU_REF_ROT), [0, 0, 1]))
    ref.apply_translation(-ref.bounds[0])
    s = ref.section(plane_origin=[0, 0, PSU_LIP_T / 2], plane_normal=[0, 0, 1])
    pts = max((s.vertices[e.points][:, :2] for e in s.entities), key=len)
    win = sg.Polygon(pts).buffer(0)
    # мапінг просвіт→просвіт: flipY (X прямий, Y дзеркально) — лице
    # деталі дивиться −z у файлі, тож фронтальний вигляд = y→−y кадру
    # перерізу. Підтверджено скріншотом користувача (FreeCAD «Знизу»).
    return sa.affine_transform(
        win, [1, 0, 0, -1, PSU_X0 + PSU_WALL_S - PSU_REF_LUM[0],
              PSU_IY0 + PSU_REF_LUM[3]])


def _merge(holes):
    """Злити кишені, що майже торкаються (стінка < ~0.16мм) — ножові
    щілини на межах полів дають нон-маніфолдні вузли в STL."""
    u = unary_union(holes).buffer(0.08, quad_segs=4).buffer(-0.08, quad_segs=4)
    return _polys(u)


def _cutters(holes, lo, hi, axis):
    """Екструзія 2D-вирізів у різаки: axis='z' → поле (X,Y);
    axis='y' → поле (X,Z); axis='x' → поле (Z,Y)... через матриці."""
    out = []
    for h in holes:
        c = trimesh.creation.extrude_polygon(h, hi - lo)
        if axis == 'z':
            c.apply_translation([0, 0, lo])
        elif axis == 'y':   # поле (u=X, v=Z): (u,v,w) → (X=u, Y=w+lo, Z=v)
            T = np.array([[1, 0, 0, 0], [0, 0, 1, lo],
                          [0, 1, 0, 0], [0, 0, 0, 1]], dtype=float)
            c.apply_transform(T)
        elif axis == 'x':   # поле (u=Z, v=Y): (u,v,w) → (X=w+lo, Y=v, Z=u)
            T = np.array([[0, 0, 1, lo], [0, 1, 0, 0],
                          [1, 0, 0, 0], [0, 0, 0, 1]], dtype=float)
            c.apply_transform(T)
        out.append(c)
    return out


def build():
    # ---- фронт-плита ----
    plate = sg.box(0, 0, W, H).buffer(-CORNER_R).buffer(CORNER_R, quad_segs=12)
    holes2d = []
    for xc in EAR_SLOT_XC:
        for (y0, y1) in EAR_SLOT_Y:
            holes2d.append(_stadium(xc, y0, y1, EAR_SLOT_W))
    # апертура БЖ = губа лиця з еталона (вікно + 4 болтові отвори);
    # позаду губи (z < −PSU_LIP_T) плита розкривається до повного просвіту
    holes2d.append(psu_window())
    # вікно під колиску: інсет 1.0 від її габариту (перекриття, кути R1.5)
    holes2d.append(sg.box(KVM_X0 + 1.0, 1.0, KVM_X1 - 0.5, H - 1.0)
                   .buffer(-1.5).buffer(1.5, quad_segs=8))
    panel2d = plate.difference(unary_union(holes2d))
    panel = _prism(panel2d, -PANEL_T, 0.0)

    # ---- тунель БЖ ----
    tube2d = sg.box(PSU_X0, 0, PSU_X1, H).difference(
        sg.box(PSU_X0 + PSU_WALL_S, PSU_IY0,
               PSU_X1 - PSU_WALL_S, PSU_IY0 + PSU_IN_H))
    tube = _prism(tube2d, PSU_Z0, PSU_Z1 + 0.5)   # +0.5 захід у плиту

    # ---- ребра жорсткості середнього прольоту (верх/низ, за плитою) ----
    # глибина 8 (було 11 — фідбек 14.07 «чи потрібен такий широкий»):
    # прогін лише 48мм між трубою БЖ і колискою, 8мм вистачає з запасом.
    # Далі вправо НЕ тягнемо: колиска = коробка 33мм, сама жорсткість.
    ribs = [_prism(sg.box(PSU_X1 - 1, 0, KVM_X0 + 1, 3.0), -8.0, PSU_Z1 + 0.5),
            _prism(sg.box(PSU_X1 - 1, H - 3.0, KVM_X0 + 1, H), -8.0,
                   PSU_Z1 + 0.5)]

    # ---- колиска JetKVM: ПОВОРОТ 180° НАВКОЛО ОСІ Y (13.07, вказівка
    # користувача; Rx180 ставив кліпсу вниз — «догори дриґом»).
    # Ry180: лице вперед (+Z), кліпса ЗВЕРХУ, фланець — лівий край колиски
    # (до центру юніта), вікно модуля — біля правої стійки. Чистий поворот,
    # геометрія 1:1 без дзеркала.
    kvm = trimesh.load(KVM_REF, force='mesh')
    kvm.apply_translation(-kvm.bounds[0])
    kvm.apply_transform(trimesh.transformations.rotation_matrix(np.pi, [0, 1, 0]))
    kvm.apply_translation([KVM_X1, 0, 0])      # x → 150.31..237.5; z −33.16..0
    assert abs(kvm.bounds[0][0] - KVM_X0) < 0.01 and \
           abs(kvm.bounds[1][2]) < 0.01 and abs(kvm.bounds[1][1] - H) < 0.01

    # заглушки рейкових слотів фланця колиски (слоти її standalone-
    # кріплення, bbox 153.94..166.68 × 2.98..9.73 / 34.72..41.47, безель
    # z 0..−3.2) — у юніті зайві отвори (фідбек 14.07), заливаємо +0.5
    plugs = [_prism(sg.box(153.44, 2.48, 167.18, 10.23), -3.2, 0.0),
             _prism(sg.box(153.44, 34.22, 167.18, 41.97), -3.2, 0.0)]

    # ---- полегшення: rhombille ----
    cut = []
    # розкриття плити позаду губи БЖ до повного просвіту коміра
    cut.append(_prism(sg.box(PSU_X0 + PSU_WALL_S, PSU_IY0,
                             PSU_X1 - PSU_WALL_S, PSU_IY0 + PSU_IN_H),
                      -PANEL_T - EPS, -PSU_LIP_T))
    # середина панелі + зона фланця колиски (фідбек 13.07: «залити всю
    # область») — до рами 4.9 перед вікном модуля (181.9); кишені слотів
    # фланця (виміряні у Ry180-кадрі) в keepout з обідком 1.5; глибина
    # різу −3.7 — крізь плиту (3) і безель колиски (3.2), НЕ чіпаючи
    # шелл колиски (починається з z=−4)
    MID_X1 = 177.0
    mid = sg.box(PSU_X1 + FRAME, FRAME, MID_X1, H - FRAME)
    # keepout лівої стінки шелла колиски (x≥170.94, y≥17.58, z≤−3.6):
    # кріплення проступало крізь кишені поля (фідбек 14.07, обідок ~1)
    mid = mid.difference(sg.box(169.9, 16.6, MID_X1 + 1, H))
    cut += _cutters(_merge(rhombille_holes(mid, PSU_X1 + FRAME, FRAME)),
                    -3.7, EPS, 'z')
    # стінки тунелю: верх/низ — поле (X, Z)
    fx0, fx1 = PSU_X0 + PSU_WALL_S + FRAME, PSU_X1 - PSU_WALL_S - FRAME
    fz0, fz1 = PSU_Z0 + FRAME, PSU_Z1 - FRAME
    fld = sg.box(fx0, fz0, fx1, fz1)
    hl = _merge(rhombille_holes(fld, fld.bounds[0], fld.bounds[1]))
    cut += _cutters(hl, -EPS, PSU_IY0 + EPS, 'y')                    # низ
    cut += _cutters(hl, H - PSU_IY0 - EPS, H + EPS, 'y')             # верх
    # стінки тунелю: боки — поле (Z, Y)
    fldS = sg.box(fz0, PSU_IY0 + FRAME, fz1, H - PSU_IY0 - FRAME)
    hlS = _merge(rhombille_holes(fldS, fldS.bounds[0], fldS.bounds[1]))
    cut += _cutters(hlS, PSU_X0 - EPS, PSU_X0 + PSU_WALL_S + EPS, 'x')
    cut += _cutters(hlS, PSU_X1 - PSU_WALL_S - EPS, PSU_X1 + EPS, 'x')

    print(f"різаків: {len(cut)}")
    solid = trimesh.boolean.union([panel, tube, kvm] + ribs + plugs,
                                  engine='manifold')
    res = trimesh.boolean.difference(
        [solid, trimesh.util.concatenate(cut)], engine='manifold')

    # фініш: скинути нуль-об'ємні крихти (дотики кишень на межах полів),
    # зшити рештки — конвеєр _heal з exporter.py (+float32-раундтрип)
    from exporter import _heal
    bodies = sorted(res.split(only_watertight=False),
                    key=lambda b: -abs(b.volume))
    assert all(abs(b.volume) < 1.0 for b in bodies[1:]), \
        [round(b.volume, 2) for b in bodies[1:]]
    res = bodies[0]
    res.merge_vertices(digits_vertex=4)
    res.update_faces(res.nondegenerate_faces())
    res.update_faces(res.unique_faces())
    if not res.is_watertight:
        res = _heal(res)
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "psu_kvm.stl")
    if not res.is_watertight:          # float32-раундтрип через файл
        res.export(path)
        res = _heal(trimesh.load(path))
    res.fix_normals()
    print(f"vol={res.volume:.0f} мм³  watertight={res.is_watertight} "
          f"bodies={res.body_count}")
    print(f"bounds={np.round(res.bounds, 2).tolist()}")
    res.export(path)
    print("→ out/psu_kvm.stl")
    return res


if __name__ == "__main__":
    build()
