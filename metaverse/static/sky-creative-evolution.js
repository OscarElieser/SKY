(()=>{'use strict';
const $=id=>document.getElementById(id);
const ROOT='/api/creative/evolution';
let lastWork=null;
const status=message=>{$('evo-status').textContent=message};
const val=id=>$(id).value.trim();
const common=()=>({locale:val('evo-locale'),provider:val('evo-provider')});
const post=(url,data)=>{if(typeof window.SKYCreativeAPI!=='function')throw Error('Ingresá primero como propietario de SKY');return window.SKYCreativeAPI(ROOT+url,'POST',data)};
async function busy(button,operation){
  button.disabled=true;
  status('SKY está procesando la solicitud. La respuesta depende del motor instalado.');
  try{await operation()}catch(error){status('No se pudo completar: '+(error?.message||'Error del motor de SKY'))}
  finally{button.disabled=false}
}
function idea(minimum){
  const text=val('evo-idea');
  if(text.length<minimum)throw Error('Describí mejor tu idea (mínimo '+minimum+' caracteres).');
  return text;
}
function consent(){
  if(!$('evo-cloud-consent').checked)throw Error('Se requiere autorización explícita para generar medios mediante Gemini.');
}
$('evo-write').onclick=()=>busy($('evo-write'),async()=>{
  const result=await post('/writing',{kind:val('evo-kind'),title:val('evo-title'),
    premise:idea(12),genre:val('evo-genre'),...common()});
  lastWork={id:result.id,version:result.version,title:result.title};
  $('evo-output').value=result.text;
  status('Obra guardada en SKY · '+result.locale+' · versión '+result.version+' · '+result.provider);
});
$('evo-continue').onclick=()=>busy($('evo-continue'),async()=>{
  if(!lastWork)throw Error('Primero creá una historia, novela, cuento o guion.');
  const result=await post('/writing/'+lastWork.id+'/continue',{
    instruction:idea(8),expected_version:lastWork.version,provider:val('evo-provider')});
  lastWork.version=result.version;
  $('evo-output').value=result.text;
  status('Continuación guardada: '+result.title+' · versión '+result.version);
});
$('evo-image').onclick=()=>busy($('evo-image'),async()=>{
  consent();
  const result=await post('/images/generate',{prompt:idea(8),...common(),
    improve:$('evo-improve').checked,cloud_authorized:true,mode:'image'});
  status('Imagen real incorporada a la biblioteca SKY: '+result.asset.id);
  await window.SKYCreativeRefresh();
  await window.SKYCreativeDownload('/api/creative/assets/'+result.asset.id+'/preview',result.asset.filename,true);
});
$('evo-music').onclick=()=>busy($('evo-music'),async()=>{
  const result=await post('/music/generate',{genre:val('evo-music-style'),
    mood:val('evo-music-mood'),seconds:Number(val('evo-music-seconds')),
    bpm:Number(val('evo-bpm')),seed_text:val('evo-title')});
  status('Audio WAV real creado en la biblioteca de SKY. Música instrumental sin voz cantada.');
  await window.SKYCreativeRefresh();
  await window.SKYCreativeDownload('/api/creative/assets/'+result.asset.id+'/download','SKY_Musica_Original.wav',false);
});
$('evo-movie').onclick=()=>busy($('evo-movie'),async()=>{
  consent();
  const argument=idea(12);
  if(!window.confirm('SKY solicitará varias imágenes a Gemini; esto puede consumir cuota. ¿Continuar con el montaje MP4?'))return;
  const result=await post('/movies/generate',{title:val('evo-title'),idea:argument,
    ...common(),soundtrack:$('evo-soundtrack').checked,cloud_authorized:true});
  status('Montaje IA en cola de FFmpeg: '+result.scenes+
    ' escenas, proyecto '+result.project_id+'. Consultá Mis proyectos y Tareas para obtener el MP4.');
  await window.SKYCreativeRefresh();
});
$('evo-download-text').onclick=()=>{
  const text=$('evo-output').value;
  if(!text.trim())return status('Generá una obra narrativa antes de descargar.');
  const blob=new Blob([text],{type:'text/plain;charset=utf-8'});
  const uri=URL.createObjectURL(blob),link=document.createElement('a');
  link.href=uri;link.download=(lastWork?.title||'SKY_Obra').replace(/[^a-zA-Z0-9 _-]/g,'').slice(0,45)+'.txt';
  link.click();setTimeout(()=>URL.revokeObjectURL(uri),1000);
};
})();