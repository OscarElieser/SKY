(()=>{'use strict';
const $=id=>document.getElementById(id);let token='',assets=[],selected=null,project=null,view='image',previewUrl='';
function toast(m){$('toast').textContent=m;$('toast').style.display='block';setTimeout(()=>$('toast').style.display='none',5000)}
function err(e){toast(e?.message||String(e))}
async function api(path,method='GET',body,form=false){const opts={method,headers:{'X-SKY-KEY':token,...window.SKYOwnerAuth.headers()}};if(body){if(form)opts.body=body;else{opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(body)}}const r=await fetch(path,opts);if(!r.ok){let msg=await r.text();try{msg=JSON.parse(msg).detail||msg}catch{}throw Error(msg)}return r.json()}
async function binary(path,name,display=false){const r=await fetch(path,{headers:{'X-SKY-KEY':token,...window.SKYOwnerAuth.headers()}});if(!r.ok)throw Error('No se pudo obtener el archivo');const b=await r.blob();const url=URL.createObjectURL(b);if(display){if(previewUrl)URL.revokeObjectURL(previewUrl);previewUrl=url;const elt=b.type.startsWith('video/')?$('video-preview'):$('image-preview');$('video-preview').hidden=true;$('image-preview').hidden=true;elt.src=url;elt.hidden=false;$('empty-preview').hidden=true}else{let a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000)}}
function button(label,callback){const b=document.createElement('button');b.textContent=label;b.type='button';b.onclick=()=>Promise.resolve(callback()).catch(err);return b}
function text(el,s){el.textContent=s}
async function refresh(){assets=await api('/api/creative/assets');const list=$('assets');list.replaceChildren();assets.forEach(a=>{const el=document.createElement('div');el.className='asset'+(a.id===selected?' selected':'');const name=document.createElement('div');const title=document.createElement('strong');text(title,a.filename);const kind=document.createElement('small');text(kind,a.kind+(a.duration?' · '+a.duration.toFixed(1)+' s':''));name.append(title,kind);el.append(name,button('Vista',()=>binary('/api/creative/assets/'+a.id+'/preview',a.filename,true)));el.addEventListener('click',()=>{selected=a.id;refresh().catch(err)});list.append(el)});const ps=$('projects');ps.replaceChildren();(await api('/api/creative/projects')).forEach(p=>ps.append(button(p.name+' · v'+p.version,()=>openProject(p.id))))}
function emptyImage(){return {width:1280,height:720,background:'#121e32',layers:[],adjustments:{brightness:1,contrast:1,saturation:1}}}
async function create(kind){const name=$('project-name').value.trim()||'Proyecto SKY';const videos=assets.filter(a=>['video','image'].includes(a.kind));let spec=kind==='image'?emptyImage():{width:640,height:360,fps:25,clips:videos.length?[{asset_id:videos[0].id,start:0,end:Math.min(videos[0].duration||5,8),speed:1,caption:''}]:[]};if(kind==='video'&&!spec.clips.length){toast('Primero importá un video para la línea de tiempo');return}const obj=await api('/api/creative/projects','POST',{kind,name,spec,sky_project_id:window.skyActiveProject||null});await openProject(obj.id);await refresh()}
async function openProject(id){project=await api('/api/creative/projects/'+id);view=project.kind;$('project-name').value=project.name;$('save').disabled=false;$('export-bundle').disabled=false;$('mode-image').classList.toggle('active',view==='image');$('mode-video').classList.toggle('active',view==='video');$('image-editor').hidden=view!=='image';$('video-editor').hidden=view!=='video';text($('project-state'),'Guardado · versión '+project.version);redraw();await updateExports();await updateVersions();await updateJobs()}
function redraw(){if(!project)return;if(project.kind==='image'){const ls=$('layers');ls.replaceChildren();project.spec.layers.forEach((layer,i)=>{const li=document.createElement('li');const label=document.createElement('span');text(label,(i+1)+'. '+layer.type+(layer.type==='text'?' · '+(layer.text||'').slice(0,35):''));li.append(label);[['X','x',-10000,10000],['Y','y',-10000,10000],['Opacidad','opacity',0,1]].forEach(([name,key,min,max])=>{const inp=document.createElement('input');inp.type='number';inp.step=key==='opacity'?'0.1':'1';inp.min=min;inp.max=max;inp.value=layer[key]??(key==='opacity'?1:0);inp.style.width='75px';inp.title=name;inp.setAttribute('aria-label',name+' de la capa');inp.onchange=()=>{layer[key]=Number(inp.value)};li.append(inp)});li.append(button('Eliminar',()=>{project.spec.layers.splice(i,1);redraw()}));ls.append(li)});let ad=project.spec.adjustments||{};['brightness','contrast','saturation'].forEach(n=>$(n).value=ad[n]??1)}else{const area=$('clips');area.replaceChildren();project.spec.clips.forEach((clip,i)=>{const wrap=document.createElement('div');let asset=assets.find(x=>x.id===clip.asset_id);const heading=document.createElement('strong');text(heading,(i+1)+'. '+(asset?.filename||'Clip'));wrap.append(heading);[['Inicio','start',0,1800],['Fin','end',0,1800],['Velocidad','speed',.5,2],['Texto','caption',null,null]].forEach(([title,key,lo,hi])=>{let label=document.createElement('label');text(label,title);const input=document.createElement('input');input.type=key==='caption'?'text':'number';if(lo!==null){input.min=String(lo);input.max=String(hi);input.step='.1'}input.value=clip[key]??'';input.onchange=()=>{clip[key]=key==='caption'?input.value:Number(input.value)};label.append(input);wrap.append(label)});wrap.append(button('Quitar',()=>{project.spec.clips.splice(i,1);redraw()}));area.append(wrap)})}}
async function save(){if(!project)return;project=await api('/api/creative/projects/'+project.id,'PUT',{spec:project.spec,expected_version:project.version});text($('project-state'),'Guardado · versión '+project.version);toast('Proyecto editable guardado sin sobrescribir versiones exportadas')}
async function renderImage(){await save();let a=await api('/api/creative/projects/'+project.id+'/image/render','POST');await binary('/api/creative/assets/'+a.id+'/preview',a.filename,true);await refresh();await updateExports();toast('Imagen exportada y guardada en tu biblioteca')}
async function renderVideo(){await save();const job=await api('/api/creative/projects/'+project.id+'/video/render','POST');await updateJobs();toast('Render en cola: '+job.id)}
async function updateVersions(){if(!project)return;const area=$('version-history');area.replaceChildren();(await api('/api/creative/projects/'+project.id+'/versions')).forEach(v=>{const d=document.createElement('div');d.className='version-item';text(d,'Versión '+v.version+' · '+v.saved_at+' ');d.append(button('Cargar al editor',()=>{if(!window.confirm('¿Reemplazar los cambios no guardados por esta revisión?'))return;project.spec=JSON.parse(v.spec);redraw();toast('Revisión cargada. Guardá para crear una nueva versión.')}));area.append(d)})}
async function updateExports(){if(!project)return;const out=$('exports');out.replaceChildren();(await api('/api/creative/projects/'+project.id+'/exports')).forEach(async v=>{let el=document.createElement('div');text(el,'Exportación de la versión '+v.version+' · '+v.created_at+' ');el.append(button('Descargar',async()=>{const a=assets.find(x=>x.id===v.asset_id)||await api('/api/creative/assets').then(x=>x.find(a=>a.id===v.asset_id));await binary('/api/creative/assets/'+v.asset_id+'/download',a?.filename||'SKY_media',false)}));out.append(el)})}
async function updateJobs(){const jobs=await api('/api/creative/jobs');const out=$('jobs');out.replaceChildren();jobs.slice(0,15).forEach(j=>{const d=document.createElement('div');text(d,j.status+' · '+j.progress+'%'+(j.error?' · '+j.error:''));if(j.status==='completed')d.append(button('Descargar MP4',async()=>{const a=assets.find(x=>x.id===j.asset_id);await binary('/api/creative/assets/'+j.asset_id+'/download',a?.filename||'SKY_video.mp4')}));if(['failed','needs_review'].includes(j.status))d.append(button('Reintentar',async()=>{await api('/api/creative/jobs/'+j.id+'/retry','POST');await updateJobs()}));if(j.status==='queued')d.append(button('Cancelar',async()=>{await api('/api/creative/jobs/'+j.id+'/cancel','POST');await updateJobs()}));out.append(d)})}
$('connect').onclick=async()=>{try{token=$('key').value;await window.SKYOwnerAuth.begin(token);await api('/api/creative/capabilities');$('login').hidden=true;$('key').value='';await refresh();setInterval(()=>{if(token)updateJobs().catch(()=>{})},5500)}catch(e){text($('auth-error'),e.message)}};
$('generate-ai').onclick=async()=>{try{if(!token)throw Error('Ingresá primero con la clave de SKY');const prompt=$('ai-prompt').value.trim();if(prompt.length<4)throw Error('Describí la imagen que querés crear');$('generate-ai').disabled=true;const a=await api('/api/creative/generate-image','POST',{prompt,provider:'gemini'});selected=a.id;await refresh();await binary('/api/creative/assets/'+a.id+'/preview',a.filename,true);toast('Imagen generada e incorporada a tu biblioteca')}catch(ex){err(ex)}finally{$('generate-ai').disabled=false}};

$('apply-keyframes').onclick=()=>{try{if(!project||project.kind!=='video')throw Error('Abrí un proyecto de video');
 const i=Number($('kf-clip').value)-1,clip=project.spec.clips[i];if(!clip)throw Error('Número de clip inválido');
 const frames=JSON.parse($('kf-json').value);if(!Array.isArray(frames)||frames.length<2||frames.length>16)throw Error('Usá entre 2 y 16 fotogramas');
 clip.caption_keyframes=frames;clip.caption_easing=$('kf-ease').value;toast('Fotogramas aplicados; guardá para crear una nueva versión.');}
 catch(e){err(e)}};
$('upload').onchange=async e=>{if(!token){toast('Ingresá primero con la clave privada');return}for(const file of e.target.files){try{let f=new FormData();f.append('file',file);await api('/api/creative/assets','POST',f,true)}catch(ex){toast(file.name+': '+ex.message)}}e.target.value='';refresh().catch(err)};
$('apply-command').onclick=async()=>{try{if(!project)throw Error('Primero creá o abrí un proyecto');const updated=await api('/api/creative/projects/'+project.id+'/command','POST',{instruction:$('instruction').value,expected_version:project.version});project=updated;redraw();await updateVersions();text($('project-state'),'Guardado · versión '+updated.version);toast('SKY aplicó tu instrucción y conservó las versiones anteriores')}catch(e){err(e)}};
$('export-bundle').onclick=()=>{if(project)binary('/api/creative/projects/'+project.id+'/portable',project.name.replace(/[^a-zA-Z0-9_-]+/g,'_')+'.skyzip',false).catch(err)};
$('bundle-upload').onchange=async e=>{if(!token)return toast('Accedé con la clave del creador');const file=e.target.files?.[0];if(!file)return;try{const data=new FormData();data.append('file',file);const p=await api('/api/creative/portable','POST',data,true);await refresh();await openProject(p.id);toast('Proyecto portable recuperado con su biblioteca')}catch(ex){err(ex)}finally{e.target.value=''}};
$('new-image').onclick=()=>create('image').catch(err);$('new-video').onclick=()=>create('video').catch(err);$('save').onclick=()=>save().catch(err);
$('mode-image').onclick=()=>{if(project?.kind!=='image')toast('Creá un proyecto de imagen para usar esta herramienta')};$('mode-video').onclick=()=>{if(project?.kind!=='video')toast('Creá un proyecto de video para usar esta herramienta')};
$('add-text').onclick=()=>{if(project?.kind!=='image')return;project.spec.layers.push({type:'text',text:$('layer-text').value||'Título SKY',color:$('layer-color').value,size:Number($('layer-size').value),x:55,y:60,opacity:1});redraw()};
$('add-image').onclick=()=>{if(project?.kind!=='image')return;let a=assets.find(x=>x.id===selected);if(!a||a.kind!=='image')return toast('Seleccioná una imagen de la biblioteca');project.spec.layers.push({type:'image',asset_id:a.id,x:100,y:90,width:700,opacity:1});redraw()};
$('apply-image').onclick=()=>{if(project?.kind!=='image')return;project.spec.adjustments={brightness:Number($('brightness').value),contrast:Number($('contrast').value),saturation:Number($('saturation').value)};toast('Ajustes preparados. Exportá para ver la imagen final.')};
$('render-image').onclick=()=>renderImage().catch(err);$('render-video').onclick=()=>renderVideo().catch(err);
$('add-clip').onclick=()=>{if(project?.kind!=='video')return;const a=assets.find(x=>x.id===selected);if(!a||!['image','video'].includes(a.kind))return toast('Seleccioná una imagen o video de la biblioteca');project.spec.clips.push({asset_id:a.id,start:0,end:Math.min(a.duration||5,10),speed:1,caption:''});redraw()};
let lastMask='';
$('make-mask').onclick=async()=>{try{
 const asset=assets.find(a=>a.id===selected);if(!asset||asset.kind!=='image')throw Error('Seleccioná una imagen de la biblioteca');
 const rectangle=['mask-x','mask-y','mask-w','mask-h'].map(id=>Number($(id).value));
 const foreground=JSON.parse($('guide-foreground').value||'[]');const background=JSON.parse($('guide-background').value||'[]');
 const brush_radius=Number($('guide-radius').value);
 const output=await api('/api/creative/assets/'+asset.id+'/selection','POST',{rectangle,iterations:4,foreground,background,brush_radius});
 lastMask=output.mask_asset.id;text($('mask-result'),'Máscara guardada: '+lastMask);
 await refresh();toast('Máscara GrabCut creada y guardada sin cambiar la imagen original');
 }catch(ex){err(ex)}};
$('apply-mask').onclick=()=>{if(!project||project.kind!=='image'||!lastMask)return toast('Creá una máscara y abrí un proyecto de imagen');
 const layer=[...project.spec.layers].reverse().find(x=>x.type==='image');if(!layer)return toast('Agregá una capa de imagen');
 layer.mask_asset_id=lastMask;layer.mask_mode='luminance';layer.mask_feather=1;redraw();toast('Máscara aplicada; guardá para crear una nueva versión.');};
$('motion-apply').onclick=()=>{if(!project||project.kind!=='video')return toast('Abrí un proyecto de video');
 const i=Number($('motion-clip').value)-1;if(!Number.isInteger(i)||i<0||i>=project.spec.clips.length)return toast('Clip inexistente');
 project.spec.clips[i].caption_motion={x0:Number($('motion-x0').value),x1:Number($('motion-x1').value),
 y0:Number($('motion-y0').value),y1:Number($('motion-y1').value),fade_in:Number($('motion-in').value),fade_out:Number($('motion-out').value)};
 redraw();toast('Movimiento preparado: guardá y renderizá para verificarlo.')};
$('set-music').onclick=()=>{if(project?.kind!=='video')return;const a=assets.find(x=>x.id===selected);if(!a||a.kind!=='audio')return toast('Seleccioná un archivo de audio');project.spec.music_asset_id=a.id;project.spec.music_volume=.2;toast('Música añadida. Guardá y renderizá.')};

// SKY v10 — Las opciones avanzadas quedan plegadas; no alteran la portada principal.
$('v10-add-layer').onclick=()=>{try{if(!project||project.kind!=='video')throw Error('Abrí un proyecto de video');const n=Number($('v10-clip').value)-1;if(!project.spec.clips[n])throw Error('Clip no válido');const asset=assets.find(x=>x.id===$('v10-layer').value.trim())||assets.find(x=>x.id===selected&&x.kind==='image');if(!asset||asset.kind!=='image')throw Error('Seleccioná un recurso de imagen de la biblioteca');const clip=project.spec.clips[n];clip.overlays=clip.overlays||[];clip.overlays.push({asset_id:asset.id,width:Number($('v10-w').value),opacity:Number($('v10-opacity').value),x:Number($('v10-x').value),y:Number($('v10-y').value)});toast('Capa agregada. Guardá para crear una nueva versión.')}catch(e){err(e)}};
$('v10-track').onclick=async()=>{try{if(!project||project.kind!=='video')throw Error('Abrí un proyecto de video');const n=Number($('v10-clip').value)-1;const clip=project.spec.clips[n];if(!clip)throw Error('Clip no válido');if(!clip.overlays?.length)throw Error('Primero agregá una capa de imagen');const video=assets.find(x=>x.id===clip.asset_id);if(!video||video.kind!=='video')throw Error('El clip debe ser un video real');const duration=Number($('v10-duration').value);const data=await api('/api/creative/assets/'+video.id+'/track','POST',{rectangle:[Number($('v10-x').value),Number($('v10-y').value),Number($('v10-w').value),Number($('v10-h').value)],start:Number(clip.start||0),end:Number(clip.start||0)+duration,step:.3,width:project.spec.width,height:project.spec.height,speed:Number(clip.speed||1)});clip.overlays.at(-1).keyframes=data.keyframes;toast('Trayectoria obtenida: '+data.samples+' fotogramas; '+data.lost_samples+' con baja confianza. Revisá antes de renderizar.')}catch(e){err(e)}};
$('v10-preview').onclick=async()=>{try{if(!project||project.kind!=='video')throw Error('Abrí un proyecto de video');const t=Number($('v10-time').value);await binary('/api/creative/projects/'+project.id+'/video/frame?t='+encodeURIComponent(t),'fotograma.png',true)}catch(e){err(e)}};

$('v10-gemini-check').onclick=async()=>{try{const r=await api('/api/creative/gemini/check','POST');toast('Gemini respondió: '+r.response)}catch(e){err(e)}};

// SKY v10.1: pistas gráficas sobre todo el montaje, con máscaras animadas.
$('v101-add-track').onclick=()=>{try{
 if(!project||project.kind!=='video')throw Error('Abrí un proyecto de video');
 const aid=$('v101-track-asset').value.trim()||selected;
 if(!assets.some(a=>a.id===aid&&a.kind==='image'))throw Error('Elegí una imagen de la biblioteca');
 const duration=project.spec.clips.reduce((total,c)=>total+(Number(c.end)-Number(c.start))/Number(c.speed||1),0);
 const from=Number($('v101-track-from').value),to=Number($('v101-track-to').value);
 if(!Number.isFinite(from)||!Number.isFinite(to)||from<0||to<=from||to>duration)throw Error('Intervalo de pista fuera del montaje');
 project.spec.tracks=project.spec.tracks||[];
 if(project.spec.tracks.length>=8)throw Error('Límite: ocho pistas globales');
 project.spec.tracks.push({asset_id:aid,width:Number($('v101-track-width').value),opacity:1,x:0,y:0,from,to});
 text($('v101-track-summary'),'Pistas preparadas: '+project.spec.tracks.length+' (guardá la edición)');
 toast('Pista global añadida; guardá y renderizá');
 }catch(e){err(e)}};
$('v101-set-masks').onclick=()=>{try{
 if(!project||project.kind!=='video'||!project.spec.tracks?.length)throw Error('Primero agregá una pista global');
 const frames=JSON.parse($('v101-masks').value);
 if(!Array.isArray(frames)||!frames.length||frames.length>8)throw Error('Máscaras: 1 a 8 fotogramas');
 project.spec.tracks.at(-1).mask_keyframes=frames;
 toast('Máscaras animadas preparadas; guardá y renderizá para validarlas');
 }catch(e){err(e)}};


// SKY v10.2: subtitles (SRT/VTT/MP4) and opt-in multilingual narration.
async function skyV102Media(endpoint,payload,filename){
 if(!token)throw Error('Ingresá con la clave privada del creador');
 const response=await fetch(endpoint,{method:'POST',headers:{'X-SKY-KEY':token,...window.SKYOwnerAuth.headers(),'Content-Type':'application/json'},body:JSON.stringify(payload)});
 if(!response.ok){let detail='No se pudo completar la operación';try{detail=(await response.json()).detail||detail}catch{}throw Error(detail)}
 const url=URL.createObjectURL(await response.blob());const link=document.createElement('a');link.href=url;link.download=filename;link.click();setTimeout(()=>URL.revokeObjectURL(url),2500);
}
$('v102-vtt').onclick=async()=>{try{await skyV102Media('/api/global-media/subtitles/vtt',{srt:$('v102-srt').value,language:$('v102-locale').value},'SKY_subtitulos.vtt');text($('v102-status'),'Subtítulos WebVTT exportados.')}catch(ex){text($('v102-status'),ex.message)}};
$('v102-caption-video').onclick=async()=>{try{
 const asset=assets.find(a=>a.id===selected&&a.kind==='video')||assets.find(a=>a.id===project?.spec?.clips?.[0]?.asset_id&&a.kind==='video');
 if(!asset)throw Error('Seleccioná un video de la biblioteca para subtitular');
 await skyV102Media('/api/global-media/subtitles/render',{video_asset_id:asset.id,srt:$('v102-srt').value,language:$('v102-locale').value},'SKY_video_subtitulado.mp4');
 text($('v102-status'),'MP4 generado con subtítulos incorporados; el original sigue intacto.');
 }catch(ex){text($('v102-status'),ex.message)}};
$('v102-narrate').onclick=async()=>{try{
 await skyV102Media('/api/global-media/narration/mp3',{text:$('v102-narration').value,language:$('v102-locale').value,provider:'gtts',external_consent:$('v102-consent').checked},'SKY_narracion.mp3');
 text($('v102-status'),'Narración MP3 generada.');
 }catch(ex){text($('v102-status'),ex.message)}};
window.addEventListener('sky:languagechange',event=>{$('v102-locale').value=event.detail.language});


$('v103-voice').onclick=async()=>{try{
 const textValue=$('v102-narration').value.trim();if(!textValue||textValue.length>800)throw Error('Usá entre 1 y 800 caracteres para la voz local');
 await skyV102Media('/api/global-media/voice/local-wav',{
  text:textValue,language:$('v102-locale').value},'SKY_voz_local.wav');
 text($('v102-status'),'Voz WAV producida sin proveedor externo.');
 }catch(ex){text($('v102-status'),ex.message)}};
$('v103-dub').onclick=async()=>{try{
 const asset=assets.find(a=>a.id===selected&&a.kind==='video');if(!asset)throw Error('Seleccioná primero un video en la biblioteca');
 const textValue=$('v102-narration').value.trim();if(!textValue||textValue.length>800)throw Error('Usá entre 1 y 800 caracteres');
 await skyV102Media('/api/global-media/voice/dub-mp4',{
  text:textValue,language:$('v102-locale').value,video_asset_id:asset.id},'SKY_video_narrado.mp4');
 text($('v102-status'),'MP4 con voz local generado; el video original se conserva.');
 }catch(ex){text($('v102-status'),ex.message)}};

// SKY v10.5: private offline transcription. Only the user-selected audio is read.
$('v105-check').onclick=async()=>{try{
 if(!token)throw Error('Ingresá con la clave privada del creador');
 const r=await fetch('/api/global-media/stt/capabilities',{headers:{'X-SKY-KEY':token,...window.SKYOwnerAuth.headers()},cache:'no-store'});
 if(!r.ok)throw Error('No se pudo consultar la configuración');
 const info=await r.json();
 text($('v105-state'),info.available?'Modelo local listo, sin conexión externa.':'Modelo local no configurado: instalá faster-whisper y definí SKY_STT_MODEL_DIR.');
 }catch(ex){text($('v105-state'),ex.message)}};
$('v105-transcribe').onclick=async()=>{try{
 if(!token)throw Error('Ingresá como creador para transcribir');
 const audio=$('v105-audio').files?.[0];if(!audio)throw Error('Seleccioná un audio');
 if(audio.size>10*1024*1024)throw Error('El audio supera el límite de 10 MB');
 const fd=new FormData();fd.append('file',audio,audio.name);
 const locale=$('v102-locale')?.value||'';if(locale)fd.append('language',locale);
 text($('v105-state'),'Transcribiendo con modelo local...');
 const response=await fetch('/api/global-media/stt/transcribe',{method:'POST',headers:{'X-SKY-KEY':token,...window.SKYOwnerAuth.headers()},body:fd});
 const value=await response.json();if(!response.ok)throw Error(value.detail||'No se pudo transcribir');
 $('v105-transcript').value=value.text||'';
 text($('v105-state'),'Transcripción local · '+(value.detected_language||locale||'idioma detectado')+' · revisá el contenido antes de utilizarlo.');
 }catch(ex){text($('v105-state'),ex.message)}};
})();
