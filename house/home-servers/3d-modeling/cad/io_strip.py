"""
io_strip.py — КАЛІБРУВАЛЬНА СМУЖКА I/O: тонка пластинка з вирізами портів
за P.IO_PORTS. Друк ~20-30хв, приміряється прямо на плату; поправки
(«hdmi на 1.5 вліво») вносяться в params.py.
Запуск: .venv/bin/python cad/io_strip.py → out/io_strip.stl
"""
from build123d import *
import params as P
import ioports
from exporter import save


def build():
    xs = [P.IO_BOARD_X0 + p[2] for p in P.IO_PORTS]
    x0, x1 = min(xs) - 12.0, max(xs) + 12.0
    z0, z1 = P.BOARD_Z - 4.0, P.BOARD_Z + 30.0
    with BuildPart() as sp:
        with BuildSketch(Plane.XZ) as base:
            with Locations(((x0 + x1) / 2, (z0 + z1) / 2)):
                RectangleRounded(x1 - x0, z1 - z0, radius=2.0)
            for name, sk in ioports.port_shapes():
                add(sk, mode=Mode.SUBTRACT)
        extrude(base.sketch, amount=2.0)
        # ніжка-упор знизу: спирається на край плати → низи вирізів
        # відлічуються від поверхні плати (примірка без рук)
        with BuildSketch(Plane.XZ) as foot:
            with Locations(((x0 + x1) / 2, P.BOARD_Z - 2.0)):
                Rectangle(x1 - x0, 4.0)
            # розриви ніжки: TF-слот знизу плати (і всі порти з bz<0)
            for name, kind, bx, bz, w, h in P.IO_PORTS:
                if kind == "rect" and bz < 0:
                    with Locations((P.IO_BOARD_X0 + bx, P.BOARD_Z - 2.0)):
                        Rectangle(w + 6.0, 4.2, mode=Mode.SUBTRACT)
        extrude(foot.sketch, amount=-3.0)
    return sp.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "io_strip")
