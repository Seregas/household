"""
test_petal.py — ТЕСТ-КУПОН нового undercut/пелюсткового замка SSD-блока
(31.07). Три деталі, щоб зібрати рукою й відчути тримання:
  out/test_petal_floor.stl — шматок дна з НЕСТОМ (Z-ледж undercut, наскрізь
                             знизу — барб доступний для стиску пальцем);
  out/test_petal_clip.stl  — ЗАЧЕП (голова-фланець + центр. ребро + 2
                             пелюстки з барбами −5°); друк НА БОЦІ (ROT_Y90);
  out/test_petal_block.stl — шматок БЛОКА: база (стоїть на дні) + бос із
                             Т-пазом (полиці ловлять фланці голови).

Збірка: зачеп засунути збоку в Т-паз боса блока → блок поставити на дно й
натиснути (пелюстки стискаються, барби клацають ПІД ледж) → тягнути блок
угору (має ТРИМАТИ — undercut) → зняти: пальцем знизу стиснути пару барбів.

Локальні осі (як у зборі): X — упоперек (ширина зачепа/засув голови),
Y — вісь деформації пелюсток, Z — вертикаль (0 = стіл дна).

Запуск: .venv/bin/python cad/test_petal.py
"""
from build123d import *
from exporter import save

# ── ПАРАМЕТРИ (локальні — у params.py винесемо після приймання) ──
# в2 (31.07, тест: «защолкується, але погано тримає — треба зачеп більший»):
# зачеплення 0.6→1.2 (×2 зріз+запас), нога 1.0→1.2 (жорсткіша), ширше
# 6→7, вище (нога довша L~6.4 — тримає ε<6% при вдвічі більшому ході).
W        = 7.0     # ширина зачепа по X (було 6.0)
RIB_H    = 2.0     # півширина центрального ребра
GAP      = 1.4     # щілина ребро↔нога (обмежувач ходу > хід зняття 1.3)
LEG_T    = 1.2     # товщина ноги-пружини (було 1.0)
NEST_H   = RIB_H + GAP + LEG_T          # = 4.6, півнест (зовн. грань ноги)
BARB     = 1.2     # зачеплення барба (було 0.6 — «більший»)
LEDGE_Z  = 2.0     # Z леджа (стеля мовки неста; барб хапає під нього)
REC_Z0   = 0.0     # низ рецеса (наскрізь — доступ до барба знизу)
TIP_Z    = 1.0     # низ рампи заходу барба
BARB_TIPZ= 1.6     # Z вершини барба (робоча грань до леджа 2.0)
FLA_H    = 6.5     # півширина фланця голови (> NEST_H+BARB=5.8)
FLA_Z0, FLA_Z1 = 8.0, 9.4               # фланець голови (вище — нога довша)
LEG_ROOTZ = FLA_Z0                      # корінь пелюстки = низ фланця
RELIEF_R = 0.5

FLOOR_TOP = 3.0    # верх дна = посадка блока
SLOT_HALFX = 3.3   # півслот дна по X (зачеп 6.0 + 0.3/бік = зазор 0.3)


def clip():
    """Зачеп: YZ-профіль (фланець+ребро+2 пелюстки), екструд по X."""
    with BuildPart() as p:
        # фланець (голова) — брус на повну ширину
        with BuildSketch(Plane.YZ) as fl:
            with Locations((0, (FLA_Z0 + FLA_Z1) / 2)):
                Rectangle(2 * FLA_H, FLA_Z1 - FLA_Z0)
        extrude(fl.sketch, amount=W / 2, both=True)
        # центральне ребро (Z-упор + обмежувач)
        with BuildSketch(Plane.YZ) as rb:
            with Locations((0, (1.0 + LEG_ROOTZ) / 2)):
                Rectangle(2 * RIB_H, LEG_ROOTZ - 1.0)
        extrude(rb.sketch, amount=W / 2, both=True)
        # 2 пелюстки з барбами (дзеркальні по Y)
        for s in (+1, -1):
            i, o = s * (RIB_H + GAP), s * NEST_H       # внутр./зовн. грань
            b = s * (NEST_H + BARB)                     # вершина барба
            with BuildSketch(Plane.YZ) as lg:
                with BuildLine():
                    Polyline(
                        (i, LEG_ROOTZ),                 # корінь внутр. (у фланець)
                        (i, TIP_Z + 0.9),               # внутр. грань униз
                        (s * (NEST_H - LEG_T + 0.5), TIP_Z),  # кінчик (звужений)
                        (o, TIP_Z + 0.3),               # зовн. до нест-стінки
                        (b, BARB_TIPZ),                 # РАМПА заходу ~35°
                        (o, LEDGE_Z + 0.05),            # РОБОЧА грань (undercut ~hook)
                        (o, LEG_ROOTZ),                 # зовн. грань угору
                        close=True)
                make_face()
            extrude(lg.sketch, amount=W / 2, both=True)
        # relief-отвори в корені щілин (не потрібні як тіло — просто зарубка)
    part = p.part
    return part


def floor_chunk():
    """Шматок дна з нестом (наскрізь знизу для доступу до барба)."""
    with BuildPart() as p:
        with Locations((0, 0, FLOOR_TOP / 2)):
            Box(26, 22, FLOOR_TOP)
        # МОВКА неста (верх): Y±NEST_H, Z LEDGE..верх
        with Locations((0, 0, (LEDGE_Z + FLOOR_TOP) / 2)):
            Box(2 * SLOT_HALFX, 2 * NEST_H, FLOOR_TOP - LEDGE_Z,
                mode=Mode.SUBTRACT)
        # РЕЦЕС (низ, ширший — під барб): Y±(NEST_H+BARB+0.1), Z0..LEDGE
        with Locations((0, 0, LEDGE_Z / 2)):
            Box(2 * SLOT_HALFX, 2 * (NEST_H + BARB + 0.1), LEDGE_Z,
                mode=Mode.SUBTRACT)
    return p.part


def block_chunk():
    """Шматок блока: база (на дні) + бос із Т-пазом (полиці під фланці)."""
    base_z0, base_z1 = FLOOR_TOP, FLOOR_TOP + 1.4       # база 3.0..4.4
    boss_z1 = FLA_Z1 + 1.2                               # стеля над фланцем
    open_h = NEST_H + 0.25                               # півотвір під ноги/ребро
    with BuildPart() as p:
        # база (стоїть на верху дна)
        with Locations((0, 0, (base_z0 + base_z1) / 2)):
            Box(24, 20, base_z1 - base_z0)
        # бос
        with Locations((0, 0, (base_z1 + boss_z1) / 2)):
            Box(18, 16, boss_z1 - base_z1)
        # Т-паз: наскрізний по X (засув голови) —
        # (а) отвір під ноги/ребро/шийку (Y±open_h) від бази до низу фланця
        with Locations((0, 0, (base_z0 + FLA_Z0) / 2)):
            Box(30, 2 * open_h, FLA_Z0 - base_z0 + 0.02, mode=Mode.SUBTRACT)
        # (б) пельга під фланець (Y±(FLA_H+0.25)) на висоті фланця
        with Locations((0, 0, (FLA_Z0 + FLA_Z1 + 0.3) / 2)):
            Box(30, 2 * (FLA_H + 0.25), (FLA_Z1 + 0.3) - FLA_Z0,
                mode=Mode.SUBTRACT)
    return p.part


if __name__ == "__main__":
    for name, fn in (("test_petal_clip", clip),
                     ("test_petal_floor", floor_chunk),
                     ("test_petal_block", block_chunk)):
        part = fn()
        print(f"{name:20s} valid={part.is_valid} "
              f"vol={part.volume:9.1f} bbox={part.bounding_box()}")
        save(part, name)
