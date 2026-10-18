"""Exportador GLB de mundos proceduralmente creados, con nodos independientes."""
import math
import numpy as np
import trimesh

def _hexrgba(v):
    x=v.lstrip('#');return [int(x[i:i+2],16) for i in (0,2,4)]+[255]

def _part(scene,label,mesh,color,pos=(0,0,0),scale=(1,1,1),yaw=0):
    mesh.apply_scale(scale)
    if yaw:mesh.apply_transform(trimesh.transformations.rotation_matrix(yaw,[0,1,0]))
    mesh.apply_translation(pos)
    mesh.visual.face_colors=_hexrgba(color)
    scene.add_geometry(mesh,node_name=label,geom_name=label)

def _cyl(radius=0.5,height=1):
    return trimesh.creation.cylinder(radius=radius,height=height,sections=18, transform=trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]))

def _cone(height=1,radius=.5):
    return trimesh.creation.cone(radius=radius,height=height,sections=18,
            transform=trimesh.transformations.rotation_matrix(math.pi/2,[1,0,0]))

def _torus():
    # Ring of cylinders around a circle for portability.
    ring=trimesh.Scene()
    for i in range(28):
        a=i*math.tau/28
        s=trimesh.creation.icosphere(subdivisions=1,radius=.15)
        s.apply_translation([math.cos(a)*.85,math.sin(a)*.85,0])
        ring.add_geometry(s)
    return trimesh.util.concatenate(tuple(ring.geometry.values()))

def _geometry(kind):
    if kind in ('box','platform','tower','house'):return trimesh.creation.box(extents=[1,1,1])
    if kind in ('sphere','rock'):return trimesh.creation.icosphere(subdivisions=2,radius=.5)
    if kind in ('cylinder',):return _cyl()
    if kind in ('cone',):return _cone()
    if kind=='torus':return _torus()
    raise ValueError('Forma no compatible')

def export_scene_glb(scene:dict)->bytes:
    target=trimesh.Scene()
    for ix,obj in enumerate(scene['objects']):
        sx,sy,sz=obj['scale'];x,y,z=obj['position'];angle=obj['rotation'][1]
        kind=obj['kind'];color=obj['color'];oid=f'{ix:03d}_{obj["id"]}'
        if kind in ('tree','palm'):
            trunk=_cyl()
            _part(target,oid+'_tronco',trunk,'#7B573E',(x,y+sy*.34,z),(sx*.23,sy*.68,sz*.23),angle)
            foliage=trimesh.creation.icosphere(subdivisions=2,radius=.5) if kind=='palm' else _cone()
            _part(target,oid+'_copa',foliage,color,(x,y+sy*.76,z),(sx,sy*.60,sz),angle)
        elif kind=='house':
            _part(target,oid+'_edificio',_geometry('box'),color,(x,y+sy*.35,z),(sx,sy*.7,sz),angle)
            roof=_cone()
            _part(target,oid+'_tejado',roof,'#A45D4A',(x,y+sy*.93,z),(sx*1.35,sy*.53,sz*1.35),angle)
        else:
            mesh=_geometry(kind)
            h=0 if kind=='torus' else sy*.5
            _part(target,oid,mesh,color,(x,y+h,z),(sx,sy,sz),angle)
    return target.export(file_type='glb')
