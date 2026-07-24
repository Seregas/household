"""
probe_zones.py — точковий зонд друкованості (21.07, питання користувача):
(1) постаменти плати (лежачі циліндри ⌀9 у друці лицем вниз) і
(2) верхні стінки RAM-вікон (мости при закритті отворів).
Корпус у бойовій орієнтації FACE_DOWN: print-XY = (model_x, −model_z),
висота друку = model_y (зсунута в 0, = model_y + 99.4).
Для кожної зони: пошарово «нове» = cur − prev.buffer(tol); міряємо
REACH (макс. відстань точок нового до попереднього шару = виліт консолі
або півпроліт моста) і SPAN (протяжність компонента по X).
Запуск: .venv/bin/python cad/probe_zones.py   (лише з кореня проєкту)
"""
import numpy as np
import trimesh
from shapely.geometry import Point, box
from shapely.ops import unary_union

import sys
sys.path.insert(0, "cad")
import params as P

FACE_DOWN = np.array([[1, 0, 0], [0, 0, 1], [0, -1, 0]], float)
TOL = 0.05

m = trimesh.load("out/tray.stl", force="mesh")
m.vertices = m.vertices @ FACE_DOWN          # (x, -z, y)
zoff = -m.vertices[:, 2].min()               # = 99.4
m.vertices[:, 2] += zoff


def slices(z_lo, z_hi, lh):
    zs = np.arange(z_lo + lh / 2, z_hi, lh)
    secs = m.section_multiplane([0, 0, 0], [0, 0, 1], zs)
    out = []
    for z, s in zip(zs, secs):
        if s is None:
            out.append((z, None))
            continue
        polys = [p for p in s.polygons_full if p is not None and p.area > 1e-6]
        out.append((z, unary_union(polys) if polys else None))
    return out


def reach(comp, prev):
    pts = list(comp.exterior.coords)
    for hole in comp.interiors:
        pts += list(hole.coords)
    return max(Point(p).distance(prev) for p in pts)


def zone_report(title, z_lo, z_hi, lh, clip, min_area=0.3):
    print(f"\n═══ {title} — висоти {z_lo:.1f}..{z_hi:.1f}, шар {lh} ═══")
    data = slices(z_lo - lh, z_hi, lh)
    worst = []
    prev = None
    for z, cur in data:
        if cur is None:
            prev = None
            continue
        if prev is None:
            prev = cur
            continue
        new = cur.intersection(clip).difference(prev.buffer(TOL))
        comps = ([] if new.is_empty else
                 list(new.geoms) if new.geom_type == "MultiPolygon" else [new])
        for c in comps:
            if c.area < min_area:
                continue
            r = reach(c, prev)
            if r < lh + 0.06:                 # ≤45° — не цікаво
                continue
            bb = c.bounds
            worst.append((r, z, c.area, bb[2] - bb[0],
                          c.representative_point().coords[0]))
        prev = cur
    if not worst:
        print("  ✅ жодного навісу за 45° у зоні")
        return
    worst.sort(key=lambda t: -t[0])
    for r, z, a, spanx, (x, y) in worst[:8]:
        print(f"  z={z:7.2f}  reach={r:5.2f}  span_x={spanx:5.1f}"
              f"  area={a:6.1f}  @({x:.1f},{y:.1f})")


# ── 1. Постаменти: диск ⌀9 (+галтель R1) навколо кожного центру ──
# print-plane: (x_c, −z), z 0..7.55 → y'' −7.55..0; шар у бандах VLH = 0.12
for name, (xc, yc) in sorted(P.STANDOFF_XY.items()):
    clip = box(xc - 6, -P.BOARD_Z - 1, xc + 6, 1)
    zc = yc + zoff
    zone_report(f"Постамент {name} (x={xc}, y={yc})",
                zc - 5.5, zc + 5.5, 0.12, clip)

# ── 2. Верхні кромки RAM-вікон: мости при закритті ──
for name, w in sorted(P.RAM_KEEPOUT.items()):
    x0, x1 = w["x"]
    y_top = w["y"][1]
    clip = box(x0 - 3, -P.FRAME_T - 2, x1 + 3, 1)
    zt = y_top + zoff
    zone_report(f"RAM-вікно {name} верх (x {x0}..{x1}, кромка y={y_top})",
                zt - 1.0, zt + 3.0, 0.24, clip)
