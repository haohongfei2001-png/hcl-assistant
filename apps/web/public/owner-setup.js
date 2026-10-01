// Standalone browser-only setup. No network, analytics, URL state or persistence.
const form=document.querySelector('#setup'),status=document.querySelector('#status');
const result=document.querySelector('#result'),bundle=document.querySelector('#bundle');
const generate=document.querySelector('#generate'),password=document.querySelector('#password');
const confirmation=document.querySelector('#confirmation'),login=document.querySelector('#login');
let generation=0;
const hex=bytes=>Array.from(bytes,value=>value.toString(16).padStart(2,'0')).join('');
function clear(){generation++;password.value='';confirmation.value='';bundle.value='';result.hidden=true;status.textContent='本页内容已清空'}
form.addEventListener('submit',async event=>{
 event.preventDefault();if(generate.disabled)return;
 if(!window.isSecureContext||!crypto.subtle||location.search||location.hash){status.textContent='请从不含查询参数的 HTTPS 设置页打开，本页未生成任何设置';return}
 if(Array.from(password.value).length<12||Array.from(password.value).length>1024||password.value!==confirmation.value||!login.value.trim()||login.value.length>80||/[\u0000-\u001f]/.test(login.value)){status.textContent='请检查账号和两次输入的密码（至少 12 个字符）';return}
 const epoch=++generation,ownerLogin=login.value;generate.disabled=true;result.hidden=true;bundle.value='';status.textContent='正在本地生成…';
 try{
  const salt=crypto.getRandomValues(new Uint8Array(16)),stateKey=crypto.getRandomValues(new Uint8Array(32));
  const material=await crypto.subtle.importKey('raw',new TextEncoder().encode(password.value),'PBKDF2',false,['deriveBits']);
  const derived=new Uint8Array(await crypto.subtle.deriveBits({name:'PBKDF2',hash:'SHA-256',salt,iterations:600000},material,256));
  if(epoch!==generation)return;
  bundle.value=JSON.stringify({schema_version:1,login:ownerLogin,verifier:`pbkdf2-sha256$600000$${hex(salt)}$${hex(derived)}`,temporary_state_key:hex(stateKey)});
  password.value='';confirmation.value='';result.hidden=false;status.textContent='已在当前浏览器生成，未发送或保存';
 }catch{clear();status.textContent='浏览器无法完成安全生成，请换用支持 Web Crypto 的浏览器'}
 finally{generate.disabled=false}
});
document.querySelector('#copy').addEventListener('click',async()=>{if(!bundle.value)return;try{await navigator.clipboard.writeText(bundle.value);status.textContent='已复制，请只粘贴到 Vercel 的 HCLA_OWNER_CONFIG 安全字段'}catch{status.textContent='无法复制，请检查浏览器剪贴板权限后重试'}});
document.querySelector('#clear').addEventListener('click',clear);
window.addEventListener('pagehide',clear);
