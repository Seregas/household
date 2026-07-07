"""
ioports.py — параметричні вирізи портів I/O (CW-NAS-ADLP) для власної
фронт-панелі замість сталевого щитка. Джерело правди — P.IO_PORTS
(координати в системі ПЛАТИ, конвертація тут). Використовується:
  • io_strip.py — калібрувальна смужка (швидкий друк, примірка на плату)
  • front.py (майбутнє) — заміна суцільної I/O-апертури на вирізи
"""
from build123d import *
import params as P


def port_shapes():
    """Список (name, Sketch-об'єкт у площині XZ моделі): x = IO_BOARD_X0+bx,
    z = BOARD_Z + bz (+h/2 для rect; для round bz вже центр)."""
    out = []
    c = P.IO_CLEAR
    for name, kind, bx, bz, w, h in P.IO_PORTS:
        x = P.IO_BOARD_X0 + bx
        if kind == "round":
            z = P.BOARD_Z + bz
            with BuildSketch() as s:
                with Locations((x, z)):
                    Circle(w / 2 + c)
        else:
            z = P.BOARD_Z + bz + h / 2
            with BuildSketch() as s:
                with Locations((x, z)):
                    RectangleRounded(w + 2 * c, h + 2 * c,
                                     radius=min(1.2, (h + 2 * c) / 2 - 0.1))
        out.append((name, s.sketch))
    return out
