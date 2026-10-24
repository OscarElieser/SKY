(()=>{"use strict";
const $=id=>document.getElementById(id);
let lessonId="", lessonText="", lastProject=null;

function headers(){
  const key=$("sky-key").value.trim();
  if(!key)throw new Error("Ingresá tu clave de propietario SKY.");
  const result={"X-SKY-KEY":key};
  const session=$("sky-session").value.trim();
  if(session)result["X-SKY-SESSION"]=session;
  return result;
}

async function request(path,method="GET",body=null,outputType="json"){
  const params={method,headers:headers(),cache:"no-store"};
  if(body!==null){
    params.headers["Content-Type"]="application/json";
    params.body=JSON.stringify(body);
  }
  const res=await fetch(path,params);
  if(!res.ok){
    let error={};
    try{error=await res.json()}catch{}
    const detail=error.detail;
    throw new Error(typeof detail==="string"?detail:"SKY respondió HTTP "+res.status);
  }
  if(outputType==="blob"){
    const blob=await res.blob();
    const disposition=res.headers.get("Content-Disposition")||"";
    const match=disposition.match(/filename="([^"]{1,100})"/);
    return {blob,filename:match?match[1]:"documento_sky.docx"};
  }
  return res.json();
}

function status(text,isError=false){
  $("status").textContent=text;
  $("status").style.color=isError?"#ffbbb4":"#9adff0";
}

function lessonBody(){
  return {
    topic:$("lesson-topic").value.trim(),
    level:$("lesson-level").value,
    duration_minutes:Number($("lesson-duration").value),
    learning_goal:$("lesson-goal").value.trim(),
    reference_text:$("lesson-material").value,
    grade:$("lesson-grade").value.trim(),
  };
}

function renderStep(step){
  lessonText=step.voice_ready_text||"";
  $("lesson-output").textContent=
    "Momento "+step.stage_number+" de "+step.total_stages+
    ": "+step.stage_name+" ("+step.minutes+" minutos)\n\n"+
    step.voice_ready_text+"\n\nPregunta para conversar:\n"+
    step.question+"\n\nEstado de verificación: contenido de clase pendiente de revisión curricular.";
  $("speak-lesson").disabled=!lessonText;
  $("next-lesson").disabled=step.stage_number>=step.total_stages;
}

function stopVoice(){
  if("speechSynthesis" in window)window.speechSynthesis.cancel();
}

function speakLesson(){
  if(!("speechSynthesis" in window)||!("SpeechSynthesisUtterance" in window)){
    status("Este navegador no dispone de voz. El contenido permanece legible en pantalla.",true);
    return;
  }
  if(!lessonText)return;
  stopVoice();
  const utterance=new SpeechSynthesisUtterance(lessonText.slice(0,3600));
  utterance.lang="es-NI";
  utterance.rate=Number($("voice-speed").value)||1;
  const voices=window.speechSynthesis.getVoices();
  const spanish=voices.find(v=>v.lang==="es-NI"&&v.localService)
      ||voices.find(v=>/^es/i.test(v.lang)&&v.localService)
      ||voices.find(v=>/^es/i.test(v.lang));
  if(spanish)utterance.voice=spanish;
  utterance.onerror=()=>status("El sintetizador de voz no respondió. Podés leer la etapa en pantalla.",true);
  window.speechSynthesis.speak(utterance);
  status("SKY está narrando el momento de la clase.");
}

async function download(kind,endpoint,data){
  const answer=await request(endpoint,"POST",{...data,kind},"blob");
  const url=URL.createObjectURL(answer.blob);
  const link=document.createElement("a");
  link.href=url;link.download=answer.filename;
  document.body.append(link);link.click();link.remove();
  URL.revokeObjectURL(url);
  status("SKY creó el archivo. Revisá su contenido y las evidencias antes de publicarlo.");
}

function projectBody(){
  return {
    name:$("project-name").value.trim(),
    challenge:$("project-problem").value.trim(),
    category:$("project-area").value,
    event:$("project-event").value,
    solution:$("project-solution").value.trim(),
    beneficiaries:$("project-beneficiaries").value.trim(),
    evidence_text:$("project-evidence").value.trim(),
    pitch_minutes:Number($("project-pitch").value),
  };
}

function execute(button,action){
  if(button.disabled)return;
  button.disabled=true;
  Promise.resolve().then(action)
    .catch(error=>status(error.message,true))
    .finally(()=>{button.disabled=false});
}

$("tab-aula").onclick=()=>{
  $("aula").classList.remove("hidden");
  $("innovation").classList.add("hidden");
  $("tab-aula").setAttribute("aria-selected","true");
  $("tab-innovation").setAttribute("aria-selected","false");
};
$("tab-innovation").onclick=()=>{
  stopVoice();
  $("aula").classList.add("hidden");
  $("innovation").classList.remove("hidden");
  $("tab-aula").setAttribute("aria-selected","false");
  $("tab-innovation").setAttribute("aria-selected","true");
};

$("start-lesson").onclick=()=>execute($("start-lesson"),async()=>{
  stopVoice();
  const result=await request("/api/sky/academy/education/sessions","POST",lessonBody());
  lessonId=result.lesson_id;
  $("export-lesson").disabled=false;
  $("send-answer").disabled=false;
  $("student-feedback").textContent="";
  renderStep(result.step);
  status(result.plan.material_supplied ?
    "Clase preparada. El material aportado requiere cotejo curricular.":
    "Estructura didáctica lista; faltan fuentes para enseñar hechos específicos.");
});
$("next-lesson").onclick=()=>execute($("next-lesson"),async()=>{
  if(!lessonId)throw new Error("Iniciá primero una clase.");
  stopVoice();
  const res=await request(
    "/api/sky/academy/education/sessions/"+encodeURIComponent(lessonId)+"/next","POST",{}
  );
  if(res.status==="completed"){
    $("next-lesson").disabled=true;
    $("lesson-output").textContent="Clase concluida. Podés iniciar una nueva.";
    status("Se completaron los siete momentos didácticos.");
    return;
  }
  renderStep(res.step);
  $("student-feedback").textContent="";
  $("student-answer").value="";
  status("Etapa preparada. Presioná «Escuchar a SKY» para oír la explicación.");
});
$("send-answer").onclick=()=>execute($("send-answer"),async()=>{
  if(!lessonId)throw new Error("Iniciá una clase primero.");
  const answer=$("student-answer").value.trim();
  if(answer.length<2)throw new Error("Escribí una respuesta.");
  const feedback=await request(
    "/api/sky/academy/education/sessions/"+encodeURIComponent(lessonId)+"/respond",
    "POST",{answer:answer.slice(0,800)}
  );
  $("student-feedback").textContent=feedback.message+
    " Tu respuesta no fue almacenada ni calificada.";
  lessonText=feedback.voice_ready_text||lessonText;
  $("student-answer").value="";
  status("SKY te hizo una pregunta de reflexión. Escuchá la respuesta o avanzá cuando querás.");
});
$("speak-lesson").onclick=speakLesson;
$("stop-lesson").onclick=()=>{stopVoice();status("Narración detenida por vos.");};
$("export-lesson").onclick=()=>execute($("export-lesson"),async()=>{
  await download("docx","/api/sky/academy/education/lesson/document",lessonBody());
});

$("project-verify-sources").onclick=()=>execute($("project-verify-sources"),async()=>{
  const selected=Array.from($("project-sources").selectedOptions).map(o=>o.value);
  if(selected.length<1||selected.length>4){
    throw new Error("Seleccioná entre una y cuatro fuentes oficiales.");
  }
  const topic=$("project-problem").value.trim();
  if(topic.length<5)throw new Error("Escribí el problema que querés investigar.");
  const result=await request("/api/sky/academy/research/official-sources","POST",{
    topic:topic.slice(0,240),source_ids:selected,
  });
  let out="SKY recuperó "+result.pages_retrieved+" de "+result.sources.length+
    " páginas oficiales.\n\n";
  for(const item of result.sources){
    out+=item.label+"\n"+item.url+"\nEstado: "+item.status+"\n";
    if(item.retrieved_at)out+="Fecha de consulta: "+item.retrieved_at+"\n";
    if(item.topic_excerpts?.length){
      out+="Extractos relacionados:\n"+item.topic_excerpts.join("\n\n")+"\n";
    }else out+="Sin extractos relevantes recuperados.\n";
    out+="\n";
  }
  out+="Las afirmaciones requieren verificación cruzada y revisión de fecha de publicación.";
  $("research-output").textContent=out;
  status("Consulta completada cuando hay fuentes recuperadas; no equivale a investigación científica final.");
});

$("build-project").onclick=()=>execute($("build-project"),async()=>{
  const body=projectBody();
  const result=await request("/api/sky/academy/innovation/project","POST",body);
  lastProject=body;
  $("project-output").textContent=result.document_markdown+
    "\n\nAVISO SKY: Las estadísticas y evidencias siguen pendientes de comprobación.";
  $("export-project-word").disabled=false;
  $("export-project-pdf").disabled=false;
  $("export-project-slides").disabled=false;
  status("SKY preparó un Canvas y pitch preliminares. Faltan investigación y validación de campo.");
});
for(const [id,kind] of [
  ["export-project-word","docx"],["export-project-pdf","pdf"],
  ["export-project-slides","pptx"]]){
  $(id).onclick=()=>execute($(id),async()=>{
    if(!lastProject)throw new Error("Construí primero la propuesta.");
    await download(kind,"/api/sky/academy/innovation/project/document",lastProject);
  });
}
window.addEventListener("pagehide",stopVoice);
})();