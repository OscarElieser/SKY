"""SKY 10.1: per-frame alpha mask interpolation and global video overlay tracks.

Masks are ordinary library images interpolated between timed keyframes; the
exporter creates temporary RGBA frames that FFmpeg actually renders. Neither
input source media nor project revisions are rewritten.
"""
from __future__ import annotations
import math
from pathlib import Path
from PIL import Image, ImageChops
from . import sky_creative as cr
from .sky_creative_v10 import validate_overlays


def validate_masks(entry,duration):
    masks=entry.get('mask_keyframes')
    if not masks:return False
    if not isinstance(masks,list) or not 1<=len(masks)<=8:
        raise ValueError('Se permiten de 1 a 8 fotogramas de máscara')
    if duration>30:raise ValueError('Las máscaras animadas admiten clips de hasta 30 segundos')
    previous=-1.
    for frame in masks:
        if not isinstance(frame,dict):raise ValueError('Fotograma de máscara inválido')
        t=frame.get('t')
        if isinstance(t,bool) or not isinstance(t,(float,int)) or not math.isfinite(t) or not 0<=t<=duration or t<=previous:
            raise ValueError('Tiempos de máscara inválidos o desordenados')
        previous=t
        asset=cr.get_asset(frame.get('mask_asset_id',''))
        if not asset or asset['kind']!='image':raise ValueError('Máscara inexistente en biblioteca privada')
    if int(entry.get('width',100))>512:
        raise ValueError('Las máscaras animadas tienen ancho máximo de 512 px')
    return True


def create_mask_frames(entry,duration,fps,folder:Path,prefix:str):
    """Render masked image frames at the same FPS as the resulting MP4."""
    frames=entry.get('mask_keyframes',[])
    if not frames:raise ValueError('La capa no contiene máscaras animadas')
    validate_masks(entry,duration)
    if duration*fps>900:raise ValueError('Demasiados fotogramas de máscara')
    image_path,_=cr.asset_path(entry['asset_id'])
    width=int(entry.get('width',100))
    with Image.open(image_path) as photo:
        rgba=photo.convert('RGBA')
        height=max(1,round(rgba.height*width/rgba.width))
        image=rgba.resize((width,height),Image.Resampling.LANCZOS)
    originals=[]
    for key in frames:
        path,_=cr.asset_path(key['mask_asset_id'])
        with Image.open(path) as original:
            originals.append(original.convert('L').resize((width,height),Image.Resampling.BILINEAR))
    alpha=image.getchannel('A')
    num=math.ceil(duration*fps)+1
    for i in range(num):
        t=min(duration,i/fps)
        if t<=frames[0]['t']:mask=originals[0]
        elif t>=frames[-1]['t']:mask=originals[-1]
        else:
            next_index=next(j for j in range(1,len(frames)) if frames[j]['t']>=t)
            a,b=frames[next_index-1],frames[next_index]
            amount=(t-a['t'])/(b['t']-a['t'])
            mask=Image.blend(originals[next_index-1],originals[next_index],amount)
        current=image.copy()
        current.putalpha(ImageChops.multiply(alpha,mask))
        current.save(folder/f'{prefix}_{i:05d}.png',format='PNG')
    return str(folder/f'{prefix}_%05d.png'),num


def validate_global_tracks(spec):
    tracks=spec.get('tracks',[])
    if not isinstance(tracks,list) or len(tracks)>8:
        raise ValueError('Máximo ocho pistas de superposición globales')
    duration=0.
    for clip in spec['clips']:
        asset=cr.get_asset(clip['asset_id'])
        duration+=(clip.get('end',5 if asset['kind']=='image' else asset['duration'])-clip.get('start',0))/clip.get('speed',1)
    validate_overlays({'overlays':tracks},duration)
    mask_count=0
    for entry in tracks:
        if validate_masks(entry,duration):mask_count+=1
    if mask_count>2:raise ValueError('Hasta dos pistas globales con máscaras animadas')
    return tracks,duration


def apply_global_tracks(spec,joined:Path,folder:Path,ff:str,fps:int):
    tracks,duration=validate_global_tracks(spec)
    if not tracks:return joined
    from .sky_creative_v10 import build_overlay_filters
    command=[ff,'-hide_banner','-loglevel','error','-y','-i',str(joined)]
    for i,entry in enumerate(tracks):
        if entry.get('mask_keyframes'):
            pattern,_=create_mask_frames(entry,duration,fps,folder,f'global_mask_{i}')
            command+=['-framerate',str(fps),'-start_number','0','-i',pattern]
        else:
            path,_=cr.asset_path(entry['asset_id'])
            command+=['-loop','1','-framerate',str(fps),'-i',str(path)]
    output_labels,filters=build_overlay_filters(tracks,list(range(1,len(tracks)+1)),'0:v',100,duration)
    # Global-track processing happens after each individual clip has been joined.
    target=folder/'joined_tracks.mp4'
    command+=['-filter_complex',';'.join(filters),'-map',f'[{output_labels}]','-map','0:a:0',
              '-t',str(duration),'-c:v','libx264','-preset','veryfast','-crf','23',
              '-pix_fmt','yuv420p','-c:a','copy','-movflags','+faststart',str(target)]
    cr._execute(command,timeout=180)
    return target
