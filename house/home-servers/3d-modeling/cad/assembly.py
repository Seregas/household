"""
assembly.py — збірка корпусу: дно + фронт-панель (+ стінки, коли будуть).
Усі частини в одній системі координат; фланець дна (Z0..3) і низ панелі
займають той самий об'єм Y[-99.4,-96.4] → union зливає їх у моноліт.
Запуск: .venv/bin/python cad/assembly.py  →  out/tray.step / out/tray.stl
"""
import floor
import front
import walls
from exporter import save, save_parts


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
        if not t.is_valid:
            t = t.fix()          # 08.07: fuse на глибині 113.5 віддає
                                 # повний, але invalid солід — лікується
        if t.is_valid and len(t.solids()) > 0 and t.volume > 0.9 * vsum:
            tray = t
    except Exception:
        pass
    if tray is not None:
        print("valid:", tray.is_valid, "| volume:", round(tray.volume, 1))
        save(tray, "tray")
    else:
        print("fuse ненадійний → compound-STEP + manifold-STL")
        save_parts(parts, "tray")
