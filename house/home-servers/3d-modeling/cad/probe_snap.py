"""
probe_snap.py — зонди посадки snap-fit зачепів (20.07):
  1) зачеп у слоті дна: перетин із floor = 0 (нога в слоті з зазором,
     зуб у підмембранній кишені);
  2) зачеп у кишені блока: перетин = ЛИШЕ crush-ребра (~0.1 мм³/ребро);
  3) стоп ВГОРУ: зачеп +Z0.5 → зуб упирається в мембрану (перетин > 0);
  4) стоп ВБІК (блок +Y0.5 із зачепами): нога → стінка слота (перетин > 0);
  5) нижче Z0 нічого не стирчить (bbox).
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


if __name__ == "__main__":
    fl = floor.build()
    blk = ssd_block.build()
    clips = [snap_clip.placed(cx, ry, nose) for cx, ry, nose in P.SNAP_SSD_CELLS]

    print("── 1) зачеп ∩ floor (посадка; має бути 0) ──")
    for (cell, c) in zip(P.SNAP_SSD_CELLS, clips):
        print(f"  cell {cell}: {vol(fl, c):.3f} мм³")

    print("── 2) зачеп ∩ block (лише crush-ребра) ──")
    for (cell, c) in zip(P.SNAP_SSD_CELLS, clips):
        print(f"  cell {cell}: {vol(blk, c):.3f} мм³")

    print("── 3) стоп вгору: зачеп +Z0.5 → зуб у мембрану (>0) ──")
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

    print("── 7) блок ∩ зачепи у зборі (голова в кишені; crush) ──")
    for (cell, c) in zip(P.SNAP_SSD_CELLS, clips):
        print(f"  cell {cell}: {vol(blk, c):.3f} мм³")
