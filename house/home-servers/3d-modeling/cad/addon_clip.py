"""
addon_clip.py — АДДОН-КЛІП (17.07 в3; історія: 09.07 «lsi_clip»
виделка-защіпка LSI, перейменовано — головна роль тепер тримати
ПАНЕЛЬ-АДДОН). Опускається ЗГОРИ ПІСЛЯ установки аддона:
  1. тримає АДДОН від вдавлення — ЛЕЗО від тіла вправо у вертикальному
     ПАЗУ передньої товщі брови (жорсткість рами не втрачена: спереду
     плита ободка t3, ззаду брова) опускається ЗА рамку аддона (зазор
     0.05, контакт 80.1..80.75); crush-ребра тилу леза (натяг 0.1 у
     стінку паза) додають тертя-ретенцію. Лезо — ГРЕБІНКА з вирізами
     під мостоопори паза (друкованість корпусу, front.py), зверху
     суцільний хребет CAP_NOTCH_TOP..88.75;
  2. у НАШОМУ варіанті заразом ПРИТРИМУЄ ПЛАТУ LSI — виделка в
     колодязі крізь брову: паз (лійка знизу) захоплює передній край
     карти, лівий барб клацає у кишеню лівої стінки колодязя.

Конструкція: тіло ±3.05 × y 3.9 × Z73.25..88.75 (верх урівень панелі);
низ = дві щоки 2.2 з пазом 1.7 (лійка-розтруб знизу) + суцільна
перемичка-упор 2мм спереду (край карти впирається по Y); верх карти на
LSI_BRK_TOP=80.75 накритий суцільним центром (карта замкнена
вертикально); ЛІВИЙ проріз 0.5 формує пронг 1.7 з барбом 0.35/45°
(правий бік суцільний = якір леза). Знімання — підважити плоскою
викруткою за виїмку на задньому верхньому краї.
Запуск: .venv/bin/python cad/addon_clip.py → out/addon_clip.step/stl
Координати збірки; друк — ЛИЦЕМ (y−96.35) вниз: тіло і лезо копланарні
спереду, лежать на столі; пронг гнеться по X = у площині шарів.
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
        # ЛІВИЙ бічний проріз 0.5 → пружний ПРОНГ 1.7 (центр і правий
        # бік лишаються суцільними — стеля над картою ціла, правий бік
        # несе руку)
        with Locations((P.LSI_X - (hw + 0.25), (y0 + y1) / 2,
                        z_card + 0.2)):
            Box(0.5, y1 - y0 + 1, zt - z_card + 1,
                align=AMIN, mode=Mode.SUBTRACT)
        # барб 0.35 (45/45) на зовнішній грані лівого пронга
        xb = P.LSI_X - xw
        with BuildSketch(Plane.XZ.offset(95.4)) as brb:
            with BuildLine():
                Polyline((xb, 86.2), (xb - 0.35, 86.95),
                         (xb, 87.7), close=True)
            make_face()
        extrude(brb.sketch, amount=-(95.4 - 93.4))
        # ── ЛЕЗО-ковпак (17.07 в3): у вертикальному ПАЗУ передньої
        # товщі брови (колодязь до 91.6 + паз 91.6..133.2, y −96.4..
        # −94.8) опускається ЗА рамку аддона — блокує ВДАВЛЕННЯ (зазор
        # 0.05 лице↔тил рамки). Перекриття з тілом 0.45 по X. Верхня
        # СМУГА — на всю довжину паза (зазори: 0.05 перед, 0.15 зад,
        # 0.2 правий кінець, 0.2 до дна паза 81.5); нижня ГУБА — лише
        # у прольоті (x≥ADP_X0+0.2: між колодязем 91.6 і розрізом 92
        # лишається ків брови — там низом не пройти), контакт за
        # рамкою 80.1..80.75 (вище рамка фаскована ADP_CHAMF) ──
        yf = y0                                  # лице леза −96.35
        yr = yf + P.CAP_BLADE_T                  # тил −94.95
        bx0 = P.LSI_X + xw - 0.45                # 91.0
        with Locations(((bx0 + P.CAP_BLADE_X1) / 2, (yf + yr) / 2,
                        (81.7 + zt) / 2)):
            Box(P.CAP_BLADE_X1 - bx0, P.CAP_BLADE_T, zt - 81.7)
        gx0 = P.ADP_X[0] + 0.2                   # 92.2
        with Locations(((gx0 + P.CAP_BLADE_X1) / 2, (yf + yr) / 2,
                        (P.CAP_BOT_Z + 82.0) / 2)):
            Box(P.CAP_BLADE_X1 - gx0, P.CAP_BLADE_T,
                82.0 - P.CAP_BOT_Z)
        # фаска 45° нижнього лицьового ребра губи (захід за рамку)
        with BuildSketch(Plane.YZ.offset(gx0 - 0.1)) as bch:
            with BuildLine():
                Polyline((yf - 0.1, P.CAP_BOT_Z + 0.4),
                         (yf - 0.1, P.CAP_BOT_Z - 0.1),
                         (yf + 0.4, P.CAP_BOT_Z - 0.1), close=True)
            make_face()
        extrude(bch.sketch, amount=P.CAP_BLADE_X1 - gx0 + 0.2,
                mode=Mode.SUBTRACT)
        # crush-ребра тилу леза (вертикальні): виступ 0.25 → натяг 0.1
        # у стінку паза −94.8 (стінка існує лише з z≈83.4 — ків брови
        # сягає −94.8 від цієї висоти); конус-лійка знизу
        for xc in P.CAP_RIB_XC:
            ry = yr - P.CAP_RIB_R + P.CAP_RIB_PROT   # центр −95.2
            with Locations((xc, ry, P.CAP_RIB_Z[0])):
                Cylinder(P.CAP_RIB_R,
                         P.CAP_RIB_Z[1] - P.CAP_RIB_Z[0], align=AMIN)
            with Locations((xc, ry, P.CAP_RIB_Z[0] - 0.4)):
                Cone(0.1, P.CAP_RIB_R, 0.4, align=AMIN)
        # ГРЕБІНКА (17.07): вирізи знизу до CAP_NOTCH_TOP під
        # мостоопори паза (друкованість корпусу — див. front.py);
        # вище лишається суцільний ХРЕБЕТ (CAP_NOTCH_TOP..верх) —
        # сегменти з'єднані (наскрізні вирізи давали bodies=5)
        nw = P.CAP_SLOT_RIB_T + 2 * P.CAP_NOTCH_CLR
        for xc in P.CAP_SLOT_RIB_XC:
            with Locations((xc, (yf + yr) / 2,
                            (P.CAP_BOT_Z - 0.5 + P.CAP_NOTCH_TOP) / 2)):
                Box(nw, P.CAP_BLADE_T + 0.2,
                    P.CAP_NOTCH_TOP - (P.CAP_BOT_Z - 0.5),
                    mode=Mode.SUBTRACT)
        # виїмка-підважка на задньому верхньому краї
        with Locations((P.LSI_X, y1 - 1.0, zt - 1.2)):
            Box(4.0, 1.6, 1.3 + 1, align=AMIN, mode=Mode.SUBTRACT)
    return clip.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "addon_clip")
