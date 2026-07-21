"""
probe_snap.py — зонди посадки snap-fit зачепів (20.07 в6.1, Т-паз;
в6.3 — клин-дотиск):
  1) зачеп у слоті дна: перетин із floor = ЛИШЕ клин-переднатяг
     (~0.008 мм³/зачеп — клин над зламом 1.40 > низ мембрани 1.4 на кромці
     слота, ЗАДУМ в6.3; до в6.3 було 0);
  2) зачеп у Т-пазу блока: перетин = ЛИШЕ 4 лінзи-переднатяги у стелю
     (~0.1-0.2 мм³, ЗАДУМ в6.6 анти-проворот; горбик дотичний позаду);
  3) стоп ВГОРУ (збірка): зачеп +Z0.5 → зуб упирається в мембрану (>0);
  4) стоп ВБІК: зачеп ±Y0.6 → нога/зуб у стінку слота дна (>0);
  5) нижче Z0 нічого не стирчить (bbox);
  6) блок ∩ floor = 0;
  7) Т-паз тримає зачеп у БЛОЦІ: вниз −Z0.3 → полиці (>0),
     вгору +Z0.5 → стеля (>0), до упору по X 0.5 → глуха стінка (>0),
     назад до входу 0.5 → горбик (>0, мале — клац-страховка);
  8) висування по X у ЗБОРІ: зачеп ±X0.6 → стінка слота дна (>0).
Запуск: .venv/bin/python cad/probe_snap.py
"""
from build123d import *
import params as P
import floor
import ssd_block
import snap_clip


def vol(a, b):
    r = a.intersect(b)
    if r is None:
        return 0.0
    if hasattr(r, "volume"):
        return r.volume
    return sum(s.volume for s in r)  # intersect може віддати ShapeList


def entry_of(ccx):
    """Бік входу Т-паза: −1 = з лівої грані слаба, +1 = з правої."""
    bx0f, bx1f = P.SSD_BASE_X
    return -1 if (ccx - bx0f) < (bx1f - ccx) else +1


if __name__ == "__main__":
    fl = floor.build()
    blk = ssd_block.build()
    clips = [snap_clip.placed(cx, ry, nose) for cx, ry, nose in P.SNAP_SSD_CELLS]

    print("── 1) зачеп ∩ floor (лише клин-переднатяг ~0.008 мм³ (в6.4)) ──")
    for (cell, c) in zip(P.SNAP_SSD_CELLS, clips):
        print(f"  cell {cell}: {vol(fl, c):.3f} мм³")

    print("── 2) зачеп ∩ block (Т-паз; лише 4 лінзи-переднатяги в6.6) ──")
    for (cell, c) in zip(P.SNAP_SSD_CELLS, clips):
        print(f"  cell {cell}: {vol(blk, c):.3f} мм³")

    print("── 3) стоп вгору (збірка): зачеп +Z0.5 → зуб у мембрану (>0) ──")
    for (cell, c) in zip(P.SNAP_SSD_CELLS, clips):
        print(f"  cell {cell}: {vol(fl, c.translate((0, 0, 0.5))):.3f} мм³")

    print("── 4) стоп вбік: зачеп ±Y0.6 → нога/зуб у стінку (>0) ──")
    for (cell, c) in zip(P.SNAP_SSD_CELLS, clips):
        vp = vol(fl, c.translate((0, 0.6, 0)))
        vm = vol(fl, c.translate((0, -0.6, 0)))
        print(f"  cell {cell}: +Y {vp:.3f} / -Y {vm:.3f} мм³")

    print("── 5) bbox зачепів (низ має бути ≥ 0) ──")
    for (cell, c) in zip(P.SNAP_SSD_CELLS, clips):
        bb = c.bounding_box()
        print(f"  cell {cell}: Z {bb.min.Z:.2f}..{bb.max.Z:.2f}")

    print("── 6) блок ∩ floor (посадка блока; лише відомі дотики) ──")
    print(f"  {vol(fl, blk):.3f} мм³")

    print("── 7) Т-паз тримає зачеп у блоці (всі > 0) ──")
    for (cell, c) in zip(P.SNAP_SSD_CELLS, clips):
        ent = entry_of(cell[0])
        vdn = vol(blk, c.translate((0, 0, -0.3)))          # полиці
        vup = vol(blk, c.translate((0, 0, 0.5)))           # стеля
        vst = vol(blk, c.translate((-ent * 0.5, 0, 0)))    # глухий упор
        vbk = vol(blk, c.translate((ent * 0.5, 0, 0)))     # горбик
        print(f"  cell {cell}: вниз {vdn:.3f} / вгору {vup:.3f}"
              f" / упор {vst:.3f} / горбик {vbk:.3f} мм³")

    print("── 8) висування по X у зборі: зачеп ±X0.6 → слот дна (>0) ──")
    for (cell, c) in zip(P.SNAP_SSD_CELLS, clips):
        vp = vol(fl, c.translate((0.6, 0, 0)))
        vm = vol(fl, c.translate((-0.6, 0, 0)))
        print(f"  cell {cell}: +X {vp:.3f} / -X {vm:.3f} мм³")
