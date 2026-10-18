(()=>{'use strict';
const $=id=>document.getElementById(id);let key='',previewSpec=null,previewHTML='',previewSignature='',currentProject='';
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=String(text);if(cls)n.className=cls;return n};
const notice=(message,isError=false)=>{const n=$('job-message');n.textContent=message;n.className=isError?'notice error':'notice'};
async function api(path,method='GET',body){const opts={method,headers:{'X-SKY-KEY':key}};if(body!==undefined){opts.headers['Content-Type']='application/json';opts.body=JSON.stringify(body)}const res=await fetch(path,opts);const contentType=res.headers.get('content-type')||'';const data=contentType.includes('application/json')?await res.json():await res.text();if(!res.ok)throw Error((data&&typeof data==='object'&&data.detail)||'No se pudo completar la operación ('+res.status+')');return data}
function rolesView(plan){const result=$('role-result');result.replaceChildren();const chips=el('div',undefined,'role-chips');for(const role of plan.roles||[]){const item=el('span',role.title,'role-chip');item.title=role.description;chips.append(item)}result.append(el('h3','Especialidades seleccionadas'),chips);const ol=el('ol',undefined,'steps');for(const step of plan.steps||[])ol.append(el('li',step.name));result.append(ol);result.append(el('p',plan.policy||'', 'muted'))}
function options(){const o={palette:$('palette').value,title:$('design-title').value.trim()};if($('template').value)o.template=$('template').value;return o}
function intent(){return $('intent').value.trim()}
function designSignature(){return JSON.stringify({task:intent(),options:options()})}
function resetPreview(){previewSpec=null;previewHTML='';previewSignature='';$('save-experience').disabled=true;$('download-html').disabled=true;$('preview-frame').removeAttribute('srcdoc')}
function previewIsCurrent(){return Boolean(previewSpec)&&previewSignature===designSignature()}
async function plan(){if(intent().length<6){notice('Escribí una solicitud de al menos 6 caracteres.',true);return}const result=await api('/api/sky/plan','POST',{task:intent()});rolesView(result);notice('Plan generado localmente, sin ejecutar acciones ni enviar datos a la nube.')}
async function conversation(){
if(!intent()){notice('Escribí una pregunta para conversar.',true);return}
const provider=$('provider').value;
const payload={message:intent(),provider,include_memory:$('share-memory').checked,project_id:currentProject||null,
 share_project_context:Boolean(currentProject)&&$('use-project-context').checked,
 share_project_history:Boolean(currentProject)&&$('use-project-history').checked,
 save_to_project:Boolean(currentProject)&&$('save-project-chat').checked};
if(provider!=='local'){
 const shared=[payload.include_memory?'memoria global':null,payload.share_project_context?'resumen del proyecto':null,payload.share_project_history?'historial del proyecto':null].filter(Boolean).join(', ')||'ningún dato adicional';
 if(!confirm('La pregunta se enviará a '+provider+'. Datos adicionales compartidos: '+shared+'. ¿Autorizar?'))return;
}
const result=await api('/api/sky/assist','POST',payload);
if(result.plan)rolesView(result.plan);else rolesView({roles:result.roles,steps:[]});
$('answer').hidden=false;$('answer').textContent=result.answer||'';
notice('Respuesta recibida desde '+result.provider+'.');
if(currentProject&&payload.save_to_project)await loadProjectMessages();
}
async function preview(){const text=intent();if(!text){notice('Primero describí tu diseño en el campo principal.',true);return}const signature=designSignature();const data=await api('/api/sky/experiences/preview','POST',{prompt:text,options:options()});if(designSignature()!==signature){resetPreview();notice('La solicitud cambió durante la generación. Generá otra vista previa.',true);return}previewSpec=data.spec;previewHTML=data.html;previewSignature=signature;$('preview-frame').srcdoc=previewHTML;$('save-experience').disabled=false;$('download-html').disabled=false;notice('Vista previa generada. Podés descargarla o guardarla en SKY.')}
function downloadRaw(data,name,type){const url=URL.createObjectURL(new Blob([data],{type}));const a=el('a');a.href=url;a.download=name;document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000)}
function getActionParams(act=$('action').value){const title=$('action-title').value.trim()||'Creación SKY';if(act==='experience')return {title, ...options()};if(act==='world')return {name:title,prompt:intent()};if(act==='document'){const csv=$('table-csv').value;const body={kind:$('format').value,title,content:$('doc-content').value,template:'general',csv};return {document:body}}if(act==='memory')return {label:title,content:$('memory-text').value};return {}}
async function createTask(actionOverride){const action=actionOverride||$('action').value;if(action==='experience'&&!previewIsCurrent()){notice('Primero generá una vista previa actualizada para guardar exactamente ese diseño.',true);return}let task=intent();if(action==='experience'){task=previewSpec.description}if(!task||task.length<6){notice('Escribí primero qué necesitás hacer.',true);return}const params=getActionParams(action);if(action==='experience'){Object.assign(params,{template:previewSpec.template,palette:previewSpec.palette,title:previewSpec.title,sections:[...previewSpec.sections],description:previewSpec.description})}const path=currentProject?'/api/sky/projects/'+encodeURIComponent(currentProject)+'/tasks':'/api/sky/tasks';const data=await api(path,'POST',{task,action,params});notice('Tarea '+data.id+' preparada. Revisá el detalle y confirmá su ejecución.');await loadTasks();if(currentProject)await loadProject();return data}
async function executeTask(id){if(!confirm('¿Confirmás ejecutar esta acción dentro de SKY? Se guardará un resultado local.'))return;try{const data=await api('/api/sky/tasks/'+encodeURIComponent(id)+'/execute','POST',{approve:true});notice('Tarea '+data.id+' '+data.status+'.');await loadTasks();await memoryList();if(currentProject)await loadProject()}catch(err){notice(err.message,true);await loadTasks()}}
async function fileDownload(id,name){const res=await fetch('/api/sky/files/'+encodeURIComponent(id),{headers:{'X-SKY-KEY':key}});if(!res.ok)throw Error('No se pudo recuperar el archivo.');const bytes=await res.blob();const url=URL.createObjectURL(bytes);const a=el('a');a.href=url;a.download=name||'SKY_archivo';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
async function loadTasks(){const tasks=await api('/api/sky/tasks');const root=$('jobs');root.replaceChildren();if(!tasks.length){root.append(el('p','Todavía no hay entregables creados.','muted'));return}for(const t of tasks){const wrap=el('article',undefined,'job');const top=el('div',undefined,'job-top');top.append(el('h4',t.task.slice(0,145)));top.append(el('span',t.status,'status'));wrap.append(top);wrap.append(el('p',(t.action||'plan')+' · '+t.id));if(t.status==='pendiente'){const b=el('button','Confirmar y ejecutar');b.addEventListener('click',()=>executeTask(t.id).catch(e=>notice(e.message,true)));wrap.append(b)}if(t.status==='completada'&&t.output){const d=t.output;wrap.append(el('p',d.kind==='file'?'Archivo disponible: '+d.name:d.kind==='world'?'Mundo generado: '+d.world_id:d.kind==='experience'?'Diseño editable guardado':'Acción completada'));if(d.kind==='file'){const b=el('button','Descargar '+d.name);b.addEventListener('click',()=>fileDownload(t.id,d.name).catch(e=>notice(e.message,true)));wrap.append(b)}if(d.kind==='experience'){const b=el('button','Descargar experiencia HTML');b.addEventListener('click',async()=>{try{const spec=await api('/api/sky/experiences/'+t.id);const result=await api('/api/sky/experiences/'+t.id+'/html');downloadRaw(result,'SKY_Experience.html','text/html')}catch(e){notice(e.message,true)}});wrap.append(b)}}if(t.status==='error')wrap.append(el('p',t.error||'No pudo completarse','error'));root.append(wrap)}}
async function memoryList(){const notes=await api('/api/sky/memory');const root=$('memories');root.replaceChildren();if(!notes.length){root.append(el('p','Sin notas guardadas.','muted'));return}for(const note of notes){const block=el('div',undefined,'note');const content=el('div');content.append(el('strong',note.label),el('p',note.content));block.append(content);const b=el('button','Eliminar');b.addEventListener('click',async()=>{if(confirm('¿Eliminar este recuerdo privado?')){await api('/api/sky/memory/'+note.id,'DELETE');await memoryList()}});block.append(b);root.append(block)}}
function drawNeurons(){const ns='http://www.w3.org/2000/svg',g=$('nodes');const xs=[90,260,465,665];for(let c=0;c<xs.length;c++)for(let r=0;r<5;r++){const n=document.createElementNS(ns,'circle');n.setAttribute('cx',xs[c]);n.setAttribute('cy',35+r*40);n.setAttribute('r',r%2?6:4);n.setAttribute('fill',['#61e4ff','#6cb9ff','#b28dff','#ffb57b'][c]);g.append(n)}}
async function activity(){const data=await api('/api/sky/activity');$('events-count').textContent=data.events_sampled;$('latency').textContent=data.average_ms_in_sample??'—';const groups=$('groups');groups.replaceChildren();const entries=Object.entries(data.groups||{});const max=Math.max(1,...entries.map(x=>x[1]));for(const [name,count] of entries){const line=el('div',name+' · '+count,'bar');const i=el('i');i.style.width=(count/max*100)+'%';line.append(i);groups.append(line)}const div=$('activity-events');div.replaceChildren();for(const entry of data.events.slice(0,12))div.append(el('div',entry.module+' · HTTP '+entry.status+' · '+entry.latency_ms+' ms','event-row'));}
async function integrations(){const data=await api('/api/sky/integrations');$('integration-summary').textContent='Núcleo: '+(data.core_operational?'operativo':'requiere atención')+' · Diagnóstico: '+data.state+' · Proveedores externos y hardware no verificados.';const list=$('integration-list');list.replaceChildren();for(const [name,item] of Object.entries(data.libraries||{})){const row=el('div',name+' — '+item.state+(item.missing.length?' (faltan: '+item.missing.join(', ')+')':''),'event-row');list.append(row)}for(const [name,item] of Object.entries(data.databases||{}))list.append(el('div',name+' — '+item.state+' · '+item.message,'event-row'));}
async function login(){key=$('key').value.trim();try{const data=await api('/api/sky/roles');$('role-count').textContent=data.count;$('gate').hidden=true;$('app').hidden=false;$('key').value='';try{await api('/api/sky/owner/baqueano');let link=document.getElementById('sky-baqueano-owner-link');if(!link){link=document.createElement('a');link.id='sky-baqueano-owner-link';link.href='/owner/baqueano';link.textContent='✦ BAQUEANO · Solo creador';document.querySelector('.sidebar').append(link)}}catch(e){}await Promise.all([loadTasks(),memoryList(),activity(),integrations(),loadProjects()]);}catch(err){key='';$('gate-error').textContent='No se pudo entrar. Verificá la clave privada y que SKY esté ejecutándose.'}}

async function loadProjects(){
 const all=await api('/api/sky/projects');const sel=$('project-select');const old=currentProject;
 sel.replaceChildren();sel.append(new Option('Sin proyecto · sesión suelta',''));
 for(const p of all)sel.append(new Option(p.title+' ('+p.linked_items+' entregables)',p.id));
 currentProject=all.some(p=>p.id===old)?old:'';sel.value=currentProject;
 await loadProject();
}
async function createProject(){
 const title=$('new-project-title').value.trim();if(!title){notice('Escribí el nombre del proyecto.',true);return}
 const p=await api('/api/sky/projects','POST',{title,description:$('new-project-desc').value.trim()});
 currentProject=p.id;$('new-project-title').value='';$('new-project-desc').value='';
 await loadProjects();notice('Proyecto creado: '+p.title);
}
async function loadProject(){
 const active=Boolean(currentProject);
 for(const id of ['export-project','save-project-note','refresh-project-messages','clear-project-messages','link-project-item'])$(id).disabled=!active;
 const panel=$('project-items');panel.replaceChildren();
 if(!active){$('project-summary').textContent='Sin proyecto seleccionado. Las tareas seguirán funcionando individualmente.';$('project-chat-history').replaceChildren();return}
 const p=await api('/api/sky/projects/'+encodeURIComponent(currentProject));
 $('project-summary').textContent=p.project.title+' · Versión '+p.project.version+' · '+p.items.length+' entregables asociados · '+p.notes_count+' notas privadas. '+p.project.description;
 if(!p.items.length)panel.append(el('p','Todavía no hay entregables relacionados. Generá una tarea desde el panel inferior.','muted'));
 for(const item of p.items){
  const row=el('article',undefined,'project-entry');row.append(el('strong',item.label));
  row.append(el('span',item.kind+' · '+(item.status||'guardado'),'status'));
  if(item.kind==='task'){
   const t=await api('/api/sky/tasks/'+encodeURIComponent(item.ref));
   if(t.status==='completada'&&t.output&&t.output.kind==='file'){
    const b=el('button','Descargar archivo');b.addEventListener('click',()=>fileDownload(item.ref,t.output.name).catch(e=>notice(e.message,true)));row.append(b);
   }
  }
  panel.append(row);
 }
 await loadProjectMessages();
}
async function loadProjectMessages(){
 const panel=$('project-chat-history');panel.replaceChildren();if(!currentProject)return;
 const m=await api('/api/sky/projects/'+encodeURIComponent(currentProject)+'/messages');
 if(!m.length){panel.append(el('p','Aún no se ha guardado una conversación para este proyecto.','muted'));return}
 for(const item of m){const line=el('div',undefined,'project-message');line.append(el('b',item.role==='user'?'Vos:':'SKY ('+item.provider+'):'));line.append(el('p',item.content));panel.append(line)}
}
async function exportProject(){
 if(!currentProject)return;
 const res=await fetch('/api/sky/projects/'+encodeURIComponent(currentProject)+'/export.zip',{headers:{'X-SKY-KEY':key}});
 if(!res.ok){let data={};try{data=await res.json()}catch(e){}throw Error(data.detail||'No se pudo exportar el proyecto')}
 const blob=await res.blob();const url=URL.createObjectURL(blob);const a=el('a');a.href=url;a.download='SKY_proyecto_'+currentProject+'.zip';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),2000);
}
async function linkProjectItem(){
 if(!currentProject)return;
 const kind=$('link-project-kind').value,ref=$('link-project-ref').value.trim(),label=$('link-project-title').value.trim();
 if(!ref||!label){notice('Necesitás el ID y un nombre para la creación.',true);return}
 await api('/api/sky/projects/'+encodeURIComponent(currentProject)+'/links','POST',{kind,ref,label});
 $('link-project-ref').value='';$('link-project-title').value='';await loadProject();notice('Creación existente vinculada al proyecto.');
}
async function saveProjectNote(){
 if(!currentProject)return;
 await api('/api/sky/projects/'+encodeURIComponent(currentProject)+'/notes','POST',{title:$('project-note-title').value.trim(),content:$('project-note-text').value.trim()});
 $('project-note-title').value='';$('project-note-text').value='';await loadProject();notice('Nota privada del proyecto guardada.');
}
async function clearProjectMessages(){
 if(!currentProject||!confirm('¿Eliminar el historial de conversación de este proyecto? Esta acción no se puede deshacer.'))return;
 await api('/api/sky/projects/'+encodeURIComponent(currentProject)+'/messages','DELETE');await loadProjectMessages();
}

function listen(){const SR=window.SpeechRecognition||window.webkitSpeechRecognition;if(!SR){notice('Este navegador no admite reconocimiento de voz. Escribí tu instrucción o utilizá el módulo de voz local.',true);return}const r=new SR();r.lang='es-NI';r.interimResults=false;r.onresult=e=>{$('intent').value=($('intent').value+' '+e.results[0][0].transcript).trim();resetPreview()};r.onerror=()=>notice('No se pudo reconocer la voz. Revisá permisos del micrófono.',true);r.start()}
function bind(id,fn){$(id).addEventListener('click',()=>Promise.resolve().then(fn).catch(e=>notice(e.message,true)))}
bind('link-project-item',linkProjectItem);bind('create-project',createProject);bind('refresh-projects',loadProjects);bind('export-project',exportProject);bind('save-project-note',saveProjectNote);bind('refresh-project-messages',loadProjectMessages);bind('clear-project-messages',clearProjectMessages);$('project-select').addEventListener('change',()=>{currentProject=$('project-select').value;loadProject().catch(e=>notice(e.message,true))});bind('login',login);$('key').addEventListener('keydown',e=>{if(e.key==='Enter')login()});bind('logout',()=>{key='';$('app').hidden=true;$('gate').hidden=false});bind('plan',plan);bind('ask',conversation);bind('voice',listen);bind('preview',preview);bind('save-experience',async()=>{await createTask('experience')});bind('download-html',()=>{if(previewHTML)downloadRaw(previewHTML,'SKY_Experience.html','text/html')});bind('prepare',()=>createTask());bind('reload',loadTasks);bind('reload-memory',memoryList);bind('refresh-activity',activity);bind('check-integrations',integrations);$('action').addEventListener('change',()=>{$('doc-panel').hidden=$('action').value!=='document';$('memory-panel').hidden=$('action').value!=='memory'});for(const b of document.querySelectorAll('[data-go]'))b.addEventListener('click',()=>document.getElementById(b.dataset.go).scrollIntoView({behavior:'smooth'}));for(const id of ['intent','design-title'])$(id).addEventListener('input',resetPreview);for(const id of ['template','palette'])$(id).addEventListener('change',resetPreview);drawNeurons();
})();
