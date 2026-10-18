'use strict';
const $=id=>document.getElementById(id);
let privateKey='',format='docx';
const fmtButtons=[...document.querySelectorAll('[data-kind]')];
function choose(kind){format=kind;fmtButtons.forEach(el=>{el.classList.toggle('selected',el.dataset.kind===kind);el.setAttribute('aria-pressed',String(el.dataset.kind===kind))});$('filetype').textContent=kind.toUpperCase();}
fmtButtons.forEach(el=>el.addEventListener('click',()=>choose(el.dataset.kind)));
$('use-ai').addEventListener('change',()=>{$('ai-settings').classList.toggle('hidden',!$('use-ai').checked)});
function preview(){$('prev-title').textContent=$('title').value||'Sin título';$('prev-content').textContent=($('content').value||$('prompt').value||'Escribí el contenido para verlo aquí...').slice(0,2500)};
['title','content','prompt'].forEach(id=>$(id).addEventListener('input',preview));
function notify(msg,ok){$('result').replaceChildren();const el=document.createElement('div');el.className=ok?'file-ready':'notice';el.id=ok?'done':'err';el.textContent=msg;$('result').append(el)}
async function get(path,opts={}){let res=await fetch(path,{...opts,headers:{'X-SKY-KEY':privateKey,...opts.headers}});if(!res.ok){let message='Error '+res.status;try{message=(await res.json()).detail||message}catch{}throw Error(message)}return res}
async function connect(){privateKey=$('key').value.trim();try{await get('/api/office/formats');$('gate').classList.add('hidden');$('key').value=''}catch(e){$('gate-error').textContent=e.message;privateKey=''}}
$('connect').addEventListener('click',connect);$('key').addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();connect()}})
$('logout').addEventListener('click',()=>{privateKey='';$('gate').classList.remove('hidden');$('result').replaceChildren()});
$('make').addEventListener('submit',async e=>{
  e.preventDefault();if(!privateKey){notify('Primero iniciá sesión.');return}
  const btn=$('generate');btn.disabled=true;btn.textContent='Generando archivo...';$('result').replaceChildren();
  const payload={kind:format,title:$('title').value.trim(),prompt:$('prompt').value,content:$('content').value,csv:$('csv').value,template:$('template').value,ai_provider:$('use-ai').checked?$('provider').value:'none'};
  try{
    const r=await get('/api/office/generate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    const disposition=r.headers.get('Content-Disposition')||'';const found=/filename="([^"\n]+)"/.exec(disposition);const filename=found?found[1]:`archivo_sky.${format}`;
    const blob=await r.blob();const uri=URL.createObjectURL(blob);const link=document.createElement('a');link.href=uri;link.download=filename;document.body.append(link);link.click();link.remove();setTimeout(()=>URL.revokeObjectURL(uri),4000);
    notify('Archivo real creado: '+filename+' ('+Math.ceil(blob.size/1024)+' KB). Ya podés editarlo o compartirlo.',true);
  }catch(err){notify('No se pudo generar: '+err.message,false)}finally{btn.disabled=false;btn.textContent='✦ Crear y descargar'}
});
$('mic').addEventListener('click',()=>{const Recognition=window.SpeechRecognition||window.webkitSpeechRecognition;if(!Recognition){notify('Este navegador no ofrece dictado. Podés escribir tus instrucciones.');return}const sr=new Recognition();sr.lang='es-NI';sr.onresult=e=>{$('prompt').value=( $('prompt').value+' '+e.results[0][0].transcript).trim();preview()};sr.onerror=()=>notify('No se pudo utilizar el micrófono. Revisá permisos.');sr.start()});
choose('docx');
