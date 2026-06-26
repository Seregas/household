#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ГЕНЕРАТОР ДНА 3U board-tray для NAS (Lab-RAX 10").
Поточний baseline: board3u_voronoi_v6.stl

ЗАПУСК (на компʼютері Клода / sandbox, де є залежності):
    pip install --break-system-packages trimesh manifold3d shapely scipy rtree numpy
    # скопіювати базову STL поряд як board3u_base.stl, тоді:
    python3 build_board_tray_v6.py

БАЗА: MINI_ITX_GPU_FAN.stl з /Volumes/Data/Projects/Household/3d print/
      (це чистий watertight 3U tray; ми його НЕ трансформуємо — координати як є).
      У новій сесії Клод копіює його до себе (copy_file_user_to_claude) і кладе
      поряд зі скриптом під імʼям board3u_base.stl.

ЩО РОБИТЬ СКРИПТ (по кроках):
  1. shell  = база МІНУС вся стара начинка дна (box X[-71,126] Y[-83,82] Z[-1,7]),
              лишаючи стінки/рейки/вушка та фронтальну панель.
  2. rim    = обід-рамка X[-75,130] Y[-89,92], ширина 6, товщина 2.5 мм,
              задні кути заокруглені R10. ГЛИБИНА наростена назад: Y77 -> Y92,
              щоб під увесь модуль RAM A була відкрита павутина (вентиляція).
  3. web    = розріджена Voronoi-павутина: 20 jitter-точок (Lloyd 3x) + 4 пеедестали
              як НАСІННЯ = 24 комірки. Перемички = межі комірок (буфер 1.0 -> 2 мм),
              товщина 2.0 мм. Доходить до обода всіх сторін.
  4. fills  = СОТИ всередині 4 комірок пеедесталів (органічна межа = край комірки):
              hex-кільця ftf7/wall1.5 (буфер 0.75), keepout r9.5, ∩ комірка.
  5. bead   = округлий ВАЛИК уздовж внутрішнього краю обода (циліндри r2.3, центр Z2.5),
              продовження бортика з бічних рейок. Задні кути R4.
  6. peds   = пеедестали, профіль: циліндр r7.5 (Z0-2, товщина заливки) ->
              конус r7.5->r5 (Z2-5.5) -> циліндр r5 (Z5.5-7.5, площадка під плату),
              ⌀4 наскрізь (під M3 heat-set insert зверху).

ВАЖЛИВІ УРОКИ (вшиті у код):
  * extrude_polygon на складній павутині буває НЕ watertight -> після екструду
    робимо merge_vertices/nondegenerate_faces/fill_holes/fix_normals (див. extrude2d).
  * Соти/заливку робимо як БУФЕРОВАНІ ЛІНІЇ (стінки), НЕ «суцільне мінус отвори»
    (останнє дає невалідні полігони, коли отвір торкається нерівної межі комірки).
  * Наприкінці лишаємо найбільше тіло (прибрати вироджені фрагменти на кутах)
    і чистимо nondegenerate_faces. Має бути bodies==1, watertight.

КООРДИНАТИ: X -99.6..154.4, Y -99.4..92 (дно подовжене), Z 0..133.3.
  Фронт (I/O) Y=-99.4. Зад відкритий. Плата лежить на верхах стійок Z7.5.
  SO-DIMM знизу плати -> низ модуля Z2.5 (павутина 2 мм = 0.5 мм зазор).
  Стійки: S1(-63,-60) фронт-лів, S2(94,-83) фронт-прав, S3(-63,72) зад-лів, S4(94,72) зад-прав.
  RAM keepout: A (зад) X[-59.5,13.1] Y[47,79]; B (лівий, верт) X[-70,-38] Y[-30.6,42].
"""
import trimesh, numpy as np
from shapely.geometry import box as sbox, Point, MultiPoint, Polygon, LineString
from shapely.ops import unary_union, voronoi_diagram
from scipy.spatial import Voronoi

BASE_STL = 'board3u_base.stl'      # = MINI_ITX_GPU_FAN.stl
OUT_STL  = 'board3u_voronoi_v6.stl'

def cylZ(r,L,cx,cy,cz,sec=64):
    c=trimesh.creation.cylinder(radius=r,height=L,sections=sec); c.apply_translation([cx,cy,cz]); return c
def boxm(sx,sy,sz,cx,cy,cz):
    b=trimesh.creation.box(extents=[sx,sy,sz]); b.apply_translation([cx,cy,cz]); return b
def hexring(cx,cy,R):
    a=np.deg2rad([0,60,120,180,240,300,0]); return LineString([(cx+R*np.cos(t),cy+R*np.sin(t)) for t in a])
def extrude2d(poly2d,h):
    geoms=list(poly2d.geoms) if poly2d.geom_type in ('MultiPolygon','GeometryCollection') else [poly2d]
    parts=[]
    for g in geoms:
        try: g=g.buffer(0)
        except: continue
        if g.is_empty or g.geom_type!='Polygon' or g.area<0.5: continue
        em=trimesh.creation.extrude_polygon(g,height=h)
        if not em.is_watertight:
            em.merge_vertices(); em.update_faces(em.nondegenerate_faces()); em.fill_holes(); em.fix_normals()
        parts.append(em)
    return trimesh.boolean.union(parts,engine='manifold') if len(parts)>1 else parts[0]
def pedestal(x,y):
    base=cylZ(7.5,2.0,0,0,1.0)
    cone=trimesh.creation.cone(radius=7.5,height=10.5,sections=56); cone.apply_translation([0,0,2.0])
    cone=trimesh.boolean.intersection([cone, boxm(30,30,3.5,0,0,3.75)],engine='manifold')
    top=cylZ(5.0,2.0,0,0,6.5)
    p=trimesh.boolean.union([base,cone,top],engine='manifold'); p.apply_translation([x,y,0]); return p

m=trimesh.load(BASE_STL)
so=[(-63,-60),(94,-83),(-63,72),(94,72)]
shell=trimesh.boolean.difference([m, boxm(197,167,8.0,(-71+126)/2,(-83+82)/2,3.0)],engine='manifold')

ox0,ox1,oy0,oy1=-75,130,-89,92; rw=6.0; R=10.0
pp=[(ox0,oy0),(ox1,oy0),(ox1,oy1-R)]
pp+=[(ox1-R+R*np.cos(t),oy1-R+R*np.sin(t)) for t in np.linspace(0,np.pi/2,12)]
pp+=[(ox0+R+R*np.cos(t),oy1-R+R*np.sin(t)) for t in np.linspace(np.pi/2,np.pi,12)]
pp+=[(ox0,oy1-R)]
rim=Polygon(pp).difference(sbox(ox0+rw,oy0+rw,ox1-rw,oy1-rw))
rim_solid=trimesh.creation.extrude_polygon(rim,height=2.5)

region=sbox(-72,-86,127,89); relax=sbox(-69,-83,124,86)
rng=np.random.default_rng(7)
gx=np.linspace(-58,117,5); gy=np.linspace(-74,80,4)
jit=np.array([[x+rng.uniform(-12,12), y+rng.uniform(-11,11)] for y in gy for x in gx])
for _ in range(3):
    v=Voronoi(jit); npp=[]
    for k in range(len(jit)):
        reg=v.regions[v.point_region[k]]
        if reg and -1 not in reg:
            poly=Polygon(v.vertices[reg]).intersection(relax)
            npp.append([poly.centroid.x,poly.centroid.y] if not poly.is_empty else jit[k])
        else: npp.append(jit[k])
    jit=np.array(npp)
seeds=np.vstack([jit,np.array(so)])
vd=voronoi_diagram(MultiPoint([tuple(p) for p in seeds]),envelope=region)
cells=[c.intersection(region) for c in vd.geoms]
web=unary_union([c.boundary.buffer(1.0,cap_style=2,join_style=2) for c in cells if not c.is_empty]).intersection(region)

# honeycomb (buffered hex-ring walls) inside pedestal cells
ftf,wall=7.0,1.5; pitch=ftf+wall; Rhex=ftf/np.sqrt(3); rdy=pitch*np.sqrt(3)/2
fills=[]
for (px,py) in so:
    pcell=next((c for c in cells if not c.is_empty and c.contains(Point(px,py))),None)
    if pcell is None: continue
    minx,miny,maxx,maxy=pcell.bounds; rings=[]; row=0; yy=miny-3
    while yy<maxy+3:
        xx=minx-3+(pitch/2 if row%2 else 0)
        while xx<maxx+3:
            if np.hypot(xx-px,yy-py)>9.5: rings.append(hexring(xx,yy,Rhex).buffer(0.75,join_style=1))
            xx+=pitch
        yy+=rdy; row+=1
    if rings: fills.append(unary_union(rings).intersection(pcell))
disks=[Point(x,y).buffer(7.6,resolution=24) for x,y in so]
frame2d=unary_union([web]+fills+disks).intersection(region).buffer(0)
frame=extrude2d(frame2d,2.0)
print("frame wt",frame.is_watertight)

ix0,ix1,iy0,iy1=ox0+rw,ox1-rw,oy0+rw,oy1-rw; R2=R-rw
bpath=[(ix0,iy0),(ix1,iy0),(ix1,iy1-R2)]
bpath+=[(ix1-R2+R2*np.cos(t),iy1-R2+R2*np.sin(t)) for t in np.linspace(0,np.pi/2,8)]
bpath+=[(ix0+R2+R2*np.cos(t),iy1-R2+R2*np.sin(t)) for t in np.linspace(np.pi/2,np.pi,8)]
bpath+=[(ix0,iy1-R2),(ix0,iy0)]
P=[]
for a,b in zip(bpath[:-1],bpath[1:]):
    a=np.array(a);b=np.array(b);d=np.linalg.norm(b-a);n=max(2,int(d/5))
    for i in range(n): P.append(a+(b-a)*i/n)
P=np.array(P)
beadparts=[]
for a,b in zip(P,np.roll(P,-1,axis=0)):
    a3=np.array([a[0],a[1],2.5]);b3=np.array([b[0],b[1],2.5])
    if np.linalg.norm(b3-a3)<1e-6: continue
    beadparts.append(trimesh.creation.cylinder(radius=2.3,segment=[a3,b3],sections=16))
bead=trimesh.boolean.union(beadparts,engine='manifold')
print("bead wt",bead.is_watertight)

peds=trimesh.boolean.union([pedestal(x,y) for x,y in so],engine='manifold')
m2=trimesh.boolean.union([shell,rim_solid,frame,bead,peds],engine='manifold')
m2=trimesh.boolean.difference([m2]+[cylZ(2,9,x,y,3.5) for x,y in so],engine='manifold')
bs=m2.split(only_watertight=False); m2=max(bs,key=lambda b:abs(b.volume))
m2.update_faces(m2.nondegenerate_faces()); m2.remove_unreferenced_vertices()
print("final wt",m2.is_watertight,"bodies",len(m2.split(only_watertight=False)),"vol",round(m2.volume))
m2.export(OUT_STL); print("saved", OUT_STL)
