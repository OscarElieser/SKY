"""SKY Studio 3D: separación guiada, piezas PNG RGBA y aproximación 2.5D en GLB.

No infiere superficies ocultas de fotografías monoculares; usa siluetas y extrusión.
Sin conexiones externas ni archivos persistidos salvo exportación elegida por usuario.
"""
from __future__ import annotations
from dataclasses import dataclass
from io import BytesIO
import json, math, re, zipfile
import numpy as np
from PIL import Image, ImageOps

MAX_PIXELS=12_000_000
MAX_BYTES=12_000_000


def leer_imagen(blob: bytes) -> Image.Image:
    if len(blob)>MAX_BYTES: raise ValueError('Imagen superior a 12 MB')
    Image.MAX_IMAGE_PIXELS=MAX_PIXELS
    with Image.open(BytesIO(blob)) as im:
        im=ImageOps.exif_transpose(im)
        if im.width * im.height > MAX_PIXELS: raise ValueError('Resolución demasiado grande')
        return im.convert('RGB').copy()


def caja_relativa(ancho:int, alto:int, x0:float,y0:float,x1:float,y1:float) -> tuple[int,int,int,int]:
    vals=[x0,y0,x1,y1]
    if not all(math.isfinite(v) and 0<=v<=1 for v in vals) or not (x0<x1 and y0<y1):
        raise ValueError('La caja relativa debe estar entre 0 y 1 y tener área positiva')
    l=max(0,min(ancho-1,int(ancho*x0))); t=max(0,min(alto-1,int(alto*y0)))
    r=max(l+1,min(ancho,int(math.ceil(ancho*x1))))
    b=max(t+1,min(alto,int(math.ceil(alto*y1))))
    return l,t,r,b


def segmentar_parte(imagen:Image.Image, caja:tuple[int,int,int,int], *, modo:str='grabcut') -> Image.Image:
    """Máscara RGBA a tamaño original. 'rectangulo' es respaldo inequívoco."""
    arr=np.array(imagen.convert('RGB')); h,w=arr.shape[:2]
    l,t,r,b=caja
    if not(0<=l<r<=w and 0<=t<b<=h): raise ValueError('Caja inválida')
    mask=np.zeros((h,w),dtype=np.uint8)
    if modo=='grabcut':
        try:
            import cv2
            if r-l>=6 and b-t>=6 and l>0 and t>0 and r<w and b<h:
                reduced=arr
                factor=min(1.0,900/max(w,h))
                if factor<1:
                    reduced=cv2.resize(arr,(max(2,int(w*factor)),max(2,int(h*factor))))
                hh,ww=reduced.shape[:2]
                xx=max(1,int(l*ww/w)); yy=max(1,int(t*hh/h))
                ww2=max(2,min(ww-xx-1,int((r-l)*ww/w)))
                hh2=max(2,min(hh-yy-1,int((b-t)*hh/h)))
                if xx+ww2>=ww or yy+hh2>=hh: raise ValueError('Caja en el borde')
                m=np.zeros((hh,ww),dtype=np.uint8)
                cv2.grabCut(cv2.cvtColor(reduced,cv2.COLOR_RGB2BGR),m,(xx,yy,ww2,hh2),
                            np.zeros((1,65),np.float64),np.zeros((1,65),np.float64),3,cv2.GC_INIT_WITH_RECT)
                m=np.where((m==2)|(m==0),0,255).astype('uint8')
                if factor<1: m=cv2.resize(m,(w,h),interpolation=cv2.INTER_NEAREST)
                mask=m
                if np.count_nonzero(mask)<12: raise ValueError('No se halló primer plano')
            else: raise ValueError('Imagen o caja en el borde')
        except Exception:  # Si falta OpenCV o falla el contorno: recorte explícito como respaldo.
            mask[t:b,l:r]=255
    elif modo=='rectangulo':
        mask[t:b,l:r]=255
    else:
        raise ValueError('Modo de segmentación no reconocido')
    rgba=np.concatenate((arr,mask[:,:,None]),axis=-1)
    return Image.fromarray(rgba,mode='RGBA')


def png_bytes(img:Image.Image)->bytes:
    out=BytesIO(); img.save(out,format='PNG'); return out.getvalue()


def _mesh_from_rgba(rgba:Image.Image, *, depth:float=0.08, max_side:int=80):
    """Malla 2.5D local con dos superficies y paredes de contorno.

    Para cada celda RGBA visible se crean caras superior e inferior; laterales sólo
    en borde de máscara. No necesita triangulador nativo ni conexión a la nube.
    """
    if not 0.005<=depth<=2: raise ValueError('Profundidad relativa fuera de rango')
    import trimesh
    src=rgba.convert('RGBA')
    w,h=src.size
    f=min(1,max_side/max(w,h))
    if f<1: src=src.resize((max(2,round(w*f)),max(2,round(h*f))),Image.Resampling.NEAREST)
    arr=np.asarray(src)
    active=arr[:,:,3]>=128
    if not np.any(active): raise ValueError('La pieza no contiene píxeles visibles')
    H,W=active.shape
    # La pieza se centra de manera natural en su lienzo, no en el centro de la caja.
    vertices=[]; faces=[]; face_colors=[]
    idx={}
    for j in range(H+1):
        for i in range(W+1):
            for z_id,z in enumerate((0,depth)):
                idx[(i,j,z_id)]=len(vertices)
                vertices.append(((i/W-.5)*(w/max(w,h)), (.5-j/H)*(h/max(w,h)),z))
    def tri(a,b,c,rgb):
        faces.append([idx[a],idx[b],idx[c]])
        face_colors.append([int(rgb[0]),int(rgb[1]),int(rgb[2]),255])
    for y in range(H):
        for x in range(W):
            if not active[y,x]:continue
            rgb=arr[y,x,:3]
            p00=(x,y,1);p10=(x+1,y,1);p11=(x+1,y+1,1);p01=(x,y+1,1)
            tri(p00,p11,p10,rgb);tri(p00,p01,p11,rgb)
            b00=(x,y,0);b10=(x+1,y,0);b11=(x+1,y+1,0);b01=(x,y+1,0)
            tri(b00,b10,b11,rgb);tri(b00,b11,b01,rgb)
            if y==0 or not active[y-1,x]:
                tri(b00,p10,p00,rgb);tri(b00,b10,p10,rgb)
            if y==H-1 or not active[y+1,x]:
                tri(b01,p01,p11,rgb);tri(b01,p11,b11,rgb)
            if x==0 or not active[y,x-1]:
                tri(b00,p00,p01,rgb);tri(b00,p01,b01,rgb)
            if x==W-1 or not active[y,x+1]:
                tri(b10,b11,p11,rgb);tri(b10,p11,p10,rgb)
    mesh=trimesh.Trimesh(vertices=np.asarray(vertices,dtype=float),faces=np.asarray(faces),process=False)
    mesh.visual.face_colors=np.asarray(face_colors,dtype=np.uint8)
    return mesh


def ensamblar_glb(partes:list[dict], ancho:int, alto:int) -> bytes:
    """Partes: name, rgba bytes PNG, depth, dx, dy, dz, enabled.

    Conserva posiciones de la fotografía. dx/dy/dz permiten separarlas/ensamblarlas.
    """
    if not partes: raise ValueError('Agregá al menos una pieza antes de exportar')
    if len(partes)>18: raise ValueError('Máximo 18 piezas por proyecto')
    if ancho<1 or alto<1: raise ValueError('Dimensiones inválidas')
    import trimesh
    scene=trimesh.Scene()
    for n,p in enumerate(partes):
        if not p.get('enabled',True):continue
        rgba=Image.open(BytesIO(p['png'])).convert('RGBA')
        if rgba.size!=(ancho,alto): raise ValueError('La pieza no coincide con el lienzo')
        mesh=_mesh_from_rgba(rgba,depth=float(p.get('depth',0.08)))
        for axis,key in enumerate(('dx','dy','dz')):
            shift=float(p.get(key,0))
            if not math.isfinite(shift) or abs(shift)>10: raise ValueError('Desplazamiento fuera de rango')
            mesh.vertices[:,axis]+=shift
        name=re.sub('[^A-Za-z0-9_-]','_',str(p.get('name','pieza'))[:48]) or 'pieza'
        scene.add_geometry(mesh,node_name=f'{n:02d}_{name}',geom_name=f'{n:02d}_{name}')
    if not scene.geometry: raise ValueError('No hay piezas activas')
    return scene.export(file_type='glb')


def crear_paquete(partes:list[dict], imagen_original:bytes, w:int,h:int)->bytes:
    glb=ensamblar_glb(partes,w,h)
    datos={'version':'SKY-5.0','tipo':'extrusion_2_5D','width':w,'height':h,'partes':[]}
    buff=BytesIO()
    with zipfile.ZipFile(buff,'w',compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr('modelo_ensamblado.glb',glb)
        z.writestr('original.png',imagen_original)
        for k,p in enumerate(partes,1):
            nombre=f'piezas/pieza_{k:02}.png'
            z.writestr(nombre,p['png'])
            datos['partes'].append({key:p.get(key) for key in ('name','depth','dx','dy','dz','enabled')}|{'png':nombre})
        z.writestr('proyecto_sky.json',json.dumps(datos,ensure_ascii=False,indent=2))
        z.writestr('LEEME.txt','SKY Studio 3D: estas mallas son siluetas extruidas (2.5D), no reconstrucción real de las superficies ocultas. Abrí el GLB en Blender para editar cada pieza.\n')
    return buff.getvalue()


def importar_paquete(blob:bytes):
    """Restaurar proyecto SKY exportado (sin extraer archivos al disco)."""
    if not blob or len(blob)>35_000_000: raise ValueError('Proyecto ZIP demasiado grande')
    with zipfile.ZipFile(BytesIO(blob)) as z:
        if len(z.infolist())>28: raise ValueError('Demasiados archivos en proyecto')
        if sum(i.file_size for i in z.infolist())>55_000_000:
            raise ValueError('Proyecto descomprimido demasiado grande')
        metadata=json.loads(z.read('proyecto_sky.json'))
        if metadata.get('tipo')!='extrusion_2_5D':raise ValueError('No es un proyecto de SKY Studio 3D')
        original=z.read('original.png')
        img=leer_imagen(original)
        if list(img.size)!=[metadata.get('width'),metadata.get('height')]:
            raise ValueError('La imagen y el manifiesto no coinciden')
        if len(metadata.get('partes',[]))>18:raise ValueError('Demasiadas piezas')
        partes=[]
        for i,item in enumerate(metadata['partes'],1):
            nombre=f'piezas/pieza_{i:02}.png'
            if item.get('png')!=nombre:raise ValueError('Ruta de pieza incorrecta')
            png=z.read(nombre)
            part=Image.open(BytesIO(png)).convert('RGBA')
            if part.size!=img.size:raise ValueError('Dimensiones de pieza incorrectas')
            data={'name':str(item['name'])[:48],'png':png,'depth':float(item['depth']),
                  'dx':float(item['dx']),'dy':float(item['dy']),'dz':float(item['dz']),
                  'enabled':bool(item.get('enabled',True))}
            if not .005<=data['depth']<=2:raise ValueError('Profundidad inválida')
            if not all(math.isfinite(data[k]) and abs(data[k])<=10 for k in ('dx','dy','dz')):
                raise ValueError('Desplazamiento inválido')
            partes.append(data)
        return png_bytes(img),partes
