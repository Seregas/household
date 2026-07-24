"""
snap_kin.py — 2D-ескіз НОВОЇ схеми кріплення аддонів (20.07):
УНІВЕРСАЛЬНИЙ SNAP-FIT ЗАЧЕП (окремий друк, один дизайн).

Архітектура (вводні користувача):
  • зачеп защолкується в аддон ЗАВЖДИ ЗНИЗУ (один тип, без варіантів);
  • на аддоні ДВА зачепи носами в протилежні боки (той самий зачеп,
    розвернутий на 180°);
  • отвір у дні СИМЕТРИЧНИЙ — приймає зачеп будь-якого напрямку.

Переріз YZ (локальний: Y0 = центр отвору, ніс зачепа → −Y):
  • ЗАЧЕП: ГОЛОВА з U-прорізом (2 щоки з бампами 0.35 — клац у виїмки
    кишені аддона знизу) → НОГА t1.0 (пружина, гнеться в Y = площина
    шарів при друці на боці) → ЗУБ (кам 45° знизу, реліз-скіс зверху)
    чіпляється ПІД ПЛИТУ ДНА (низ плити Z1.4 відкритий — ніші не
    потрібні, отвір простий наскрізний).
  • АДДОН: кишеня в слабі знизу (Z3) з виїмками під бампи.
  • ДНО: плита зони Z1.4..3, отвір Y±0.75 (симетричний).

Установка аддона: зачепи вже в аддоні → вертикально вниз → зуби
кам-ляться об кромки отворів (ноги гнуться назустріч) → клац під
плиту. Зняття: впевнене потягування вгору (реліз-скіс) або притиснути
зуби крізь отвори зверху шилом.

Запуск: .venv/bin/python cad/snap_kin.py → out/snap_kin.png
"""
import shapely.geometry as sg
import shapely.affinity as sa
from shapely.ops import unary_union
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

CLR = 0.25        # зазор нога↔отвір на грань
LEG_T = 1.0       # товщина ноги-пружини
LEG_ROOT_Z = 6.0  # корінь пружини (низ голови)
TOOTH_TIP = 1.5   # виліт кінчика зуба від осі
# отвір ШИРШИЙ за ногу+CLR: при прогині 0.45 тил ноги (0.5+0.45=0.95)
# мусить лишатись у отворі — інакше нога впирається в протилежну кромку
HOLE_HALF = 1.05  # півширина отвору (симетричний, двонаправлений)
ENGAGE = TOOTH_TIP - HOLE_HALF          # зачеплення = інтерференція каму
LEG_L = LEG_ROOT_Z - 1.4                # робоча довжина пружини
EPS = 1.5 * LEG_T * ENGAGE / LEG_L**2   # деформація при клацанні

# --- зачеп (ніс → −Y) ------------------------------------------------
HEAD = sg.box(-2.7, 6.0, 2.7, 7.2).difference(
    sg.box(-0.6, 6.0, 0.6, 7.3))                       # U-проріз → 2 щоки
BUMPS = unary_union([sg.box(-3.05, 6.4, -2.7, 6.9),
                     sg.box(2.7, 6.4, 3.05, 6.9)])     # клац у кишеню
LEG = sg.box(-0.5, 0.2, 0.5, 6.0)
TOOTH = sg.Polygon([(-0.5, 0.2), (-TOOTH_TIP, 0.9),    # кам 45° знизу
                    (-TOOTH_TIP, 1.05),                # робоча грань
                    (-0.5, 1.4)])                      # реліз-скіс ~25°
SNAP = unary_union([HEAD, BUMPS, LEG, TOOTH]).buffer(0)

# --- аддон: слаб з кишенею знизу ------------------------------------
POCKET = unary_union([
    sg.box(-2.85, 3.0, 2.85, 7.35),                    # тіло голови
    sg.box(-3.25, 6.3, -2.85, 7.0),                    # виїмки бампів
    sg.box(2.85, 6.3, 3.25, 7.0),
])
SLAB = sg.box(-8.0, 3.0, 12.0, 8.0).difference(POCKET)

# --- дно: плита зони з симетричним отвором ---------------------------
PLATE = sg.box(-12.0, 1.4, 12.0, 3.0).difference(
    sg.box(-HOLE_HALF, 1.3, HOLE_HALF, 3.1))

# --- діагностика -----------------------------------------------------
print(f"зачеплення під плитою: {ENGAGE:.2f} мм/зачеп (×2 зачепи)")
print(f"пружина: t{LEG_T} L{LEG_L:.1f} → ε при клацанні ≈ {EPS*100:.1f}% "
      "(транзієнт; прецеденти проєкту 2.7–4.5%)")
import math
flex_deg = math.degrees(math.atan(ENGAGE / LEG_L))
flexed = sa.rotate(unary_union([LEG, TOOTH]), flex_deg,
                   origin=(0, LEG_ROOT_Z))
print("зігнута нога проходить отвір:",
      "ТАК" if flexed.intersection(PLATE).area < 0.02 else "НІ",
      f"(залишок {flexed.intersection(PLATE).area:.3f})")
print("дзеркальний зачеп у тому ж отворі: зуб тип",
      f"{TOOTH_TIP:.2f} vs кромка {HOLE_HALF} → зачеплення те саме")
for name, dy, dz in (("вбік ±Y0.5", 0.5, 0), ("вгору +Z0.5", 0, 0.5)):
    hit = sa.translate(SNAP, dy, dz).intersection(PLATE)
    print(f"стоп {name}: перетин {hit.area:.2f}",
          [round(v, 2) for v in hit.bounds] if hit.area else "")

# --- рендер ----------------------------------------------------------
def draw(ax, geom, fc, ec, alpha=1.0, ls="-"):
    for g in (geom.geoms if hasattr(geom, "geoms") else [geom]):
        if g.is_empty or not isinstance(g, sg.Polygon):
            continue
        if fc:
            ax.fill(*g.exterior.xy, fc=fc, ec=ec, lw=1.0, alpha=alpha)
        else:
            ax.plot(*g.exterior.xy, color=ec, lw=0.9, ls=ls)


fig, axs = plt.subplots(1, 2, figsize=(13, 6), sharey=True)
for ax, flip, title in ((axs[0], 1, "зачеп «носом уперед» (−Y)"),
                        (axs[1], -1, "ТОЙ САМИЙ зачеп розвернутий 180°")):
    s = sa.scale(SNAP, flip, 1, origin=(0, 0))
    sl = sa.scale(SLAB, flip, 1, origin=(0, 0))
    draw(ax, PLATE, "#b0b0b0", "#555")
    draw(ax, sl, "#e8a869", "#8a5a20", alpha=0.85)
    draw(ax, s, "#7fbf7f", "#2e7d32")
    fl = sa.translate(
        sa.scale(sa.rotate(unary_union([LEG, TOOTH]), flex_deg,
                           origin=(0, LEG_ROOT_Z)), flip, 1, origin=(0, 0)),
        0, 1.2)
    draw(ax, fl, None, "#2e7d32", ls="--")
    ax.annotate("", xy=(flip * 5.0, 3.6), xytext=(flip * 5.0, 8.6),
                arrowprops=dict(arrowstyle="->", color="#2e7d32", lw=1.5))
    ax.text(-11.5, 2.0, "плита дна Z1.4..3", fontsize=8)
    ax.text(flip * 4.5 - 3.5, 8.4, "слаб аддона", fontsize=8,
            color="#7a4a10")
    ax.set_xlim(-12.5, 12.5)
    ax.set_ylim(-1.5, 10.5)
    ax.set_aspect("equal")
    ax.grid(alpha=0.3)
    ax.set_title(title, fontsize=10)
    ax.set_xlabel("Y локальний")
axs[0].set_ylabel("Z")
fig.suptitle("Універсальний snap-fit зачеп: знизу в аддон (щоки+бампи), "
             "вертикально в дно (нога+зуб)", fontsize=11)
fig.tight_layout()
fig.savefig("out/snap_kin.png", dpi=130)
print("збережено out/snap_kin.png")
