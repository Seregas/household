"""
assembly.py — збірка корпусу: дно + фронт-панель (+ стінки, коли будуть).
Усі частини в одній системі координат; фланець дна (Z0..3) і низ панелі
займають той самий об'єм Y[-99.4,-96.4] → union зливає їх у моноліт.
Запуск: .venv/bin/python cad/assembly.py  →  out/tray.step / out/tray.stl
"""
import floor
import front
import walls
import params as P
from build123d import Cylinder, Location, Mode, Align
from exporter import save, save_parts


def _head_holes(t):
    """Отвори під головки M3 постаментів диска A — НАСКРІЗЬ у збірці:
    плінтус стінки (X132.9.., Z0..5) перекривав їхній правий край
    (фідбек 06.07: 133.57/-10.19/0). Різ до низу палуби (Z8)."""
    amin = (Align.CENTER, Align.CENTER, Align.MIN)
    for yb in (P.SSD_Y[1] - 14.0, P.SSD_Y[1] - 90.6):
        c = Location((sum(P.SSD_CH_A) / 2, yb, -1)) * Cylinder(
            P.SSD_HEAD_D / 2, 9.0, align=amin)
        t = (t - c).fix()
    return t

if __name__ == "__main__":
    # ⚠️ OCC-fuse із філетованими стінками ненадійний (тихо викидає соліди
    # або видає невалідний результат). Пробуємо fuse з контролем об'єму;
    # при провалі — save_parts: compound-STEP + trimesh/manifold-STL.
    parts = [floor.build(), walls.build(), front.build()]
    vsum = sum(p.volume for p in parts)
    tray = None
    try:
        t = parts[0]
        for p in parts[1:]:
            t = t + p
        if t.is_valid and len(t.solids()) > 0 and t.volume > 0.9 * vsum:
            tray = _head_holes(t)
    except Exception:
        pass
    if tray is not None:
        print("valid:", tray.is_valid, "| volume:", round(tray.volume, 1))
        save(tray, "tray")
    else:
        print("fuse ненадійний → compound-STEP + manifold-STL")
        save_parts(parts, "tray")
