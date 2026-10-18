/* SKY 10.1: small optional language switcher; no third-party scripts or data sharing. */
(()=>{'use strict';
const LOCAL_KEY='sky_ui_language';
const host=document.querySelector('.right-top')||document.querySelector('header');
if(!host)return;
const label=document.createElement('label');label.className='sky-locale';label.style.cssText='display:inline-flex;align-items:center;gap:5px;font-size:12px;margin-inline:8px';
label.textContent='🌐';const select=document.createElement('select');select.id='sky-language';select.setAttribute('aria-label','Idioma / Language');
select.style.cssText='max-width:130px;background:#10223b;color:#fff;border:1px solid #416179;border-radius:8px;padding:5px';label.append(select);host.insertBefore(label,host.firstChild);
const safeGet=()=>{try{return localStorage.getItem(LOCAL_KEY)}catch{return null}};
const safeSet=code=>{try{localStorage.setItem(LOCAL_KEY,code)}catch{}};
const rtl=new Set(['ar','he','fa','ur']);
async function apply(lang){
 const response=await fetch('/api/i18n/phrases?locale='+encodeURIComponent(lang),{credentials:'same-origin'});
 if(!response.ok)throw Error('Catálogo no disponible');const data=await response.json();
 document.documentElement.lang=data.locale;document.documentElement.dir=data.direction;
 document.querySelectorAll('[data-sky-i18n]').forEach(el=>{let value=data.phrases[el.dataset.skyI18n];if(value)el.textContent=value});
 document.querySelectorAll('[data-sky-i18n-placeholder]').forEach(el=>{let value=data.phrases[el.dataset.skyI18nPlaceholder];if(value)el.placeholder=value});
}
async function init(){
 try{
  const response=await fetch('/api/i18n/languages',{credentials:'same-origin'});
  if(!response.ok)return;const body=await response.json();
  for(const item of body.languages){const option=document.createElement('option');option.value=item.code;option.textContent=item.name+(item.ui_offline?'':' · parcial');select.append(option)}
  const saved=safeGet()||body.negotiated||'es';
  select.value=Array.from(select.options).some(o=>o.value===saved.split('-')[0])?saved.split('-')[0]:'es';
  await apply(select.value);
  select.addEventListener('change',()=>{safeSet(select.value);apply(select.value).catch(()=>{})});
 }catch(e){label.remove()}
}
init();
})();
