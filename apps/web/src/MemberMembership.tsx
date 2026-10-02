import React from 'react';

export type Membership={enabled:boolean;expires_at?:number};
export type MemberGeneration={model:boolean;temporary:boolean;persistent:boolean;reason?:string;membership?:Membership};

// Display-only projection. The server still verifies membership on every
// admission/publication; neither this date nor a client flag grants access.
export function MemberMembership({value}:{value:Membership}){
 const candidate=typeof value.expires_at==='number'?new Date(value.expires_at*1000):null;
 const expires=candidate&&Number.isFinite(candidate.getTime())?candidate:null;
 return <section aria-label="会员状态"><h3>会员状态</h3>
  <p>{value.enabled?'会员有效':'会员未开通、已到期或已停用'}</p>
  {expires&&<p>有效期至 <time dateTime={expires.toISOString()}>{expires.toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})}</time>（北京时间）</p>}
  <p>注册账号不包含模型使用权限。在线购买会员暂未开放。</p>
 </section>;
}
