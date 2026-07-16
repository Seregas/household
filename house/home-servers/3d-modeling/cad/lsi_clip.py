"""
lsi_clip.py — ЗНІМНИЙ КОВПАК (09.07 в2 виделка-защіпка LSI; 16.07 —
подвійна роль): опускається ЗГОРИ в колодязь крізь брову ПІСЛЯ
установки плати LSI та панелі-аддона і ОДНОЧАСНО:
  1. тримає ПЛАТУ LSI — паз (лійка знизу) захоплює передній край
     карти, лівий барб клацає у кишеню лівої стінки колодязя;
  2. тримає АДДОН від підйому — РУКА проходить крізь канал у брові
     (колодязь розширено до розрізу X92) у НОТЧ верхньої кромки
     аддона (дно нотча 85.5, низ руки 85.6 → люфт 0.1).

Конструкція: тіло ±3.05 × y 3.9 × Z73.25..88.75 (верх урівень панелі);
низ = дві щоки 2.2 з пазом 1.7 (лійка-розтруб знизу) + суцільна
перемичка-упор 2мм спереду (край карти впирається по Y); верх карти на
LSI_BRK_TOP=80.75 накритий суцільним центром (карта замкнена
вертикально); ЛІВИЙ проріз 0.5 формує пронг 1.7 з барбом 0.35/45°
(правий пронг/барб 16.07 ВИДАЛЕНО — права стінка колодязя зникла з
перегородкою; правий бік суцільний = якір руки). Знімання — підважити
плоскою викруткою за виїмку на задньому верхньому краї.
Запуск: .venv/bin/python cad/lsi_clip.py → out/lsi_clip.step/stl
Координати збірки; друк — ЗАДНЬОЮ (плоскою, y−92.45) гранню вниз:
тіло+рука лежать у площині столу, пронг гнеться по X = у площині шарів.
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
        # ── РУКА-ковпак (16.07): тримає АДДОН від підйому. Основна
        # балка йде крізь канал у брові (перекриття з тілом 0.45 по X);
        # передній ПАЛЕЦЬ заходить у нотч аддона ЗА його лицьову стінку
        # (зазори: 0.15 до стінки нотча X97, 0.15 до тилу лицьової
        # стінки −98.0, 0.1 до дна нотча 85.5, 0.1 до тилу передньої
        # ламелі панелі −97.95) ──
        with Locations(((P.LSI_X + xw - 0.45 + P.ADP_NOTCH_X1 - 0.15) / 2,
                        (y0 + y1) / 2,
                        (P.ADP_NOTCH_Z0 + 0.1 + zt) / 2)):
            Box(P.ADP_NOTCH_X1 - 0.15 - (P.LSI_X + xw - 0.45),
                y1 - y0, zt - (P.ADP_NOTCH_Z0 + 0.1))
        with Locations(((P.ADP_X[0] + 0.15 + P.ADP_NOTCH_X1 - 0.15) / 2,
                        (-97.85 + -96.25) / 2,
                        (P.ADP_NOTCH_Z0 + 0.1 + zt) / 2)):
            Box(P.ADP_NOTCH_X1 - 0.15 - (P.ADP_X[0] + 0.15),
                -96.25 + 97.85, zt - (P.ADP_NOTCH_Z0 + 0.1))
        # виїмка-підважка на задньому верхньому краї
        with Locations((P.LSI_X, y1 - 1.0, zt - 1.2)):
            Box(4.0, 1.6, 1.3 + 1, align=AMIN, mode=Mode.SUBTRACT)
    return clip.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "lsi_clip")
