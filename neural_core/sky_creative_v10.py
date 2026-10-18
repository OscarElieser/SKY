"""SKY v10: seguimiento local de objetos y composición multicapa con FFmpeg.

Seguimiento por coincidencia de plantillas (OpenCV), no identificación semántica:
requiere una selección inicial aportada por la persona usuaria. Los fotogramas
clave generados son editables y la confianza queda registrada por muestra.
"""
from __future__ import annotations
import math
from pathlib import Path
from . import sky_creative as cr


def numeric(x, low, high, name):
    if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not low<=x<=high:
        raise ValueError(f'{name} debe estar entre {low} y {high}')
    return float(x)


def validate_overlays(clip, duration):
    overlays=clip.get('overlays',[])
    if not isinstance(overlays,list) or len(overlays)>8:
        raise ValueError('Se permiten hasta 8 superposiciones de video')
    for entry in overlays:
        if not isinstance(entry,dict):raise ValueError('Superposición inválida')
        asset=cr.get_asset(entry.get('asset_id',''))
        if not asset or asset['kind']!='image':raise ValueError('La capa multimedia debe ser una imagen')
        numeric(entry.get('width',100),1,1500,'Ancho de capa')
        numeric(entry.get('opacity',1),0,1,'Opacidad')
        start=numeric(entry.get('from',0),0,duration,'Inicio de superposición')
        end=numeric(entry.get('to',duration),0,duration,'Fin de superposición')
        if end<=start:raise ValueError('El final debe ser posterior al inicio de la capa')
        for key in ('x','y'):numeric(entry.get(key,0),-4000,4000,key)
        positions=entry.get('keyframes',[])
        if not isinstance(positions,list) or len(positions)>100:
            raise ValueError('Máximo 100 fotogramas de seguimiento por capa')
        previous=-1
        for p in positions:
            if not isinstance(p,dict):raise ValueError('Fotograma inválido')
            t=numeric(p.get('t'),0,duration,'Tiempo de seguimiento')
            if t<=previous:raise ValueError('Los tiempos deben aumentar')
            previous=t
            for key in ('x','y'):numeric(p.get(key),-4000,4000,key)
            if 'confidence' in p:numeric(p['confidence'],0,1,'Confianza')
    return True


def path_expression(frames,axis,default):
    if not frames:return f'{float(default):.4f}'
    expr=f'{float(frames[-1][axis]):.4f}'
    for first,last in reversed(list(zip(frames,frames[1:]))):
        a=float(first['t']);b=float(last['t']);start=float(first[axis]);delta=float(last[axis])-start
        fraction=f'min(1,max(0,(t-{a:.4f})/{b-a:.4f}))'
        expression=f'({start:.4f}+({delta:.4f})*{fraction})'
        expr=f'if(lt(t,{b:.4f}),{expression},{expr})'
    return f'if(lt(t,{float(frames[0]["t"]):.4f}),{float(frames[0][axis]):.4f},{expr})'


def build_overlay_filters(entries, inputs, prior, stage, duration):
    """Produce filtros acotados con expresiones numéricas; jamás shell."""
    lines=[]
    for n,(entry,idx) in enumerate(zip(entries,inputs)):
        validate_overlays({'overlays':[entry]},duration)
        width=int(entry.get('width',100));alpha=float(entry.get('opacity',1))
        overlay=f'sky_layer_{stage}_{n}'
        out=f'sky_merge_{stage}_{n}'
        lines.append(f'[{idx}:v]scale={width}:-1,format=rgba,colorchannelmixer=aa={alpha:.3f}[{overlay}]')
        x=path_expression(entry.get('keyframes',[]),'x',entry.get('x',0))
        y=path_expression(entry.get('keyframes',[]),'y',entry.get('y',0))
        start=float(entry.get('from',0));end=float(entry.get('to',duration))
        lines.append(f"[{prior}][{overlay}]overlay=x='{x}':y='{y}':eval=frame:shortest=1:enable='between(t,{start:.4f},{end:.4f})'[{out}]")
        prior=out
    return prior,lines


def _scaled_frame(frame, width, height):
    import cv2
    h,w=frame.shape[:2]
    ratio=min(width/w,height/h)
    new_w=max(1,int(w*ratio));new_h=max(1,int(h*ratio))
    frame=cv2.resize(frame,(new_w,new_h),interpolation=cv2.INTER_AREA)
    import numpy as np
    canvas=np.zeros((height,width,3),dtype='uint8')
    x=(width-new_w)//2;y=(height-new_h)//2
    canvas[y:y+new_h,x:x+new_w]=frame
    return canvas


def track_object(asset_id, box, start=0., end=3., step=.3, output_width=640,output_height=360,confidence_floor=.3,speed=1.):
    """Seguimiento de ROI desde un video real; devuelve keyframes para overlays.

    Muestra el fotograma inicial y busca la misma textura cerca de su posición.
    Los desplazamientos fuertes, oclusiones y escenas sin textura pueden fallar.
    """
    asset=cr.get_asset(asset_id)
    if not asset or asset['kind']!='video':raise ValueError('El seguimiento requiere un video de la biblioteca')
    if not isinstance(box,list) or len(box)!=4 or any(type(v) is not int for v in box):
        raise ValueError('Se requiere un rectángulo [x,y,ancho,alto]')
    output_width=int(numeric(output_width,128,1280,'Ancho'));output_height=int(numeric(output_height,128,720,'Alto'))
    start=numeric(start,0,1800,'Inicio');end=numeric(end,0,1800,'Final');speed=numeric(speed,.5,2,'Velocidad')
    step=numeric(step,.12,2,'Intervalo');confidence_floor=numeric(confidence_floor,.1,.9,'Umbral')
    if end<=start or end-start>20 or end>float(asset['duration'] or 0)+.02:raise ValueError('Seguimiento limitado a 20 segundos de material válido')
    if int((end-start)/step)>100:raise ValueError('Máximo 100 muestras')
    x,y,w,h=box
    if x<0 or y<0 or w<12 or h<12 or x+w>=output_width or y+h>=output_height:
        raise ValueError('El rectángulo inicial debe estar dentro del video de salida')
    try:
        import cv2
    except ImportError as exc:raise RuntimeError('Instalá OpenCV para seguir objetos') from exc
    path,_=cr.asset_path(asset_id)
    video=cv2.VideoCapture(str(path))
    if not video.isOpened():raise ValueError('El video no puede analizarse')
    try:
        def frame_at(seconds):
            video.set(cv2.CAP_PROP_POS_MSEC,seconds*1000)
            success,frame=video.read()
            if not success:raise ValueError('No se pudo leer el fotograma del video')
            return cv2.cvtColor(_scaled_frame(frame,output_width,output_height),cv2.COLOR_BGR2GRAY)
        initial=frame_at(start)
        template=initial[y:y+h,x:x+w].copy()
        if template.std()<4:raise ValueError('La región no tiene detalles suficientes para el seguimiento')
        coords=[];last_x,last_y=x,y;lost=0
        n=int((end-start)/step)+1
        for i in range(n+1):
            t=min(end,start+i*step)
            current=frame_at(t)
            if i==0:
                score=1.0
            else:
                delta=max(35,int(max(w,h)*1.5))
                sx=max(0,last_x-delta);sy=max(0,last_y-delta)
                ex=min(output_width,last_x+w+delta);ey=min(output_height,last_y+h+delta)
                search=current[sy:ey,sx:ex]
                if search.shape[0]<h or search.shape[1]<w:raise ValueError('No hay espacio suficiente para seguir la selección')
                matches=cv2.matchTemplate(search,template,cv2.TM_CCOEFF_NORMED)
                _,score,_,point=cv2.minMaxLoc(matches)
                if not math.isfinite(score):score=0
                if score>=confidence_floor:
                    last_x=sx+point[0];last_y=sy+point[1]
                else:lost+=1
            coords.append({'t':round((t-start)/speed,3),'x':last_x,'y':last_y,'confidence':round(max(0,min(1,score)),3)})
            if t>=end-1e-6:break
        if lost>max(2,len(coords)//2):raise ValueError('El objeto se perdió en demasiados fotogramas; elegí una región más clara')
        return {'asset_id':asset_id,'box':box,'keyframes':coords,'lost_samples':lost,'samples':len(coords),
                'method':'opencv-template-matching','limitations':'Seguimiento local aproximado; revisá los resultados antes del render'}
    finally:video.release()
