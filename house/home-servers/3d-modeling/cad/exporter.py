"""exporter.py — STEP (первинний) + зшитий watertight STL (похідний для друку)."""
import trimesh, numpy as np
from build123d import export_step, export_stl

def _heal(m):
    """Точкові дефекти OCC-тесселяції: зварити вершини відкритих/нон-маніфолдних
    ребер у радіусі 0.05, прибрати вироджені й дубльовані грані, залатати діри.
    Геометричні (лінійні) дефекти так НЕ лікуються — їх чинити у моделі."""
    import collections
    from scipy.spatial import cKDTree
    for _ in range(3):
        if m.is_watertight:
            break
        cnt = collections.Counter(map(tuple, m.edges_sorted))
        bad = [k for k, v in cnt.items() if v != 2]
        if not bad:
            break
        vids = np.unique(np.array(bad).ravel())
        pts = m.vertices[vids]
        v = m.vertices.copy()
        for i, j in cKDTree(pts).query_pairs(0.05):
            a, b = vids[i], vids[j]
            mid = (v[a] + v[b]) / 2
            v[a] = mid; v[b] = mid
        m = trimesh.Trimesh(vertices=v, faces=m.faces, process=False)
        m.merge_vertices(digits_vertex=4)
        m.update_faces(m.nondegenerate_faces())
        m.update_faces(m.unique_faces())
        # дубль-грані з протилежною орієнтацією (злиплі трикутники)
        srt = np.sort(m.faces, axis=1)
        _, first = np.unique(srt, axis=0, return_index=True)
        keep = np.zeros(len(m.faces), bool); keep[first] = True
        m.update_faces(keep)
        m.fill_holes()
    return m


def save(part, stem, outdir="out"):
    import os
    os.makedirs(outdir, exist_ok=True)
    step = f"{outdir}/{stem}.step"
    stl  = f"{outdir}/{stem}.stl"
    export_step(part, step)
    export_stl(part, stl)                     # OCC-тесселяція, грані незалежні → не wt
    m = trimesh.load(stl)
    m.merge_vertices(digits_vertex=4)         # зшити копланарні шви
    m.update_faces(m.nondegenerate_faces())
    m.update_faces(m.unique_faces())
    if not m.is_watertight:
        m.fill_holes()
    if not m.is_watertight:
        m = _heal(m)
    m.fix_normals()
    m.export(stl)
    print(f"  STEP: {step}")
    print(f"  STL : {stl}  | watertight={m.is_watertight} bodies={m.body_count} "
          f"vol={round(m.volume,1)} bounds={np.round(m.bounds,2).tolist()}")
    return m


def save_parts(parts, stem, outdir="out"):
    """Надійний експорт збірки, коли OCC-fuse ламається (2026-07-03):
    STEP = Compound з окремих солідів (FreeCAD відкриває як групу тіл),
    STL = boolean-union через trimesh/manifold (один watertight меш для друку)."""
    import os, tempfile
    from build123d import Compound
    os.makedirs(outdir, exist_ok=True)
    step = f"{outdir}/{stem}.step"
    stl = f"{outdir}/{stem}.stl"
    export_step(Compound(children=list(parts)), step)
    meshes = []
    for i, p in enumerate(parts):
        tmp = f"{tempfile.gettempdir()}/_asm_{i}.stl"
        export_stl(p, tmp)
        m = trimesh.load(tmp)
        m.merge_vertices(digits_vertex=4)
        m.update_faces(m.nondegenerate_faces())
        if not m.is_watertight:
            m.fill_holes()
        meshes.append(m)
    u = trimesh.boolean.union(meshes, engine='manifold')
    u.merge_vertices(digits_vertex=4)
    u.update_faces(u.nondegenerate_faces())
    u.fix_normals()
    u.export(stl)
    print(f"  STEP: {step} (compound, {len(parts)} солідів)")
    print(f"  STL : {stl}  | watertight={u.is_watertight} bodies={u.body_count} "
          f"vol={round(u.volume,1)} bounds={np.round(u.bounds,2).tolist()}")
    return u
