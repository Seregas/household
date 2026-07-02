#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ДНО board-tray v16 (BASELINE). Задній валик = гладкий арочний профіль (PROFILE) з
нижнім носиком біля основи. Кінці side-run обрізані рівно по Y77.62 (передній край
поперечного бортика, де дно стає пласким): перетин із поперечним лишається, хвоста
попереду немає, прямокутних boolean-різів НЕ використовуємо (дно ціле, без виямки).
Кутові артефакти старого валика прибрані. Регенерується з board3u_base.stl.
TODO: додати галтель на внутрішньому куті Т-стиків (helper cove_fillet нижче, поки НЕ викликається)."""
import trimesh, numpy as np
from shapely.geometry import box as sbox, Point, MultiPoint, Polygon
from shapely.ops import unary_union, voronoi_diagram, triangulate
from scipy.spatial import Voronoi

BASE_STL='board3u_base.stl'; OUT_STL="board3u_voronoi_v16.stl"
def cylZ(r,L,cx,cy,cz,sec=64):
    c=trimesh.creation.cylinder(radius=r,height=L,sections=sec); c.apply_translation([cx,cy,cz]); return c
def boxm(sx,sy,sz,cx,cy,cz):
    b=trimesh.creation.box(extents=[sx,sy,sz]); b.apply_translation([cx,cy,cz]); return b
def hexpoly(cx,cy,R):
    a=np.deg2rad([30,90,150,210,270,330]); return Polygon([(cx+R*np.cos(t),cy+R*np.sin(t)) for t in a])
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

# ---- ВАЛИК ----
PROFILE=[(0.00,0.00),(0.00,4.80),(0.05,5.30),(0.20,5.70),(0.50,5.92),(0.95,6.00),
 (1.85,6.00),(2.35,5.92),(2.62,5.70),(2.78,5.30),(2.85,4.80),
 (2.92,4.20),(3.10,3.60),(3.40,3.20),(3.88,3.00),(3.88,0.00)]
def densify(p0,p1,step=1.0):
    d=np.hypot(p1[0]-p0[0],p1[1]-p0[1]); n=max(1,int(d/step))
    return [(p0[0]+(p1[0]-p0[0])*t/n,p0[1]+(p1[1]-p0[1])*t/n) for t in range(1,n+1)]
def bead_path():
    R=10.0; main=[(-75,77.62)]; main+=densify((-75,77.62),(-75,82))
    for t in np.linspace(np.pi,np.pi/2,30)[1:]: main.append((-65+R*np.cos(t),82+R*np.sin(t)))
    main+=densify((-65,92),(120,92))
    for t in np.linspace(np.pi/2,0.0,30)[1:]: main.append((120+R*np.cos(t),82+R*np.sin(t)))
    main+=densify((130,82),(130,77.62))
    out=[main[0]]
    for p in main[1:]:
        if np.hypot(p[0]-out[-1][0],p[1]-out[-1][1])>1e-6: out.append(p)
    vs=[1.0]*len(out)
    return np.array(out,float),np.array(vs,float)
def cove_fillet(y_end,x0,x1,z=2.5,r=1.6,facing=-1,seg=16):
    cy=y_end+facing*r; cz=z+r
    pts=[(y_end,z),(y_end,z+r)]
    for a in np.linspace(0,np.pi/2,seg):
        pts.append((cy-facing*r*np.cos(a), cz-r*np.sin(a)))
    pts.append((y_end+facing*r,z))
    poly=Polygon(pts).buffer(0)
    me=trimesh.creation.extrude_polygon(poly,height=(x1-x0))   # extrudes along Z, coords (Y,Z,0..W)
    T=np.array([[0,0,1.0,x0],[1,0,0,0],[0,1,0,0],[0,0,0,1]])    # (X,Y,Z)=(x0+z, x, y)
    me.apply_transform(T); me.merge_vertices(); me.fix_normals()
    return me
def sweep(path,vscale,profile,inward=+1):
    n=len(path); tang=np.zeros((n,2))
    tang[1:-1]=path[2:]-path[:-2]; tang[0]=path[1]-path[0]; tang[-1]=path[-1]-path[-2]
    tang/=(np.linalg.norm(tang,axis=1,keepdims=True)+1e-12)
    nrm=np.stack([tang[:,1],-tang[:,0]],axis=1)*inward
    prof=np.array(profile,float); m=len(prof); V=np.zeros((n,m,3))
    for i in range(n):
        px,py=path[i]; nx,ny=nrm[i]; s=vscale[i]
        for j,(u,v) in enumerate(prof): V[i,j]=[px+u*nx,py+u*ny,v*s]
    verts=V.reshape(-1,3); faces=[]; idx=lambda i,j:i*m+j
    for i in range(n-1):
        for j in range(m):
            j2=(j+1)%m; a,b,c,d=idx(i,j),idx(i,j2),idx(i+1,j2),idx(i+1,j)
            faces.append([a,b,c]); faces.append([a,c,d])
    poly=Polygon(profile); tris=[t for t in triangulate(poly) if t.within(poly.buffer(1e-9))]
    for end,flip in [(0,False),(n-1,True)]:
        s=vscale[end]
        for tri in tris:
            xy=list(tri.exterior.coords)[:3]; ids=[]
            for (u,v) in xy:
                px,py=path[end]; nx,ny=nrm[end]
                verts=np.vstack([verts,[px+u*nx,py+u*ny,v*s]]); ids.append(len(verts)-1)
            faces.append(ids[::-1] if flip else ids)
    me=trimesh.Trimesh(vertices=verts,faces=np.array(faces),process=True)
    me.merge_vertices(); me.update_faces(me.nondegenerate_faces()); me.fill_holes(); me.fix_normals()
    return me

m=trimesh.load(BASE_STL)
so=[(-63,-60),(94,-83),(-63,72),(94,72)]
shell=trimesh.boolean.difference([m, boxm(197,167,8.0,(-71+126)/2,(-83+82)/2,3.0)],engine='manifold')
# прибрати кутові артефакти старого валика (тільки над ободом, Z>2.4)
art_l=boxm(5.0,6.0,5.0,-71.5,80.0,4.5)   # X[-74,-69] Y[77,83] Z[2,7]
art_r=boxm(5.0,6.0,5.0,126.5,80.0,4.5)   # X[124,129] Y[77,83] Z[2,7]
shell=trimesh.boolean.difference([shell,art_l,art_r],engine='manifold')

ox0,ox1,oy0,oy1=-75,130,-89,92; rw=6.0; R=10.0
pp=[(ox0,oy0),(ox1,oy0),(ox1,oy1-R)]
pp+=[(ox1-R+R*np.cos(t),oy1-R+R*np.sin(t)) for t in np.linspace(0,np.pi/2,16)]
pp+=[(ox0+R+R*np.cos(t),oy1-R+R*np.sin(t)) for t in np.linspace(np.pi/2,np.pi,16)]
pp+=[(ox0,oy1-R)]
rim=Polygon(pp).difference(sbox(ox0+rw,oy0+rw,ox1-rw,oy1-rw))
rim_solid=trimesh.creation.extrude_polygon(rim,height=2.5)

region=sbox(-72,-86,127,89); relax=sbox(-69,-83,124,86)
rng=np.random.default_rng(7); gx=np.linspace(-58,117,5); gy=np.linspace(-74,80,4)
jit=np.array([[x+rng.uniform(-12,12),y+rng.uniform(-11,11)] for y in gy for x in gx])
for _ in range(3):
    v=Voronoi(jit); npp=[]
    for k in range(len(jit)):
        reg=v.regions[v.point_region[k]]
        if reg and -1 not in reg:
            poly=Polygon(v.vertices[reg]).intersection(relax); npp.append([poly.centroid.x,poly.centroid.y] if not poly.is_empty else jit[k])
        else: npp.append(jit[k])
    jit=np.array(npp)
vd=voronoi_diagram(MultiPoint([tuple(p) for p in jit]),envelope=region)
cells=[c.intersection(region).buffer(0) for c in vd.geoms]
cells=[c for c in cells if (not c.is_empty) and c.geom_type=='Polygon' and c.area>2]
shrunk=unary_union([c.buffer(-1.0) for c in cells]); web=region.difference(shrunk)
F,w=9.0,1.3; D=F+w; Rhex=F/np.sqrt(3); rdy=D*np.sqrt(3)/2; fills=[]
for (px,py) in so:
    for pcell in [c for c in cells if c.distance(Point(px,py))<4.0]:
        minx,miny,maxx,maxy=pcell.bounds; holes=[]; row=0; yy=miny-4
        while yy<maxy+4:
            xx=minx-4+(D/2 if row%2 else 0)
            while xx<maxx+4: holes.append(hexpoly(xx,yy,Rhex)); xx+=D
            yy+=rdy; row+=1
        fills.append(pcell.difference(unary_union(holes)))
disks=[Point(x,y).buffer(8.5,resolution=28) for x,y in so]
frame2d=unary_union([web]+fills+disks).intersection(region).buffer(0)
frame=extrude2d(frame2d,2.0)

path,vs=bead_path(); bead=sweep(path,vs,PROFILE,inward=+1)
print("bead wt",bead.is_watertight,"vol",round(bead.volume,1))
peds=trimesh.boolean.union([pedestal(x,y) for x,y in so],engine='manifold')
m2=trimesh.boolean.union([shell,rim_solid,frame,bead,peds],engine='manifold')
m2=trimesh.boolean.difference([m2]+[cylZ(2,9,x,y,3.5) for x,y in so],engine='manifold')
bs=m2.split(only_watertight=False); m2=max(bs,key=lambda b:abs(b.volume))
m2.update_faces(m2.nondegenerate_faces()); m2.remove_unreferenced_vertices()
print("final wt",m2.is_watertight,"bodies",len(m2.split(only_watertight=False)),"vol",round(m2.volume))
m2.export(OUT_STL); print("saved",OUT_STL)