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
    """Список (name, Sketch-об'єкт у площині XZ моделі): x = IO_SHIELD_X0+sx,
    z = IO_SHIELD_Z0 + sz (+h/2 для rect; для round sz вже центр)."""
    out = []
    c = P.IO_CLEAR
    for name, kind, sx, sz, w, h in P.IO_PORTS:
        x = P.IO_SHIELD_X0 + sx
        if kind == "round":
            z = P.IO_SHIELD_Z0 + sz
            with BuildSketch() as s:
                with Locations((x, z)):
                    Circle(w / 2 + c)
        else:
            z = P.IO_SHIELD_Z0 + sz + h / 2
            # Type-C: R2 (фідбек примірки 08.07), решта R1.2
            rr = 2.0 if name == "typec" else 1.2
            with BuildSketch() as s:
                with Locations((x, z)):
                    RectangleRounded(w + 2 * c, h + 2 * c,
                                     radius=min(rr, (h + 2 * c) / 2 - 0.1))
        out.append((name, s.sketch))
    return out
