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
