"""
lsi_clip.py — ЗНІМНА ВИДЕЛКА-ЗАЩІПКА ПЛАТИ LSI (09.07 в2, «замість
вбудованої»): на панелі виделки НЕМА — плата ставиться вільно, потім ця
деталь опускається ЗГОРИ в колодязь крізь брову, її паз (лійка знизу)
захоплює передній край карти, а барби клацають у кишені стінок колодязя.

Конструкція: тіло ±3.05 × y 3.9 × Z73.25..88.75 (верх урівень панелі);
низ = дві щоки 2.2 з пазом 1.7 (лійка-розтруб знизу) + суцільна
перемичка-упор 2мм спереду (край карти впирається по Y); верх карти на
LSI_BRK_TOP=80.75 накритий суцільним центром (карта замкнена вертикально);
два бічні прорізи 0.5 формують ПРОНГИ 1.7 (згин у площині шарів при
друку лицем униз) з барбами 0.35/45°. Знімання — підважити плоскою
викруткою за виїмку на задньому верхньому краї.
Запуск: .venv/bin/python cad/lsi_clip.py → out/lsi_clip.step/stl
Координати збірки; друк — передньою (плоскою) гранню вниз.
"""
from build123d import *
import params as P
from exporter import save

AMIN = (Align.CENTER, Align.CENTER, Align.MIN)


def build():
    hw = P.LSI_SLOT_W / 2           # півширина паза 0.85
    bw = P.LSI_FORK_W               # щока 2.2
    xw = hw + bw                    # півширина тіла 3.05
    y0, y1 = -96.35, -92.45         # тіло по Y (0.05 від тилу панелі)
    zb = P.LSI_FORK_Z[0] - 0.5      # низ щік 73.25
    zt = P.PANEL_H                  # верх урівень з панеллю
    z_card = P.LSI_BRK_TOP + 0.25   # стеля над картою 81.0
    with BuildPart() as clip:
        with Locations((P.LSI_X, (y0 + y1) / 2, zb)):
            Box(2 * xw, y1 - y0, zt - zb, align=AMIN)
        # паз карти: від перемички-упора (−94.3) назад НАСКРІЗЬ, до
        # стелі z_card; вище — суцільний центр (замок карти)
        with Locations((P.LSI_X, ((P.FRONT_Y + P.FRONT_PANEL_T + P.LSI_WEB_T + 0.1) + y1 + 1) / 2, zb - 0.5)):
            Box(2 * hw, y1 + 1 - (P.FRONT_Y + P.FRONT_PANEL_T + P.LSI_WEB_T + 0.1), z_card - (zb - 0.5),
                align=AMIN, mode=Mode.SUBTRACT)
        # лійка-розтруб знизу паза (самоцентрування на краю карти)
        for sx in (-1, 1):
            with BuildSketch(Plane.XZ.offset(94.3)) as fl:
                with BuildLine():
                    Polyline((P.LSI_X + sx * hw, zb + 2.0),
                             (P.LSI_X + sx * (hw + 0.8), zb - 0.01),
                             (P.LSI_X + sx * hw, zb - 0.01),
                             close=True)
                make_face()
            extrude(fl.sketch, amount=-(y1 + 1 - (P.FRONT_Y + P.FRONT_PANEL_T + P.LSI_WEB_T + 0.1)),
                    mode=Mode.SUBTRACT)
        # фаска знизу перемички-упора (з'їзд на край карти по Y)
        with BuildSketch(Plane.YZ.offset(P.LSI_X - hw)) as wch:
            with BuildLine():
                Polyline(((P.FRONT_Y + P.FRONT_PANEL_T + P.LSI_WEB_T + 0.1), zb + 1.2), ((P.FRONT_Y + P.FRONT_PANEL_T + P.LSI_WEB_T + 0.1), zb - 0.01),
                         (-95.5, zb - 0.01), close=True)
            make_face()
        extrude(wch.sketch, amount=2 * hw, mode=Mode.SUBTRACT)
        # бічні прорізи 0.5 → пружні ПРОНГИ 1.7 (центр лишається
        # суцільним на всю глибину — стеля над картою цілa)
        for sx in (-1, 1):
            with Locations((P.LSI_X + sx * (hw + 0.25), (y0 + y1) / 2,
                            z_card + 0.2)):
                Box(0.5, y1 - y0 + 1, zt - z_card + 1,
                    align=AMIN, mode=Mode.SUBTRACT)
        # барби 0.35 (45/45) на зовнішніх гранях пронгів
        for sx in (-1, 1):
            xb = P.LSI_X + sx * xw
            with BuildSketch(Plane.XZ.offset(95.4)) as brb:
                with BuildLine():
                    Polyline((xb, 86.2), (xb + sx * 0.35, 86.95),
                             (xb, 87.7), close=True)
                make_face()
            extrude(brb.sketch, amount=-(95.4 - 93.4))
        # виїмка-підважка на задньому верхньому краї
        with Locations((P.LSI_X, y1 - 1.0, zt - 1.2)):
            Box(4.0, 1.6, 1.3 + 1, align=AMIN, mode=Mode.SUBTRACT)
    return clip.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "lsi_clip")
