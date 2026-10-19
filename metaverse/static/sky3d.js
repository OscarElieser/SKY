/* SKY Engine 3D WebGL renderer: sin CDN, sin librerías de terceros en el navegador. */
'use strict';
const $=id=>document.getElementById(id);
let secret='', world=null, selectedId=null, socket=null, selfId=null, peers=new Map(), lastMove=0;
let dragging=false, downX=0, downY=0, yaw=.55, pitch=.56, distance=27, avatar={x:0,y:0,z:4};
let toastTimer=null, view3d=null, webxr=null;
const isNumber=n=>Number.isFinite(n);
function notify(message){const t=$('toast'); t.textContent=String(message);t.style.display='block';clearTimeout(toastTimer);toastTimer=setTimeout(()=>t.style.display='none',4000)}
async function api(path,opts={}){
  let res=await fetch(path,{...opts,headers:{'X-SKY-KEY':secret,...opts.headers}});
  if(!res.ok){let msg='Error '+res.status;try{let j=await res.json();msg=typeof j.detail==='string'?j.detail:JSON.stringify(j.detail||j)}catch{}throw Error(msg)}
  return res;
}
async function json(path,opts={}){let res=await api(path,opts);return res.json()}
const jsonPost=(path,obj,method='POST')=>json(path,{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(obj)});
function safeText(el,value){el.textContent=String(value)}
function chatBubble(txt,role='bot'){let node=document.createElement('div');node.className='chat '+(role==='user'?'me':'bot');node.textContent=txt;$('chat-log').append(node);$('chat-log').scrollTop=$('chat-log').scrollHeight}
function roomBubble(txt){let node=document.createElement('div');node.textContent=txt;$('world-feed').append(node);$('world-feed').scrollTop=$('world-feed').scrollHeight}
function option(el,text,value){let op=document.createElement('option');op.textContent=text;op.value=value;el.append(op)}
async function login(){secret=$('key').value.trim();try{await json('/api/capabilities');$('login').classList.add('hidden');$('app').classList.remove('hidden');startGL();await refreshWorlds();notify('SKY Engine conectado. Bienvenido a tu universo.')}catch(e){$('login-error').textContent='No fue posible conectar: '+e.message;secret=''}}
$('connect').addEventListener('click',login);$('key').addEventListener('keydown',e=>{if(e.key==='Enter')login()});$('logout').addEventListener('click',()=>{if(socket)socket.close();secret='';world=null;$('key').value='';$('app').classList.add('hidden');$('login').classList.remove('hidden')});
async function refreshWorlds(select){let worlds=await json('/api/worlds');$('worlds').replaceChildren();for(const w of worlds)option($('worlds'),w.name,w.id);await openWorld(select||worlds[0]?.id)}
async function openWorld(id){if(!id)return;if(socket)socket.close();peers.clear();world=await json('/api/worlds/'+id);$('worlds').value=id;safeText($('world-title'),world.name);renderObjects();await connectPresence(id);notify('Mundo listo: '+world.name)}
$('worlds').addEventListener('change',()=>openWorld($('worlds').value).catch(e=>notify(e.message)));
function renderObjects(){if(!world)return;let objs=world.scene.objects;safeText($('object-count'),objs.length+' elementos');let sel=$('objects');sel.replaceChildren();for(const o of objs)option(sel,o.name+' · '+o.kind,o.id);if(!objs.find(o=>o.id===selectedId))selectedId=objs.find(o=>o.kind!=='platform')?.id||objs[0]?.id;sel.value=selectedId;inspect()}
function inspect(){let obj=world?.scene.objects.find(o=>o.id===selectedId);if(!obj){safeText($('selection-label'),'Sin selección');return}safeText($('selection-label'),obj.name+' · '+obj.kind);$('edit-color').value=obj.color;for(let i=0;i<3;i++){$('edit-'+['x','y','z'][i]).value=obj.position[i];$('edit-'+['sx','sy','sz'][i]).value=obj.scale[i]}}
$('objects').addEventListener('change',()=>{selectedId=$('objects').value;inspect()});
$('apply').addEventListener('click',()=>{if(!world)return;let obj=world.scene.objects.find(o=>o.id===selectedId);if(!obj)return;let pos=['x','y','z'].map(v=>Number($('edit-'+v).value));let sc=['sx','sy','sz'].map(v=>Number($('edit-'+v).value));if(!pos.every(v=>isNumber(v)&&Math.abs(v)<=100)||!sc.every(v=>isNumber(v)&&v>=.05&&v<=100))return notify('Coordenadas o escalas inválidas');obj.position=pos;obj.scale=sc;obj.color=$('edit-color').value;notify('Pieza modificada. Presioná Guardar mundo para conservarla.')});
async function save(){if(!world)return;let updated=await jsonPost('/api/worlds/'+world.id,{version:world.version,scene:world.scene},'PUT');world=updated;renderObjects();notify('Mundo guardado en SKY Engine ✓')}
$('save').addEventListener('click',()=>save().catch(e=>notify(e.message)));
$('create').addEventListener('click',async()=>{let name=$('world-name').value.trim()||'Mi universo SKY';let prompt=$('prompt').value.trim()||'Mundo de innovación, educación y creatividad';try{let w=await jsonPost('/api/worlds',{name,prompt,seed:Date.now()%1000000});await refreshWorlds(w.id)}catch(e){notify(e.message)}});
$('extend').addEventListener('click',async()=>{if(!world)return;let prompt=$('prompt').value.trim();if(!prompt)return notify('Escribí qué elementos querés añadir');try{world=await jsonPost('/api/worlds/'+world.id+'/generate',{prompt,seed:Math.floor(Math.random()*100000),append:true,version:world.version});renderObjects();notify('Nuevos objetos añadidos y guardados')}catch(e){notify(e.message)}});
$('add').addEventListener('click',async()=>{if(!world)return;let kind=$('shape').value;try{let name=kind+' '+(world.scene.objects.length+1);world=await jsonPost('/api/worlds/'+world.id+'/objects',{version:world.version,object:{name,kind,position:[avatar.x,0,avatar.z-3],rotation:[0,0,0],scale:[1,2,1],color:'#4BAFC6'}});selectedId=world.scene.objects.at(-1).id;renderObjects();notify('Pieza añadida')}catch(e){notify(e.message)}});
$('delete-object').addEventListener('click',()=>{if(!world||!selectedId)return;let obj=world.scene.objects.find(o=>o.id===selectedId);if(obj&&confirm('¿Eliminar la pieza «'+obj.name+'»?')){world.scene.objects=world.scene.objects.filter(o=>o.id!==selectedId);selectedId=null;renderObjects();notify('Pieza eliminada; falta guardar la escena.')}});
$('delete-world').addEventListener('click',async()=>{if(!world||!confirm('¿Eliminar definitivamente el mundo «'+world.name+'»?'))return;try{await api('/api/worlds/'+world.id,{method:'DELETE'});world=null;await refreshWorlds()}catch(e){notify(e.message)}});
$('download').addEventListener('click',async()=>{if(!world)return;try{let res=await api('/api/worlds/'+world.id+'/export.glb');let blob=await res.blob();let url=URL.createObjectURL(blob);let a=document.createElement('a');a.href=url;a.download='SKY_'+world.name.replace(/[^a-z0-9-]/ig,'_').slice(0,35)+'.glb';a.click();setTimeout(()=>URL.revokeObjectURL(url),4000);notify('Archivo GLB exportado para Blender')}catch(e){notify(e.message)}});
$('screenshot').addEventListener('click',()=>{if(!view3d)return;view3d.canvas.toBlob(blob=>{if(!blob)return;let a=document.createElement('a');let u=URL.createObjectURL(blob);a.href=u;a.download='SKY_metaverso.png';a.click();setTimeout(()=>URL.revokeObjectURL(u),3000)},'image/png')});
$('chat-form').addEventListener('submit',async e=>{e.preventDefault();let message=$('message').value.trim();if(!message)return;$('message').value='';chatBubble(message,'user');let m=message.match(/(?:sky[, :]*\s*)?(?:cre[aá]|crea|genera|construye)\s+(?:un |una |el |la )?(bosque|playa|ciudad|selva|planeta|galaxia|laboratorio|mundo)(.*)/i);if(m&&world){$('prompt').value=message;try{world=await jsonPost('/api/worlds/'+world.id+'/generate',{prompt:message,seed:Date.now()%999999,append:false,version:world.version});renderObjects();chatBubble('Mundo creado. Podés editar cada elemento, recorrerlo y exportarlo a GLB.')}catch(err){chatBubble('No se pudo generar: '+err.message)}return}try{let data=await jsonPost('/api/chat',{message,provider:$('provider').value,area:'Asistente universal'});chatBubble(data.answer);speak(data.answer)}catch(e){chatBubble('SKY: '+e.message)}});
function speak(text){if(!window.speechSynthesis||!$('mic').dataset.speak)return;window.speechSynthesis.cancel();let utter=new SpeechSynthesisUtterance(text.slice(0,900));utter.lang=window.SKYGlobalI18N?.locale()||'es-NI';utter.rate=1;window.speechSynthesis.speak(utter)}
$('mic').addEventListener('click',()=>{const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!Recognition)return notify('Este navegador no dispone de dictado de voz Web Speech. Podés usar SKY manos libres desde Python.');let sr=new Recognition();sr.lang=window.SKYGlobalI18N?.locale()||'es-NI';sr.interimResults=false;sr.onresult=e=>{$('message').value=e.results[0][0].transcript;$('message').focus()};sr.onerror=()=>notify('No se pudo reconocer la voz');sr.start();notify('SKY está escuchando...')});
$('world-chat-form').addEventListener('submit',e=>{e.preventDefault();let msg=$('world-msg').value.trim();if(!msg||!socket||socket.readyState!==WebSocket.OPEN)return;socket.send(JSON.stringify({type:'say',text:msg}));$('world-msg').value=''});
async function connectPresence(id){try{let {ticket}=await jsonPost('/api/ws-ticket',{});let proto=location.protocol==='https:'?'wss:':'ws:';socket=new WebSocket(proto+'//'+location.host+'/api/ws/'+id+'?ticket='+encodeURIComponent(ticket));socket.onmessage=e=>{let d=JSON.parse(e.data);if(d.type==='peers'){selfId=d.you;peers.clear();for(let peer of d.peers)peers.set(peer.id,peer)}else if(d.type==='join'||d.type==='move'){peers.set(d.peer.id,d.peer)}else if(d.type==='leave'){peers.delete(d.id)}else if(d.type==='say'){roomBubble((d.from===selfId?'Yo':'Participante')+': '+d.text)}let n=Math.max(0,peers.size-1);safeText($('peers'),(n?'Otros participantes: '+n:'Estás en tu sala privada')+' · Conexión en tiempo real')};socket.onclose=()=>safeText($('peers'),'Conexión en tiempo real cerrada')}catch(e){safeText($('peers'),'Sala sin conexión: '+e.message)}}
// -------- Motor de WebGL autocontenido --------
const VERT=`attribute vec3 aP;attribute vec3 aN;uniform mat4 uProj,uView,uModel;varying vec3 vNormal;varying float vFog;void main(){vec4 view=uView*uModel*vec4(aP,1.0);gl_Position=uProj*view;vNormal=mat3(uModel)*aN;vFog=clamp((-view.z-4.0)/65.0,0.0,0.55);}`;
const FRAG=`precision mediump float;uniform vec3 uColor;uniform vec3 uSky;varying vec3 vNormal;varying float vFog;void main(){float sun=max(dot(normalize(vNormal),normalize(vec3(0.4,1.0,0.5))),0.0);vec3 lit=uColor*(0.62+sun*0.46);gl_FragColor=vec4(mix(lit,uSky,vFog),1.0);}`;
const norm=v=>{let l=Math.hypot(...v)||1;return v.map(x=>x/l)};
const sub=(a,b)=>a.map((v,i)=>v-b[i]);const cross=(a,b)=>[a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]];const dot=(a,b)=>a.reduce((s,v,i)=>s+v*b[i],0);
function mul(a,b){let out=new Float32Array(16);for(let c=0;c<4;c++)for(let r=0;r<4;r++)for(let k=0;k<4;k++)out[c*4+r]+=a[k*4+r]*b[c*4+k];return out}
function matrix(x,y,z,sx,sy,sz,angle=0){let c=Math.cos(angle),s=Math.sin(angle);return new Float32Array([c*sx,0,-s*sx,0,0,sy,0,0,s*sz,0,c*sz,0,x,y,z,1])}
function perspective(fov,aspect,near,far){let f=1/Math.tan(fov/2);return new Float32Array([f/aspect,0,0,0,0,f,0,0,0,0,(far+near)/(near-far),-1,0,0,2*far*near/(near-far),0])}
function lookAt(eye,at){let z=norm(sub(eye,at)),x=norm(cross([0,1,0],z)),y=cross(z,x);return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-dot(x,eye),-dot(y,eye),-dot(z,eye),1])}
function makeMesh(type){let a=[];function tri(p,q,r){let n=norm(cross(sub(q,p),sub(r,p)));for(let v of [p,q,r])a.push(...v,...n)}function quad(p,q,r,s){tri(p,q,r);tri(p,r,s)}
if(type==='box'){
const b=[-.5,.5];for(let k=0;k<3;k++)for(let side of b){let x=[0,0,0],y=[0,0,0],z=[0,0,0];let p=[];for(let u of b)for(let v of b){let q=[0,0,0];q[k]=side;q[(k+1)%3]=u;q[(k+2)%3]=v;p.push(q)}if(side>.0)quad(p[0],p[1],p[3],p[2]);else quad(p[0],p[2],p[3],p[1])}}
else if(type==='sphere'){let lat=12,lon=20;const v=(t,p)=>[.5*Math.sin(t)*Math.cos(p),.5*Math.cos(t),.5*Math.sin(t)*Math.sin(p)];for(let i=0;i<lat;i++)for(let j=0;j<lon;j++){let t=i*Math.PI/lat,t2=(i+1)*Math.PI/lat,p=j*2*Math.PI/lon,p2=(j+1)*2*Math.PI/lon;quad(v(t,p),v(t2,p),v(t2,p2),v(t,p2))}}
else if(type==='cylinder'||type==='cone'){let n=20;for(let i=0;i<n;i++){let t=i*2*Math.PI/n,t2=(i+1)*2*Math.PI/n;let a=[.5*Math.cos(t),-.5,.5*Math.sin(t)],b=[.5*Math.cos(t2),-.5,.5*Math.sin(t2)];if(type==='cylinder'){let c=[b[0],.5,b[2]],d=[a[0],.5,a[2]];quad(a,b,c,d);tri([0,.5,0],d,c)}else tri(a,b,[0,.5,0]);tri([0,-.5,0],b,a)}}
else if(type==='torus'){let m=24,n=8,R=.39,r=.12;const v=(t,p)=>[(R+r*Math.cos(p))*Math.cos(t),(R+r*Math.cos(p))*Math.sin(t),r*Math.sin(p)];for(let i=0;i<m;i++)for(let j=0;j<n;j++){let t=i*2*Math.PI/m,t2=(i+1)*2*Math.PI/m,p=j*2*Math.PI/n,p2=(j+1)*2*Math.PI/n;quad(v(t,p),v(t2,p),v(t2,p2),v(t,p2))}}
return new Float32Array(a)}
function shader(gl,type,source){let sh=gl.createShader(type);gl.shaderSource(sh,source);gl.compileShader(sh);if(!gl.getShaderParameter(sh,gl.COMPILE_STATUS))throw Error(gl.getShaderInfoLog(sh));return sh}
function startGL(){if(view3d)return;let canvas=$('scene');let gl=canvas.getContext('webgl',{antialias:true,alpha:false,preserveDrawingBuffer:true,xrCompatible:true});if(!gl){notify('WebGL no está disponible: SKY activó el visor de reserva 3D proyectado.');startFallbackRenderer(canvas);return}let pr=gl.createProgram();gl.attachShader(pr,shader(gl,gl.VERTEX_SHADER,VERT));gl.attachShader(pr,shader(gl,gl.FRAGMENT_SHADER,FRAG));gl.linkProgram(pr);if(!gl.getProgramParameter(pr,gl.LINK_STATUS))throw Error('No se pudo iniciar WebGL');gl.useProgram(pr);gl.enable(gl.DEPTH_TEST);gl.disable(gl.CULL_FACE);
let u={proj:gl.getUniformLocation(pr,'uProj'),view:gl.getUniformLocation(pr,'uView'),model:gl.getUniformLocation(pr,'uModel'),color:gl.getUniformLocation(pr,'uColor'),sky:gl.getUniformLocation(pr,'uSky')};let pa=gl.getAttribLocation(pr,'aP'),na=gl.getAttribLocation(pr,'aN');let buffers={};for(let shape of ['box','sphere','cylinder','cone','torus']){let data=makeMesh(shape),buffer=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,buffer);gl.bufferData(gl.ARRAY_BUFFER,data,gl.STATIC_DRAW);buffers[shape]={buffer,count:data.length/6}};
function color(c){return [1,3,5].map(i=>parseInt(c.slice(i,i+2),16)/255)}
function drawShape(kind,position,scale,shade,rot=0){let m=buffers[kind]||buffers.box;gl.bindBuffer(gl.ARRAY_BUFFER,m.buffer);gl.enableVertexAttribArray(pa);gl.enableVertexAttribArray(na);gl.vertexAttribPointer(pa,3,gl.FLOAT,false,24,0);gl.vertexAttribPointer(na,3,gl.FLOAT,false,24,12);gl.uniformMatrix4fv(u.model,false,matrix(...position,...scale,rot));gl.uniform3fv(u.color,color(shade));gl.drawArrays(gl.TRIANGLES,0,m.count)}
function drawObject(o){const [x,y,z]=o.position,[sx,sy,sz]=o.scale;const a=o.rotation?.[1]||0;let c=o.color,k=o.kind;if(k==='tree'||k==='palm'){drawShape('cylinder',[x,y+sy*.34,z],[sx*.23,sy*.68,sz*.23],'#795139',a);drawShape(k==='palm'?'sphere':'cone',[x,y+sy*.76,z],[sx,sy*.6,sz],c,a)}else if(k==='house'){drawShape('box',[x,y+sy*.35,z],[sx,sy*.7,sz],c,a);drawShape('cone',[x,y+sy*.93,z],[sx*1.3,sy*.53,sz*1.3],'#AE6659',a)}else drawShape(k==='rock'?'sphere':k==='platform'||k==='tower'?'box':k,[x,y+(k==='torus'?0:sy*.5),z],[sx,sy,sz],c,a)}
function drawFrame(proj,view,viewport){gl.viewport(...viewport);gl.uniformMatrix4fv(u.proj,false,proj);gl.uniformMatrix4fv(u.view,false,view);let sky=world?.scene?.sky||'#0D233B';let c=color(sky);gl.uniform3fv(u.sky,c);gl.clearColor(...c,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);for(let obj of world?.scene?.objects||[])drawObject(obj);for(let p of peers.values()){if(p.id===selfId||!p.position)continue;let [x,y,z]=p.position;drawShape('cylinder',[x,y+.8,z],[.45,1.3,.45],'#64CEDF');drawShape('sphere',[x,y+1.7,z],[.48,.48,.48],'#F5C99E')}}
function render(){if(!webxr){let dpr=Math.min(devicePixelRatio||1,2);let w=Math.max(1,Math.floor(canvas.clientWidth*dpr)),h=Math.max(1,Math.floor(canvas.clientHeight*dpr));if(canvas.width!==w||canvas.height!==h){canvas.width=w;canvas.height=h}let target=[avatar.x,2,avatar.z-2];let eye=[target[0]+Math.cos(pitch)*Math.sin(yaw)*distance,target[1]+Math.sin(pitch)*distance,target[2]+Math.cos(pitch)*Math.cos(yaw)*distance];drawFrame(perspective(.9,w/h,.1,300),lookAt(eye,target),[0,0,w,h]);}requestAnimationFrame(render)}
view3d={canvas,gl,drawFrame};requestAnimationFrame(render);
canvas.addEventListener('pointerdown',e=>{dragging=true;downX=e.clientX;downY=e.clientY;canvas.setPointerCapture(e.pointerId)});canvas.addEventListener('pointermove',e=>{if(!dragging)return;yaw-=(e.clientX-downX)*.008;pitch=Math.min(1.45,Math.max(.05,pitch+(e.clientY-downY)*.008));downX=e.clientX;downY=e.clientY});canvas.addEventListener('pointerup',()=>dragging=false);canvas.addEventListener('pointercancel',()=>dragging=false);canvas.addEventListener('wheel',e=>{distance=Math.max(4,Math.min(80,distance*(e.deltaY>0?1.12:.89)));e.preventDefault()},{passive:false});
window.addEventListener('keydown',e=>{if(['INPUT','TEXTAREA','SELECT'].includes(document.activeElement?.tagName))return;let key=e.key.toLowerCase();let d=key==='w'||key==='arrowup'?-1:key==='s'||key==='arrowdown'?1:0;let a=key==='a'||key==='arrowleft'?-1:key==='d'||key==='arrowright'?1:0;if(!d&&!a)return;avatar.x=Math.max(-75,Math.min(75,avatar.x+a*.85));avatar.z=Math.max(-75,Math.min(75,avatar.z+d*.85));safeText($('coords'),'X: '+avatar.x.toFixed(1)+' · Z: '+avatar.z.toFixed(1));if(socket?.readyState===1&&Date.now()-lastMove>90){socket.send(JSON.stringify({type:'move',position:[avatar.x,avatar.y,avatar.z]}));lastMove=Date.now()}e.preventDefault()});
}
$('vr').addEventListener('click',async()=>{if(!view3d||!navigator.xr)return notify('WebXR no está disponible. Necesitás un visor VR compatible y HTTPS.');try{if(webxr){await webxr.end();return}if(!await navigator.xr.isSessionSupported('immersive-vr'))return notify('Este equipo no permite sesiones VR.');let gl=view3d.gl;await gl.makeXRCompatible();let session=await navigator.xr.requestSession('immersive-vr',{optionalFeatures:['local-floor']});webxr=session;let layer=new XRWebGLLayer(session,gl);session.updateRenderState({baseLayer:layer});let ref=await session.requestReferenceSpace('local-floor').catch(()=>session.requestReferenceSpace('local'));session.addEventListener('end',()=>{webxr=null;gl.bindFramebuffer(gl.FRAMEBUFFER,null);notify('Modo VR finalizado')});function frame(t,f){if(!webxr)return;session.requestAnimationFrame(frame);let pose=f.getViewerPose(ref);if(!pose)return;gl.bindFramebuffer(gl.FRAMEBUFFER,layer.framebuffer);for(let v of pose.views){let vp=layer.getViewport(v);view3d.drawFrame(v.projectionMatrix,v.transform.inverse.matrix,[vp.x,vp.y,vp.width,vp.height])}}session.requestAnimationFrame(frame);notify('SKY VR activado')}catch(e){notify('No fue posible iniciar VR: '+e.message)}});
// Reconstrucción local 2.5D desde cámara/foto: archivo generado sin subir a servicios externos.
$('photo-extrude').addEventListener('click',async()=>{
  let file=$('photo').files[0];if(!file)return notify('Seleccioná una fotografía PNG, JPG o WebP');
  if(file.size>12_000_000)return notify('La foto debe tener menos de 12 MB');
  try{notify('SKY está extruyendo la silueta en 3D...');let response=await api('/api/studio/photo-to-glb',{method:'POST',headers:{'Content-Type':file.type},body:file});let b=await response.blob();let u=URL.createObjectURL(b);let a=document.createElement('a');a.href=u;a.download='SKY_pieza_desde_foto.glb';a.click();setTimeout(()=>URL.revokeObjectURL(u),3500);notify('Pieza GLB creada. Abrila en Blender o SKY Studio 3D.')}catch(e){notify(e.message)}
});

// Render de reserva sin GPU: proyección 3D por polígonos, sin bibliotecas externas.
// Se activa únicamente si WebGL está deshabilitado por el navegador.
function startFallbackRenderer(canvas){
  const ctx=canvas.getContext('2d');if(!ctx)return;
  function project(v,eye,fw,right,up,focal,w,h){const r=sub(v,eye),d=dot(r,fw);if(d<=.1)return null;return [w/2+dot(r,right)*focal/d,h/2-dot(r,up)*focal/d,d]}
  let boxfaces=[[0,1,3,2],[4,5,7,6],[0,1,5,4],[2,3,7,6],[0,2,6,4],[1,3,7,5]];
  function shapeList(obj){let [x,y,z]=obj.position,[sx,sy,sz]=obj.scale;let base=obj.color;
    if(obj.kind==='tree'||obj.kind==='palm')return [{pos:[x,y+sy*.34,z],size:[sx*.24,sy*.68,sz*.24],color:'#815E46'},
      {pos:[x,y+sy*.75,z],size:[sx*1.25,sy*.55,sz*1.25],color:base,sphere:true}];
    if(obj.kind==='house')return [{pos:[x,y+sy*.35,z],size:[sx,sy*.7,sz],color:base},
      {pos:[x,y+sy*.89,z],size:[sx*1.15,sy*.37,sz*1.15],color:'#AA6658'}];
    return [{pos:[x,y+(obj.kind==='torus'?0:sy*.5),z],size:[sx,sy,sz],color:base,sphere:['sphere','rock','torus'].includes(obj.kind)}]}
  function render2d(){const w=canvas.clientWidth,h=canvas.clientHeight,dpr=Math.min(devicePixelRatio||1,2);
    if(canvas.width!==Math.floor(w*dpr)||canvas.height!==Math.floor(h*dpr)){canvas.width=Math.floor(w*dpr);canvas.height=Math.floor(h*dpr)}
    ctx.setTransform(dpr,0,0,dpr,0,0);ctx.fillStyle=world?.scene?.sky||'#102844';ctx.fillRect(0,0,w,h);
    const target=[avatar.x,2,avatar.z-2],eye=[target[0]+Math.cos(pitch)*Math.sin(yaw)*distance,target[1]+Math.sin(pitch)*distance,target[2]+Math.cos(pitch)*Math.cos(yaw)*distance];
    const fw=norm(sub(target,eye)),right=norm(cross(fw,[0,1,0])),up=cross(right,fw);const focal=Math.min(w,h)*1.12;
    const paint=[];
    for(let ob of world?.scene?.objects||[])for(let obj of shapeList(ob)){
      let [x,y,z]=obj.pos,[a,b,c]=obj.size,cs=obj.color;
      const corners=[];for(let j of [-.5,.5])for(let k of [-.5,.5])for(let l of [-.5,.5])corners.push([x+j*a,y+k*b,z+l*c]);
      const pts=corners.map(v=>project(v,eye,fw,right,up,focal,w,h));
      if(obj.sphere){let p=project([x,y,z],eye,fw,right,up,focal,w,h);if(p){paint.push({depth:p[2],pts:null,p,r:Math.max(2,(a+b+c)/6*focal/p[2]),color:cs})}continue}
      for(let i=0;i<boxfaces.length;i++){
        let pp=boxfaces[i].map(index=>pts[index]);if(pp.some(p=>!p))continue;
        paint.push({depth:pp.reduce((sum,p)=>sum+p[2],0)/4,pts:pp,color:cs,face:i});
      }
    }
    paint.sort((a,b)=>b.depth-a.depth);
    for(let item of paint){ctx.fillStyle=item.color;ctx.strokeStyle='#071c2855';ctx.lineWidth=.8;
      if(item.pts){ctx.beginPath();ctx.moveTo(...item.pts[0]);for(let p of item.pts.slice(1))ctx.lineTo(p[0],p[1]);ctx.closePath();ctx.fill();ctx.stroke()}
      else{ctx.beginPath();ctx.arc(item.p[0],item.p[1],item.r,0,Math.PI*2);ctx.fill()}}
    /* El visor de reserva se identifica mediante el aviso temporal del panel. */
    requestAnimationFrame(render2d)}
  canvas.addEventListener('pointerdown',e=>{dragging=true;downX=e.clientX;downY=e.clientY;canvas.setPointerCapture(e.pointerId)});
  canvas.addEventListener('pointermove',e=>{if(!dragging)return;yaw-=(e.clientX-downX)*.008;pitch=Math.min(1.45,Math.max(.05,pitch+(e.clientY-downY)*.008));downX=e.clientX;downY=e.clientY});
  canvas.addEventListener('pointerup',()=>dragging=false);canvas.addEventListener('wheel',e=>{distance=Math.max(4,Math.min(80,distance*(e.deltaY>0?1.12:.89)));e.preventDefault()},{passive:false});
  view3d={canvas,fallback:true};requestAnimationFrame(render2d);
}
