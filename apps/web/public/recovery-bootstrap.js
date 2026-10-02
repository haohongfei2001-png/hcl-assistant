// Same-origin, CSP-compatible bootstrap. Never persist or log callback material.
(()=>{
 if(location.pathname!=='/account/recovery')return;
 const values=new URLSearchParams(location.search).getAll('code');
 const code=values.length===1&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(values[0])?values[0]:null;
 Object.defineProperty(window,'__hclaRecovery',{value:{code,invalid:Boolean(location.search||location.hash)&&!code},configurable:true});
 try{history.replaceState(null,'','/account/recovery')}catch{location.replace('/account/recovery')}
})();
