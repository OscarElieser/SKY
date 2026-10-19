/* SKY v10.2: short-lived administrative session with opt-in TOTP.
   No master key or OTP is stored in browser storage. */
(()=>{'use strict';
const SESSION_KEY='sky_owner_mfa_session_v102';
function session(){try{return sessionStorage.getItem(SESSION_KEY)||''}catch{return ''}}
function save(value){try{if(value)sessionStorage.setItem(SESSION_KEY,value);else sessionStorage.removeItem(SESSION_KEY)}catch{}}
async function begin(key){
 const status=await fetch('/api/security/owner-mfa/status',{cache:'no-store'});
 if(!status.ok)throw Error('No se pudo comprobar la protección administrativa');
 const settings=await status.json();
 if(!settings.required)return true;
 if(session()){const check=await fetch('/api/security/owner-mfa/verify',{headers:{'X-SKY-KEY':key,'X-SKY-SESSION':session()},cache:'no-store'});if(check.ok)return true;save('');}
 const code=window.prompt('SKY: introducí el código temporal de 6 dígitos de tu aplicación de autenticación.');
 if(!code)throw Error('Se requiere un segundo factor para acceder');
 const response=await fetch('/api/security/owner-mfa/session',{method:'POST',headers:{'X-SKY-KEY':key,'Content-Type':'application/json'},body:JSON.stringify({code:code.trim()}),cache:'no-store'});
 if(!response.ok)throw Error('Segundo factor no válido o temporalmente bloqueado');
 const data=await response.json();save(data.session);return true;
}
function headers(){const value=session();return value?{'X-SKY-SESSION':value}:{}}
async function logout(key){
 const value=session();if(key&&value){try{await fetch('/api/security/owner-mfa/logout',{method:'POST',headers:{'X-SKY-KEY':key,'X-SKY-SESSION':value}})}catch{}}
 save('');
}
window.SKYOwnerAuth={begin,headers,logout};
})();
