import numpy as np, trimesh
from shapely.geometry import Polygon
from scipy.spatial import cKDTree
def loft(path, prof, Xof):
    """path: list (Y,ztop). prof: list (u,zrel) simple polygon (no repeat). Xof: u->X."""
    M=len(prof); N=len(path)
    V=np.zeros((N*M,3))
    for i,(y,zt) in enumerate(path):
        for j,(u,zr) in enumerate(prof):
            V[i*M+j]=[Xof(u),y,zt+zr]
    F=[]
    idx=lambda i,j:i*M+j
    for i in range(N-1):
        for j in range(M):
            j2=(j+1)%M
            F.append([idx(i,j),idx(i,j2),idx(i+1,j2)])
            F.append([idx(i,j),idx(i+1,j2),idx(i+1,j)])
    poly=Polygon(prof)
    v2d,f2d=trimesh.creation.triangulate_polygon(poly,engine='earcut')
    tree=cKDTree(np.array(prof))
    _,map2=tree.query(np.asarray(v2d)[:,:2])
    for tri in f2d:
        a,b,c=[map2[k] for k in tri]
        F.append([idx(0,a),idx(0,c),idx(0,b)])
        F.append([idx(N-1,a),idx(N-1,b),idx(N-1,c)])
    me=trimesh.Trimesh(vertices=V,faces=np.array(F),process=True)
    me.merge_vertices();me.update_faces(me.nondegenerate_faces());me.update_faces(me.unique_faces())
    me.fix_normals()
    return me
