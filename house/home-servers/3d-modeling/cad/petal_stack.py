"""
petal_stack.py — СХЕМА ЕТАЖЕРКИ (31.07): чим тримається SSD-блок у дні.
Переріз YZ, три тіла + дорога навантаження на ПІДЙОМ (критичний напрям —
перевертання/вібрація у стійці). Схематично (пропорції ясності, не точні
params) — щоб пояснити ланцюг БЛОК → ЗАЧЕП → ДНО.

  ДНО (сіре): мембрана Z0..3 з нестом; Z-ЛЕДЖ (undercut) на Z1.6; верх
              Z3 = ПАД, на який блок спирається вагою (донизу — сюди).
  ЗАЧЕП (крем): ГОЛОВА з ФЛАНЦЯМИ (широка) + шийка/ребро + 2 пелюстки з
                барбами. Голова засунута збоку в Т-паз блока.
  БЛОК (синій): слаб зверху; ПОЛИЦІ Т-паза під фланцями голови; вузька
                ШИЙКА пропускає ребро/ноги вниз до неста; стеля над головою.

Дорога ПІДЙОМУ: блок↑ → полиці піднімають фланці → зачеп↑ → барби ГЛИБШЕ
під ледж дна (undercut) → ТРИМАЄ. Тертя в ланцюзі немає.

Запуск: .venv/bin/python cad/petal_stack.py → out/petal_stack.png
"""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
import shapely.geometry as sg
import shapely.ops as so
import numpy as np

# ── рівні Z ──
Z_STOOL = 0.0
Z_LEDGE = 1.6          # ледж undercut (стеля підмембранної кишені)
Z_MEMB = 3.0           # верх мембрани дна = ПАД (блок спирається)
Z_HEAD0, Z_HEAD1 = 5.6, 7.6     # голова зачепа
Z_SHELF = Z_HEAD0               # полиці блока під фланцями
Z_CEIL = Z_HEAD1 + 1.6          # стеля Т-паза блока
Z_BLKTOP = Z_CEIL + 2.0

# ── ширини Y (пів) ──
NEST_H = 3.2           # внутр. пів-нест (прохід ніг)
BARB = 1.0
WALL = 1.6
FLANGE = 4.6           # пів-голова (фланці ширші за ноги)
NECK = 3.5             # пів-шийка Т-паза (пропускає ребро/ноги, ловить фланці)
RIB_H = 2.0
GAP = 1.35
LEG_T = 1.4


def floor_sec():
    parts = []
    for s in (+1, -1):
        x0 = s * NEST_H
        x1 = s * (NEST_H + WALL + BARB + 3.5)
        wall = sg.box(min(x0, x1), Z_STOOL, max(x0, x1), Z_MEMB)
        pocket = sg.box(min(x0, s * (NEST_H + WALL + BARB + 0.4)), Z_STOOL,
                        max(x0, s * (NEST_H + WALL + BARB + 0.4)), Z_LEDGE)
        parts.append(wall.difference(pocket))
    parts.append(sg.box(-(NEST_H + WALL + BARB + 3.5), -0.6,
                        NEST_H + WALL + BARB + 3.5, Z_STOOL))
    return so.unary_union(parts)


def clip_sec():
    # голова з фланцями
    head = sg.box(-FLANGE, Z_HEAD0, FLANGE, Z_HEAD1)
    # ребро вниз крізь шийку до неста
    rib = sg.Polygon([(-RIB_H, Z_STOOL + 0.3), (RIB_H, Z_STOOL + 0.3),
                      (RIB_H, Z_HEAD0 + 0.2), (-RIB_H, Z_HEAD0 + 0.2)])
    legs = []
    for s in (+1, -1):
        xi = s * (RIB_H + GAP)
        xo = s * NEST_H
        xb = s * (NEST_H + BARB)
        ux = -s * BARB * 0.07
        legs.append(sg.Polygon([
            (xi, Z_HEAD0 + 0.2), (xi, Z_LEDGE + 0.15),
            (xo, Z_STOOL + 0.25), (xo, Z_LEDGE - 1.0),
            (xb, Z_LEDGE), (xb + ux, Z_LEDGE + 0.2),
            (xo, Z_LEDGE + 0.5), (xo, Z_HEAD0 + 0.2)]).buffer(0))
    body = so.unary_union([head, rib] + legs)
    for s in (+1, -1):
        body = body.difference(
            sg.Point(s * (RIB_H + GAP / 2), Z_HEAD0 + 0.1).buffer(0.55, 48))
    return body


def block_sec():
    slab = sg.box(-9.5, Z_SHELF, 9.5, Z_BLKTOP)
    # Т-паз: пельга голови (пів-FLANGE+0.3) від Z_SHELF..Z_CEIL
    pocket = sg.box(-(FLANGE + 0.3), Z_SHELF + 0.0, FLANGE + 0.3, Z_CEIL)
    # шийка вниз (пропускає ребро/ноги) — але слаб і так лише від Z_SHELF,
    # тож знизу відкрито; шийка = звуження над полицями? Ні: полиці =
    # матеріал блока під фланцями поза шийкою. Реалізуємо: slab − pocket,
    # потім повертаємо ПОЛИЦІ (смужки під фланцями) шириною NECK..FLANGE.
    blk = slab.difference(pocket)
    for s in (+1, -1):
        shelf = sg.box(min(s * NECK, s * (FLANGE + 0.3)), Z_SHELF,
                       max(s * NECK, s * (FLANGE + 0.3)), Z_SHELF + 0.0)
    # полиці як тонкі виступи під фланці:
    for s in (+1, -1):
        blk = blk.union(sg.box(min(s * NECK, s * (FLANGE + 0.3)),
                               Z_SHELF - 0.0, max(s * NECK, s * (FLANGE + 0.3)),
                               Z_SHELF + (Z_HEAD1 - Z_HEAD0) * 0.0 + 0.0))
    # додаємо реальні полиці (виступ під фланець, товщина 0.0 виродж) —
    # намалюємо явно нижче як окремі бокси:
    return blk


def _draw(ax, geom, fc, ec, lw=1.3, z=3, alpha=1.0):
    for gm in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
        if gm.is_empty or gm.geom_type != 'Polygon':
            continue
        ax.add_patch(MPoly(np.array(gm.exterior.coords), closed=True,
                           fc=fc, ec=ec, lw=lw, zorder=z, alpha=alpha))
        for r in gm.interiors:
            ax.add_patch(MPoly(np.array(r.coords), closed=True, fc='w',
                               ec=ec, lw=lw, zorder=z + 1))


fig, ax = plt.subplots(figsize=(11, 9))
_draw(ax, floor_sec(), '#c8ccd4', '#7f8c8d', 1.2, z=1)
# пади (верх дна Z3) — підпис
ax.plot([-(NEST_H + WALL + BARB + 3.5), -(NEST_H + 0.1)], [Z_MEMB, Z_MEMB],
        color='#16a085', lw=2.2, zorder=2)
ax.plot([NEST_H + 0.1, NEST_H + WALL + BARB + 3.5], [Z_MEMB, Z_MEMB],
        color='#16a085', lw=2.2, zorder=2)
# блок: слаб з Т-пазом + ЯВНІ полиці під фланцями
blk = sg.box(-9.5, Z_MEMB, 9.5, Z_BLKTOP).difference(
    sg.box(-(FLANGE + 0.3), Z_MEMB, FLANGE + 0.3, Z_CEIL))          # порожнина
for s in (+1, -1):                                                  # полиці
    blk = blk.union(sg.box(min(s * NECK, s * (FLANGE + 0.3)), Z_SHELF - 1.4,
                           max(s * NECK, s * (FLANGE + 0.3)), Z_SHELF))
# шийка: під полицями до низу блока — відкрито (ребро/ноги проходять)
_draw(ax, blk, '#aed6f1', '#2471a3', 1.3, z=2, alpha=0.95)
_draw(ax, clip_sec(), '#fdf3d0', '#b9770e', 1.5, z=4)
ax.plot([-(NEST_H + WALL + BARB), NEST_H + WALL + BARB], [Z_LEDGE, Z_LEDGE],
        color='#2980b9', lw=1.0, ls=':', zorder=5)

AN = dict(fontsize=9, va='center', color='#c0392b',
          arrowprops=dict(arrowstyle='->', lw=1.2, color='#c0392b'))
ax.annotate('БЛОК (слаб)', xy=(7.5, Z_BLKTOP - 1), xytext=(6.0, Z_BLKTOP + 1.2),
            ha='center', fontsize=11, color='#1b4f72', weight='bold')
ax.annotate('ПОЛИЦІ Т-паза\nпід фланцями голови',
            xy=(-(FLANGE + NECK) / 2, Z_SHELF - 0.7), xytext=(-13.5, 4.5),
            ha='left', **AN)
ax.annotate('ГОЛОВА з ФЛАНЦЯМИ\n(засув збоку в Т-паз)',
            xy=(FLANGE - 0.5, (Z_HEAD0 + Z_HEAD1) / 2), xytext=(5.5, 9.5),
            ha='left', **AN)
ax.annotate('ЦЕНТР. РЕБРО\n(Z-упор + обмежувач)',
            xy=(0, 3.2), xytext=(-13.5, 8.5), ha='left', **AN)
ax.annotate('БАРБ −4° ПІД ЛЕДЖ дна\n(undercut = позитивний замок)',
            xy=(NEST_H + BARB, Z_LEDGE + 0.1), xytext=(4.2, 1.0),
            ha='left', **AN)
ax.annotate('ПАД дна — блок стоїть вагою\n(напрям ВНИЗ)',
            xy=(-(NEST_H + WALL + 1), Z_MEMB), xytext=(-13.5, 1.6),
            ha='left', **AN)
# дорога ПІДЙОМУ (жирна зелена)
ax.annotate('', xy=(8.7, Z_SHELF), xytext=(8.7, Z_BLKTOP - 0.5),
            arrowprops=dict(arrowstyle='-|>', lw=2.6, color='#27ae60'))
ax.text(9.0, (Z_SHELF + Z_BLKTOP) / 2, 'блок ↑\n(перевертання)',
        color='#1e8449', fontsize=9.5, va='center', weight='bold')

ax.set_title('Чим тримається блок: БЛОК → ЗАЧЕП → ДНО (дорога підйому)',
             fontsize=12.5, weight='bold')
ax.set_xlim(-14, 14); ax.set_ylim(-1.5, Z_BLKTOP + 3)
ax.set_aspect('equal'); ax.axis('off')
plt.tight_layout()
plt.savefig('out/petal_stack.png', dpi=150, facecolor='w')
print('OK out/petal_stack.png')
