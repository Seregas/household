"""
test_latch.py — ШВИДКИЙ ТЕСТ КРІПЛЕННЯ SSD-БЛОКА (20.07, snap-fit):
вирізає з готових тіл лише зону зачепів, щоб надрукувати і перевірити
механіку до друку повного корпусу.

Деталі:
  • test_tray  — шматок дна зі слотами SNAP-сітки (колонки 122.8/130.6,
    ряди 11/41/71) + підмембранні кишені + смужка правої стінки
    (X 114..137.95, Y −1..75, Z 0..12).
  • test_block — SSD-блок, зрізаний по Z8.6: слаб з обома Т-пазами
    зачепів (Y11 вхід зліва, Y71 вхід справа) і горбиками-стопорами.
  • snap_clip — сам зачеп (2 шт мінімум: ніс −Y і ніс +Y — та сама
    деталь, розвернута).

Друк:
  • test_tray — СТОЯЧИ на передньому торці (Y вниз), як корпус лицем
    вниз: слоти і кишені друкуються в тій самій орієнтації, що в
    бойовому друці (інакше тест бреше про зазори). Brim!
  • test_block — дном вниз, як бойовий блок (стеля кишень Z7.35 — міст).
  • snap_clip — НА БОЦІ (X-гранню вниз), згин ноги в площині шарів.
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
    # 20.07: зона снап-сітки — ряди 11/41/71 обох колонок; верх 12
    # (дно + кишені + низ стінки; вище для тесту нічого нема)
    piece = _clip(tray, 114.0, -1.0, -0.5, 137.95, 75.0, 12.0)
    print("tray piece: valid", piece.is_valid)
    save(piece, "test_tray")

    blk = ssd_block.build()
    # 20.07: зріз по Z8.6 — слаб (3..8) з Т-пазами зачепів (стеля 7.35)
    bpiece = _clip(blk, 114.0, -2.0, -0.5, 137.0, 75.0, 8.6)
    print("block piece: valid", bpiece.is_valid)
    save(bpiece, "test_block")
