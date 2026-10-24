(()=>{'use strict';
const $=id=>document.getElementById(id);
let mode='owner',ownerKey='',userToken='',authType='owner',activeRequest=null,progressTimer=null;
let attachedFiles=[]; // [{ filename, size, media_type, media_url, summary, full_text }]

// Storage y Memoria Local de Conversaciones (Estilo ChatGPT)
const CHAT_HISTORY_KEY='sky_chat_history_v1';
let currentChatId=Date.now().toString();
let currentChatMessages=[];

function getStoredChats(){
  try{
    return JSON.parse(localStorage.getItem(CHAT_HISTORY_KEY)||'[]');
  }catch(e){return [];}
}

function saveStoredChats(list){
  try{
    localStorage.setItem(CHAT_HISTORY_KEY, JSON.stringify(list));
  }catch(e){}
}

function persistCurrentChat(){
  if(!currentChatMessages.length)return;
  const chats=getStoredChats();
  const firstUserMsg=currentChatMessages.find(m=>m.who==='Tú');
  const title=firstUserMsg?(firstUserMsg.rawText||firstUserMsg.txt).slice(0,32):'Conversación SKY';
  const existingIdx=chats.findIndex(c=>c.id===currentChatId);
  const record={
    id:currentChatId,
    title:title.replace(/\n/g,' ')+(title.length>=32?'...':''),
    timestamp:Date.now(),
    dateStr:new Date().toLocaleTimeString([],{hour:'2-digit',minute:'2-digit'}),
    messages:currentChatMessages
  };
  if(existingIdx>=0){
    chats[existingIdx]=record;
  }else{
    chats.unshift(record);
  }
  // Limitar a las últimas 40 conversaciones
  saveStoredChats(chats.slice(0,40));
  renderHistoryUI();
}

function renderHistoryUI(){
  const container=$('history-list');
  if(!container)return;
  const chats=getStoredChats();
  if(!chats.length){
    container.innerHTML='<div style="font-size:12px; color:#64748b; padding:8px 12px;">Sin conversaciones previas</div>';
    return;
  }
  container.replaceChildren();
  chats.forEach(c=>{
    const item=document.createElement('div');
    item.className='history-item'+(c.id===currentChatId?' active':'');
    
    const icon=document.createElement('span');
    icon.className='hist-icon';
    icon.textContent='💬';

    const titleSpan=document.createElement('span');
    titleSpan.className='hist-title';
    titleSpan.textContent=c.title;
    titleSpan.title=c.title;

    const delBtn=document.createElement('button');
    delBtn.type='button';
    delBtn.className='hist-del';
    delBtn.textContent='×';
    delBtn.title='Eliminar del historial';
    delBtn.onclick=(ev)=>{
      ev.stopPropagation();
      const updated=getStoredChats().filter(x=>x.id!==c.id);
      saveStoredChats(updated);
      if(c.id===currentChatId){
        startNewChat();
      }else{
        renderHistoryUI();
      }
    };

    item.append(icon,titleSpan,delBtn);
    item.onclick=()=>loadChat(c.id);
    container.append(item);
  });
}

function loadChat(id){
  const chats=getStoredChats();
  const found=chats.find(c=>c.id===id);
  if(!found)return;
  currentChatId=found.id;
  currentChatMessages=found.messages||[];
  const conv=$('conversation');
  conv.replaceChildren();
  currentChatMessages.forEach(m=>{
    renderMessageBubble(m.who,m.txt,m.isHtml);
  });
  renderHistoryUI();
  closeSidebar();
}

function startNewChat(){
  persistCurrentChat();
  currentChatId=Date.now().toString();
  currentChatMessages=[];
  attachedFiles=[];
  renderAttachedChips();
  const conv=$('conversation');
  conv.replaceChildren();
  const initialText='Hola, soy SKY. Contame qué querés crear, investigar u organizar. Tus herramientas y documentos están disponibles cuando los necesitás.';
  renderMessageBubble('SKY',initialText,false);
  renderHistoryUI();
  closeSidebar();
}

// Formateador limpio para SKY: Emojis dinámicos, separación visual de secciones y viñetas ordenadas
function formatSkyText(text){
  if(!text) return '';
  let t = text;

  // 1. Encabezados markdown (#, ##, ###, ####, #####)
  t = t.replace(/^#####\s+(.*$)/gim, '<div style="font-weight:700; color:#93c5fd; margin:10px 0 4px; font-size:14px;">🔹 $1</div>');
  t = t.replace(/^####\s+(.*$)/gim, '<div style="font-weight:700; color:#7dedff; margin:12px 0 4px; font-size:15px;">🔹 $1</div>');
  t = t.replace(/^###\s+(.*$)/gim, '<div style="font-weight:700; color:#38bdf8; font-size:16px; margin:14px 0 6px;">📌 $1</div>');
  t = t.replace(/^##\s+(.*$)/gim, '<div style="font-weight:800; color:#38bdf8; font-size:17px; margin:16px 0 6px;">🚀 $1</div>');
  t = t.replace(/^#\s+(.*$)/gim, '<div style="font-weight:800; color:#60a5fa; font-size:18px; margin:18px 0 8px;">✨ $1</div>');

  // 2. Limpiar asteriscos crudos y aplicar negritas / cursivas
  t = t.replace(/\*{3,}/g, '');
  t = t.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
  t = t.replace(/__(.*?)__/g, '<strong>$1</strong>');
  t = t.replace(/\*([^\*]+)\*/g, '<em>$1</em>');

  // 3. Detectar títulos emoji de secciones estructuradas (ej: 📌 DATOS E INCÓGNITA, 💡 REGLAS, 🔹 PROCEDIMIENTO, ✅ RESULTADO, 🔍 COMPROBACIÓN)
  t = t.replace(/(?:^|\n|[•·]\s*)([📌💡🔹🔷🔶✅🔍🚀👑⭐⚡])\s*([A-ZÁÉÍÓÚÑ0-9\s]{3,}:?)/g, function(match, icon, title){
    return `<div style="margin:16px 0 8px; font-weight:700; color:#38bdf8; font-size:15px; display:flex; align-items:center; gap:8px; border-bottom:1px solid rgba(56,189,248,0.25); padding-bottom:4px;"><span style="font-size:16px;">${icon}</span><span style="color:#f1f5f9; letter-spacing:0.5px;">${title.trim()}</span></div>`;
  });

  // 4. Elementos de lista con viñeta (• o - )
  t = t.replace(/(?:^|\n|[•·])\s*([A-Za-z0-9][^•\n]{6,}?)(?=\s*[•·]|\s*$|\n)/gim, function(match, itemText){
    if(itemText.includes('<div') || itemText.includes('<strong>📌') || itemText.startsWith('★')) return match;
    return `<div style="margin:4px 0 4px 12px; display:flex; align-items:flex-start; gap:8px;"><span style="color:#38bdf8; font-weight:bold;">•</span><span style="flex:1;">${itemText.trim()}</span></div>`;
  });

  // 5. Listas numeradas (1. , 2. , 3. )
  t = t.replace(/(?:^|\n)(\d+)\.\s+(.*$)/gim, '<div style="margin:6px 0 6px 12px; display:flex; align-items:flex-start; gap:8px;"><span style="background:#1e3a5f; color:#38bdf8; border-radius:50%; width:22px; height:22px; display:inline-flex; align-items:center; justify-content:center; font-size:11px; font-weight:bold; flex-shrink:0;">$1</span><span style="flex:1;">$2</span></div>');

  // 6. Separadores y saltos
  t = t.replace(/^---\s*$/gim, '<hr style="border:none; border-top:1px solid #1e3650; margin:14px 0;">');
  t = t.replace(/^===\s*$/gim, '');
  t = t.replace(/\n\n+/g, '<div style="height:10px;"></div>');
  t = t.replace(/\n/g, '<br>');

  return t.trim();
}


function renderMessageBubble(who,txt,isHtml=false){
  const p=document.createElement('div');
  p.className='bubble '+(who==='SKY'?'sky-bubble':'user-bubble');
  if(isHtml){
    p.innerHTML=txt;
  } else {
    if(who==='SKY'){
      p.innerHTML=formatSkyText(txt);
    } else {
      p.textContent=txt;
    }
  }
  $('conversation').append(p);
  // Renderizado formal KaTeX para fórmulas matemáticas ($...$ y $$...$$)
  if(window.renderMathInElement){
    try{
      window.renderMathInElement(p, {
        delimiters: [
          {left: '$$', right: '$$', display: true},
          {left: '$', right: '$', display: false}
        ],
        throwOnError: false
      });
    }catch(e){}
  }
  p.scrollIntoView({block:'end',behavior:'smooth'});
}

const msg=(who,txt,isHtml=false,rawText='')=>{
  renderMessageBubble(who,txt,isHtml);
  currentChatMessages.push({who,txt,isHtml,rawText:rawText||txt});
  persistCurrentChat();
};

const buildLink=(label,url)=>{const a=document.createElement('a');a.href=url;a.textContent=label;return a};
const skyHeaders=()=>({'X-SKY-KEY':ownerKey,'Content-Type':'application/json',...(window.SKYOwnerAuth?window.SKYOwnerAuth.headers():{})});

async function apiPost(url,data){
  const r=await fetch(url,{method:'POST',headers:skyHeaders(),body:JSON.stringify(data)});
  const d=await r.json();
  if(!r.ok)throw Error(d.detail||'Error del servidor');
  return d;
}

async function skyGet(url){
  const r=await fetch(url,{headers:{'X-SKY-KEY':ownerKey,...(window.SKYOwnerAuth?window.SKYOwnerAuth.headers():{})}});
  const d=await r.json();
  if(!r.ok)throw Error(d.detail||'Error del servidor');
  return d;
}

async function savePrivate(url,filename){
  const r=await fetch(url,{headers:{'X-SKY-KEY':ownerKey,...(window.SKYOwnerAuth?window.SKYOwnerAuth.headers():{})}});
  if(!r.ok)throw Error('No se pudo descargar el archivo');
  const blob=await r.blob();
  const link=document.createElement('a');
  const object=URL.createObjectURL(blob);
  link.href=object;link.download=filename;document.body.append(link);link.click();link.remove();
  setTimeout(()=>URL.revokeObjectURL(object),2000);
}

function actionButton(text,handler,extraClass=''){
  const b=document.createElement('button');b.type='button';b.textContent=text;if(extraClass)b.className=extraClass;
  b.addEventListener('click',async()=>{b.disabled=true;try{await handler()}catch(e){msg('SKY','Operación no completada: '+e.message)}finally{b.disabled=false}});
  return b;
}

function resetWork(){
  if(progressTimer){clearInterval(progressTimer);progressTimer=null}
  activeRequest=null;$('workspace-activity').hidden=true;
  $('workspace-details').replaceChildren();$('workspace-actions').replaceChildren();
}

function renderWork(d){
  activeRequest=d.id;
  const panel=$('workspace-activity'),details=$('workspace-details'),actions=$('workspace-actions');
  panel.hidden=false;details.replaceChildren();actions.replaceChildren();
  const title=document.createElement('h2');title.textContent=d.name;details.append(title);
  const status=document.createElement('div');status.className='state';
  status.textContent='SKY Workspace · '+({'awaiting_approval':'Plan pendiente de aprobación','scheduled':'Programado','running':'Trabajando','completed':'Completado','needs_review':'Requiere revisión','paused':'Pausado','failed':'Revisar error','cancelled':'Cancelado','retry_wait':'Reintentando'}[d.status]||d.status);
  details.append(status);
  const summary=document.createElement('p');summary.textContent=d.requires_approval?'Revisá lo que SKY va a producir. El siguiente paso requiere tu autorización.':'Progreso del flujo y entregables vinculados a tu proyecto.';details.append(summary);
  const prog=document.createElement('progress');prog.max=100;prog.value=d.completed_percent||0;details.append(prog);
  const pct=document.createElement('p');pct.textContent=`${d.completed_percent||0}% de etapas completadas`;details.append(pct);
  const stages=document.createElement('ol');for(const step of d.stages){const li=document.createElement('li');li.textContent=step.description;stages.append(li)}details.append(stages);
  if(d.error){const warn=document.createElement('p');warn.className='warning';warn.textContent='Revisar: '+d.error;details.append(warn)}
  if(d.deliverables?.length){const row=document.createElement('div');row.className='workspace-files';for(const file of d.deliverables){if(file.kind==='file'&&file.download)row.append(actionButton('↓ '+file.name,()=>savePrivate(file.download,file.name)));if(file.kind==='world'&&file.world_id)row.append(actionButton('🌐 Mundo 3D',()=>{location.href='/world'}));if(file.kind==='experience'&&file.design_id)row.append(actionButton('✦ Diseño web',()=>savePrivate('/api/sky/experiences/'+encodeURIComponent(file.design_id)+'/html','SKY_experiencia.html')))}details.append(row)}
  if(d.requires_approval){
    actions.append(actionButton('Editar este plan',()=>{
      const holder=document.createElement('div');holder.className='inline-edit';
      const field=document.createElement('textarea');field.rows=3;field.maxLength=1500;
      field.placeholder='¿Qué querés añadir o corregir antes de aprobar?';holder.append(field);
      holder.append(actionButton('Guardar cambios al plan',async()=>{
        const next=await apiPost('/api/sky/intelligent/requests/'+encodeURIComponent(d.id)+'/revise-plan',{instruction:field.value.trim(),expected_fingerprint:d.fingerprint});
        renderWork(next);msg('SKY','Plan actualizado.');
      }));
      actions.replaceChildren(holder);field.focus();
    },'secondary'));
    actions.append(actionButton('Aprobar y ejecutar',async()=>{
      const next=await apiPost('/api/sky/intelligent/requests/'+encodeURIComponent(d.id)+'/approve',{approve:true,expected_fingerprint:d.fingerprint});
      renderWork(next);msg('SKY','Aprobación registrada. SKY está ejecutando las etapas locales.');beginPolling(d.id);
    }));
  }
  if(d.status==='completed'){
    for(const file of (d.deliverables||[])){
      if(!file.item_id)continue;
      actions.append(actionButton('Preparar revisión',async()=>{
        msg('SKY','Preparando revisión para '+file.name);
      },'secondary'));
    }
  }
}

function beginPolling(id){
  if(progressTimer)clearInterval(progressTimer);
  progressTimer=setInterval(async()=>{
    if(activeRequest!==id){clearInterval(progressTimer);progressTimer=null;return}
    try{
      const d=await skyGet('/api/sky/intelligent/requests/'+encodeURIComponent(id));
      renderWork(d);
      if(['completed','failed','needs_review','cancelled'].includes(d.status)){
        clearInterval(progressTimer);progressTimer=null;
        msg('SKY',d.status==='completed'?'El flujo terminó. Podés revisar los entregables en tu pantalla.':'El flujo se detuvo; revisá el estado.')
      }
    }catch(e){clearInterval(progressTimer);progressTimer=null;}
  },2600);
}

// Iniciar sesión automática de Superadmin desde localhost
async function autoBootstrap(){
  try{
    const r=await fetch('/api/client/bootstrap');
    if(r.ok){
      const d=await r.json();
      if(d.key){
        ownerKey=d.key;
        mode='owner';
        updateEvolutionStats();
        return;
      }
    }
  }catch(e){}
  mode='owner';
  updateEvolutionStats();
}

// Estado de evolución neural y memoria continua
async function updateEvolutionStats(){
  try{
    const headers=ownerKey?{'X-SKY-KEY':ownerKey,...(window.SKYOwnerAuth?window.SKYOwnerAuth.headers():{})}:{};
    const r=await fetch('/api/evolution/stats',{headers});
    if(r.ok){
      const d=await r.json();
      const memCount=$('modal-mem-count');
      const docCount=$('modal-doc-count');
      const intCount=$('modal-int-count');
      if(memCount) memCount.textContent=`${d.total_memories||0} unidades registradas`;
      if(docCount) docCount.textContent=`${d.total_documents||0} archivos asimilados`;
      if(intCount) intCount.textContent=`${d.total_interactions||0} ciclos completados`;
    }
  }catch(e){}
}

// Control de Sidebar y Menú ChatGPT
const sidebar=$('sidebar');
function openSidebar(){
  if(sidebar) sidebar.classList.add('open');
}
function closeSidebar(){
  if(sidebar) sidebar.classList.remove('open');
}
$('sidebar-toggle')?.addEventListener('click',()=>sidebar.classList.toggle('open'));
$('sidebar-close')?.addEventListener('click',closeSidebar);
$('btn-new-chat')?.addEventListener('click',startNewChat);
$('top-new-chat')?.addEventListener('click',startNewChat);

// Modal de Configuración y Perfil
const settingsModal=$('settings-modal');
function openSettingsModal(){
  if(settingsModal){
    settingsModal.hidden=false;
    updateEvolutionStats();
  }
}
function closeSettingsModal(){
  if(settingsModal) settingsModal.hidden=true;
}

$('user-profile-card')?.addEventListener('click',openSettingsModal);
$('btn-settings')?.addEventListener('click',(e)=>{
  e.stopPropagation();
  openSettingsModal();
});
$('settings-close')?.addEventListener('click',closeSettingsModal);
settingsModal?.addEventListener('click',e=>{
  if(e.target===settingsModal) closeSettingsModal();
});

// Pestañas del Modal
document.querySelectorAll('.tab-btn').forEach(btn=>{
  btn.addEventListener('click',()=>{
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    document.querySelectorAll('.tab-content').forEach(c=>c.classList.remove('active'));
    btn.classList.add('active');
    const targetId=btn.getAttribute('data-tab');
    const targetContent=$(targetId);
    if(targetContent) targetContent.classList.add('active');
  });
});

// Gestión de archivos adjuntos (Videos, Música, Documentos, Código, Imágenes...)
function renderAttachedChips(){
  const container=$('attached-chips');
  if(!container)return;
  if(!attachedFiles.length){
    container.classList.add('is-hidden');
    container.replaceChildren();
    return;
  }
  container.classList.remove('is-hidden');
  container.replaceChildren();
  attachedFiles.forEach((f,idx)=>{
    const chip=document.createElement('div');
    chip.className='file-chip';
    const icon=document.createElement('span');
    const ext=f.filename.toLowerCase();
    if(ext.match(/\.(mp4|mov|avi|mkv|webm)$/)) icon.textContent='🎬';
    else if(ext.match(/\.(mp3|wav|ogg|m4a|flac|aac)$/)) icon.textContent='🎵';
    else if(ext.endsWith('.pdf')) icon.textContent='📕';
    else if(ext.match(/\.(xlsx|xls|csv)$/)) icon.textContent='📊';
    else if(ext.match(/\.(docx|doc|pptx)$/)) icon.textContent='📘';
    else if(ext.match(/\.(png|jpg|jpeg|webp|gif|bmp)$/)) icon.textContent='🖼️';
    else icon.textContent='📄';

    const name=document.createElement('span');
    name.className='chip-name';
    name.textContent=f.filename;
    name.title=f.filename;
    const size=document.createElement('span');
    size.className='chip-size';
    size.textContent=`(${Math.round(f.size/1024)} KB)`;
    const btnRemove=document.createElement('button');
    btnRemove.type='button';
    btnRemove.className='chip-remove';
    btnRemove.textContent='×';
    btnRemove.title='Quitar archivo';
    btnRemove.onclick=()=>{
      attachedFiles.splice(idx,1);
      renderAttachedChips();
    };
    chip.append(icon,name,size,btnRemove);
    container.append(chip);
  });
}

const skyEscapeHtml=(value)=>String(value??'').replace(/[&<>"']/g,
  c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const skyCanIndex=(name)=>/\.(pdf|docx|pptx|xlsx|txt|md|csv|tsv|json|xml|yaml|yml|py|js|ts|dart|html|css|sql)$/i.test(name);
const skySafePreviewUrl=(url)=>typeof url==='string'&&
  /^\/api\/media\/uploads\/[a-f0-9]{32}\.(png|jpg|jpeg|webp|mp4|mov|mkv|webm|mp3|wav|m4a|flac|ogg)\?expires=\d+&sig=[a-f0-9]{64}$/.test(url)
  ?skyEscapeHtml(url):'';
const attachInput=$('attach-input');
const btnAttach=$('btn-attach');
if(btnAttach&&attachInput){
  btnAttach.addEventListener('click',()=>attachInput.click());
  attachInput.addEventListener('change',async e=>{
    const files=Array.from(e.target.files||[]);
    if(!files.length)return;
    for(const file of files){
      const formData=new FormData();
      formData.append('file',file);
      const remember=Boolean($('remember-documents')?.checked&&skyCanIndex(file.name));
      if(remember){
        formData.append('remember_document','true');
        formData.append('owner_attested','true');
      }
      try{
        msg('SKY',`📥 Analizando ${file.name}${remember?' y guardando con autorización':''}...`);
        const r=await fetch('/api/chat/upload',{
          method:'POST',
          headers:ownerKey?{'X-SKY-KEY':ownerKey,...(window.SKYOwnerAuth?window.SKYOwnerAuth.headers():{})}:{},
          body:formData
        });
        const d=await r.json();
        if(r.ok&&d.ok){
          attachedFiles.push({
            filename:d.filename,
            size:d.size_bytes,
            media_type:d.media_type,
            media_url:d.media_url,
            summary:d.summary,
            full_text:d.full_text
          });
          renderAttachedChips();

          let mediaPreview='';
          const safeUrl=skySafePreviewUrl(d.media_url);
          if(d.media_type==='video'&&safeUrl){
            mediaPreview=`<div style="margin-top:8px;"><video controls src="${safeUrl}" style="max-width:100%; max-height:220px; border-radius:10px;"></video></div>`;
          }else if(d.media_type==='audio'&&safeUrl){
            mediaPreview=`<div style="margin-top:8px;"><audio controls src="${safeUrl}" style="width:100%;"></audio></div>`;
          }else if(d.media_type==='image'&&safeUrl){
            mediaPreview=`<div style="margin-top:8px;"><img src="${safeUrl}" style="max-width:100%; max-height:200px; border-radius:10px;" /></div>`;
          }

          const memoryStatus=d.doc_id ? 'Guardado en la biblioteca cifrada con tu autorización. Podés decir «SKY, buscá en mis documentos sobre…».' : 'Leído para esta conversación; no se guardó como memoria permanente.';
          msg('SKY',`✅ Archivo <strong>${skyEscapeHtml(d.filename)}</strong> analizado.<br>📁 Tipo: ${skyEscapeHtml(d.media_type.toUpperCase())} · Tamaño: ${(d.size_bytes/1024).toFixed(1)} KB.${mediaPreview}<br>${memoryStatus}`,true);
          updateEvolutionStats();
        }else{
          msg('SKY',`⚠️ Error al procesar ${file.name}: `+(d.detail||'no procesable'));
        }
      }catch(err){
        msg('SKY',`⚠️ No se pudo adjuntar ${file.name}: `+err.message);
      }
    }
    attachInput.value='';
  });
}

// Chat principal: SKY es el referente central
$('chat-form').addEventListener('submit',async e=>{
  e.preventDefault();
  const text=$('prompt').value.trim();
  if(!text&&!attachedFiles.length)return;
  $('prompt').value='';
  
  // Resumen del prompt para el usuario
  let userDisplay=text;
  if(attachedFiles.length){
    const fileList=attachedFiles.map(f=>`📎 ${f.filename}`).join(', ');
    userDisplay=(text?text+'\n':'')+`[Archivos adjuntos: ${fileList}]`;
  }
  msg('Tú',userDisplay,false,text);
  $('send').disabled=true;

  // Contexto de archivos adjuntos para SKY
  let fileContext='';
  if(attachedFiles.length>0){
    fileContext=attachedFiles.map(f=>`=== ARCHIVO: ${f.filename} (Tipo: ${f.media_type}) ===\n${f.full_text}`).join('\n\n');
  }

  try{
    const lower=text.toLowerCase();
    
    // Herramienta A: Generación de Video Autónomo (1, 3, 5, 8 o 10 minutos)
    if(lower.startsWith('video') || lower.includes('crea un video') || lower.includes('genera un video') || lower.includes('haz un video') || lower.includes('crear un video')){
      let dur=1;
      const m=text.match(/(\d+)\s*minuto/i);
      if(m){
        dur=parseInt(m[1],10);
      }
      msg('SKY',`🎬 Generando video de ${dur} minuto(s) coordinado por SKY...`,true);
      try {
        const rVid=await fetch('/api/tools/video',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({prompt:text,minutes:dur})
        });
        const dVid=await rVid.json();
        if(rVid.ok&&dVid.ok){
          const card=`<div style="text-align:center;">
            <div style="font-weight:700; color:#38bdf8; margin-bottom:8px;">🎬 Video Generado (${dVid.duration_minutes} min · ${dVid.resolution}):</div>
            <video controls autoplay loop src="${dVid.url}" style="max-width:100%; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.5);"></video>
            <div style="margin-top:8px;"><a href="${dVid.url}" download="${dVid.filename}" style="color:#7dedff; text-decoration:underline; font-size:12px;">⬇ Descargar archivo de video MP4 (${(dVid.size_bytes/1024/1024).toFixed(2)} MB)</a></div>
            <div style="font-size:11px; color:#94a3b8; margin-top:6px;">✦ Cómputo audiovisual procesado por SKY · Duración: ${dVid.duration_minutes} min</div>
          </div>`;
          msg('SKY',card,true);
          attachedFiles=[];renderAttachedChips();
          $('send').disabled=false;
          return;
        }
      }catch(eVid){}
    }

    // Herramienta B: Generación de Imagen (Flux / Puter.js) con guardado local
    if(lower.startsWith('dibuja') || lower.startsWith('genera una imagen') || lower.startsWith('crea una imagen') || lower.includes('generar una imagen')){
      msg('SKY','🎨 Generando imagen con los motores integrados de SKY...');
      try {
        const rImg=await fetch('/api/tools/image',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({prompt:text})
        });
        const dImg=await rImg.json();
        if(dImg.ok&&dImg.result&&dImg.result.length){
          const imgUrl=dImg.local_url||dImg.result[0];
          const card=`<div style="text-align:center;">
            <div style="font-weight:600; color:#38bdf8; margin-bottom:8px;">🎨 Imagen generada por SKY:</div>
            <img src="${imgUrl}" style="max-width:100%; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.5);" onerror="this.onerror=null;this.src='${dImg.result[0]}';" />
            <div style="font-size:11px; color:#94a3b8; margin-top:6px;">✦ Cómputo ejecutado y asegurado localmente · Orquestado por SKY</div>
          </div>`;
          msg('SKY',card,true);
          attachedFiles=[];renderAttachedChips();
          $('send').disabled=false;
          return;
        }
      }catch(e){}

      if(window.puter&&window.puter.ai&&window.puter.ai.txt2img){
        const imgElement=await window.puter.ai.txt2img(text);
        const holder=document.createElement('div');
        holder.className='bubble sky-bubble';
        holder.style.textAlign='center';
        imgElement.style.maxWidth='100%';
        imgElement.style.borderRadius='12px';
        imgElement.style.marginTop='8px';
        imgElement.style.boxShadow='0 4px 20px rgba(0,0,0,0.5)';
        holder.innerHTML=`<div><strong>Resultado visual coordinado por SKY:</strong></div>`;
        holder.append(imgElement);
        $('conversation').append(holder);
        holder.scrollIntoView({block:'end',behavior:'smooth'});
        attachedFiles=[];renderAttachedChips();
        $('send').disabled=false;
        return;
      }
    }

    // Herramienta C: Búsqueda Web en Vivo coordinada por SKY
    if(lower.startsWith('busca') || lower.startsWith('noticias') || lower.includes('en internet')){
      try {
        msg('SKY','🔍 Consultando búsqueda web en tiempo real...');
        const rSearch=await fetch('/api/tools/search',{
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body:JSON.stringify({query:text})
        });
        const dSearch=await rSearch.json();
        if(dSearch.ok&&dSearch.results){
          let linksHtml=dSearch.results.slice(0,4).map(res=> 
            `<div style="margin-top:8px; padding:8px; background:#071a2b; border-radius:8px;">
              <a href="${res.url}" target="_blank" style="color:#38bdf8; font-weight:600; text-decoration:none;">${res.title}</a>
              <p style="margin:4px 0 0; font-size:12px; color:#cbd5e1;">${res.content.slice(0,160)}...</p>
            </div>`
          ).join('');
          const searchCard=`<div>
            <div style="font-weight:600; color:#10b981;">🌐 Hallazgos web organizados por SKY:</div>
            ${linksHtml}
            <div style="font-size:11px; color:#94a3b8; margin-top:8px;">✦ Búsqueda en vivo completada · Conocimiento asimilado</div>
          </div>`;
          msg('SKY',searchCard,true);
          attachedFiles=[];renderAttachedChips();
          $('send').disabled=false;
          return;
        }
      }catch(e){}
    }

    // Herramienta D: Sensores y Telemetría de Hardware Real (Solo cuando el usuario solicita explícitamente ver sensores en UI)
    const isExplicitTelemetry = /^(telemetria|sensores?|estado de sensores|leer sensores|telemetria en vivo|ver telemetria|panel de telemetria|ver sensores)$/i.test(text.trim()) ||
      /^(mostrar|ver|consultar|leer)\s+(la\s+)?(telemetr[ií]a|sensores|lecturas?\s+de\s+sensores)$/i.test(text.trim());
    if(isExplicitTelemetry){
      try{
        const rSens=await fetch('/api/telemetria/latest');
        const dSens=await rSens.json();
        if(dSens.lectura){
          const card=`
            <div style="background:#091d30; border:1px solid #38bdf8; border-radius:12px; padding:14px; margin-top:6px;">
              <div style="font-weight:bold; color:#38bdf8; margin-bottom:8px;">📡 Telemetría en Vivo de Sensores Reales:</div>
              <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(110px, 1fr)); gap:10px;">
                <div>🌡️ Temp: <strong>${dSens.lectura.temperatura_c}°C</strong></div>
                <div>〰️ Vib: <strong>${dSens.lectura.vibracion_mm_s} mm/s</strong></div>
                <div>🔄 RPM: <strong>${dSens.lectura.rpm}</strong></div>
                <div>⚡ Amp: <strong>${dSens.lectura.corriente_a} A</strong></div>
                <div>⏱️ Bar: <strong>${dSens.lectura.presion_bar} Bar</strong></div>
              </div>
              <div style="margin-top:10px; font-size:12px;"><a href="http://127.0.0.1:8501" target="_blank" style="color:#7dedff; text-decoration:underline;">Ver Núcleo Neuronal 60FPS en Panel de Sensores ➔</a></div>
            </div>`;
          msg('SKY',card,true);
          attachedFiles=[];renderAttachedChips();
          $('send').disabled=false;
          return;
        }
      }catch(e){}
    }
    // Herramienta D2: SKY SPORTS CENTER · REAL MADRID (Activación por orden expresa)
    const isWatchRealMadrid = /(mu[eé]strame\s+(?:el\s+)?partido|ver\s+(?:el\s+)?partido|partido\s+en\s+vivo|pon(?:er)?\s+(?:el\s+)?partido|ver\s+al\s+real\s+madrid|sports\s+center)/i.test(text.trim()) && /madrid|real\s+madrid|sports/i.test(text.trim());
    if(isWatchRealMadrid){
      try{
        const rMatch = await fetch('/api/sports/madrid/match');
        const dMatch = await rMatch.json();
        if(dMatch.ok && dMatch.partido){
          const p = dMatch.partido;
          const sportsCard = `
            <div style="background:linear-gradient(135deg, #0b1d33 0%, #172a45 100%); border:1px solid #60a5fa; border-radius:14px; padding:16px; margin-top:8px; box-shadow:0 8px 30px rgba(0,0,0,0.45);">
              <div style="display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1e3a5f; padding-bottom:10px; margin-bottom:12px;">
                <div style="font-weight:800; color:#ffffff; font-size:16px; display:flex; align-items:center; gap:8px;">
                  👑 <span>SKY SPORTS CENTER · REAL MADRID</span>
                </div>
                <span style="background:#1d4ed8; color:#ffffff; font-size:11px; padding:3px 9px; border-radius:12px; font-weight:700;">📺 SEÑAL OFICIAL</span>
              </div>
              <div style="background:#06101e; border:1px solid #2563eb; border-radius:10px; padding:12px; margin-bottom:12px; text-align:center;">
                <div style="font-size:13px; color:#93c5fd; font-weight:600; text-transform:uppercase; margin-bottom:4px;">${p.competicion}</div>
                <div style="font-size:18px; font-weight:800; color:#ffffff; margin:6px 0;">
                  👑 Real Madrid <span style="color:#60a5fa; margin:0 8px;">VS</span> ${p.rival}
                </div>
                <div style="font-size:12px; color:#cbd5e1; margin-top:4px;">
                  📅 ${p.fecha} · 🕒 ${p.hora_nicaragua} (Hora de Nicaragua) | 🏟️ ${p.estadio}
                </div>
              </div>

              <!-- SELECTOR DE SEÑALES ESTILO FÚTBOL LIBRE FULL HD -->
              <div style="margin-bottom:10px;">
                <div style="font-size:11px; font-weight:700; color:#38bdf8; text-transform:uppercase; margin-bottom:6px; letter-spacing:0.5px;">
                  📡 Opciones de Transmisión (Estilo Fútbol Libre Full HD):
                </div>
                <div style="display:flex; flex-wrap:wrap; gap:6px;">
                  <button type="button" style="background:#1d4ed8; color:#fff; border:none; padding:5px 10px; border-radius:6px; font-size:11px; font-weight:700; cursor:pointer;" onclick="this.parentElement.nextElementSibling.querySelector('iframe').src='https://www.youtube-nocookie.com/embed/live_stream?channel=UCWV3obpZVGgJ3j9FVhEjF2Q';">⚪ Señal 1: Real Madrid TV HD</button>
                  <a href="https://futbollibrefullhd.org/" target="_blank" style="background:#16a34a; color:#fff; padding:5px 10px; border-radius:6px; font-size:11px; font-weight:700; text-decoration:none; display:inline-flex; align-items:center;">⚽ Señal 2: Fútbol Libre Full HD (Partidos Real Madrid)</a>
                  <a href="https://vix.com/es-es/deportes" target="_blank" style="background:#dc2626; color:#fff; padding:5px 10px; border-radius:6px; font-size:11px; font-weight:700; text-decoration:none; display:inline-flex; align-items:center;">🔴 Señal 3: ViX Premium (LaLiga)</a>
                  <a href="https://www.disneyplus.com" target="_blank" style="background:#1e40af; color:#fff; padding:5px 10px; border-radius:6px; font-size:11px; font-weight:700; text-decoration:none; display:inline-flex; align-items:center;">📺 Señal 4: ESPN / Disney+</a>
                  <a href="https://www.sky.com.mx" target="_blank" style="background:#0369a1; color:#fff; padding:5px 10px; border-radius:6px; font-size:11px; font-weight:700; text-decoration:none; display:inline-flex; align-items:center;">⚡ Señal 5: SKY Sports</a>
                  <a href="https://www.directvgo.com" target="_blank" style="background:#334155; color:#fff; padding:5px 10px; border-radius:6px; font-size:11px; font-weight:700; text-decoration:none; display:inline-flex; align-items:center;">📡 Señal 6: DSports</a>
                </div>
              </div>

              <!-- REPRODUCTOR OFICIAL INTEGRADO (ACTIVADO POR ORDEN EXPRESA) -->
              <div style="position:relative; width:100%; border-radius:10px; overflow:hidden; border:1px solid #3b82f6; background:#000000; margin-bottom:12px;">
                <div style="background:#0f172a; padding:8px 12px; font-size:12px; color:#94a3b8; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid #1e293b;">
                  <span>🔴 Reproductor en Vivo: <strong>Fútbol Libre Full HD Experience (Señal Autorizada)</strong></span>
                  <div style="display:flex; align-items:center; gap:8px;">
                    <button type="button" style="background:#1e3a5f; color:#7dedff; border:1px solid #38bdf8; border-radius:4px; padding:2px 8px; font-size:11px; cursor:pointer;" onclick="const ifr=this.closest('.bubble').querySelector('iframe'); if(ifr){ const s=ifr.src; ifr.src=''; setTimeout(()=>ifr.src=s, 200); }">🔄 Recargar Señal</button>
                    <span style="color:#22c55e; font-weight:700;">● EN VIVO</span>
                  </div>
                </div>
                <iframe style="width:100%; height:240px; border:none; display:block;" src="https://www.youtube-nocookie.com/embed/live_stream?channel=UCWV3obpZVGgJ3j9FVhEjF2Q" title="Real Madrid TV Live" allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" allowfullscreen></iframe>
              </div>

              <!-- GUÍA DE OPERADORES Y TRANSMISIÓN OFICIAL -->
              <div style="font-size:12px; color:#94a3b8; margin-bottom:10px;">
                <strong>Operadores con derechos de transmisión:</strong> ${p.canal_oficial}
              </div>
              <div style="display:flex; flex-wrap:wrap; gap:8px;">
                <a href="https://futbollibrefullhd.org/" target="_blank" style="background:#16a34a; color:#fff; padding:6px 12px; border-radius:6px; font-size:12px; text-decoration:none; font-weight:700;">⚽ Fútbol Libre Full HD (Partidos Real Madrid)</a>
                <a href="https://vix.com/es-es/deportes" target="_blank" style="background:#dc2626; color:#fff; padding:6px 12px; border-radius:6px; font-size:12px; text-decoration:none; font-weight:600;">📺 ViX Premium (LaLiga)</a>
                <a href="https://www.disneyplus.com" target="_blank" style="background:#1e40af; color:#fff; padding:6px 12px; border-radius:6px; font-size:12px; text-decoration:none; font-weight:600;">⭐ ESPN / Disney+ (Champions)</a>
                <a href="https://www.realmadrid.com/es-ES/madridistas/real-madrid-tv" target="_blank" style="background:#ffffff; color:#0b1d33; padding:6px 12px; border-radius:6px; font-size:12px; text-decoration:none; font-weight:700;">⚪ Web Oficial Real Madrid</a>
              </div>

              <div style="margin-top:12px; padding-top:10px; border-top:1px solid #1e3a5f; display:flex; justify-content:space-between; align-items:center; font-size:12px;">
                <span style="color:#38bdf8;">🔮 Pronóstico: <strong>${p.marcador_probable}</strong> (${p.probabilidad_victoria_rm}% Victoria RM)</span>
                <span style="color:#fbbf24; font-weight:700;">¡Hala Madrid y nada más! 🤍⚽</span>
              </div>
            </div>`;
          msg('SKY', '👑 <strong>¡Hala Madrid y nada más! 🤍⚽</strong> Aquí tenés la pantalla en vivo de <strong>SKY Sports Center</strong> para ver al Real Madrid y seguir el encuentro con transmisión oficial:', true);
          msg('SKY', sportsCard, true);
          attachedFiles=[];renderAttachedChips();
          $('send').disabled=false;
          return;
        }
      }catch(e){}
    }

    // Herramienta E: Quitar fondo inteligente (remove.bg de SKY)
    if(lower.includes('quitar fondo') || lower.includes('eliminar fondo') || lower.includes('remove.bg') || lower.includes('fondo transparente')){
      let imgRef = attachedFiles.find(f=>f.media_type==='image')?.filename || '';
      if(!imgRef){
        const match = text.match(/([\w\-_]+\.(?:png|jpg|jpeg|webp))/i);
        if(match) imgRef = match[1];
      }
      if(!imgRef && attachedFiles.length===0){
        msg('SKY','✂️ Por favor adjuntá una imagen con el botón 📎 para quitarle el fondo y dejarla transparente al instante.');
        $('send').disabled=false;
        return;
      }
      msg('SKY','✂️ Procesando eliminación de fondo inteligente (remove.bg de SKY)...');
      try{
        const rBg = await fetch('/api/tools/remove-bg', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({image: imgRef})
        });
        const dBg = await rBg.json();
        if(dBg.ok){
          const card = `<div style="text-align:center;">
            <div style="font-weight:700; color:#38bdf8; margin-bottom:8px;">✂️ Fondo Eliminado con Éxito (PNG Transparente RGBA):</div>
            <div style="background: repeating-conic-gradient(#1e293b 0% 25%, #0f172a 0% 50%) 50% / 20px 20px; display:inline-block; padding:12px; border-radius:12px; border:1px solid #334155;">
              <img src="${dBg.url}" style="max-width:100%; max-height:280px; display:block;" />
            </div>
            <div style="margin-top:8px;"><a href="${dBg.url}" download="${dBg.filename}" style="color:#7dedff; text-decoration:underline; font-size:12px;">⬇ Descargar PNG transparente (${(dBg.size_bytes/1024).toFixed(1)} KB · ${dBg.width}x${dBg.height}px)</a></div>
            <div style="font-size:11px; color:#94a3b8; margin-top:6px;">✦ Cómputo de canal alfa y visión artificial ejecutado por SKY</div>
          </div>`;
          msg('SKY', card, true);
          attachedFiles = []; renderAttachedChips();
          $('send').disabled = false;
          return;
        } else {
          msg('SKY', '⚠️ Error al quitar fondo: ' + (dBg.error || 'No se pudo procesar la imagen'));
        }
      }catch(eBg){ msg('SKY', '⚠️ Excepción al quitar fondo: ' + eBg.message); }
    }

    // Herramienta F: Descargador Multimedia (ssstik.io / savefrom.net)
    const isDownload = lower.includes('descargar video') || lower.includes('descarga el video') || lower.includes('bajar video') || lower.includes('savefrom') || lower.includes('ssstik') || lower.includes('tiktok') || lower.includes('youtube') || lower.includes('youtu.be');
    const urlMatch = text.match(/(https?:\/\/[^\s]+)/i);
    if(isDownload && urlMatch){
      const targetUrl = urlMatch[1];
      msg('SKY', `📥 Extrayendo y descargando multimedia desde ${targetUrl} (SaveFrom / SssTik de SKY)...`);
      try{
        const rDl = await fetch('/api/tools/download-video', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({url: targetUrl})
        });
        const dDl = await rDl.json();
        if(dDl.ok){
          const card = `<div style="text-align:center;">
            <div style="font-weight:700; color:#38bdf8; margin-bottom:8px;">📥 Video Descargado con Éxito:</div>
            <div style="font-size:13px; color:#f1f5f9; margin-bottom:8px;">${dDl.title}</div>
            <video controls src="${dDl.url}" style="max-width:100%; max-height:280px; border-radius:12px;"></video>
            <div style="margin-top:8px;"><a href="${dDl.url}" download="${dDl.filename}" style="color:#7dedff; text-decoration:underline; font-size:12px;">⬇ Descargar archivo local (${(dDl.size_bytes/1024/1024).toFixed(2)} MB)</a></div>
            <div style="font-size:11px; color:#94a3b8; margin-top:6px;">✦ Descarga universal procesada por SKY sin publicidad ni intermediarios</div>
          </div>`;
          msg('SKY', card, true);
          attachedFiles = []; renderAttachedChips();
          $('send').disabled = false;
          return;
        } else {
          msg('SKY', '⚠️ ' + (dDl.error || 'No se pudo descargar el video indicado'));
        }
      }catch(eDl){ msg('SKY', '⚠️ Error al procesar descarga: ' + eDl.message); }
    }

    // Herramienta G: Super-Resolución y Mejora de Imagen (magnific.com)
    if(lower.includes('upscale') || lower.includes('magnific') || lower.includes('super resolucion') || lower.includes('mejorar calidad') || lower.includes('aumentar resolucion') || lower.includes('mejorar imagen')){
      let imgRef = attachedFiles.find(f=>f.media_type==='image')?.filename || '';
      if(!imgRef){
        const match = text.match(/([\w\-_]+\.(?:png|jpg|jpeg|webp))/i);
        if(match) imgRef = match[1];
      }
      if(!imgRef && attachedFiles.length===0){
        msg('SKY','✨ Por favor adjuntá una imagen con el botón 📎 para aplicar super-resolución y mejora de microdetalles estilo Magnific AI.');
        $('send').disabled=false;
        return;
      }
      let scale = 2;
      if(lower.includes('4x') || lower.includes('cuatro')) scale = 4;
      msg('SKY',`✨ Procesando super-resolución x${scale} con mejora de nitidez y texturas (Magnific AI de SKY)...`);
      try{
        const rUp = await fetch('/api/tools/upscale', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({image: imgRef, scale: scale})
        });
        const dUp = await rUp.json();
        if(dUp.ok){
          const card = `<div style="text-align:center;">
            <div style="font-weight:700; color:#38bdf8; margin-bottom:8px;">✨ Imagen Mejorada con Super-Resolución (${dUp.scale_factor}x · Magnific):</div>
            <div style="font-size:12px; color:#94a3b8; margin-bottom:6px;">Resolución: ${dUp.original_size[0]}x${dUp.original_size[1]}px ➔ <strong>${dUp.enhanced_size[0]}x${dUp.enhanced_size[1]}px</strong></div>
            <img src="${dUp.url}" style="max-width:100%; border-radius:12px; box-shadow:0 4px 20px rgba(0,0,0,0.5);" />
            <div style="margin-top:8px;"><a href="${dUp.url}" download="${dUp.filename}" style="color:#7dedff; text-decoration:underline; font-size:12px;">⬇ Descargar Ultra HD (${(dUp.size_bytes/1024).toFixed(1)} KB)</a></div>
            <div style="font-size:11px; color:#94a3b8; margin-top:6px;">✦ Algoritmo bilateral, CLAHE adaptativo y super-resolución procesados por SKY</div>
          </div>`;
          msg('SKY', card, true);
          attachedFiles = []; renderAttachedChips();
          $('send').disabled = false;
          return;
        } else {
          msg('SKY', '⚠️ Error en super-resolución: ' + (dUp.error || 'No se pudo procesar'));
        }
      }catch(eUp){ msg('SKY', '⚠️ Excepción al mejorar imagen: ' + eUp.message); }
    }

    // Herramienta H: Iconos Vectoriales SVG/PNG (flaticon.es)
    if(lower.startsWith('icono') || lower.includes('crea un icono') || lower.includes('genera un icono') || lower.includes('flaticon') || lower.includes('icono vectorial')){
      msg('SKY','🌟 Diseñando y renderizando icono vectorial estilo Flaticon...');
      try{
        const rIco = await fetch('/api/tools/icon', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({concept: text})
        });
        const dIco = await rIco.json();
        if(dIco.ok){
          const card = `<div style="text-align:center;">
            <div style="font-weight:700; color:#38bdf8; margin-bottom:8px;">🌟 Icono Vectorial Generado (${dIco.icon_type.toUpperCase()} · Flaticon SKY):</div>
            <div style="display:inline-block; background:#071424; padding:16px; border-radius:14px; border:1px solid #1e3a5f;">
              <img src="${dIco.svg_url}" style="width:128px; height:128px; display:block;" />
            </div>
            <div style="margin-top:10px; display:flex; gap:12px; justify-content:center;">
              <a href="${dIco.svg_url}" download="${dIco.svg_filename}" style="color:#38bdf8; text-decoration:underline; font-size:12px;">⬇ Descargar SVG Vectorial</a>
              <a href="${dIco.png_url}" download="${dIco.png_filename}" style="color:#7dedff; text-decoration:underline; font-size:12px;">⬇ Descargar PNG HD</a>
            </div>
            <div style="font-size:11px; color:#94a3b8; margin-top:6px;">✦ Vector escalable con gradiente y renderizado transparente por SKY</div>
          </div>`;
          msg('SKY', card, true);
          attachedFiles = []; renderAttachedChips();
          $('send').disabled = false;
          return;
        }
      }catch(eIco){}
    }

    // --- 2. CONSULTA UNIVERSAL A SKY (Orquestación autónoma multi-motor + proyectos + documentos) ---
    let res;
    if(ownerKey && !fileContext && (lower.startsWith('crea un proyecto') || lower.startsWith('planea') || window.skyActiveProject)){
      res=await fetch('/api/sky/intelligent/message',{
        method:'POST',
        headers:skyHeaders(),
        body:JSON.stringify({
          message:text,
          provider:'local',
          language:window.SKYGlobalI18N?.locale()||'es',
          project_id:window.skyActiveProject||null
        })
      });
    } else {
      res=await fetch('/api/chat',{
        method:'POST',
        headers:skyHeaders(),
        body:JSON.stringify({
          message:text || 'Analizá y procesá los archivos adjuntos.',
          provider:'auto',
          area:'General',
          file_context:fileContext||null,
          language:window.SKYGlobalI18N?.locale()||'es'
        })
      });
    }

    const d=await res.json();
    if(!res.ok)throw Error(d.detail||'Error al comunicarse con el núcleo de SKY');
    
    // Formatear respuesta limpia sin markdown crudo (###, ****) y con emojis
    let cleanAnswer=formatSkyText(d.answer||'Operación completada.');
    let skyHtml=cleanAnswer;
    if(d.evidencias&&d.evidencias.length){
      skyHtml+=`<div style="margin-top:10px; font-size:12px; color:#7dedff;">📚 Fuentes consultadas de la base de conocimiento: ${d.evidencias.join(', ')}</div>`;
    }
    skyHtml+=`<div style="font-size:11px; color:#38bdf8; margin-top:8px; opacity:0.85;">✦ SKY es el referente · Evolución neural activa</div>`;
    msg('SKY',skyHtml,true);

    if(d.type==='proposal'&&d.request){
      renderWork(d.request);
      window.skyActiveProject=d.request.project_id||window.skyActiveProject;
    }
    
    attachedFiles=[];
    renderAttachedChips();
    updateEvolutionStats();

  }catch(err){
    // Fallback inteligente con Puter.js si el servidor tuviera intermitencias
    if(window.puter&&window.puter.ai&&window.puter.ai.chat){
      try{
        const pFallback=await window.puter.ai.chat(text);
        const fText=typeof pFallback==='string'?pFallback:(pFallback?.message?.content||JSON.stringify(pFallback));
        msg('SKY',formatSkyText(fText)+`<div style="font-size:11px; color:#38bdf8; margin-top:8px;">✦ SKY Autónomo · Nube Puter.js de contingencia</div>`,true);
        attachedFiles=[];renderAttachedChips();
        return;
      }catch(e2){}
    }
    msg('SKY','No se pudo procesar tu solicitud: '+err.message);
  }finally{
    $('send').disabled=false;
  }
});

$('mic')?.addEventListener('click',()=>{
  const SR=window.SpeechRecognition||window.webkitSpeechRecognition;
  if(!SR){msg('SKY','El navegador no admite dictado. Podés escribir tu solicitud.');return}
  const r=new SR();
  r.lang=window.SKYGlobalI18N?.locale()||document.documentElement.lang||'es-NI';
  r.continuous=false;r.interimResults=false;
  r.onresult=e=>{$('prompt').value=($('prompt').value+' '+e.results[0][0].transcript).trim()};
  r.onerror=()=>msg('SKY','No se pudo acceder al micrófono. Verificá los permisos.');
  r.start();
});

// Arrancar inmediatamente
autoBootstrap();
renderHistoryUI();
})();
