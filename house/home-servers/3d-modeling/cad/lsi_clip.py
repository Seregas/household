"""
lsi_clip.py — ЗАЩІПКА ФІКСАЦІЇ ПЛАТИ LSI (09.07, ідея користувача:
«поставив плату — защолкнув згори і тим самим зафіксував»).

Плата LSI (глуха планка 9217) опускається згори у виделку крізь виріз
брови і закінчується на 8мм нижче верху панелі (замір користувача).
Ця деталь вставляється ЗГОРИ в колодязь (проріз у front.py) над платою:
низ защіпки накриває паз виделки (зазор до плати 0.15) — плата замкнена
вертикально. Зубці-ПРОНГИ (задня половина, центральний проріз, згин у
площині шарів при друку лицем вниз) клацають барбами в кишені бічних
стінок колодязя. Передня половина СУЦІЛЬНА — саме вона висить над
платою (проріз пронгів плату не випустить). Знімання: підважити
плоскою викруткою за виїмку на задньому верхньому краї.
Запуск: .venv/bin/python cad/lsi_clip.py  → out/lsi_clip.step/stl
Координати збірки; друк — передньою (суцільною) гранню вниз.
"""
from build123d import *
import params as P
from exporter import save

AMIN = (Align.CENTER, Align.CENTER, Align.MIN)


def build():
    wy0, wy1 = P.LSI_WELL_Y                # -94.4 .. -91.4
    hw = P.LSI_WELL_HW                     # 3.0 (колодязь ±3)
    z0 = P.LSI_BRK_TOP + 0.15              # низ (плата +0.15)
    zt = P.PANEL_H                         # верх урівень з панеллю
    with BuildPart() as clip:
        # тіло: 0.15 зазору на бік у колодязі, 0.15 по Y
        with Locations((P.LSI_X, (wy0 + wy1) / 2 , z0)):
            Box(2 * hw - 0.3, wy1 - wy0 - 0.3, zt - z0, align=AMIN)
        # центральний проріз пронгів — ЛИШЕ задня половина по Y
        # (передня суцільна накриває плату); ширина 2.0, до z87.5
        with Locations((P.LSI_X, (wy0 + 1.25 + wy1) / 2, z0 - 0.5)):
            Box(2.0, wy1 - (wy0 + 1.25) + 1, 87.5 - (z0 - 0.5),
                align=AMIN, mode=Mode.SUBTRACT)
        # барби на зовнішніх X-гранях пронгів (задня половина),
        # 45° зверху і знизу — клац при вставлянні, знімання підважкою
        for sx in (-1, 1):
            xb = P.LSI_X + sx * (hw - 0.15)
            with BuildSketch(Plane.XZ.offset(-(wy0 + 1.4))) as brb:
                with BuildLine():
                    # трикутний профіль: пік 0.45 назовні, 45° зверху
                    # і знизу (клац при вставлянні / вихід підважкою)
                    Polyline((xb, z0), (xb + sx * 0.45, z0 + 0.65),
                             (xb, z0 + 1.3), close=True)
                make_face()
            extrude(brb.sketch, amount=-(wy1 - 0.15 - (wy0 + 1.4)))
        # фаска низу тіла (легший захід у колодязь)
        try:
            lowe = clip.edges().filter_by(
                lambda e: abs(e.center().Z - z0) < 0.01
                and e.bounding_box().size.Y > 1.5)
            if lowe:
                chamfer(list(lowe), length=0.5)
        except Exception as e:
            print("  (i) фаска низу:", e)
        # виїмка-підважка на задньому верхньому краї
        with Locations((P.LSI_X, wy1 - 0.15, zt - 1.2)):
            Box(4.0, 1.6, 1.3 + 1, align=AMIN, mode=Mode.SUBTRACT)
    return clip.part


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 1))
    save(part, "lsi_clip")
