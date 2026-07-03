"""exporter.py — STEP (первинний) + зшитий watertight STL (похідний для друку)."""
import trimesh, numpy as np
from build123d import export_step, export_stl

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
