// Same-origin, CSP-compatible bootstrap. Never persist or log callback material.
(()=>{
 if(location.pathname!=='/account/recovery'){
  // The app never accepts an implicit signup/OAuth fragment as login authority.
  // Drop only recognized auth-return fields before the UI module initializes;
  // unrelated hash routing stays byte-for-byte unchanged.
  const credentials=new Set(['access_token','refresh_token','provider_token','provider_refresh_token']);
  const authFields=new Set([...credentials,'token_type','expires_in','expires_at','type']);
  const pieces=location.hash.slice(1).split('&');
  const name=piece=>{const first=new URLSearchParams(piece).keys().next();return first.done?'':first.value.toLowerCase()};
  if(!pieces.some(piece=>credentials.has(name(piece))))return;
  const remaining=pieces.filter(piece=>!authFields.has(name(piece))).join('&');
  const clean=location.origin+location.pathname+location.search+(remaining?'#'+remaining:'');
  try{history.replaceState(history.state,'',clean)}catch{window.stop();location.replace(clean)}
  return;
 }
 const values=new URLSearchParams(location.search).getAll('code');
 const code=values.length===1&&/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/.test(values[0])?values[0]:null;
 Object.defineProperty(window,'__hclaRecovery',{value:{code,invalid:Boolean(location.search||location.hash)&&!code},configurable:true});
 try{history.replaceState(null,'','/account/recovery')}catch{location.replace('/account/recovery')}
})();
