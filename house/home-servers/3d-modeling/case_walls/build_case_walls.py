# build_case_walls.py — генератор СТІНОК/КОРПУСУ 2U board-tray (Lab-RAX)
# Регенерувати в Claude-чаті (sandbox з trimesh+manifold3d+shapely+scipy).
# ЗАЛЕЖНОСТІ:
#   - loft.py, mloft.py (у цій же теці; в sandbox покласти в /home/claude/ або поруч)
#   - базовий референс STL: MINI_ITX_one_12mm_button.stl (1:1). Шлях нижче — під sandbox.
#   - PROF (профіль валика) ВБУДОВАНО нижче (знято з перерізу оригіналу @Y45, simplify 0.06).
# ІСТОРІЯ: blockA-серія. Актуальний = A31 (2026-07-02). Верхня кромка пряма до (Y101.5,Z28).
#   A31: задній «рейл» ПОВНІСТЮ ПАРАМЕТРИЧНИЙ (оригінал для рейла більше не потрібен) — див.
#   блок параметрів у __main__ (RF/ZF0..ZF1/PLATW/RS/RB/SLOPE/якір). Лівий = дзеркало X'=54.9-X.
#   Звірка з A30 (вирізка з оригіналу): перерізи symdiff 0.03-0.05 мм², гребінь Δ<=0.012.
#   A30 (механіка збережена): підйом від Z7.60, конверт (loft∪підвал до кромка-4.0)∩бокс,
#   killbox старої верхівки Z7.6-13.5, збірка у manifold3d-домені => watertight за побудовою.
#   Лишаються з ОРИГІНАЛУ: rearcap (задній бортик+кути+лікті), підлога зі стійками, фронт.
import trimesh, numpy as np
from shapely.geometry import Polygon, LineString, box as sbox
from shapely.ops import unary_union
from loft import loft
E='manifold'
m=trimesh.load('/mnt/user-data/uploads/MINI_ITX_one_12mm_button.stl')
def boxm(sx,sy,sz,cx,cy,cz):
    b=trimesh.creation.box(extents=[sx,sy,sz]);b.apply_translation([cx,cy,cz]);return b
def extrudeYZ(poly2d,x0,x1):
    geoms=list(poly2d.geoms) if poly2d.geom_type in('MultiPolygon','GeometryCollection') else [poly2d]
    parts=[];Tm=np.array([[0,0,1.0,x0],[1,0,0,0],[0,1,0,0],[0,0,0,1]])
    for g in geoms:
        try:g=g.buffer(0)
        except:continue
        if g.is_empty or g.geom_type!='Polygon' or g.area<0.3:continue
        me=trimesh.creation.extrude_polygon(g,height=(x1-x0));me.apply_transform(Tm)
        if not me.is_watertight:
            me.merge_vertices();me.update_faces(me.nondegenerate_faces());me.fill_holes();me.fix_normals()
        parts.append(me)
    return trimesh.boolean.union(parts,engine=E) if len(parts)>1 else (parts[0] if parts else None)

# PROF: профіль валика (u=відступ 0..6, zrel=Z відносно верхньої кромки, -6.5..0)
PROF=[(3.001,-5.711),(2.996,-6.500),(-0.004,-6.500),(-0.004,-2.167),(0.117,-1.443),(0.264,-1.108),
      (0.710,-0.545),(1.312,-0.178),(1.649,-0.082),(3.996,-0.050),(4.680,-0.178),(4.996,-0.334),
      (5.528,-0.806),(5.728,-1.108),(5.966,-1.799),(5.996,-4.740),(5.881,-5.072),(5.506,-5.257),
      (3.401,-5.265),(3.111,-5.442)]
BEAD_BOT=-6.5

def bez(P0,P1,P2,P3,n=26):
    return [((1-t)**3*P0[0]+3*(1-t)**2*t*P1[0]+3*(1-t)*t*t*P2[0]+t**3*P3[0],
             (1-t)**3*P0[1]+3*(1-t)**2*t*P1[1]+3*(1-t)*t*t*P2[1]+t**3*P3[1]) for t in np.linspace(0,1,n)]
# ВЕРХНЯ КРОМКА: пряма (Y-85.29,Z69.33)->(Y101.5,Z28). Пологіша, без пірнання в дно.
PATH=[(y,69.33+(28.0-69.33)*(y+85.29)/186.79) for y in np.arange(-90.0,101.5+0.01,1.0)]
ytop=np.array([p[0] for p in PATH]);ztopA=np.array([p[1] for p in PATH])
ztop_of=lambda y: float(np.interp(y,ytop,ztopA))
# A29: loft валика вкорочено до YR (далі верх = заокруглення блока-закінчення)
YR=100.85
