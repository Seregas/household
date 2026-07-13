"""
anchor_clip.py — зачепи СІТКИ АДДОНІВ (13.07, схема в4 + компроміси в4.1).

  • МІСТОК (bridge_part): 2 жорсткі лижі на обидві колонки, з'єднані
    фланцем-БАРОМ, що сидить у закритій кишені ЗНИЗУ слаба аддона
    (розтяг по Y → стінки кишені, вгору → стеля кишені, вниз при
    знятому аддоні — crush-ребра; у ЗБОРІ бар ковзає по паду дна —
    випасти нікуди). Лижа = довжина отвору + ніші: п'ята впирається в
    задню стінку отвору (стоп назад), кінчик у дно ніші (стоп вперед),
    вгору тримає шельф Z1.5. Друк: ЯК ЗМОДЕЛЬОВАНО, лижами вниз
    (бар — мости ≤3мм між п'ятами, PETG тягне).

  • ЗАЩІПКА (latch_part): 2 ноги-«Т» на спільному корпусі + ричажок-
    перекладина. Корпус = фланець у зенківці ЗВЕРХУ слаба (Z6.9..8);
    пружні корені 2.0(Y)×0.8(Z)×3.0(X) — ε≈4.5% при вивільненні зуба
    1.2 (схемні 0.5×1.0 давали ε≈21% = злам PETG). Зуб уперед під
    шельф, верх Z1.4 (0.1 зазору), полога фаска знизу = клац.
    Друк НА БОЦІ (X-гранню вниз): згин коренів у площині шарів.

  • addon_cuts(ry) — вирізи в слабі майбутніх аддонів під защіпку
    (прорізи ніг + зенківка-канал); поки без споживача.

Кінематика: нахилив ~14° → лижі в отвори і вперед у ніші → опустив
зад → защіпка КЛАЦ (або гачок в5.2 за паз бортика, якщо аддон
виступає за сітку). Знімання: ричажок УПЕРЕД → підняв зад → назад.

Запуск: .venv/bin/python cad/anchor_clip.py
        → out/anchor_bridge.step/.stl + out/anchor_latch.step/.stl
"""
from build123d import *
import params as P
from exporter import save

AMIN = (Align.CENTER, Align.CENTER, Align.MIN)


def bridge_part(ry):
    """Місток-лижі для ряду ry (Y передньої кромки отвору)."""
    col0, col1 = P.ANCHOR_COLS
    w = P.ANCHOR_SKI_W                       # 5.2
    ski_top = P.ANCHOR_SHELF_Z - 0.1         # 1.4 (0.1 під шельфом)
    bar_z0, bar_z1 = P.FRAME_T, P.FRAME_T + P.ANCHOR_BAR_T   # 3.0..4.15
    tip = ry - P.ANCHOR_NICHE_L + P.ANCHOR_SKI_CLR           # −6.3 відн. ry
    heel_r = ry + P.ANCHOR_HOLE_L - 0.1      # +5.9 (0.1 до задньої стінки)
    heel_f = ry + P.ANCHOR_BAR_Y[0] + 0.5    # +4.0 (у футпринті бара)

    with BuildPart() as br:
        # лижа+п'ята: профіль YZ, extrude по X на кожну колонку
        for cx in (col0, col1):
            with BuildSketch(Plane.YZ.offset(cx - w / 2)) as pr:
                with BuildLine():
                    Polyline((tip, 0), (heel_r, 0),
                             (heel_r, bar_z1),        # п'ята до верху бара
                             (heel_f, bar_z1),
                             (heel_f, ski_top),        # верх лижі 1.4
                             (tip + 0.5, ski_top),
                             (tip, 0.9),               # фаска кінчика
                             close=True)
                make_face()
            extrude(pr.sketch, amount=w)
        # БАР: з'єднує п'яти, сидить у кишені знизу слаба аддона
        by0, by1 = ry + P.ANCHOR_BAR_Y[0], ry + P.ANCHOR_BAR_Y[1]
        with Locations(((col0 + col1) / 2, (by0 + by1) / 2, bar_z0)):
            Box(col1 - col0 + w, by1 - by0, P.ANCHOR_BAR_T, align=AMIN)
        # crush-ребра на X-торцях бара (виступ 0.25 → натяг 0.1 у кишені)
        for sx in (-1, +1):
            xe = (col0 + col1) / 2 + sx * (col1 - col0 + w) / 2
            with Locations((xe - sx * (P.ANCHOR_RIB_R - P.ANCHOR_RIB_OFF),
                            (by0 + by1) / 2, bar_z0)):
                Cylinder(P.ANCHOR_RIB_R, P.ANCHOR_BAR_T, align=AMIN)
    return br.part


def latch_part(ry):
    """Защіпка «2 ноги-Т + ричажок» для ряду ry."""
    col0, col1 = P.ANCHOR_COLS
    lw = P.ANCHOR_SKI_W                      # ширина ноги 5.2
    ly0, ly1 = ry + 0.6, ry + 0.6 + P.ANCHOR_LEG_T     # нога Y (1.4)
    tooth_top = P.ANCHOR_SHELF_Z - 0.1       # 1.4
    lever_top = P.SSD_BASE_TOP + P.ANCHOR_LEVER_H      # 13.0

    with BuildPart() as lt:
        for cx in (col0, col1):
            # нога вниз крізь слаб і отвір, суцільно з ричажком (Z0..13)
            with Locations((cx, (ly0 + ly1) / 2, 0)):
                Box(lw, ly1 - ly0, lever_top, align=AMIN)
            # зуб уперед під шельф (фаска знизу = клац при опусканні)
            with BuildSketch(Plane.YZ.offset(cx - lw / 2)) as tp:
                with BuildLine():
                    Polyline((ly0, 0), (ly0, tooth_top),
                             (ry - P.ANCHOR_TOOTH_D, tooth_top),
                             (ry - P.ANCHOR_TOOTH_D, tooth_top - 0.35),
                             close=True)
                make_face()
            extrude(tp.sketch, amount=lw)
            # пружний корінь нога↔тіло (згин у площині шарів при друку
            # на боці): 2.0(Y) × 0.8(Z) × 3.0(X)
            with Locations((cx, ly1 + P.ANCHOR_ROOT_Y / 2, 6.6)):
                Box(P.ANCHOR_ROOT_W, P.ANCHOR_ROOT_Y, P.ANCHOR_ROOT_Z,
                    align=AMIN)
            # тіло защіпки (у прорізі слаба, зазор 0.15 до стінок/дна)
            with Locations((cx, ly1 + P.ANCHOR_ROOT_Y
                            + P.ANCHOR_BODY_L / 2, 3.05)):
                Box(P.ANCHOR_WELL_W - 2 * P.ANCHOR_FIT_CLR,  # 5.3
                    P.ANCHOR_BODY_L, 7.95 - 3.05, align=AMIN)
        # фланець-бар у зенківці ЗВЕРХУ слаба (задня губа тримає;
        # спереду замість губи — корінь: X-перекриття бара)
        fy0 = ry + 0.6 + P.ANCHOR_LEG_T + P.ANCHOR_ROOT_Y      # +4.0
        fy1 = fy0 + P.ANCHOR_BODY_L + P.ANCHOR_CSK_LIP - 0.15  # +8.95
        with Locations(((col0 + col1) / 2, (fy0 + fy1) / 2, 6.9)):
            Box(col1 - col0 + P.ANCHOR_WELL_W + 2 * 1.4
                - 2 * P.ANCHOR_FIT_CLR,                         # ±3.35
                fy1 - fy0, 7.95 - 6.9, align=AMIN)
        # ричажок-перекладина (з'єднує ноги над слабом, 0.3 зазору)
        with Locations(((col0 + col1) / 2, (ly0 + ly1) / 2,
                        P.SSD_BASE_TOP + 0.3)):
            Box(col1 - col0 + lw, ly1 - ly0,
                lever_top - (P.SSD_BASE_TOP + 0.3), align=AMIN)
    return lt.part


def addon_cuts(ry):
    """Вирізи в слабі аддона під защіпку (SUBTRACT у слаб Z3..8)."""
    col0, col1 = P.ANCHOR_COLS
    with BuildPart() as cut:
        for cx in (col0, col1):
            # проріз ноги+тіла: наскрізь по слабу (Z3..8)
            with Locations((cx, (ry + 0.35 + ry + 8.25) / 2, 3.0)):
                Box(P.ANCHOR_WELL_W, 8.25 - 0.35, 5.0, align=AMIN)
        # зенківка-канал фланця (спільна на обидві колонки)
        with Locations(((col0 + col1) / 2,
                        (ry + 3.85 + ry + 9.1) / 2, 8.0 - P.ANCHOR_CSK_T)):
            Box(col1 - col0 + P.ANCHOR_WELL_W + 2 * 1.4,   # ±3.5
                9.1 - 3.85, P.ANCHOR_CSK_T, align=AMIN)
    return cut.part


if __name__ == "__main__":
    br = bridge_part(5.0)          # ряд SSD-блока
    print("bridge valid:", br.is_valid, "| vol:", round(br.volume, 1),
          "| bbox:", br.bounding_box())
    save(br, "anchor_bridge")
    lt = latch_part(65.0)          # демонстраційний ряд
    print("latch  valid:", lt.is_valid, "| vol:", round(lt.volume, 1),
          "| bbox:", lt.bounding_box())
    save(lt, "anchor_latch")
