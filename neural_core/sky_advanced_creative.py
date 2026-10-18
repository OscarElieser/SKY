"""SKY Advanced Creative v9.8: selección de primer plano con OpenCV GrabCut.
No afirma segmentación semántica ni reconstrucción 3D. Cada máscara se guarda
como recurso independiente, reutilizable y verificable.
"""
from __future__ import annotations
import io
from PIL import Image
from . import sky_creative as cr


def cutout_mask(asset_id:str, rect:list[int], iterations:int=4, foreground=None, background=None, brush_radius:int=4):
    if not isinstance(rect,list) or len(rect)!=4 or any(type(v) is not int for v in rect):
        raise ValueError('Rectángulo: [x, y, ancho, alto] con enteros')
    if type(iterations) is not int or not 1<=iterations<=7:
        raise ValueError('Iteraciones admitidas: 1 a 7')
    asset=cr.get_asset(asset_id)
    if not asset or asset['kind']!='image':raise ValueError('Seleccioná una imagen válida')
    path,_=cr.asset_path(asset_id)
    try:
        import cv2
        import numpy as np
    except ImportError as e:
        raise RuntimeError('La selección asistida requiere opencv-python-headless y numpy') from e
    with Image.open(path) as original:
        image=original.convert('RGB')
        w,h=image.size
        if w*h>8_000_000:raise ValueError('El recorte asistido admite hasta 8 MP')
        x,y,rw,rh=rect
        if x<0 or y<0 or rw<3 or rh<3 or x+rw>=w or y+rh>=h:
            raise ValueError('El rectángulo debe estar dentro de la imagen')
        pixel=np.asarray(image)[:,:,::-1].copy()
    foreground=foreground or []
    background=background or []
    if not isinstance(foreground,list) or not isinstance(background,list) or len(foreground)+len(background)>100:
        raise ValueError('Máximo 100 puntos de guía por selección')
    if type(brush_radius) is not int or not 1<=brush_radius<=20:
        raise ValueError('Radio de pincel: entre 1 y 20 píxeles')
    for points in (foreground,background):
        for point in points:
            if (not isinstance(point,list) or len(point)!=2 or any(type(v) is not int for v in point)
                or not (0<=point[0]<w and 0<=point[1]<h)):
                raise ValueError('Las guías deben ser coordenadas [x, y] dentro de la imagen')
    if {tuple(point) for point in foreground}&{tuple(point) for point in background}:
        raise ValueError('Un punto no puede ser simultáneamente fondo y objeto')
    matte=np.zeros((h,w),np.uint8)
    fg=np.zeros((1,65),np.float64);bg=np.zeros((1,65),np.float64)
    cv2.grabCut(pixel,matte,(x,y,rw,rh),bg,fg,iterations,cv2.GC_INIT_WITH_RECT)
    if foreground or background:
        for px,py in foreground:cv2.circle(matte,(px,py),brush_radius,cv2.GC_FGD,-1)
        for px,py in background:cv2.circle(matte,(px,py),brush_radius,cv2.GC_BGD,-1)
        cv2.grabCut(pixel,matte,None,bg,fg,iterations,cv2.GC_INIT_WITH_MASK)
    mask=np.where((matte==cv2.GC_FGD)|(matte==cv2.GC_PR_FGD),255,0).astype('uint8')
    buffer=io.BytesIO();Image.fromarray(mask,'L').save(buffer,format='PNG')
    result=cr.ingest(buffer.getvalue(),'SKY_mascara_'+asset_id+'.png')
    return {'mask_asset':result,'rectangle':rect,'method':'grabcut-guided' if foreground or background else 'grabcut','editable':True,'guide_points':{'foreground':len(foreground),'background':len(background)}}
