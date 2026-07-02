# mloft.py — morph-loft: плавний перехід між двома 2D-перерізами по Z (cos-ease)
# Використовується генератором стінок (build_case_walls.py) для зони згасання флера рейла.
import numpy as np, trimesh
import shapely.geometry as sg
from shapely.geometry.polygon import orient

def resample_ring(poly,n,anchor):
    p=orient(poly,sign=1.0)                       # CCW
    xy=np.array(p.exterior.coords)                # замкнений
    seg=np.linalg.norm(np.diff(xy,axis=0),axis=1)
    cum=np.concatenate([[0],np.cumsum(seg)]); L=cum[-1]
    # старт: точка контуру, найближча до anchor
    d=np.linalg.norm(xy[:-1]-np.array(anchor),axis=1); i0=int(d.argmin())
    s0=cum[i0]
    ts=(s0+np.linspace(0,L,n,endpoint=False))%L
    x=np.interp(ts,cum,xy[:,0]); y=np.interp(ts,cum,xy[:,1])
    # впорядкувати за параметром від s0 (обхід)
    order=np.argsort((ts-s0)%L)
    return np.column_stack([x[order],y[order]])

def mloft(polyA,polyB,z0,z1,anchor,nz=11,n=240):
    A=resample_ring(polyA,n,anchor); B=resample_ring(polyB,n,anchor)
    rings=[]
    for t in np.linspace(0,1,nz):
        e=(1-np.cos(np.pi*t))/2
        R=(1-e)*A+e*B
        rings.append(np.column_stack([R,np.full(n,z0+(z1-z0)*t)]))
    V=np.vstack(rings); F=[]
    for k in range(nz-1):
        b0=k*n;b1=(k+1)*n
        for i in range(n):
            j=(i+1)%n
            F+= [[b0+i,b0+j,b1+i],[b0+j,b1+j,b1+i]]
    # кришки
    capA_v,capA_f=trimesh.creation.triangulate_polygon(sg.Polygon(A),engine='earcut')
    capB_v,capB_f=trimesh.creation.triangulate_polygon(sg.Polygon(B),engine='earcut')
    mA=trimesh.Trimesh(np.column_stack([capA_v,np.full(len(capA_v),z0)]),capA_f[:,::-1],process=False)
    mB=trimesh.Trimesh(np.column_stack([capB_v,np.full(len(capB_v),z1)]),capB_f,process=False)
    side=trimesh.Trimesh(V,np.array(F),process=False)
    m=trimesh.util.concatenate([side,mA,mB]); m.merge_vertices()
    return m
