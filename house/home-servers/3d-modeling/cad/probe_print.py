"""
probe_print.py — зонд ДРУКОВАНОСТІ (20.07): «уявний слайсер» по-справжньому.
Кожен STL з print_all.3mf ріжеться пошарово У БОЙОВІЙ ОРІЄНТАЦІЇ (ті самі
матриці, що make_bambu: vv = v @ R) з бойовою висотою шару. На кожному шарі:
  • ОСТРІВ — компонент, що НЕ перетинає попередній шар (старт у повітрі,
    без підтримки не друкується) → червоний прапор;
  • НАВІС >45° — частина шару за межею prev.buffer(layer_h): для кожного
    компонента міряємо ГЛИБИНУ (макс. відстань точок до попереднього шару).
    Глибина ≈ span/2 для моста (якорі з двох боків) або повна довжина
    консолі. Мости ≤ 12мм і короткі консолі PETG тягне (правило CLAUDE.md).
Шум STL-фасеток < 0.15 мм² ігнорується. Перший шар = стіл, підтриманий.
Запуск: .venv/bin/python cad/probe_print.py   (лише з кореня проєкту)
"""
import numpy as np
import trimesh
from shapely.ops import unary_union

FACE_DOWN = (1, 0, 0, 0, 0, 1, 0, -1, 0)
IDENT = (1, 0, 0, 0, 1, 0, 0, 0, 1)
ROT_Y90 = (0, 0, 1, 0, 1, 0, -1, 0, 0)
ROT_REAR = (1, 0, 0, 0, 0, -1, 0, 1, 0)   # 21.07: фронт-аддон тилом вниз
ROT_X180 = (1, 0, 0, 0, -1, 0, 0, 0, -1)  # 27.07: 1U БЖ+KVM лицем вниз

# (stl, назва, матриця, висота шару) — рівно як у print_all.3mf
JOBS = [
    ("out/tray.stl",      "Корпус (лицем вниз)",  FACE_DOWN, 0.24),
    ("out/io_insert.stl", "Вставка IO (тилом вниз)", ROT_REAR, 0.16),
    ("out/addon_clip.stl","Аддон-кліп",           FACE_DOWN, 0.16),
    ("out/snap_clip.stl", "Snap-зачеп (на боці)", ROT_Y90,   0.16),
    ("out/front_fan.stl", "Фронт-аддон fan (тилом вниз)", ROT_REAR, 0.16),
    ("out/ssd_block.stl", "SSD-блок (дном вниз)", IDENT,     0.20),
    ("out/psu_kvm.stl",   "1U БЖ+KVM (лицем вниз)", ROT_X180, 0.24),
]

MIN_AREA = 0.15      # мм² — шум фасеток
TOL = 0.05           # мм — допуск дотику компонент до попереднього шару


def layer_polys(mesh, zs):
    """Список shapely-полігонів (union) для кожної висоти zs."""
    sections = mesh.section_multiplane(
        plane_origin=[0, 0, 0], plane_normal=[0, 0, 1], heights=zs)
    out = []
    for s in sections:
        if s is None:
            out.append(None)
            continue
        polys = [p for p in s.polygons_full if p is not None and p.area > 1e-6]
        out.append(unary_union(polys) if polys else None)
    return out


def comp_depth(comp, prev):
    """Макс. відстань точок компонента до попереднього шару (глибина навісу)."""
    from shapely.geometry import Point
    return max(Point(p).distance(prev) for p in comp.exterior.coords)


def probe(path, name, rot, lh):
    m = trimesh.load(path, force="mesh")
    R = np.array(rot, float).reshape(3, 3)
    m.vertices = m.vertices @ R
    m.vertices[:, 2] -= m.vertices[:, 2].min()
    zmax = m.vertices[:, 2].max()
    n = int(np.floor((zmax - lh / 2) / lh)) + 1
    zs = np.arange(n) * lh + lh / 2          # середини шарів
    layers = layer_polys(m, zs)

    islands, over = [], []
    prev = None
    for i, cur in enumerate(layers):
        if cur is None:
            prev = None
            continue
        if i == 0 or prev is None:
            prev = cur
            continue
        sup = prev.buffer(TOL)
        sup45 = prev.buffer(lh + TOL)
        comps = list(cur.geoms) if cur.geom_type == "MultiPolygon" else [cur]
        for c in comps:
            if c.area < MIN_AREA:
                continue
            if not c.intersects(sup):
                islands.append((zs[i], c.area, c.representative_point().coords[0]))
                continue
            beyond = c.difference(sup45)
            if beyond.is_empty:
                continue
            bcomps = (list(beyond.geoms) if beyond.geom_type == "MultiPolygon"
                      else [beyond])
            for b in bcomps:
                if b.area < MIN_AREA:
                    continue
                d = comp_depth(b, prev)
                over.append((zs[i], b.area, d, b.representative_point().coords[0]))
        prev = cur
    print(f"\n═══ {name} — {path}, шар {lh}, {n} шарів, h={zmax:.1f} ═══")
    if islands:
        print(f"  ❌ ОСТРОВИ: {len(islands)}")
        for z, a, (x, y) in islands[:12]:
            print(f"     z={z:.2f}  area={a:.2f} мм²  @({x:.1f},{y:.1f})")
    else:
        print("  ✅ островів нема")
    if over:
        # групуємо по глибині: цікаві найглибші
        over.sort(key=lambda t: -t[2])
        print(f"  ⚠️ навіси >45°: {len(over)} компонент; топ глибин:")
        seen = 0
        for z, a, d, (x, y) in over:
            if seen >= 10:
                break
            print(f"     z={z:.2f}  глибина={d:.2f}  area={a:.1f} мм²"
                  f"  @({x:.1f},{y:.1f})")
            seen += 1
    else:
        print("  ✅ навісів за 45° нема")


if __name__ == "__main__":
    for job in JOBS:
        probe(*job)
