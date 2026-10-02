import React from 'react';

export type Membership={enabled:boolean;expires_at?:number;access_kind?:'PAID_MEMBERSHIP'|'TEST_ONLY';test_max_requests?:number;test_max_cost_cny?:string;test_chat_enabled?:boolean};
export type MemberGeneration={model:boolean;temporary:boolean;persistent:boolean;reason?:string;membership?:Membership;readinessRequired?:boolean;readinessAvailable?:boolean};

// Display-only projection. The server still verifies membership on every
// admission/publication; neither this date nor a client flag grants access.
export function MemberMembership({value}:{value:Membership}){
 const candidate=typeof value.expires_at==='number'?new Date(value.expires_at*1000):null;
 const expires=candidate&&Number.isFinite(candidate.getTime())?candidate:null;
 if(value.access_kind==='TEST_ONLY')return <section aria-label="测试使用资格"><h3>测试使用资格</h3>
  <p>{value.enabled?'已获明确测试授权':'测试资格已到期、停用或不包含当前操作'}</p>
  <p>这不是付费会员。{value.test_chat_enabled?'在授权期限和额度内可进行合成内容日常测试。':'当前未获准日常聊天。'}</p>
  <p>本次测试授权累计最多 {value.test_max_requests} 次、¥{value.test_max_cost_cny}，同时计入平台共享每月500元额度；不会每月自动重置本次测试资格。</p>
  {expires&&<p>有效期至 <time dateTime={expires.toISOString()}>{expires.toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})}</time>（北京时间）</p>}
 </section>;
 return <section aria-label="会员状态"><h3>会员状态</h3>
  <p>{value.enabled?'会员有效':'会员未开通、已到期或已停用'}</p>
  {expires&&<p>有效期至 <time dateTime={expires.toISOString()}>{expires.toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false})}</time>（北京时间）</p>}
  <p>注册账号不包含模型使用权限。在线购买会员暂未开放。</p>
 </section>;
}
