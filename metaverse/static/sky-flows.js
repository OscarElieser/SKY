(()=>{'use strict';const $=id=>document.getElementById(id);let key='';
const AGENTS={planificador:'plan',creador_3d:'world',diseñador:'experience',documentalista:'document',memoria:'memory'};
function elem(tag,text,cls){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n}
async function req(url,method='GET',body){const opt={method,headers:{'X-SKY-KEY':key,...window.SKYOwnerAuth.headers()}};if(body!==undefined){opt.headers['Content-Type']='application/json';opt.body=JSON.stringify(body)}const r=await fetch(url,opt);const d=await r.json();if(!r.ok)throw Error(d.detail||r.statusText);return d}
function msg(x,err=false){$('message').textContent=x;$('message').style.color=err?'#ffaca7':'#85e8d5'}
function newStep(){if($('steps').children.length>=8){msg('Máximo 8 pasos por flujo.',true);return}const card=elem('div',undefined,'step-card');const bar=elem('div',undefined,'step-bar');const title=elem('h4','Paso '+($('steps').children.length+1));const del=elem('button','Quitar');del.addEventListener('click',()=>{card.remove();renumber()});bar.append(title,del);card.append(bar);
const select=elem('select');select.className='agent';for(const a of Object.keys(AGENTS)){const o=new Option(({planificador:'Planificación',creador_3d:'Crear mundo 3D',diseñador:'Crear diseño web',documentalista:'Crear documento',memoria:'Guardar memoria'}[a]),a);select.append(o)}
const agentLabel=elem('label','Especialidad');agentLabel.append(select);card.append(agentLabel);
const description=elem('textarea');description.className='task';description.rows=2;description.maxLength=3000;description.placeholder='Qué debe realizar SKY en este paso';const taskLabel=elem('label','Instrucción del paso');taskLabel.append(description);card.append(taskLabel);
const section=elem('div');section.className='step-options';card.append(section);
function update(){section.replaceChildren();const action=AGENTS[select.value];
 if(action==='document'){const kind=elem('select');kind.className='kind';for(const k of ['docx','pptx','pdf','xlsx','csv','md','html'])kind.append(new Option(k.toUpperCase(),k));const label=elem('label','Formato del archivo');label.append(kind);section.append(label);}
 if(action==='document'||action==='memory'){const field=elem('textarea');field.className='step-content';field.rows=3;field.placeholder=action==='document'?'Contenido real del documento; para Excel usá CSV con encabezados':'Texto que querés guardar en memoria';const label=elem('label','Contenido');label.append(field);section.append(label);}
}select.addEventListener('change',update);update();$('steps').append(card)}
function renumber(){[...$('steps').children].forEach((card,i)=>{card.querySelector('h4').textContent='Paso '+(i+1)})}
async function create(){const steps=[...$('steps').children].map(card=>{const agent=card.querySelector('.agent').value;const action=AGENTS[agent],task=card.querySelector('.task').value.trim();let params={};if(action==='world')params={name:task.slice(0,60),prompt:task};if(action==='experience')params={title:task.slice(0,90)};
 if(action==='document'){const kind=card.querySelector('.kind').value,txt=card.querySelector('.step-content').value;params={document:{kind,title:task.slice(0,120),content:kind==='xlsx'||kind==='csv'?'':txt,csv:kind==='xlsx'||kind==='csv'?txt:''}}}
 if(action==='memory')params={label:task.slice(0,80),content:card.querySelector('.step-content').value};return {agent,action,task,params}});
 const when=$('run-at').value;const data={name:$('flow-name').value.trim(),steps,project_id:$('project').value||null,run_at:when?new Date(when).toISOString():null,interval_minutes:$('interval').value?Number($('interval').value):null};
 const w=await req('/api/sky/workflows','POST',data);msg('Flujo creado: '+w.id+'. Aún NO se ejecuta. Confirmá la aprobación en Seguimiento.');await refresh();}
async function action(id,name,body){if(name==='approve') {
   const pre=await req('/api/sky/workflows/'+id+'/preview');
   const text=pre.steps.map(s=>s.number+'. '+s.agent+' / '+s.action+' — '+s.task+(s.references.length?' [usa '+s.references.join(', ')+']':'')).join('\n');
   if(!confirm('Revisá el plan antes de aprobar: \n'+text+'\n\nEste flujo no ejecuta pagos ni usa proveedores externos. ¿Autorizar?'))return;
   body={approve:true,expected_fingerprint:pre.fingerprint};
 }
 if(name==='retry'&&!confirm('¿Reintentar? Revisá antes si el paso anterior pudo crear algún resultado.'))return;
 if(name==='cancel'&&!confirm('¿Cancelar este flujo?'))return;
 const data=await req('/api/sky/workflows/'+id+'/'+name,'POST',body);msg('Flujo '+data.name+' · '+data.status);await refresh()}
async function fileDownload(id,filename){const r=await fetch('/api/sky/files/'+id,{headers:{'X-SKY-KEY':key,...window.SKYOwnerAuth.headers()}});if(!r.ok)throw Error('No se pudo recuperar el archivo');const url=URL.createObjectURL(await r.blob());const a=elem('a');a.href=url;a.download=filename;a.click();setTimeout(()=>URL.revokeObjectURL(url),2000)}
async function refresh(){const jobs=await req('/api/sky/workflows');const root=$('jobs');root.replaceChildren();if(!jobs.length){root.append(elem('p','No hay flujos creados todavía.'));return}
 for(const job of jobs){const card=elem('article',undefined,'workflow-card');const head=elem('div',undefined,'workflow-title');head.append(elem('h3',job.name),elem('span',job.status,'flow-status'));card.append(head);card.append(elem('p','Pasos: '+job.current_step+'/'+job.steps.length+' · Ejecución '+job.run_number+(job.interval_minutes?' · cada '+job.interval_minutes+' min':'')+' · '+job.id));if(job.last_error)card.append(elem('p','Último error: '+job.last_error));
 const buttons=elem('div',undefined,'workflow-buttons');const b=(title,fn)=>{const el=elem('button',title);el.addEventListener('click',()=>fn().catch(e=>msg(e.message,true)));buttons.append(el)};
 if(job.status==='awaiting_approval')b('✓ Revisar y autorizar',()=>action(job.id,'approve',{approve:true}));
 if(['scheduled','retry_wait'].includes(job.status))b('⏸ Pausar',()=>action(job.id,'pause'));
 if(job.status==='paused')b('▶ Reanudar',()=>action(job.id,'resume'));
 if(['scheduled','retry_wait','paused','failed','needs_review','awaiting_approval'].includes(job.status))b('Cancelar',()=>action(job.id,'cancel'));
 if(['failed','needs_review'].includes(job.status))b('Reintentar con revisión',()=>action(job.id,'retry',{acknowledge_partial_effects:true}));
 b('Ver historial',async()=>{const ev=await req('/api/sky/workflows/'+job.id+'/events');const display=card.querySelector('.flow-events')||elem('div',undefined,'flow-events');display.textContent=ev.map(x=>x.at+' · '+x.event+' · '+x.detail).join('\n')||'Sin eventos';card.append(display)});
 for(const result of job.results){if(result.result?.kind==='file'){b('Descargar '+result.result.name,()=>fileDownload(result.item_id,result.result.name))}}
 card.append(buttons);root.append(card)} }
async function continuity(){
 const pid=$('project').value,root=$('continuity-summary');root.replaceChildren();
 if(!pid){root.append(elem('p','Elegí primero un proyecto.'));return}
 const report=await req('/api/sky/projects/'+encodeURIComponent(pid)+'/continuity');
 root.append(elem('p',report.project.title+' · '+report.deliverables.length+' entregables · '+report.workflows.length+' flujos'));
 for(const item of report.deliverables.slice(-12)){root.append(elem('p',item.kind+' · '+item.label+' · '+item.status));}
 for(const flow of report.workflows.slice(0,12)){root.append(elem('p','Flujo '+flow.name+' · '+flow.status+' · '+flow.progress.done+'/'+flow.progress.total));}
}
$('continuity-refresh').addEventListener('click',()=>continuity().catch(e=>msg(e.message,true)));
$('login').addEventListener('click',async()=>{key=$('key').value.trim();await window.SKYOwnerAuth.begin(key);try{const val=await req('/api/sky/workflows/status');$('gate').hidden=true;$('content').hidden=false;$('key').value='';$('engine-state').textContent=val.engine+' · '+val.persistence;
 const projects=await req('/api/sky/projects');for(const p of projects)$('project').append(new Option(p.title,p.id));await refresh();if(!$('steps').children.length)newStep();}
 catch(e){key='';$('gate-error').textContent='Clave incorrecta o servidor no disponible.'}});
$('key').addEventListener('keydown',e=>{if(e.key==='Enter')$('login').click()});$('add-step').addEventListener('click',newStep);$('create').addEventListener('click',()=>create().catch(e=>msg(e.message,true)));$('refresh').addEventListener('click',()=>refresh().catch(e=>msg(e.message,true)));
})();
