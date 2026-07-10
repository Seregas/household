"""
test_latch.py — ШВИДКИЙ ТЕСТ КРІПЛЕННЯ SSD-БЛОКА (09.07): вирізає з
готових тіл лише зону защіпок, щоб надрукувати і перевірити механіку
до друку повного корпусу.

Дві деталі:
  • test_tray  — шматок корпусу: дно зі скобами + трамплін + бортик з
    пазом + смужка правої стінки (X 111..137.95, Y −8..114, Z 0..30).
  • test_block — SSD-блок, зрізаний по Z13.8: база, полози, язики з
    горбиками, задні гачки з поличками, низ рейок (ложа/палуби вище —
    для тесту кріплення не потрібні).

Друк:
  • test_tray — СТОЯЧИ на передньому торці (Y вниз), як корпус лицем
    вниз: скоби і паз друкуються в тій самій орієнтації, що в бойовому
    друці (інакше тест бреше про зазори). Brim!
  • test_block — дном вниз, як бойовий блок.
Запуск: .venv/bin/python cad/test_latch.py → out/test_tray.* out/test_block.*
"""
from build123d import *
import params as P
import floor
import walls
import ssd_block
from exporter import save


def _clip(part, x0, y0, z0, x1, y1, z1):
    with BuildPart() as bx:
        with Locations(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2)):
            Box(x1 - x0, y1 - y0, z1 - z0)
    res = part & bx.part
    return res.fix() if not res.is_valid else res


if __name__ == "__main__":
    tray = (floor.build() + walls.build()).fix()
    # 10.07: верх 30→25 — похила кромка стінки у стоячому друці
    # провокувала зайві підтримки; для тесту вистачає паза (5) і скоб
    piece = _clip(tray, 111.0, -8.0, -0.5, 137.95, 114.0, 25.0)
    print("tray piece: valid", piece.is_valid)
    save(piece, "test_tray")

    blk = ssd_block.build()
    # 10.07: верх 13.8→10.3 — пеньки рейок і похилі продовження
    # стінок малювали підтримки; руки гачків до 10.1 — нижче не можна
    bpiece = _clip(blk, 110.0, -2.0, 2.0, 136.0, 118.0, 10.3)
    print("block piece: valid", bpiece.is_valid)
    save(bpiece, "test_block")
