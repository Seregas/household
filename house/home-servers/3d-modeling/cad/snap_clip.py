"""
snap_clip.py — УНІВЕРСАЛЬНИЙ SNAP-FIT ЗАЧЕП аддонів (20.07, схема
cad/snap_kin.py). Одна деталь на всі аддони: защолкується в кишеню
ЗНИЗУ слаба аддона (crush-ребра голови у виїмки кишені — замість
«пружних щок» зі схеми: щоки 2.1×1.2 не гнуться, ε≈34%); нога-пружина
з зубом висить під слабом і при установці аддона клацає в СИМЕТРИЧНИЙ
слот дна — зуб чіпляється ПІД мембрану (Z1.4) і ховається В ТОВЩІ ДНА
(нижче Z0 нічого не стирчить). На аддоні ДВА зачепи носами в
протилежні боки (той самий зачеп, розвернутий 180°).

Локальні координати: X поперек (±SNAP_CLIP_W/2), Y уздовж (0 = центр
слота дна, ніс → −Y), Z — ГЛОБАЛЬНИЙ корпусу (0 = стіл дна).

Друк НА БОЦІ (X-гранню вниз, make_bambu ROT_Y90): весь зачеп =
YZ-профіль, екструдований по X → кожен шар ідентичний, нуль навісів;
згин ноги по Y — У ПЛОЩИНІ шарів (поперек шарів PETG розшаровується).

Запуск: .venv/bin/python cad/snap_clip.py → out/snap_clip.step/.stl
"""
from build123d import *
import params as P
from exporter import save

AMIN = (Align.CENTER, Align.CENTER, Align.MIN)


def build():
    hz0, hz1 = P.SNAP_HEAD_Z
    cam0, cam1, face1 = P.SNAP_TOOTH_Z
    lt2 = P.SNAP_LEG_T / 2
    with BuildPart() as clip:
        # ── YZ-профіль: голова (суцільна) → нога-пружина → зуб ──
        with BuildSketch(Plane.YZ) as prof:
            with BuildLine():
                Polyline(
                    (P.SNAP_HEAD_HALF, hz1),           # верх голови (зад)
                    (P.SNAP_HEAD_HALF, hz0),
                    (lt2, hz0),                        # тил ноги
                    (lt2, cam0),                       # низ ноги (Z0.2)
                    (-lt2, cam0),
                    (-P.SNAP_TOOTH_TIP, cam1),         # кам 45° при заході
                    (-P.SNAP_TOOTH_TIP, face1),        # робоча грань зуба
                    (-lt2, P.SNAP_LEDGE_Z),            # реліз-скіс ~19°
                    (-lt2, hz0),
                    (-P.SNAP_HEAD_HALF, hz0),
                    (-P.SNAP_HEAD_HALF, hz1),          # верх голови (ніс)
                    close=True)
            make_face()
        extrude(prof.sketch, amount=P.SNAP_CLIP_W / 2, both=True)

        # ── crush-ребра голови (4 шт: X±1.6 × обидві Y-грані): циліндр
        # R0.5, вісь утоплена — виступ 0.25 (тип ±2.95, стінка кишені
        # ±2.85 → натяг 0.1/бік); знизу конус-лійка (плавний захід) ──
        rz0, rz1 = P.SNAP_RIB_Z
        tipr = P.SNAP_RIB_R - P.SNAP_RIB_OFF           # 0.25 (лійка знизу)
        for sx in (-1.6, 1.6):
            for sy in (-1, 1):
                yc = sy * (P.SNAP_HEAD_HALF - tipr)    # вісь ±2.45
                with Locations((sx, yc, rz0)):
                    Cylinder(P.SNAP_RIB_R, rz1 - rz0, align=AMIN)
                with Locations((sx, yc, rz0 - 0.25)):
                    Cone(bottom_radius=tipr, top_radius=P.SNAP_RIB_R,
                         height=0.25, align=AMIN)
    return clip.part


def placed(cx, ry, nose):
    """Зачеп у зборі: слот дна (cx, ry), ніс у бік nose (±1 по Y)."""
    part = build()
    if nose > 0:
        part = part.rotate(Axis.Z, 180)
    return part.translate((cx, ry, 0))


if __name__ == "__main__":
    part = build()
    print("valid:", part.is_valid, "| volume:", round(part.volume, 2),
          "| bbox:", part.bounding_box())
    save(part, "snap_clip")
