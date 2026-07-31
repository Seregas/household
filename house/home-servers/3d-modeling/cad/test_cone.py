"""
test_cone.py — КУПОН круглого кріплення, в2 (31.07, після тесту №1:
«зламав коли вставляв… ніжки слабкі і зачеп слабкий… більший конус,
щоб полегшити вставку… 6 ніжок забагато, зробимо 4 сектори»).

ЧОМУ ЛАМАВСЯ в1 (арифметика, не здогад): пружна довжина пелюстки була
від прорізу Z3.6 до барба Z1.0 = 2.6мм, прогин заходу 0.7 →
  ε = 1.5·t·δ/L² = 1.5·1.9·0.7/2.6² = 29%   (PETG рветься ~7%)
Товщі ніжки зробили б ГІРШЕ (ε ∝ t). Лікується ДОВЖИНОЮ (ε ∝ 1/L²).
Корінь короткості — архітектурний: у в1 фланець сидів на верху ДНА,
тому пелюстка мусила вміститись у 3мм. Тепер кліп проходить КРІЗЬ БОС
БЛОКА (як у test_petal) → пружна довжина = висота боса.

Три деталі:
  out/test_cone_floor.stl — 3мм дно: отвір ⌀6.4 (мовка Z2..3, фаска
      заходу) + нижня розточка ⌀9.6 (Z0..2) → ЛЕДЖ @Z2.0. Розточка
      відкрита знизу — палець стискає барби на зняття.
  out/test_cone_block.stl — шматок блока: база Z3..4.4 + бос до Z9.0,
      наскрізний отвір ⌀6.6 (центрує шток).
  out/test_cone_clip.stl  — кліп: конічна голова (сама собі 45°-фаска,
      самонесуча) + шток ⌀6.0 + 4 сектори з барбом ⌀9.0.

Зміни проти в1:
  • 4 сектори замість 6 (в1: 3 бокси ЧЕРЕЗ ЦЕНТР = 6 прорізів).
  • пружна довжина 2.6 → 7.0мм, ε заходу 29% → 4.8%.
  • зачеплення за ледж 0.9 → 1.3мм (+44%): барб ⌀9.0 проти отвору ⌀6.4.
  • робоча грань барба — UNDERCUT −5° (в1 була плоска: тертя, сповзає).
  • РАМПА заходу: в1 від Z0.5 до 0.75 (74° від осі — «не влазить»);
    тепер двоступенева від Z0.0 до Z2.0, робоча ділянка ~45° від осі.
  • кінчик ⌀5.4 проти отвору ⌀6.4 — зазор 0.5/бік попадає й у «не дуже
    круглий» надрукований отвір (в1 було 0.2 — звідси й перекіс).

Друк: кліп КІНЧИКОМ УНИЗ (рампа й конічна голова розширюються вгору —
самонесучі); дно/блок — пласко. Ледж перпендикулярний осі → у корпусі
FACE_DOWN це вертикальна стінка, без навісу.

Тест: втиснути кліп крізь бос → барби стискаються ⌀9.0→6.4 → заскок у
розточку під ледж → тягнути (має тримати); зняти — палець знизу.

Запуск: .venv/bin/python cad/test_cone.py
"""
import math
from build123d import *
from exporter import save

# ── ДНО ──
PLATE_T  = 3.0
BORE_D   = 6.4     # мовка-напрямна (Z LEDGE..верх)
LEDGE_Z  = 2.0     # ледж = стеля розточки (барб хапає під нього)
RECESS_D = 9.6     # нижня розточка (барби розкриваються сюди)
BORE_CH  = 0.5     # фаска заходу на верхній кромці отвору

# ── БЛОК ──
BLK_Z0, BLK_Z1 = PLATE_T, 4.4          # база (лежить на дні)
BOSS_Z1  = 9.0                          # верх боса = корінь пелюсток
BLK_BORE = 6.6                          # наскрізний отвір (центрує шток)

# ── КЛІП ──
STEM_D   = 6.0     # шток (у мовці 6.4 → 0.2/бік на «некруглість»)
CORE_D   = 3.6     # центральний отвір → стінка пелюстки 1.2
BARB_D   = 9.0     # вершина барба (в розточці 9.6 → 0.3)
CATCH_Z  = LEDGE_Z                      # робоча грань — на леджі
UNDERCUT = 0.12    # підйом зовн. краю робочої грані (≈ −5°)
BARB_BOTZ= 1.75    # низ вертикальної грані барба
TIP_D    = 5.4     # кінчик (< BORE 6.4 → вільно попадає)
TIP_Z    = 0.0     # врівень з низом дна — знизу не стирчить
RAMP_MZ  = 0.45    # злам двоступеневої рампи
HEAD_Z0, HEAD_Z1 = BOSS_Z1, 11.0        # конічна голова (45°, самонесуча)
HEAD_D   = 10.0
N_SECT   = 4       # СЕКТОРІВ (2 прорізи навхрест)
SLOT_W   = 1.2     # ширина прорізу (сопло 0.4 → мінімум ~0.7)


def floor_chunk():
    with BuildPart() as p:
        with Locations((0, 0, PLATE_T / 2)):
            Box(26, 26, PLATE_T)
        with Locations((0, 0, (LEDGE_Z + PLATE_T) / 2 + 0.01)):
            Cylinder(BORE_D / 2, PLATE_T - LEDGE_Z + 0.02, mode=Mode.SUBTRACT)
        with Locations((0, 0, LEDGE_Z / 2)):
            Cylinder(RECESS_D / 2, LEDGE_Z, mode=Mode.SUBTRACT)
        # фаска заходу на верхній кромці мовки
        with BuildSketch(Plane.XZ) as ch:
            with BuildLine():
                Polyline((BORE_D / 2, PLATE_T + 0.01),
                         (BORE_D / 2 + BORE_CH, PLATE_T + 0.01),
                         (BORE_D / 2, PLATE_T - BORE_CH), close=True)
            make_face()
        revolve(ch.sketch, axis=Axis.Z, mode=Mode.SUBTRACT)
    return p.part


def block_chunk():
    """База на дні + бос; наскрізний отвір центрує шток кліпа."""
    with BuildPart() as p:
        with Locations((0, 0, (BLK_Z0 + BLK_Z1) / 2)):
            Box(24, 20, BLK_Z1 - BLK_Z0)
        with Locations((0, 0, (BLK_Z1 + BOSS_Z1) / 2)):
            Box(16, 14, BOSS_Z1 - BLK_Z1)
        with Locations((0, 0, (BLK_Z0 + BOSS_Z1) / 2)):
            Cylinder(BLK_BORE / 2, BOSS_Z1 - BLK_Z0 + 0.02, mode=Mode.SUBTRACT)
    return p.part


def clip():
    with BuildPart() as p:
        with BuildSketch(Plane.XZ) as s:
            with BuildLine():
                Polyline(
                    (0.0, HEAD_Z1),
                    (HEAD_D / 2, HEAD_Z1),              # верх голови
                    (STEM_D / 2, HEAD_Z0),              # конус голови 45°
                    (STEM_D / 2, CATCH_Z + UNDERCUT),   # шток униз
                    (BARB_D / 2, CATCH_Z),              # UNDERCUT-грань (−5°)
                    (BARB_D / 2, BARB_BOTZ),            # вертикаль барба
                    (TIP_D / 2, RAMP_MZ),               # РАМПА (робоча ~45°)
                    (TIP_D / 2 - 0.9, TIP_Z),           # вхідний конус
                    (0.0, TIP_Z),
                    close=True)
            make_face()
        revolve(axis=Axis.Z)
        # центральний отвір (тоншає пелюстку → менша ε)
        with Locations((0, 0, (0.5 + HEAD_Z1) / 2)):
            Cylinder(CORE_D / 2, HEAD_Z1 - 0.5 + 0.01, mode=Mode.SUBTRACT)
        # прорізи: N_SECT/2 боксів ЧЕРЕЗ ЦЕНТР (кожен дає 2 прорізи)
        for k in range(N_SECT // 2):
            with Locations(Rotation(0, 0, 180.0 / (N_SECT // 2) * k)):
                with Locations((0, 0, (TIP_Z - 0.1 + BOSS_Z1) / 2)):
                    Box(BARB_D + 2, SLOT_W, BOSS_Z1 - TIP_Z + 0.1,
                        mode=Mode.SUBTRACT)
    return p.part


if __name__ == "__main__":
    t = (STEM_D - CORE_D) / 2                 # товщина стінки пелюстки
    L = BOSS_Z1 - CATCH_Z                     # пружна довжина
    d = (BARB_D - BORE_D) / 2                 # прогин заходу
    eps = 1.5 * t * d / L ** 2
    ramp = math.degrees(math.atan(((BARB_D - TIP_D) / 2) / (BARB_BOTZ - RAMP_MZ)))
    print(f"секторів {N_SECT} | стінка {t:.2f} | пружна довжина {L:.1f} | "
          f"прогин {d:.2f} → ε={eps*100:.1f}% (PETG межа ~7%)")
    print(f"зачеплення за ледж {(BARB_D-BORE_D)/2:.2f}мм (в1 було 0.90) | "
          f"рампа {ramp:.0f}° від осі (в1 74°) | кінчик ⌀{TIP_D} в отвір ⌀{BORE_D}")
    for name, fn in (("test_cone_clip", clip),
                     ("test_cone_floor", floor_chunk),
                     ("test_cone_block", block_chunk)):
        part = fn()
        print(f"{name:18s} valid={part.is_valid} vol={part.volume:8.1f} "
              f"bbox={part.bounding_box()}")
        save(part, name)
