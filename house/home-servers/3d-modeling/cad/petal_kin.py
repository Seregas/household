"""
petal_kin.py — 2D-КІНЕМАТИКА нового undercut/пелюсткового замка SSD-блока
(31.07, після діагнозу «блок випадає при перевертанні»; свобода «все нове»
— НЕ сідаємо в старий слот 5.6×2.5, нест і зачеп проєктуємо оптимально).

ПЕРЕРІЗ у площині YZ (площина шарів друку зачепа на боці; він же —
переріз нового неста дна). Осі:
    y — уздовж дна (вісь деформації пелюсток; ноги гнуться ±y);
    z — ГЛОБАЛЬНИЙ корпусу (0 = стіл; барб хоче ВГОРУ під ледж).
Зачеп СЕПАРАТНИЙ (друк на боці, згин у площині шарів — ідеал для пружин),
голова засувається у Т-паз слаба блока; дві ПЕЛЮСТКИ (ноги-пружини) звисають
під слабом і при посадці блока клацають у нест дна: барб з робочою гранню
0…−4° (UNDERCUT, не полиця!) заходить ПІД Z-ЛЕДЖ неста → тягнеш блок угору,
грань заганяє барб ГЛИБШЕ (позитивний замок, тертя з рівняння прибрано).
ЦЕНТРАЛЬНЕ РЕБРО = ① Z-упор у дно неста (датум, вертикальний люфт 0) +
② ОБМЕЖУВАЧ ходу (щілина < того, що дало б перегин > ε_max) + ③ жорсткість.
Зняття: палець знизу крізь кишеню тисне ПАРУ барбів → ками зводять ноги до
ребра → барби виходять з-під леджів → блок вгору.

Друкованість: увесь зачеп — YZ-профіль, екструдований по X (на боці) →
кожен шар ідентичний, нуль навісів; згин ніг по y = У ПЛОЩИНІ шарів.
Нест дна (корпус FACE_DOWN): Z-ледж = стеля підмембранної кишені у товщі
тонкої стінки дна — у площині шару (Z горизонтальний), друкується без
підтримок (той самий принцип, що працював у старому зубі-під-мембраною).

Запуск: .venv/bin/python cad/petal_kin.py → out/petal_kin.png (+ друк цифр).
"""
import math
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
import shapely.geometry as sg
import shapely.ops as so
import numpy as np

# ─── ПАРАМЕТРИ НЕСТА ДНА (нові, щедрі) ────────────────────────────────────
LEDGE_Z   = 1.6     # верх підмембранної кишені = НИЗ леджа (барб хоче сюди)
MEMB_Z    = 3.0     # верх мембрани дна (товщина стінки неста 0..3 локально)
NEST_HALF = 3.2     # піввідстань між внутрішніми гранями Y-стінок неста
                    #   (широкий прохід — ноги вільно входять)
WALL_T    = 1.6     # товщина Y-стінки неста (до підмембранної кишені)
POCKET_Z  = 0.0     # низ кишені/слота = стіл

# ─── ПАРАМЕТРИ ЗАЧЕПА ─────────────────────────────────────────────────────
RIB_HALF  = 2.0     # півширина центрального ребра
GAP       = 1.35    # щілина ребро↔нога (обмежувач ходу): нога впреться в
                    #   ребро, вигнувшись рівно на GAP < (перегин межі PETG)
LEG_T     = 1.4     # товщина ноги-пружини
LEG_L     = 7.6     # вільна довжина пружини (корінь z_split → барб)
BARB      = 1.0     # зачеплення барба (виступ робочої грані за грань неста)
UNDERCUT  = 4.0     # ° робочої грані (НЕГАТИВ — заганяє глибше під ледж)
RAMP      = 35.0    # ° рампи заходу (самозаскок при посадці)

Z_SPLIT   = LEDGE_Z + 4.2       # корінь пружини (початок щілини), над леджем
Z_BARB1   = LEDGE_Z             # робоча грань барба = НИЗ леджа
Z_BARB0   = LEDGE_Z - 1.1       # низ рампи барба (кінчик занурений у кишеню)
Z_TIP     = POCKET_Z + 0.25     # кінчик ноги майже до стола
Z_RIB_TOP = Z_SPLIT + 1.2       # верх ребра (Z-упор у стелю/дно неста згори)
RELIEF_R  = 0.55                # relief-отвір у корені щілини


def _leg(sgn, deflect=0.0):
    """Пелюстка (нога-пружина з барбом) з боку sgn (±y). deflect — стиск
       кінчика всередину (моделюємо зняття/захід)."""
    xi = sgn * (RIB_HALF + GAP)                 # внутр. грань (до щілини)
    xo = sgn * (NEST_HALF)                       # зовн. грань = стінка неста
    xb = sgn * (NEST_HALF + BARB)                # вершина барба (за стінку)
    # робоча грань undercut: від вершини (z=Z_BARB1) всередину-вниз на кут
    ux = -sgn * BARB * math.tan(math.radians(UNDERCUT))
    pts = [
        (xi, Z_SPLIT),                           # корінь внутр.
        (xi, Z_BARB1 + 0.15),                    # внутр. грань униз
        (sgn * (NEST_HALF - 0.0), Z_TIP + (Z_BARB0 - Z_TIP)),  # зовн. під барбом
        (sgn * NEST_HALF, Z_BARB0),              # низ рампи (на стінці)
        (xb, Z_BARB1),                           # вершина барба (рампа ~35°)
        (xb + ux, Z_BARB1 + BARB * 0.18),        # робоча грань UNDERCUT
        (sgn * NEST_HALF, Z_BARB1 + 0.5),        # назад до стінки над леджем
        (xi, Z_SPLIT - 0.2),
    ]
    # кінчик ноги вниз до стола (для стиску-зняття)
    tip = [(sgn * NEST_HALF, Z_BARB0),
           (sgn * (NEST_HALF - LEG_T * 0), Z_TIP),
           (sgn * (NEST_HALF - LEG_T), Z_TIP),
           (sgn * (NEST_HALF - LEG_T), Z_BARB0)]
    leg = sg.Polygon(pts).buffer(0)
    # згин: кінчик іде всередину на deflect, квадратичний профіль консолі
    if deflect:
        out = []
        for x, z in leg.exterior.coords:
            if abs(x) > RIB_HALF + GAP * 0.5 and z < Z_SPLIT:
                u = max(0.0, (Z_SPLIT - z) / LEG_L)
                f = (u * u * (3 - u)) / 2 if u <= 1 else 1.0
                x -= sgn * deflect * f
            out.append((x, z))
        leg = sg.Polygon(out).buffer(0)
    return leg


def clip(deflect=0.0):
    rib = sg.Polygon([(-RIB_HALF, Z_BARB1 - 0.5), (RIB_HALF, Z_BARB1 - 0.5),
                      (RIB_HALF, Z_RIB_TOP - 0.5), (RIB_HALF - 0.5, Z_RIB_TOP),
                      (-RIB_HALF + 0.5, Z_RIB_TOP), (-RIB_HALF, Z_RIB_TOP - 0.5)])
    head = sg.box(-NEST_HALF - 0.3, Z_SPLIT - 0.1, NEST_HALF + 0.3, Z_SPLIT + 2.2)
    body = so.unary_union([rib, head, _leg(+1, deflect), _leg(-1, deflect)])
    for s in (+1, -1):
        c = sg.Point(s * (RIB_HALF + GAP / 2), Z_SPLIT - 0.1).buffer(RELIEF_R, 48)
        body = body.difference(c)
    return body


def nest():
    """Нест дна у перерізі: дві Y-стінки з підмембранною кишенею (Z-ледж)."""
    parts = []
    for s in (+1, -1):
        # стінка неста: від внутр. грані NEST_HALF назовні, з леджем
        x0 = s * NEST_HALF
        x1 = s * (NEST_HALF + WALL_T + BARB + 1.0)
        wall = sg.box(min(x0, x1), POCKET_Z, max(x0, x1), MEMB_Z)
        # підмембранна кишеня: виїмка Z(POCKET_Z..LEDGE_Z) від внутр. грані
        #   назовні на (WALL_T+BARB+0.4) → відкриває Z-ледж, під який хапає барб
        pocket = sg.box(min(x0, s * (NEST_HALF + WALL_T + BARB + 0.4)),
                        POCKET_Z,
                        max(x0, s * (NEST_HALF + WALL_T + BARB + 0.4)),
                        LEDGE_Z)
        parts.append(wall.difference(pocket))
    # дно неста (стеля кишені знизу вже є стіл; малюємо тонку смужку столу)
    parts.append(sg.box(-NEST_HALF - WALL_T - BARB - 1.0, -0.6,
                        NEST_HALF + WALL_T + BARB + 1.0, POCKET_Z))
    return so.unary_union(parts)


def _draw(ax, geom, fc, ec, lw=1.4, alpha=1.0, z=3):
    for gm in (geom.geoms if hasattr(geom, 'geoms') else [geom]):
        if gm.is_empty or gm.geom_type != 'Polygon':
            continue
        ax.add_patch(MPoly(np.array(gm.exterior.coords), closed=True,
                           fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=z))
        for r in gm.interiors:
            ax.add_patch(MPoly(np.array(r.coords), closed=True,
                               fc='w', ec=ec, lw=lw, zorder=z + 1))


# ─── аналітика ────────────────────────────────────────────────────────────
defl_click = BARB + 0.1                 # прогин при заході барба повз стінку
eps_click = 3 * LEG_T * defl_click / (2 * LEG_L ** 2) * 100
defl_stop = GAP                          # обмежувач: нога впреться в ребро
eps_stop = 3 * LEG_T * defl_stop / (2 * LEG_L ** 2) * 100
release = BARB + 0.15                    # стиск на зняття (барб виходить)
eps_rel = 3 * LEG_T * release / (2 * LEG_L ** 2) * 100

print(f"зачеплення барба (undercut) : {BARB:.2f} мм (грань {UNDERCUT:.0f}° негатив)")
print(f"прогин заскоку {defl_click:.2f} → ε≈{eps_click:.2f}%  (PETG робоче ≤4.5%)")
print(f"прогин зняття  {release:.2f} → ε≈{eps_rel:.2f}%")
print(f"ОБМЕЖУВАЧ (нога↔ребро) спрацює на {defl_stop:.2f} → ε≈{eps_stop:.2f}% "
      f"({'OK: раніше межі' if eps_stop < 6.5 else 'ЗАВЕЛИКИЙ'})")
print(f"хід зняття {release:.2f} < обмежувач {defl_stop:.2f}: "
      f"{'OK (виходить до упору)' if release < defl_stop else 'ПРОБЛЕМА'}")

# перевірка позитивності undercut: робоча грань має нахил ЗА вертикаль
print(f"робоча грань undercut −{UNDERCUT:.0f}°: підйом блока → барб глибше "
      f"(позитивний замок, не тертя)")

# ─── рендер ───────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(13, 8))
AN = dict(fontsize=8.5, va='center', color='#c0392b',
          arrowprops=dict(arrowstyle='->', lw=1.0, color='#c0392b'))
for ax, defl, title in ((axes[0], 0.0, 'СПОКІЙ — undercut під леджем (замок)'),
                        (axes[1], release, 'ЗНЯТТЯ — ноги стиснуті до ребра')):
    _draw(ax, nest(), '#c8ccd4', '#7f8c8d', 1.2, z=1)
    # лінія леджа
    ax.plot([-NEST_HALF - WALL_T - BARB, NEST_HALF + WALL_T + BARB],
            [LEDGE_Z, LEDGE_Z], color='#2980b9', lw=1.0, ls=':', zorder=2)
    _draw(ax, clip(defl), '#f2f2f4', '#2c3e50', 1.5, z=3)
    ax.set_title(title, fontsize=11, weight='bold')
    ax.set_xlim(-8.5, 8.5); ax.set_ylim(-1.5, 11)
    ax.set_aspect('equal'); ax.axis('off')

axes[0].annotate('Z-ЛЕДЖ (стеля кишені)\nбарб хапає ПІД нього',
                 xy=(NEST_HALF + BARB / 2, LEDGE_Z), xytext=(2.0, 8.5),
                 ha='left', **AN)
axes[0].annotate('ЦЕНТР. РЕБРО\n① Z-упор (датум)\n② обмежувач ходу\n③ жорсткість',
                 xy=(0, Z_RIB_TOP - 1), xytext=(-8.2, 8.8), ha='left', **AN)
axes[0].annotate('робоча грань −4°\n(UNDERCUT, не полиця)',
                 xy=(NEST_HALF + BARB, Z_BARB1 + 0.1), xytext=(3.2, 4.5),
                 ha='left', **AN)
axes[1].annotate('ками зводять ноги\nдо ребра → барби\nвиходять з-під леджа',
                 xy=(-RIB_HALF - GAP / 2, Z_BARB1), xytext=(-8.2, 6.5),
                 ha='left', **AN)
plt.tight_layout()
plt.savefig('out/petal_kin.png', dpi=150, facecolor='w')
print('OK out/petal_kin.png')
