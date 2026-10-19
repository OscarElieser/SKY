/* SKY v10.2 global localizer: same-origin, no external requests or user-content translation.
   Uses reviewed glossary keys; untranslated text remains untouched, visibly documented. */
(()=>{'use strict';
const KEY='sky_ui_language';
const skip='script,style,code,pre,textarea,option,svg,[contenteditable],.conversation,.bubble,.answer,.project-chat,.assets,.event-list,#messages,#memories';
const original=new WeakMap(),lastRendered=new WeakMap();
let strings={},language='es',loaded=false,userToken='';
const saved=()=>{try{return localStorage.getItem(KEY)}catch{return null}};
function remember(code){try{localStorage.setItem(KEY,code)}catch{}}
function isHumanText(node){const parent=node.parentElement;if(!parent||parent.closest(skip))return false;return Boolean(node.textContent.trim())&&node.textContent.trim().length<=120;}
function translateNode(node){if(!isHumanText(node))return;
 const current=node.textContent;
 if(!original.has(node)|| (lastRendered.has(node)&&lastRendered.get(node)!==current)) original.set(node,current);
 const value=original.get(node),word=value.trim();
 if(!word)return;
 const translated=strings[word];
 if(!translated){if(node.textContent!==value)node.textContent=value;lastRendered.set(node,value);return}
 const leading=(value.match(/^\s*/)||[''])[0],trailing=(value.match(/\s*$/)||[''])[0];
 const next=leading+translated+trailing;if(node.textContent!==next)node.textContent=next;lastRendered.set(node,next);
}
function applyAll(){
 const walker=document.createTreeWalker(document.body,NodeFilter.SHOW_TEXT);const nodes=[];
 while(walker.nextNode())nodes.push(walker.currentNode);
 for(const node of nodes)translateNode(node);
 for(const el of document.querySelectorAll('input[placeholder],textarea[placeholder],[data-sky-i18n-placeholder]')){
  if(!el.dataset.skyOriginalPlaceholder)el.dataset.skyOriginalPlaceholder=el.getAttribute('placeholder')||'';
  const key=el.dataset.skyI18nPlaceholder||el.dataset.skyOriginalPlaceholder;
  const localized=strings[key];el.placeholder=localized||el.dataset.skyOriginalPlaceholder;
 }
 for(const el of document.querySelectorAll('[data-sky-i18n-aria],[data-sky-i18n-title]')){
  for(const kind of ['aria','title']){const attribute=kind==='aria'?'aria-label':'title',key=el.dataset[kind==='aria'?'skyI18nAria':'skyI18nTitle'];
   if(key)el.setAttribute(attribute,strings[key]||key);}
 }
}
async function apply(code){
 const response=await fetch('/api/i18n/ui?locale='+encodeURIComponent(code),{cache:'no-store'});
 if(!response.ok)throw Error('Catálogo no disponible');const info=await response.json();
 strings=info.translations||{};language=info.locale;loaded=true;
 document.documentElement.lang=language;document.documentElement.dir=info.direction;
 document.body.dataset.skyLocale=language;
 applyAll();
 const infoNode=document.getElementById('sky-locale-coverage');if(infoNode){infoNode.textContent=info.completeness==='core'?'✓ '+info.coverage.reviewed_strings+' etiquetas':'◐ '+info.coverage.reviewed_strings+' etiquetas · parcial';}
 window.dispatchEvent(new CustomEvent('sky:languagechange',{detail:{language,coverage:info.completeness}}));
}
async function start(){
 const anchor=document.querySelector('.right-top')||document.querySelector('header');if(!anchor)return;
 const div=document.createElement('div');div.className='sky-global-locale';div.style.cssText='display:inline-flex;align-items:center;gap:5px;margin-inline:8px;flex-wrap:wrap';
 const label=document.createElement('label');label.setAttribute('for','sky-global-language');label.textContent='🌐';
 const select=document.createElement('select');select.id='sky-global-language';select.setAttribute('aria-label','Language / Idioma / 语言 / اللغة');select.style.cssText='max-width:135px;background:#10223b;color:white;border:1px solid #416179;border-radius:8px;padding:5px';
 const coverage=document.createElement('span');coverage.id='sky-locale-coverage';coverage.style.cssText='font-size:10px;opacity:.75';
 div.append(label,select,coverage);anchor.append(div);
 try{
  const r=await fetch('/api/i18n/languages',{cache:'no-store'});if(!r.ok)throw Error('Catálogo inaccesible');
  const data=await r.json();const preferred=saved()||data.negotiated||'es';
  data.languages.forEach(item=>{const opt=document.createElement('option');opt.value=item.code;opt.textContent=item.name+(item.ui_offline?'':' · parcial');select.append(opt)});
  const root=preferred.split('-')[0];select.value=[...select.options].some(o=>o.value===root)?root:'es';await apply(select.value);
  select.addEventListener('change',async()=>{remember(select.value);try{await apply(select.value);if(userToken){await fetch('/api/community/me/language',{method:'PUT',headers:{'Authorization':'Bearer '+userToken,'Content-Type':'application/json'},body:JSON.stringify({language:select.value})});}}catch{coverage.textContent='⚠'}});
 }catch(e){div.remove()}
}
// Global UI is deliberately narrow: never translate messages, user files or personal data.
const observer=new MutationObserver(items=>{
 if(!loaded)return;
 for(const record of items){
  if(record.type==='characterData')translateNode(record.target);
 if(record.type==='childList')for(const node of record.addedNodes){
   if(node.nodeType===Node.TEXT_NODE)translateNode(node);
   else if(node.nodeType===Node.ELEMENT_NODE&&!node.closest(skip)){
    const walker=document.createTreeWalker(node,NodeFilter.SHOW_TEXT);
    while(walker.nextNode())translateNode(walker.currentNode);
   }
  }
 }
});
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',start,{once:true});else start();
observer.observe(document.documentElement,{subtree:true,childList:true,characterData:true});
window.addEventListener('sky:auth',async event=>{userToken=event.detail?.role==='user'?(event.detail.token||''):'';if(!userToken)return;try{const r=await fetch('/api/community/me/language',{headers:{Authorization:'Bearer '+userToken}});if(r.ok){const data=await r.json();{const root=(data.explicit?data.language:navigator.language||'es').split('-')[0];const select=document.getElementById('sky-global-language');if(select&&[...select.options].some(x=>x.value===root)){select.value=root;await apply(root)}}}}catch{}});
window.SKYGlobalI18N={apply,locale:()=>language};
})();
