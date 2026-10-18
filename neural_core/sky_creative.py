"""SKY Creative Studio v9.7 — bibliotecas y exportación REAL, privada y no destructiva.

Sin telemetría ni IA externa: Pillow compone imágenes; FFmpeg monta videos. Los
proyectos guardan recetas editables, cada exportación es un archivo nuevo.
"""
from __future__ import annotations
import hashlib,io,json,os,re,shutil,sqlite3,subprocess,tempfile,time,uuid
from pathlib import Path
from datetime import datetime,timezone
from PIL import Image,ImageDraw,ImageFont,ImageEnhance,ImageFilter,ImageOps,UnidentifiedImageError

ROOT=Path(__file__).resolve().parents[1]
MAX_IMPORT=80*1024*1024
MAX_PIXEL=32_000_000
VALID_KINDS={'image','video','audio'}
IMAGE_EXTS={'PNG':'.png','JPEG':'.jpg','WEBP':'.webp'}
VIDEO_FORMATS={'.mp4','.mov','.webm','.mkv'}
AUDIO_FORMATS={'.mp3','.wav','.m4a','.ogg','.flac','.aac'}

def store_dir():return Path(os.getenv('SKY_CREATIVE_DIR') or ROOT/'local_data'/'sky_creative')
def db_path():return Path(os.getenv('SKY_CREATIVE_DB') or ROOT/'local_data'/'sky_creative.sqlite3')
def now():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def ident(prefix):return prefix+'_'+uuid.uuid4().hex[:20]
def connection():
    p=db_path();p.parent.mkdir(parents=True,exist_ok=True)
    con=sqlite3.connect(p,timeout=15);con.row_factory=sqlite3.Row
    con.execute('PRAGMA journal_mode=WAL');con.execute('PRAGMA busy_timeout=15000')
    con.executescript('''
      CREATE TABLE IF NOT EXISTS assets(id TEXT PRIMARY KEY,filename TEXT NOT NULL,kind TEXT NOT NULL,
        mimetype TEXT NOT NULL,sha256 TEXT NOT NULL,path TEXT NOT NULL,size INTEGER NOT NULL,
        duration REAL,created_at TEXT NOT NULL,source TEXT NOT NULL DEFAULT 'uploaded');
      CREATE INDEX IF NOT EXISTS idx_assets_sha ON assets(sha256);
      CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY,kind TEXT NOT NULL,name TEXT NOT NULL,
        spec TEXT NOT NULL,version INTEGER NOT NULL DEFAULT 1,sky_project_id TEXT,updated_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS exports(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,
        version INTEGER NOT NULL,asset_id TEXT NOT NULL,created_at TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS project_versions(project_id TEXT NOT NULL,version INTEGER NOT NULL,
        spec TEXT NOT NULL,saved_at TEXT NOT NULL,PRIMARY KEY(project_id,version));
      CREATE TABLE IF NOT EXISTS job_specs(job_id TEXT PRIMARY KEY,project_version INTEGER NOT NULL,spec TEXT NOT NULL);
      CREATE TABLE IF NOT EXISTS jobs(id TEXT PRIMARY KEY,project_id TEXT NOT NULL,
        status TEXT NOT NULL,progress INTEGER NOT NULL DEFAULT 0,error TEXT NOT NULL DEFAULT '',
        asset_id TEXT,created_at TEXT NOT NULL,updated_at TEXT NOT NULL);
    ''')
    return con

def _ffbin(name):
    value=shutil.which(name)
    if not value:raise RuntimeError(f'{name} no está instalado; instalá FFmpeg y añadilo al PATH')
    return value

def _probe(path):
    try:
        p=subprocess.run([_ffbin('ffprobe'),'-v','error','-show_entries','format=duration:stream=codec_type,width,height',
            '-of','json',str(path)],capture_output=True,text=True,timeout=15,check=True)
        obj=json.loads(p.stdout)
        kinds={s['codec_type'] for s in obj.get('streams',[]) if 'codec_type' in s}
        duration=float(obj.get('format',{}).get('duration') or 0)
        return kinds,duration
    except (subprocess.CalledProcessError,ValueError,KeyError,subprocess.TimeoutExpired) as ex:
        raise ValueError('El archivo multimedia no es válido o no puede leerse') from ex

def ingest(data:bytes,filename:str):
    if not data or len(data)>MAX_IMPORT:raise ValueError('El archivo debe contener datos y medir 80 MB o menos')
    name=Path(filename).name[:120] or 'archivo'
    ext=Path(name).suffix.lower()
    if ext in ('.png','.jpg','.jpeg','.webp'):
        try:
            with Image.open(io.BytesIO(data)) as im:
                im.verify()
            with Image.open(io.BytesIO(data)) as im:
                if im.width*im.height>MAX_PIXEL:raise ValueError('Imagen demasiado grande')
                fmt=im.format
            if fmt not in IMAGE_EXTS:raise ValueError('Formato de imagen inválido')
        except (OSError,UnidentifiedImageError,Image.DecompressionBombError) as ex:raise ValueError('Imagen inválida') from ex
        kind='image';mime={'PNG':'image/png','JPEG':'image/jpeg','WEBP':'image/webp'}[fmt];suffix=IMAGE_EXTS[fmt];duration=None
    elif ext in VIDEO_FORMATS|AUDIO_FORMATS:
        # Nunca se confía en la extensión: el contenido debe pasar ffprobe.
        with tempfile.TemporaryDirectory() as t:
            temp=Path(t)/('input'+ext);temp.write_bytes(data)
            streams,duration=_probe(temp)
        if duration<=0 or duration>1800:raise ValueError('Solo se admiten archivos de hasta 30 minutos')
        kind='video' if ext in VIDEO_FORMATS else 'audio'
        if ('video' if kind=='video' else 'audio') not in streams:raise ValueError('El contenido no corresponde al tipo de archivo')
        mime=({'mp4':'video/mp4','webm':'video/webm','mov':'video/quicktime','mkv':'video/x-matroska'}.get(ext[1:])
              if kind=='video' else {'mp3':'audio/mpeg','wav':'audio/wav','m4a':'audio/mp4','ogg':'audio/ogg','flac':'audio/flac','aac':'audio/aac'}.get(ext[1:]))
        suffix=ext
    else:raise ValueError('Archivo no admitido: PNG, JPEG, WEBP, MP4, MOV, WEBM, MKV y audio compatible')
    folder=store_dir()/'media';folder.mkdir(parents=True,exist_ok=True)
    digest=hashlib.sha256(data).hexdigest();target=folder/(digest+suffix)
    if not target.exists():
        with tempfile.NamedTemporaryFile(dir=folder,delete=False) as temp:
            temp.write(data);tmp=Path(temp.name)
        tmp.replace(target)
        try:os.chmod(target,0o600)
        except OSError:pass
    asset=ident('asset')
    with connection() as db:
        db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?)',
                   (asset,name,kind,mime,digest,str(target),len(data),duration,now(),'uploaded'))
    return get_asset(asset)

def get_asset(asset_id):
    with connection() as db:row=db.execute('SELECT * FROM assets WHERE id=?',(asset_id,)).fetchone()
    return dict(row) if row else None

def list_assets(kind=None):
    if kind and kind not in VALID_KINDS:raise ValueError('Tipo inválido')
    with connection() as db:
        if kind:rows=db.execute('SELECT * FROM assets WHERE kind=? ORDER BY created_at DESC,id DESC LIMIT 300',(kind,)).fetchall()
        else:rows=db.execute('SELECT * FROM assets ORDER BY created_at DESC,id DESC LIMIT 300').fetchall()
    return [dict(x) for x in rows]

def asset_path(asset_id):
    obj=get_asset(asset_id)
    if not obj:raise KeyError('Archivo no encontrado')
    p=Path(obj['path'])
    if not p.is_file() or p.is_symlink():raise FileNotFoundError('El archivo multimedia ya no está disponible')
    # Los archivos solo se leen desde el directorio privado administrado por SKY.
    if not p.resolve().is_relative_to((store_dir()/'media').resolve()):raise PermissionError('Archivo fuera del almacén privado')
    return p,obj

def create_project(kind,name,spec,sky_project_id=None):
    if kind not in ('image','video'):raise ValueError('Proyecto no compatible')
    if not name or len(name)>120:raise ValueError('Nombre inválido')
    if sky_project_id:
        from neural_core.sky_projects import project as sky_project
        if not sky_project(sky_project_id):raise KeyError('Proyecto SKY inexistente')
    validate_spec(kind,spec)
    pid=ident('crt')
    with connection() as db:
        db.execute('INSERT INTO projects VALUES(?,?,?,?,?,?,?)',
            (pid,kind,name,json.dumps(spec,ensure_ascii=False),1,sky_project_id,now()))
        db.execute('INSERT INTO project_versions VALUES(?,?,?,?)',(pid,1,json.dumps(spec,ensure_ascii=False),now()))
    if sky_project_id:
        from neural_core.sky_projects import link
        link(sky_project_id,'creative',pid,name)
    return get_project(pid)

def get_project(pid):
    with connection() as db:r=db.execute('SELECT * FROM projects WHERE id=?',(pid,)).fetchone()
    if not r:return None
    x=dict(r);x['spec']=json.loads(x['spec']);return x

def list_projects():
    with connection() as db:rows=db.execute('SELECT * FROM projects ORDER BY updated_at DESC LIMIT 150').fetchall()
    result=[]
    for r in rows:x=dict(r);x['spec']=json.loads(x['spec']);result.append(x)
    return result

def update_project(pid,spec,version):
    obj=get_project(pid)
    if not obj:raise KeyError('Proyecto creativo no encontrado')
    validate_spec(obj['kind'],spec)
    with connection() as db:
        cur=db.execute('UPDATE projects SET spec=?,version=version+1,updated_at=? WHERE id=? AND version=?',
                       (json.dumps(spec,ensure_ascii=False),now(),pid,version))
        if cur.rowcount!=1:raise RuntimeError('Otra revisión modificó el proyecto; recargá antes de guardar')
        db.execute('INSERT INTO project_versions VALUES(?,?,?,?)',(pid,version+1,json.dumps(spec,ensure_ascii=False),now()))
    return get_project(pid)

def versions(pid):
    with connection() as db:return [dict(x) for x in db.execute('SELECT version,saved_at,spec FROM project_versions WHERE project_id=? ORDER BY version DESC LIMIT 50',(pid,))]

def _num(value,low,high,label):
    if not isinstance(value,(int,float)) or isinstance(value,bool) or not low<=value<=high:raise ValueError(label+' fuera de rango')
    return value

def validate_spec(kind,spec):
    if not isinstance(spec,dict):raise ValueError('Se necesita un proyecto JSON editable')
    if kind=='image':
        w=int(_num(spec.get('width',1280),100,4000,'Ancho'));h=int(_num(spec.get('height',720),100,4000,'Alto'))
        if w*h>12_000_000:raise ValueError('Resolución demasiado grande')
        layers=spec.get('layers',[])
        if not isinstance(layers,list) or len(layers)>35:raise ValueError('Máximo 35 capas')
        for layer in layers:
            if not isinstance(layer,dict) or layer.get('type') not in ('image','text','rectangle'):raise ValueError('Tipo de capa inválido')
            for key,default in [('x',0),('y',0)]:_num(layer.get(key,default),-10000,10000,key)
            _num(layer.get('opacity',1),0,1,'Opacidad')
            if layer['type']=='image':
                asset=get_asset(layer.get('asset_id',''))
                if not asset or asset['kind']!='image':raise ValueError('Imagen de capa inexistente')
                _num(layer.get('width',600),1,5000,'Ancho de capa')
                if 'height' in layer:_num(layer['height'],1,5000,'Alto de capa')
                if 'rotate' in layer:_num(layer['rotate'],-360,360,'Rotación')
                if layer.get('mask_asset_id'):
                    mask=get_asset(layer['mask_asset_id'])
                    if not mask or mask['kind']!='image':raise ValueError('Máscara de imagen inexistente')
                    if layer.get('mask_mode','luminance') not in ('luminance','alpha'):raise ValueError('Modo de máscara inválido')
                    _num(layer.get('mask_feather',0),0,35,'Suavizado de máscara')
                    if not isinstance(layer.get('mask_invert',False),bool):raise ValueError('Invertir máscara inválido')
                if 'crop' in layer:
                    crop=layer['crop']
                    if not isinstance(crop,list) or len(crop)!=4:raise ValueError('Recorte inválido')
                    for n in crop:_num(n,0,10000,'Recorte')
                    if crop[2]<=crop[0] or crop[3]<=crop[1]:raise ValueError('Rectángulo de recorte inválido')
            elif layer['type']=='text':
                if len(str(layer.get('text','')))>3000:raise ValueError('Texto demasiado largo')
                _num(layer.get('size',48),8,250,'Tamaño de letra')
            else:
                _num(layer.get('width',200),1,5000,'Ancho de rectángulo')
                _num(layer.get('height',100),1,5000,'Alto de rectángulo')
        changes=spec.get('adjustments',{})
        if not isinstance(changes,dict):raise ValueError('Ajustes inválidos')
        for key in ('brightness','contrast','saturation','sharpness'):_num(changes.get(key,1),0,3,key)
        _num(changes.get('blur',0),0,20,'Desenfoque')
    elif kind=='video':
        clips=spec.get('clips',[])
        if not isinstance(clips,list) or len(clips)>20 or not clips:raise ValueError('Se requieren entre 1 y 20 clips')
        w=int(_num(spec.get('width',640),128,1920,'Ancho'));h=int(_num(spec.get('height',360),128,1080,'Alto'))
        if w*h>2_073_600 or w%2 or h%2:raise ValueError('Resolución de video no válida')
        for clip in clips:
            if not isinstance(clip,dict):raise ValueError('Clip inválido')
            asset=get_asset(clip.get('asset_id',''))
            if not asset or asset['kind'] not in ('video','image'):raise ValueError('Clip inexistente (se admiten imágenes o videos)')
            start=_num(clip.get('start',0),0,1800,'Inicio')
            end=_num(clip.get('end',5 if asset['kind']=='image' else asset['duration']),0,1800,'Fin')
            speed=_num(clip.get('speed',1),0.5,2,'Velocidad')
            from .sky_creative_v10 import validate_overlays
            validate_overlays(clip,(end-start)/speed)
            from .sky_creative_v101 import validate_masks
            if sum(bool(layer.get('mask_keyframes')) for layer in clip.get('overlays',[]))>2:
                raise ValueError('Máximo dos capas con máscara animada por clip')
            for layer in clip.get('overlays',[]):validate_masks(layer,(end-start)/speed)
            if 'caption_motion' in clip:
                motion=clip['caption_motion']
                if not isinstance(motion,dict):raise ValueError('Animación no válida')
                for key in ('x0','x1','y0','y1'):
                    if key in motion:_num(motion[key],-4000,4000,'Coordenada de fotograma clave')
                for key in ('fade_in','fade_out'):
                    if key in motion:_num(motion[key],0,3,'Duración de fundido')
                if (motion.get('fade_in',0)+motion.get('fade_out',0))>(end-start)/speed:
                    raise ValueError('Fundidos exceden duración del clip')
            if 'caption_keyframes' in clip:
                frames=clip['caption_keyframes']
                if not isinstance(frames,list) or not 2<=len(frames)<=16:
                    raise ValueError('Se requieren de 2 a 16 fotogramas clave')
                if clip.get('caption_easing','linear') not in ('linear','smooth'):
                    raise ValueError('Interpolación no admitida')
                previous=-1.0
                for frame in frames:
                    if not isinstance(frame,dict):raise ValueError('Fotograma clave inválido')
                    t=_num(frame.get('t'),0,(end-start)/speed,'Tiempo de fotograma')
                    if t<=previous:raise ValueError('Los fotogramas deben tener tiempos crecientes')
                    previous=t
                    _num(frame.get('x'),-4000,4000,'X de fotograma')
                    _num(frame.get('y'),-4000,4000,'Y de fotograma')
            if clip.get('sticker_asset_id'):
                st=get_asset(clip['sticker_asset_id'])
                if not st or st['kind']!='image':raise ValueError('Sticker de video inválido')
                _num(clip.get('sticker_width',100),1,1500,'Anchura de sticker')
                _num(clip.get('sticker_x',0),-4000,4000,'Posición de sticker')
                _num(clip.get('sticker_y',0),-4000,4000,'Posición de sticker')
            if end<=start or (asset['kind']=='video' and end>asset['duration']+0.05):raise ValueError('Intervalo fuera de la duración del clip')
            if (end-start)/speed>300:raise ValueError('Clip demasiado largo')
            if len(str(clip.get('caption','')))>250:raise ValueError('Texto de clip demasiado largo')
        if sum((c.get('end',(get_asset(c['asset_id'])['duration'] or 5))-c.get('start',0))/c.get('speed',1) for c in clips)>600:
            raise ValueError('Máximo 10 minutos de video exportado')
        from .sky_creative_v101 import validate_global_tracks
        validate_global_tracks(spec)
        music=spec.get('music_asset_id')
        if music and (not get_asset(music) or get_asset(music)['kind']!='audio'):
            raise ValueError('La música debe estar en la biblioteca de audio')
        _num(spec.get('music_volume',0.2),0,1,'Volumen musical')
    else:raise ValueError('Tipo de creación inválido')
    return True

def _color(value,default):
    if isinstance(value,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',value):return value
    return default

def _font(size):
    for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','C:/Windows/Fonts/arial.ttf'):
        try:return ImageFont.truetype(path,int(size))
        except OSError:pass
    return ImageFont.load_default()

def render_image(spec,format='png'):
    validate_spec('image',spec)
    w,h=int(spec.get('width',1280)),int(spec.get('height',720))
    base=Image.new('RGBA',(w,h),_color(spec.get('background'),'#111d32'))
    for layer in spec.get('layers',[]):
        kind=layer['type'];opacity=layer.get('opacity',1)
        if kind=='image':
            path,_=asset_path(layer['asset_id'])
            with Image.open(path) as im:
                tile=ImageOps.exif_transpose(im).convert('RGBA')
                if layer.get('crop'):
                    box=layer['crop']
                    if len(box)!=4:raise ValueError('Recorte inválido')
                    tile=tile.crop(tuple(map(int,box)))
                lw=int(layer.get('width',tile.width));lh=int(layer.get('height',max(1,tile.height*lw/tile.width)))
                if lw*lh>MAX_PIXEL:raise ValueError('Capa de imagen demasiado grande')
                tile=tile.resize((lw,lh),Image.Resampling.LANCZOS)
                if layer.get('flip_x'):tile=ImageOps.mirror(tile)
                if layer.get('rotate'):tile=tile.rotate(float(layer['rotate']),resample=Image.Resampling.BICUBIC,expand=True)
                if layer.get('mask_asset_id'):
                    mask_path,_=asset_path(layer['mask_asset_id'])
                    with Image.open(mask_path) as src_mask:
                        mask=(src_mask.getchannel('A') if layer.get('mask_mode')=='alpha' and 'A' in src_mask.getbands() else src_mask.convert('L'))
                        mask=mask.resize(tile.size,Image.Resampling.LANCZOS)
                        if layer.get('mask_invert'):mask=ImageOps.invert(mask)
                        if layer.get('mask_feather',0):mask=mask.filter(ImageFilter.GaussianBlur(layer['mask_feather']))
                        from PIL import ImageChops
                        tile.putalpha(ImageChops.multiply(tile.getchannel('A'),mask))
        elif kind=='rectangle':
            tile=Image.new('RGBA',(int(layer.get('width',200)),int(layer.get('height',100))),_color(layer.get('color'),'#00ceea'))
        else:
            text=str(layer.get('text',''));font=_font(int(layer.get('size',48)))
            # Texto Unicode, saltos de línea. Sin HTML ni evaluación de código.
            bbox=ImageDraw.Draw(Image.new('RGBA',(1,1))).multiline_textbbox((0,0),text,font=font,spacing=8)
            tile=Image.new('RGBA',(min(5500,max(1,bbox[2]-bbox[0]+24)),min(5500,max(1,bbox[3]-bbox[1]+24))),(0,0,0,0))
            ImageDraw.Draw(tile).multiline_text((12-bbox[0],12-bbox[1]),text,font=font,fill=_color(layer.get('color'),'#ffffff'),spacing=8)
        if opacity!=1:tile.putalpha(tile.getchannel('A').point(lambda v:int(v*opacity)))
        base.alpha_composite(tile,(int(layer.get('x',0)),int(layer.get('y',0))))
    adj=spec.get('adjustments',{})
    if adj:
        rgb=base.convert('RGB')
        for key,cls in [('brightness',ImageEnhance.Brightness),('contrast',ImageEnhance.Contrast),('saturation',ImageEnhance.Color),('sharpness',ImageEnhance.Sharpness)]:
            if key in adj:rgb=cls(rgb).enhance(adj[key])
        if adj.get('blur',0):rgb=rgb.filter(ImageFilter.GaussianBlur(adj['blur']))
        if format=='png':base=rgb.convert('RGBA');base.putalpha(Image.new('L',(w,h),255))
        else:base=rgb
    buf=io.BytesIO()
    fmt={'png':'PNG','jpg':'JPEG','webp':'WEBP'}.get(format)
    if not fmt:raise ValueError('Exportación: PNG, JPG o WEBP')
    if fmt=='JPEG':base=base.convert('RGB')
    base.save(buf,format=fmt,quality=92)
    return buf.getvalue()

def save_result(pid,data,filename,mime,version=None):
    project=get_project(pid)
    if not project:raise KeyError('Proyecto inexistente')
    folder=store_dir()/'media';folder.mkdir(parents=True,exist_ok=True)
    ext=Path(filename).suffix.lower()
    digest=hashlib.sha256(data).hexdigest();path=folder/(digest+ext)
    if not path.exists():
        with tempfile.NamedTemporaryFile(dir=folder,delete=False) as tmp:
            tmp.write(data);temp=Path(tmp.name)
        temp.replace(path)
    aid=ident('asset')
    kind='image' if mime.startswith('image/') else 'video'
    duration=_probe(path)[1] if kind=='video' else None
    with connection() as db:
        db.execute('INSERT INTO assets VALUES(?,?,?,?,?,?,?,?,?,?)',(aid,filename,kind,mime,digest,str(path),len(data),duration,now(),'exported'))
        db.execute('INSERT INTO exports VALUES(?,?,?,?,?)',(ident('exp'),pid,version or project['version'],aid,now()))
    return get_asset(aid)

def image_export(pid,format='png'):
    p=get_project(pid)
    if not p or p['kind']!='image':raise KeyError('Proyecto de imagen no encontrado')
    return save_result(pid,render_image(p['spec'],format),'SKY_'+pid+'.'+format,{'jpg':'image/jpeg','png':'image/png','webp':'image/webp'}[format])

def exports(pid):
    with connection() as db:rows=db.execute('SELECT * FROM exports WHERE project_id=? ORDER BY created_at DESC,id DESC',(pid,)).fetchall()
    return [dict(r) for r in rows]

def queue_video(pid):
    p=get_project(pid)
    if not p or p['kind']!='video':raise KeyError('Proyecto de video inexistente')
    validate_spec('video',p['spec'])
    job=ident('job')
    with connection() as db:
        db.execute('INSERT INTO jobs VALUES(?,?,?,?,?,?,?,?)',(job,pid,'queued',0,'',None,now(),now()))
        db.execute('INSERT INTO job_specs VALUES(?,?,?)',(job,p['version'],json.dumps(p['spec'],ensure_ascii=False)))
    return job_info(job)

def job_info(job):
    with connection() as db:r=db.execute('SELECT * FROM jobs WHERE id=?',(job,)).fetchone()
    return dict(r) if r else None

def list_jobs():
    with connection() as db:rows=db.execute('SELECT * FROM jobs ORDER BY created_at DESC LIMIT 100').fetchall()
    return [dict(r) for r in rows]

def cancel_job(job):
    with connection() as db:
        cur=db.execute("UPDATE jobs SET status='cancelled',updated_at=? WHERE id=? AND status='queued'",(now(),job))
    return cur.rowcount>0

def _execute(command,timeout=120):
    try:
        res=subprocess.run(command,capture_output=True,text=True,timeout=timeout)
    except subprocess.TimeoutExpired as ex:raise RuntimeError('FFmpeg superó el tiempo máximo de ejecución') from ex
    if res.returncode:raise RuntimeError('FFmpeg: '+res.stderr[-1100:])

def _caption_png(text,width):
    f=_font(max(20,int(width/26)))
    h=max(90,int(width/7))
    pic=Image.new('RGBA',(width,h),(0,0,0,0));draw=ImageDraw.Draw(pic)
    draw.rounded_rectangle((15,14,width-15,h-10),radius=18,fill=(3,13,25,190))
    # varias líneas en panel inferior
    words=text.split();lines=[];current=''
    for word in words:
        trial=(current+' '+word).strip()
        if draw.textbbox((0,0),trial,font=f)[2]>width-90 and current:
            lines.append(current);current=word
        else:current=trial
    lines.append(current)
    for i,line in enumerate(lines[:3]):draw.text((width/2,22+i*int(width/23)),line,font=f,fill='white',anchor='ma')
    return pic

def render_video(spec,output:Path,progress=lambda value:None):
    validate_spec('video',spec)
    ff=_ffbin('ffmpeg');w,h=int(spec.get('width',640)),int(spec.get('height',360));fps=int(_num(spec.get('fps',25),15,60,'FPS'))
    output.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='sky_video_',dir=store_dir()) as temp:
        folder=Path(temp);parts=[]
        for index,clip in enumerate(spec['clips']):
            source,asset=asset_path(clip['asset_id']);start=float(clip.get('start',0));end=float(clip.get('end',asset['duration']))
            speed=float(clip.get('speed',1));effective=(end-start)/speed
            segment=folder/f'part{index:02d}.mp4';parts.append(segment)
            base=f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2,setsar=1,fps={fps},setpts=(PTS-STARTPTS)/{speed}'
            if asset['kind']=='image':
                command=[ff,'-hide_banner','-loglevel','error','-y','-loop','1','-framerate',str(fps),'-t',str(end-start),'-i',str(source)]
            else:
                command=[ff,'-hide_banner','-loglevel','error','-y','-ss',str(start),'-t',str(end-start),'-i',str(source)]
            caption=str(clip.get('caption','')).strip()
            # Inputs: 0=video, 1=caption if set, next=sticker if set, last=silence if needed.
            current_input=1
            caption_index=None
            if caption:
                pic=folder/f'caption{index}.png';_caption_png(caption,w).save(pic)
                caption_index=current_input;current_input+=1
                command+=['-loop','1','-framerate',str(fps),'-i',str(pic)]
            sticker_index=None
            if clip.get('sticker_asset_id'):
                sticker,_=asset_path(clip['sticker_asset_id']);sticker_index=current_input;current_input+=1
                command+=['-loop','1','-framerate',str(fps),'-i',str(sticker)]
            overlays=clip.get('overlays',[])
            overlay_inputs=[]
            for overlay_n,entry in enumerate(overlays):
                overlay_inputs.append(current_input);current_input+=1
                if entry.get('mask_keyframes'):
                    from .sky_creative_v101 import create_mask_frames
                    pattern,_=create_mask_frames(entry,effective,fps,folder,f'clip_{index}_mask_{overlay_n}')
                    command+=['-framerate',str(fps),'-start_number','0','-i',pattern]
                else:
                    pic,_=asset_path(entry['asset_id'])
                    command+=['-loop','1','-framerate',str(fps),'-i',str(pic)]
            streams,_=_probe(source) if asset['kind']=='video' else (set(),0)
            silence=not ('audio' in streams and not clip.get('mute',False))
            if silence:
                silence_index=current_input
                command+=['-f','lavfi','-t',str(effective),'-i','anullsrc=channel_layout=stereo:sample_rate=48000']
            filters=[f'[0:v]{base}[v0]'];prior='v0';stage=0
            if caption_index is not None:
                motion=clip.get('caption_motion') or {}
                # Position is linearly interpolated between explicit first and last keyframes.
                # x/y expressions are FFmpeg evaluated against presentation timestamp t.
                def coordinate(name,default):
                    a=float(motion.get(name+'0',default));b=float(motion.get(name+'1',a))
                    return f'({a:.3f}+({b-a:.3f})*min(1,max(0,t/{effective:.3f})))'
                # SKY v9.9: secuencia de hasta 16 keyframes, con interpolación
                # acotada y valores numéricos validados previamente.
                frames=clip.get('caption_keyframes')
                if frames:
                    easing=clip.get('caption_easing','linear')
                    def path_coordinate(axis):
                        expression=f'{float(frames[-1][axis]):.4f}'
                        for a,b in reversed(list(zip(frames,frames[1:]))):
                            t0=float(a['t']);t1=float(b['t'])
                            fraction=f'min(1,max(0,(t-{t0:.4f})/{t1-t0:.4f}))'
                            factor=f'({fraction}*{fraction}*(3-2*{fraction}))' if easing=='smooth' else fraction
                            v0=float(a[axis]);delta=float(b[axis])-v0
                            segment=f'({v0:.4f}+({delta:.4f})*{factor})'
                            expression=f'if(lt(t,{t1:.4f}),{segment},{expression})'
                        return f'if(lt(t,{float(frames[0]["t"]):.4f}),{float(frames[0][axis]):.4f},{expression})'
                    x=path_coordinate('x');y=path_coordinate('y')
                else:
                    x=coordinate('x',0);y=coordinate('y',h-_caption_png(caption,w).height-12)
                fin=float(motion.get('fade_in',0));fout=float(motion.get('fade_out',0))
                effects=['format=rgba']
                if fin>0:effects.append(f'fade=t=in:st=0:d={fin:.3f}:alpha=1')
                if fout>0:effects.append(f'fade=t=out:st={max(0,effective-fout):.3f}:d={fout:.3f}:alpha=1')
                filters.append(f'[{caption_index}:v]{",".join(effects)}[caption]')
                filters.append(f"[{prior}][caption]overlay=x='{x}':y='{y}':shortest=1[v1]")
                prior='v1';stage=1
            if sticker_index is not None:
                size=int(clip.get('sticker_width',100));x=float(clip.get('sticker_x',0));y=float(clip.get('sticker_y',0))
                filters.append(f'[{sticker_index}:v]scale={size}:-1,format=rgba[sticker]')
                filters.append(f'[{prior}][sticker]overlay=x={x:.2f}:y={y:.2f}:shortest=1[v{stage+1}]')
                prior=f'v{stage+1}'
            if overlay_inputs:
                from .sky_creative_v10 import build_overlay_filters
                prior,new_filters=build_overlay_filters(overlays,overlay_inputs,prior,stage+2,effective)
                filters.extend(new_filters)
            if caption_index is not None or sticker_index is not None or overlay_inputs:
                command+=['-filter_complex',';'.join(filters),'-map',f'[{prior}]']
            else:command+=['-vf',base,'-map','0:v:0']
            if silence:command+=['-map',f'{silence_index}:a:0']
            else:command+=['-map','0:a:0','-af',f'atempo={speed},aresample=48000']
            command+=['-t',str(effective),'-r',str(fps),'-c:v','libx264','-preset','veryfast','-crf','24',
                      '-pix_fmt','yuv420p','-c:a','aac','-ar','48000','-ac','2','-movflags','+faststart',str(segment)]
            _execute(command,timeout=150)
            progress(int(5+(index+1)/len(spec['clips'])*75))
        playlist=folder/'concat.txt';playlist.write_text(''.join("file '"+str(p).replace("'","'\\''")+"'\n" for p in parts),encoding='utf-8')
        joined=folder/'joined.mp4'
        _execute([ff,'-hide_banner','-loglevel','error','-y','-f','concat','-safe','0','-i',str(playlist),
                '-c','copy','-movflags','+faststart',str(joined)],timeout=120)
        from .sky_creative_v101 import apply_global_tracks
        joined=apply_global_tracks(spec,joined,folder,ff,fps)
        progress(88)
        if spec.get('music_asset_id'):
            music,_=asset_path(spec['music_asset_id']);vol=float(spec.get('music_volume',0.2))
            _execute([ff,'-hide_banner','-loglevel','error','-y','-i',str(joined),'-stream_loop','-1','-i',str(music),
                    '-filter_complex',f'[0:a]volume=1[a];[1:a]volume={vol}[b];[a][b]amix=inputs=2:duration=first:dropout_transition=0[m]',
                    '-map','0:v:0','-map','[m]','-c:v','copy','-c:a','aac','-b:a','160k','-shortest','-movflags','+faststart',str(output)],timeout=140)
        else:shutil.copyfile(joined,output)
        progress(99)
    return output

def run_next_job():
    """Reclama y ejecuta un render. Las tareas interrumpidas NO se repiten silenciosamente."""
    with connection() as db:
        row=db.execute("SELECT * FROM jobs WHERE status='queued' ORDER BY created_at,id LIMIT 1").fetchone()
        if not row:return None
        id=row['id'];db.execute("UPDATE jobs SET status='running',progress=1,updated_at=? WHERE id=? AND status='queued'",(now(),id))
    folder=store_dir()/'tmp';folder.mkdir(parents=True,exist_ok=True);out=folder/(id+'.mp4')
    def progress(v):
        with connection() as db:db.execute("UPDATE jobs SET progress=?,updated_at=? WHERE id=? AND status='running'",(v,now(),id))
    try:
        project=get_project(row['project_id'])
        if not project:raise KeyError('Proyecto inexistente')
        with connection() as db:spec_row=db.execute('SELECT project_version,spec FROM job_specs WHERE job_id=?',(id,)).fetchone()
        if not spec_row:raise RuntimeError('El render no tiene una instantánea aprobada y debe revisarse')
        frozen_spec=json.loads(spec_row['spec'])
        render_video(frozen_spec,out,progress)
        asset=save_result(project['id'],out.read_bytes(),'SKY_'+id+'.mp4','video/mp4',version=spec_row['project_version'])
        with connection() as db:db.execute("UPDATE jobs SET status='completed',progress=100,asset_id=?,updated_at=? WHERE id=?",(asset['id'],now(),id))
    except Exception as ex:
        with connection() as db:db.execute("UPDATE jobs SET status='failed',error=?,updated_at=? WHERE id=?",(str(ex)[:1200],now(),id))
    finally:out.unlink(missing_ok=True)
    return job_info(id)

def mark_interrupted():
    with connection() as db:
        db.execute("UPDATE jobs SET status='needs_review',error='Render interrumpido; revisá antes de reintentar',updated_at=? WHERE status='running'",(now(),))

def retry_job(job_id):
    with connection() as db:
        cur=db.execute("UPDATE jobs SET status='queued',progress=0,error='',asset_id=NULL,updated_at=? WHERE id=? AND status IN ('failed','needs_review')",(now(),job_id))
    if cur.rowcount!=1:raise RuntimeError('El trabajo no puede reintentarse en este estado')
    return job_info(job_id)

def interpret_edit(kind,spec,instruction):
    """Órdenes locales explícitas, auditable. No inventa edición asistida por IA."""
    import copy,unicodedata
    original=instruction.strip()
    if not 3<=len(original)<=700:raise ValueError('Escribí una instrucción de edición de 3 a 700 caracteres')
    cmd=''.join(c for c in unicodedata.normalize('NFD',original.lower()) if unicodedata.category(c)!='Mn')
    result=copy.deepcopy(spec)
    if kind=='image':
        m=re.search(r'(?:agrega|anade|pon|coloca|escribe)\s+(?:un\s+)?(?:texto|titulo|frase)\s*[:\-]?\s*["“]?(.+)',original,re.I)
        if m:
            value=m.group(1).strip(' "”\'')
            if len(value)>3000:raise ValueError('Texto demasiado largo')
            result.setdefault('layers',[]).append({'type':'text','text':value,'x':45,'y':55,'size':58,'color':'#ffffff','opacity':1})
        elif (m:=re.search(r'\b(brillo|contraste|saturacion|desenfoque)\s+(?:a\s+|en\s+)?(\d+(?:[\.,]\d+)?)',cmd)):
            key={'brillo':'brightness','contraste':'contrast','saturacion':'saturation','desenfoque':'blur'}[m.group(1)]
            result.setdefault('adjustments',{})[key]=float(m.group(2).replace(',','.'))
        elif (m:=re.search(r'(?:fondo|color de fondo)\s*(?:a\s+)?(#[0-9a-f]{6})',cmd)):
            result['background']=m.group(1)
        elif (m:=re.search(r'(?:gira|rota)\s+(?:la\s+)?(?:ultima\s+)?capa\s+(\d{1,3})\s*(?:grados)?',cmd)):
            if not result.get('layers'):raise ValueError('Añadí una capa antes de rotarla')
            layer=result['layers'][-1]
            if layer['type']!='image':raise ValueError('La rotación precisa necesita una capa de imagen')
            layer['rotate']=(float(layer.get('rotate',0))+int(m.group(1)))%360
        else:raise ValueError('Orden no reconocida. Ejemplos: Agregá texto Bienvenidos, brillo 1.3, contraste 1.2, fondo #112233')
    elif kind=='video':
        move=re.search(r'(?:mueve|ubica|coloca)\s+(?:la\s+)?(?:capa|superposicion)\s+(\d+)\s+(?:del\s+)?clip\s+(\d+)\s+a\s+x\s+(-?\d+)\s+y\s+(-?\d+)',cmd)
        opacity=re.search(r'opacidad\s+(?:de\s+)?(?:la\s+)?(?:capa|superposicion)\s+(\d+)\s+(?:del\s+)?clip\s+(\d+)\s+a\s+(\d+(?:[\.,]\d+)?)',cmd)
        if move or opacity:
            match=move or opacity;layer_number=int(match.group(1))-1;clip_number=int(match.group(2))-1
            if not 0<=clip_number<len(result['clips']):raise ValueError('Clip inexistente')
            layers=result['clips'][clip_number].get('overlays',[])
            if not 0<=layer_number<len(layers):raise ValueError('Capa de video inexistente')
            if move:layers[layer_number].update({'x':int(match.group(3)),'y':int(match.group(4)),'keyframes':[]})
            else:layers[layer_number]['opacity']=float(match.group(3).replace(',','.'))
        else:
            m=re.search(r'(?:pon|cambia|agrega)\s+(?:el\s+)?texto\s+(.+?)\s+en\s+(?:el\s+)?clip\s+(\d+)',original,re.I)
            if m:
                index=int(m.group(2))-1
                if not 0<=index<len(result['clips']):raise ValueError('No existe ese clip')
                result['clips'][index]['caption']=m.group(1).strip(' "”\'')
            elif (m:=re.search(r'(?:velocidad|rapidez)\s+(?:del\s+)?clip\s+(\d+)\s+(?:a\s+)?(\d+(?:[\.,]\d+)?)',cmd)):
                i=int(m.group(1))-1
                if not 0<=i<len(result['clips']):raise ValueError('No existe ese clip')
                result['clips'][i]['speed']=float(m.group(2).replace(',','.'))
            elif (m:=re.search(r'(?:volumen|musica)\s+(?:a\s+)?(\d+(?:[\.,]\d+)?)',cmd)):
                result['music_volume']=float(m.group(1).replace(',','.'))
            else:raise ValueError('Orden no reconocida. Ejemplos: Pon texto Bienvenidos en clip 1, velocidad clip 2 a 1.5')
    validate_spec(kind,result)
    return result

def apply_instruction(pid,instruction,expected_version):
    p=get_project(pid)
    if not p:raise KeyError('Proyecto no encontrado')
    if expected_version!=p['version']:raise RuntimeError('La versión cambió; recargá antes de aplicar la orden')
    updated=interpret_edit(p['kind'],p['spec'],instruction)
    return update_project(pid,updated,expected_version)

def export_portable(pid):
    """ZIP portable con receta + medios usados. Sin claves, notas ni sesiones privadas."""
    import zipfile
    project=get_project(pid)
    if not project:raise KeyError('Proyecto inexistente')
    spec=project['spec'];refs=[]
    if project['kind']=='image':refs=[id for x in spec.get('layers',[]) if x['type']=='image' for id in (x.get('asset_id'),x.get('mask_asset_id')) if id]
    else:refs=[aid for x in spec.get('clips',[]) for aid in ([x.get('asset_id'),x.get('sticker_asset_id')]+[layer.get('asset_id') for layer in x.get('overlays',[])]) if aid]+([spec['music_asset_id']] if spec.get('music_asset_id') else [])
    items=[];total=0;raw=io.BytesIO()
    with zipfile.ZipFile(raw,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for aid in dict.fromkeys(refs):
            path,asset=asset_path(aid);total+=asset['size']
            if total>120*1024*1024:raise ValueError('Proyecto portable supera 120 MB; exportá los videos por separado')
            member='assets/'+aid+path.suffix
            z.write(path,member)
            items.append({'id':aid,'member':member,'name':asset['filename'],'sha256':asset['sha256']})
        z.writestr('SKY_Creative_Project.json',json.dumps({'schema':'SKY-creative-v1','kind':project['kind'],
          'name':project['name'],'spec':spec,'assets':items},ensure_ascii=False,indent=2))
    return raw.getvalue(),re.sub(r'[^A-Za-z0-9_-]','_',project['name'])[:70]+'.skyzip'

def import_portable(data:bytes,sky_project_id=None):
    import zipfile
    if len(data)>120*1024*1024 or len(data)<100:raise ValueError('Archivo portable vacío o demasiado grande')
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            if len(z.infolist())>80:raise ValueError('El proyecto contiene demasiados archivos')
            for info in z.infolist():
                if info.file_size>80*1024*1024:raise ValueError('Archivo demasiado grande en el paquete')
            if sum(x.file_size for x in z.infolist())>120*1024*1024:
                raise ValueError('Paquete expandido demasiado grande')
            manifest=json.loads(z.read('SKY_Creative_Project.json'))
            if manifest.get('schema')!='SKY-creative-v1':raise ValueError('Versión de paquete no compatible')
            spec=manifest['spec'];ids={}
            for entry in manifest.get('assets',[]):
                member=entry['member']
                if not re.fullmatch(r'assets/asset_[0-9a-f]{20}\.(?:png|jpg|webp|mp4|mov|webm|mkv|mp3|wav|m4a|ogg|flac|aac)',member):
                    raise ValueError('Ruta de archivo insegura en el paquete')
                payload=z.read(member)
                if hashlib.sha256(payload).hexdigest()!=entry['sha256']:raise ValueError('Huella SHA-256 incorrecta')
                ids[entry['id']]=ingest(payload,entry['name'])['id']
    except (zipfile.BadZipFile,KeyError,UnicodeDecodeError,json.JSONDecodeError) as ex:
        raise ValueError('Archivo SKY portable no válido') from ex
    if manifest['kind']=='image':
        for layer in spec.get('layers',[]):
            if layer['type']=='image':
                layer['asset_id']=ids[layer['asset_id']]
                if layer.get('mask_asset_id'):layer['mask_asset_id']=ids[layer['mask_asset_id']]
    else:
        for clip in spec.get('clips',[]):
            clip['asset_id']=ids[clip['asset_id']]
            if clip.get('sticker_asset_id'):clip['sticker_asset_id']=ids[clip['sticker_asset_id']]
            for layer in clip.get('overlays',[]):layer['asset_id']=ids[layer['asset_id']]
        if spec.get('music_asset_id'):spec['music_asset_id']=ids[spec['music_asset_id']]
    return create_project(manifest['kind'],manifest['name'],spec,sky_project_id)
