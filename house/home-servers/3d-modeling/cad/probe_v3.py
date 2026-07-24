"""probe_v3.py — зонди схеми в3 «ОБОДОК + АДДОН-КЛІП-ЛЕЗО» (17.07).
Перевіряє: посадкові перетини (лише crush — задум), упори зсувами
±0.5, шлях установки аддона КАЧАННЯМ (розклад нахилу від dz) і
кліпа згори (+Z). Запуск: .venv/bin/python cad/probe_v3.py
"""
import numpy as np
import trimesh

tray = trimesh.load('out/tray.stl')
cap = trimesh.load('out/addon_clip.stl')
addons = {v: trimesh.load(f'out/front_{v}.stl')
          for v in ('fan', 'grille', 'blank')}

PIV = np.array([0, -96.4, 5.0])   # задня кромка сідла (вісь качання)


def inter(a, b):
    r = trimesh.boolean.intersection([a, b], engine='manifold')
    return 0.0 if r.is_empty else r.volume


def shifted(m, dx=0, dy=0, dz=0):
    c = m.copy()
    c.apply_translation((dx, dy, dz))
    return c


def tilted(m, deg, dz=0.0):
    """Нахил ВЕРХОМ НАЗАД (−θ навколо X через PIV) + підйом dz."""
    a = np.radians(-deg)
    R = np.array([[1, 0, 0, 0],
                  [0, np.cos(a), -np.sin(a), 0],
                  [0, np.sin(a), np.cos(a), 0],
                  [0, 0, 0, 1]])
    T1 = np.eye(4); T1[:3, 3] = -PIV
    T2 = np.eye(4); T2[:3, 3] = PIV
    c = m.copy()
    c.apply_transform(T2 @ R @ T1)
    c.apply_translation((0, 0, dz))
    return c


print('── посадкові перетини (задум: лише crush) ──')
for v, ad in addons.items():
    print(f'  {v}∩tray = {inter(ad, tray):.3f} мм³')
print(f'  cap∩tray  = {inter(cap, tray):.3f} мм³')
print(f'  cap∩addon(fan) = {inter(cap, addons["fan"]):.3f} мм³')

ad = addons['fan']
print('── упори аддона (зсув 0.5 → перетин має бути СУТТЄВИМ) ──')
print(f'  вдавлення (+Y) → кліп   : {inter(shifted(ad, dy=0.5), cap):.2f}')
print(f'  вдавлення (+Y) → tray   : {inter(shifted(ad, dy=0.5), tray):.2f}')
print(f'  вперед (−Y) → ламелі    : {inter(shifted(ad, dy=-0.5), tray):.2f}')
print(f'  підйом (+Z) → ободок    : {inter(shifted(ad, dz=0.5), tray):.2f}')
print(f'  вбік (+X)               : {inter(shifted(ad, dx=0.5), tray):.2f}')
print(f'  вбік (−X)               : {inter(shifted(ad, dx=-0.5), tray):.2f}')

print('── упори кліпа ──')
print(f'  вдавлення cap (+Y)      : {inter(shifted(cap, dy=0.5), tray):.2f}')
print(f'  cap вперед (−Y)         : {inter(shifted(cap, dy=-0.5), tray):.2f}')

# ── шлях кліпа: підйом із посадки строго вгору, кроки ──
print('── шлях кліпа вгору (+Z, має бути ~0 крім crush) ──')
for dz in (1, 3, 6, 10, 14):
    print(f'  dz={dz:>2}: ∩tray={inter(shifted(cap, dz=dz), tray):.3f}'
          f' ∩addon={inter(shifted(cap, dz=dz), addons["fan"]):.3f}')

# ── шлях аддона КАЧАННЯМ: reverse-установка — з посадки нахил
# верхом назад + підйом за розкладом (більший dz → більший нахил
# допустимий; біля посадки нахил малий) ──
print('── качання аддона (півот y−96.4 z5, верх НАЗАД) ──')
# 24.07 (зачеп язиків 2.0, GRIP_Z=3.0): фінальний нахил ≤4° —
# повна товщина язика нижче z3.8 не пролазить при 6° (зсув 0.21>0.15)
SCHED = [(14, 10), (12, 9), (10, 8), (8, 8), (6, 8), (5, 7),
         (4, 6), (3.5, 5.5), (3, 5), (2, 4), (1, 4)]
for dz, deg in SCHED:
    print(f'  dz={dz:>4} θ={deg:>4}°: ∩tray = '
          f'{inter(tilted(ad, deg, dz), tray):.3f} мм³')
# фініш: ротація у вертикаль на посадці (dz=0)
for deg in (4, 2, 1, 0):
    print(f'  dz=   0 θ={deg:>4}°: ∩tray = '
          f'{inter(tilted(ad, deg, 0), tray):.3f} мм³')
