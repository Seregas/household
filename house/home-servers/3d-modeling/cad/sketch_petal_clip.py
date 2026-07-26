"""Концепт «волейбольного» зачепа: 2 пружини + центральне ребро.
Параметрична побудова профілю (2D, площина ескіза = площина шарів друку)."""
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly
import shapely.geometry as sg
import shapely.ops as so
import shapely.affinity as saf
import numpy as np

# ── базові параметри (масштаб k множить УСЕ) ────────────────────────────
BASE = dict(
    rw=2.2,      # півширина центрального ребра
    g=0.9,       # щілина = барб + 0.2 (вона ж over-travel stop)
    t=1.4,       # товщина пружини
    b=0.7,       # виступ барба (зачеплення)
    z_split=6.0, # корінь пружини (початок щілини)
    zb0=12.0,    # низ рампи барба
    zb1=13.0,    # робоча грань барба
    z_rib=14.0,  # верх центрального ребра (обмежувач стиску)
    H=20.0,      # повна висота
    ww=7.0,      # півширина по кінцях вусів
    xtip=3.2,    # півширина кінчика (конус заходу)
    zcone=3.0,   # висота конуса заходу
    relief=0.55, # радіус relief-отвору в корені щілини
)


def clip_body(k=1.0):
    p = {n: v * k for n, v in BASE.items()}
    hw = p['rw'] + p['g'] + p['t']

    base = sg.Polygon([(-p['xtip'], 0), (p['xtip'], 0), (hw, p['zcone']),
                       (hw, p['z_split'] + 0.1), (-hw, p['z_split'] + 0.1),
                       (-hw, p['zcone'])])
    rib = sg.Polygon([(-p['rw'], p['z_split'] - 1), (p['rw'], p['z_split'] - 1),
                      (p['rw'], p['z_rib'] - 0.6 * k), (p['rw'] - 0.6 * k, p['z_rib']),
                      (-p['rw'] + 0.6 * k, p['z_rib']), (-p['rw'], p['z_rib'] - 0.6 * k)])

    def spring(sgn):
        xi, xo = sgn * (p['rw'] + p['g']), sgn * hw          # внутр./зовн. грань
        pts = [(xi, p['z_split'] - 1), (xo, p['z_split'] - 1),
               (xo, p['zb0']),
               (sgn * (hw + p['b']), p['zb1']),               # рампа заходу ~35°
               (sgn * (hw + p['b']), p['zb1'] + 0.05 * k),    # робоча грань (undercut)
               (xo, p['zb1'] + 0.15 * k),
               (sgn * p['ww'], p['H']),                       # вус назовні
               (sgn * (p['ww'] - p['t']), p['H']),
               (xi, p['zb1'])]
        return sg.Polygon(pts)

    body = so.unary_union([base, rib, spring(+1), spring(-1)])
    for s in (+1, -1):                                        # relief-отвори
        c = sg.Point(s * (p['rw'] + p['g'] / 2), p['z_split']).buffer(p['relief'], 64)
        body = body.difference(c)
    return body, p, hw


def bend(poly, p, delta, sgn):
    """Зігнути пружину: квадратичний профіль консолі, далі — прямою."""
    L = p['zb1'] - p['z_split']
    out = []
    for x, z in poly.exterior.coords:
        if x * sgn > p['rw'] * 0.9 and z > p['z_split']:
            u = (z - p['z_split']) / L
            f = (u * u * (3 - u)) / 2 if u <= 1 else 1 + (u - 1) * 1.5
            x -= sgn * delta * f
        out.append((x, z))
    return out


def draw(ax, body, fc='#f2f2f4', ec='#2c3e50', lw=1.6, alpha=1.0):
    geoms = body.geoms if hasattr(body, 'geoms') else [body]
    for gm in geoms:
        ax.add_patch(MPoly(np.array(gm.exterior.coords), closed=True,
                           fc=fc, ec=ec, lw=lw, alpha=alpha, zorder=3))
        for ring in gm.interiors:
            ax.add_patch(MPoly(np.array(ring.coords), closed=True,
                               fc='w', ec=ec, lw=lw, zorder=4))


fig = plt.figure(figsize=(17.5, 9.5))
gs = fig.add_gridspec(1, 3, width_ratios=[1.0, 0.85, 1.25], wspace=0.05)
AN = dict(fontsize=9.5, va='center', color='#c0392b',
          arrowprops=dict(arrowstyle='->', lw=1.1, color='#c0392b'))

# ══ A. анатомія ═══════════════════════════════════════════════════════
ax = fig.add_subplot(gs[0])
body, p, hw = clip_body()
draw(ax, body)
ax.annotate('ВУС — щипок для зняття\n(важіль ~2:1 до барба)',
            xy=(6.6, 19.2), xytext=(-2.0, 24.0), ha='center', **AN)
ax.annotate('БАРБ\nрампа заходу ~35°\nробоча грань 0…−5°\n(НЕ скіс — інакше сповзе)',
            xy=(5.2, 12.9), xytext=(9.4, 15.5), ha='left', **AN)
ax.annotate('ПРУЖИНА t=1.4, L=6.5\nε = 3·t·y/(2L²) = 3.5 %\n(PETG робоче ≤4.5 %)',
            xy=(4.0, 9.5), xytext=(9.4, 7.0), ha='left', **AN)
ax.annotate('ЦЕНТРАЛЬНЕ РЕБРО\n① жорсткість на стиск\n② Z-упор у дно гнізда\n'
            '③ ОБМЕЖУВАЧ ходу:\n   щілина 0.9 > барб 0.7',
            xy=(1.4, 11.0), xytext=(-19.0, 13.5), ha='left', **AN)
ax.annotate('RELIEF ⌀1.1 у корені щілини\n(галтель у щілину 0.9 не влазить)',
            xy=(-3.1, 6.0), xytext=(-19.0, 3.4), ha='left', **AN)
ax.annotate('конус заходу —\nсамоцентрування в гнізді',
            xy=(-3.4, 1.4), xytext=(-19.0, -1.2), ha='left', **AN)
ax.set_title('A. Анатомія (базовий масштаб k=1, ~14×20 мм)',
             fontsize=12, weight='bold')
ax.set_xlim(-19.5, 20); ax.set_ylim(-4, 26)

# ══ B. у гнізді: спокій / стиснутий ══════════════════════════════════
ax2 = fig.add_subplot(gs[1])
SW, ZT = hw + 0.1, 15.0          # стінка гнізда, рівень лиця
for s in (+1, -1):
    x0, x1 = s * SW, s * (SW + 2.6)
    wall = sg.Polygon([(x0, -1), (x1, -1), (x1, ZT), (x0, ZT)]).difference(
        sg.box(min(x0, s * (SW + p['b'] + 0.1)), p['zb1'] - 0.05,
               max(x0, s * (SW + p['b'] + 0.1)), p['zb1'] + 1.5))
    ax2.add_patch(MPoly(np.array(wall.exterior.coords), closed=True,
                        fc='#c8ccd4', ec='#7f8c8d', lw=1.2, zorder=1))
ax2.add_patch(MPoly(np.array([(-SW, -1), (SW, -1), (SW, -0.1), (-SW, -0.1)]),
                    closed=True, fc='#c8ccd4', ec='#7f8c8d', lw=1.2, zorder=1))
draw(ax2, body)
for sgn in (+1, -1):             # стиснутий стан пунктиром
    for gm in ([body] if not hasattr(body, 'geoms') else body.geoms):
        ax2.plot(*zip(*bend(gm, p, 0.9, sgn)), color='#c0392b', lw=1.1,
                 ls='--', zorder=5)
ax2.annotate('виїмка в стінці гнізда\n= ПОЗИТИВНИЙ упор угору\n(не тертя!)',
             xy=(SW + 0.4, 13.3), xytext=(1.0, 24.0), ha='center', **AN)
ax2.annotate('щипок ≈ 8 Н за вуса\n(пунктир — стиснутий стан)',
             xy=(6.2, 19.6), xytext=(-13.0, 21.5), ha='left', **AN)
ax2.annotate('ребро впирається\nраніше, ніж ε дійде\nдо межі PETG',
             xy=(2.2, 11.5), xytext=(-13.0, 5.5), ha='left', **AN)
ax2.set_title('B. У гнізді: спокій vs зняття', fontsize=12, weight='bold')
ax2.set_xlim(-13.5, 13.5); ax2.set_ylim(-4, 26)

# ══ C. масштабування ═════════════════════════════════════════════════
ax3 = fig.add_subplot(gs[2])
off = 0
for k, lbl in ((0.8, 'k=0.8 — МІНІМУМ'), (1.0, 'k=1.0 — базовий'), (1.6, 'k=1.6')):
    bk, pk, hwk = clip_body(k)
    bk = saf.translate(bk, xoff=off)
    draw(ax3, bk, fc='#eaf3fb' if k != 1.0 else '#f2f2f4')
    ax3.text(off, -2.0, f'{lbl}\n{2*pk["ww"]:.1f} × {pk["H"]:.1f} мм\n'
                        f'щілина {pk["g"]:.2f} · пружина {pk["t"]:.2f}\n'
                        f'барб {pk["b"]:.2f} · ε = 3.5 %',
             ha='center', va='top', fontsize=9.0)
    off += 2 * pk['ww'] + 15
ax3.text(0.5, 0.99,
         'Лінійне масштабування ЗБЕРІГАЄ деформацію:\n'
         'ε ∝ t·y/L²  →  (k·k)/k² = const  ⇒  ε = 3.5 % на БУДЬ-ЯКОМУ k\n'
         'Сила клацання ∝ k²   (5 Н при k=0.8 · 8 Н при k=1.0 · 20 Н при k=1.6)\n\n'
         'НЕ масштабуються (упираються в сопло 0.4):\n'
         'щілина ≥ 0.7 → k ≥ 0.78     ·     пружина ≥ 0.8 → k ≥ 0.57\n'
         '⇒ k_min ≈ 0.8 (менше — щілина злипнеться в друці).  Угору обмежень нема.',
         transform=ax3.transAxes, ha='center', va='top', fontsize=10.5,
         bbox=dict(boxstyle='round,pad=0.6', fc='#fff8e1', ec='#e0b400'))
ax3.set_title('C. Масштабованість', fontsize=12, weight='bold')
ax3.set_xlim(-12, off - 3); ax3.set_ylim(-13, 46)

for a in (ax, ax2, ax3):
    a.set_aspect('equal'); a.axis('off')
plt.subplots_adjust(left=0.01, right=0.99, top=0.94, bottom=0.02)
plt.savefig('out/sketch_petal_clip.png', dpi=155, facecolor='w')
print('OK out/sketch_petal_clip.png')
