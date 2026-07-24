"""
make_labrax.py — Bambu-проєкт друку СТІЙКИ Lab-RAX 5U (21.07) з
references/labrax/ (оригінальні 3mf автора, 1:1, НЕ регенеруються).

Комплект (вибір користувача): КАРКАС + НІЖКИ, без ручок і панелей:
  • 4× 5U Vertical Post (стояки)
  • 4× Edge (бічні кромки: 2 ліві + 2 ДЗЕРКАЛЬНІ праві — деталь хіральна,
    автор дає лише "Top Left"; дзеркало z→−z + розворот нормалей, у друці
    це in-plane дзеркало → друкованість ідентична лівій)
  • 4× Foot (ніжки; деталь симетрична — 4 однакові)
  • 2× Horizontal Edge Solid — НИЗ (рекомендація: у прольоті вага йде
    через кутові вузли, суцільний низ = менше пилу знизу до дисків)
  • 2× Horizontal Edge Vented With Logo — ВЕРХ (вентиляція + лого;
    кінці однакові повні у всіх варіантів — міцність кутів та сама)

ОРІЄНТАЦІЇ — знайдені зондом (усі 6 осьових + ±45/135° для кромок,
probe_print-механіка, 0 островів скрізь):
  • Стояки ЛЕЖАЧИ (лицем униз, max навіс 1.09) — а НЕ стоячи: шари
    вздовж довжини (згин стійки в площині шарів — міцніше), нема
    гойдання 222-мм веж, швидше. Стоячи мали б мости 14мм у слотах.
  • Бічні кромки на X-торці (max 3.0 — короткі мости кишень).
  • Ніжки фліпом (пласка грань вниз, 0 навісів).
  • Горизонтальні кромки: профіль ДІАГОНАЛЬНИЙ 45° → друк повернутим
    на 45° навколо довгої осі (діагональна грань плазом, зовнішнє лице
    до стола = гладке; max навіс 1.34). Плазом «по-збірковому» кутові
    блоки висіли б леджем 19мм — НЕ робити. Solid = Rx+45°,
    Vented/Logo = Rx+135° (діагональ «Top» нахилена в інший бік).
    Довжина 282.2 > пластини 256 → додатково Rz45 (діагональна
    розкладка, bbox ~229) — по ОДНІЙ кромці на пластину.

Профіль: PETG 0.24 (AMS-шаблон NAS_tray), але СТРУКТУРНО міцніше за
корпус: wall_loops 3, інфіл 15% grid (стійка тримає NAS + диски).
Травел 6000 (високих деталей нема — все ≤41мм).

Запуск: .venv/bin/python cad/make_labrax.py → out/print_labrax.3mf
(6 пластин: стояки / бічні+ніжки / 2× низ Solid / 2× верх Logo)
"""
import json
import zipfile
from pathlib import Path

import numpy as np
import trimesh

import make_bambu as MB

HERE = Path(__file__).resolve().parent.parent
REF = HERE / "references" / "labrax"
OUT = HERE / "out"

SRC = {
    "labrax_post.stl": "5U Vertical Post.3mf",
    "labrax_edge_L.stl": "Edge.3mf",
    "labrax_foot.stl": "Foot.3mf",
    "labrax_hedge_solid.stl": "Horizontal Edge Solid.3mf",
    "labrax_hedge_logo.stl": "Horizontal Edge Vented With Logo.3mf",
}


def export_stls():
    """references/labrax/*.3mf → out/labrax_*.stl (+ дзеркальна права
    бічна кромка). Кожен 3mf = одне тіло, watertight (перевірено)."""
    for name, src in SRC.items():
        sc = trimesh.load(REF / src)
        m = list(sc.geometry.values())[0]
        assert m.is_watertight, f"{src}: не watertight!"
        m.export(OUT / name)
        print(f"  {name}: vol={m.volume / 1000:.1f} см³")
    # дзеркало для правих бічних кромок: z→−z (in-plane у друці на
    # X-торці) + faces[::-1] — розворот нормалей після дзеркала
    sc = trimesh.load(REF / SRC["labrax_edge_L.stl"])
    m = list(sc.geometry.values())[0]
    v = m.vertices.copy()
    v[:, 2] *= -1.0
    mr = trimesh.Trimesh(v, m.faces[:, ::-1], process=False)
    assert mr.is_watertight and mr.volume > 0
    mr.export(OUT / "labrax_edge_R.stl")
    print(f"  labrax_edge_R.stl (дзеркало): vol={mr.volume / 1000:.1f} см³")


# ── орієнтації (row-major, запікаються v @ R у make_bambu) ─────────────
POST_LAY = (1, 0, 0, 0, 0, 1, 0, -1, 0)    # −Y вниз: (x,y,z)→(x,−z,y), h=35
EDGE_LAY = (0, 0, 1, 0, 1, 0, -1, 0, 0)    # +X вниз: (x,y,z)→(−z,y,x), h=30
FOOT_FLIP = (1, 0, 0, 0, -1, 0, 0, 0, -1)  # фліп X180: пласка грань вниз


def _rx_rz(deg_x, deg_z=45.0):
    """Rx(deg_x) → Rz(deg_z) для v @ R (спершу діагональ плазом,
    потім діагональна розкладка на пластині)."""
    tx, tz = np.deg2rad(deg_x), np.deg2rad(deg_z)
    cx, sx = np.cos(tx), np.sin(tx)
    cz, sz = np.cos(tz), np.sin(tz)
    rx = np.array([[1, 0, 0], [0, cx, sx], [0, -sx, cx]])
    rz = np.array([[cz, sz, 0], [-sz, cz, 0], [0, 0, 1]])
    return tuple((rx @ rz).ravel())


HS_ROT = _rx_rz(45.0)     # Solid: діагональ «Bottom» → +45°
HL_ROT = _rx_rz(135.0)    # Vented Logo: діагональ «Top» → +135°

SPEC = dict(
    plates=[
        # стояки ЛЕЖАЧИ поряд: футпринт 30×222.2, крок 40
        dict(name="4 стояки (лежачи)", objects=[
            ("labrax_post.stl", f"Post_{i + 1}", POST_LAY, (x, 0.0), {})
            for i, x in enumerate((-60.0, -20.0, 20.0, 60.0))]),
        # бічні кромки на X-торці (35×170) + ніжки смужкою знизу
        dict(name="4 бічні кромки + 4 ніжки", objects=[
            ("labrax_edge_L.stl", "Edge_L1", EDGE_LAY, (-67.5, 30.0), {}),
            ("labrax_edge_L.stl", "Edge_L2", EDGE_LAY, (-22.5, 30.0), {}),
            ("labrax_edge_R.stl", "Edge_R1", EDGE_LAY, (22.5, 30.0), {}),
            ("labrax_edge_R.stl", "Edge_R2", EDGE_LAY, (67.5, 30.0), {}),
            ("labrax_foot.stl", "Foot_1", FOOT_FLIP, (-60.0, -95.0), {}),
            ("labrax_foot.stl", "Foot_2", FOOT_FLIP, (-20.0, -95.0), {}),
            ("labrax_foot.stl", "Foot_3", FOOT_FLIP, (20.0, -95.0), {}),
            ("labrax_foot.stl", "Foot_4", FOOT_FLIP, (60.0, -95.0), {})]),
        dict(name="Низ Solid #1 (діагонально)", objects=[
            ("labrax_hedge_solid.stl", "HEdge_solid_1", HS_ROT,
             (0.0, 0.0), {})]),
        dict(name="Низ Solid #2 (діагонально)", objects=[
            ("labrax_hedge_solid.stl", "HEdge_solid_2", HS_ROT,
             (0.0, 0.0), {})]),
        dict(name="Верх Vented Logo #1 (діагонально)", objects=[
            ("labrax_hedge_logo.stl", "HEdge_logo_1", HL_ROT,
             (0.0, 0.0), {})]),
        dict(name="Верх Vented Logo #2 (діагонально)", objects=[
            ("labrax_hedge_logo.stl", "HEdge_logo_2", HL_ROT,
             (0.0, 0.0), {})]),
    ],
    # структурні деталі стійки: 3 периметри + 15% (корпус NAS — 2/8%)
    over={"layer_height": "0.24", "wall_loops": "3",
          "sparse_infill_density": "15%",
          "sparse_infill_pattern": "grid",
          "brim_type": "no_brim",
          "default_acceleration": "6000",
          "travel_acceleration": "6000"},
)


if __name__ == "__main__":
    export_stls()
    with zipfile.ZipFile(MB.TEMPLATE) as z:
        base = json.loads(z.read("Metadata/project_settings.config"))
    MB.build_project("print_labrax", SPEC, None, base)
