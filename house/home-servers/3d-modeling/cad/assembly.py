"""
assembly.py — збірка корпусу: дно + фронт-панель (+ стінки, коли будуть).
Усі частини в одній системі координат; фланець дна (Z0..3) і низ панелі
займають той самий об'єм Y[-99.4,-96.4] → union зливає їх у моноліт.
Запуск: .venv/bin/python cad/assembly.py  →  out/tray.step / out/tray.stl
"""
import floor
import front
from exporter import save

if __name__ == "__main__":
    parts = [floor.build(), front.build()]
    tray = parts[0]
    for p in parts[1:]:
        tray = tray + p           # OCC fuse
    print("valid:", tray.is_valid, "| volume:", round(tray.volume, 1))
    save(tray, "tray")
