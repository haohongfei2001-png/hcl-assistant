import React,{useEffect,useRef,useState} from 'react';
import {api} from './api';

type Offer={plan_id:string;version:number;title:string;amount_minor:number;currency:'CNY';duration_days:number;max_requests:number;max_cost_cny:string;temporary:boolean;persistent:boolean;terms_digest:string;shared_capacity_limited:boolean;renewal_mode:'USER_INITIATED_FIXED_DURATION';usage_period:'ASIA_SHANGHAI_CALENDAR_MONTH'};
type Order={order_id:string;plan_id:string;plan_version:number;amount_minor:number;currency:'CNY';duration_days:number;state:string;verification_state:string;created_at:number;expires_at:number;access_starts_at?:number;access_expires_at?:number;access_enabled?:boolean;verification_deferred?:boolean};
type Catalog={available:boolean;plans:Offer[];reason?:string};
const money=(minor:number)=>new Intl.NumberFormat('zh-CN',{style:'currency',currency:'CNY'}).format(minor/100);
const date=(seconds:number)=>new Date(seconds*1000).toLocaleString('zh-CN',{timeZone:'Asia/Shanghai',hour12:false});
const quoteOpen=(order:Order,now:number)=>Number.isSafeInteger(order.expires_at)&&order.expires_at*1000>now;
const canPrepare=(order:Order,now:number)=>['PENDING','CHECKOUT_READY'].includes(order.state)&&quoteOpen(order,now);
const terminalOrder=(order:Order)=>['FULFILLED','REFUNDED','DISPUTED','REVIEW_REQUIRED','EXPIRED'].includes(order.state);
const expiredQuote='此订单报价已到期，请勿继续付款；若已付款，请核验原订单。';
const orderLabels:Record<string,string>={PENDING:'订单已创建，尚未准备支付',CREATING:'支付页面创建中，暂勿重复操作',CHECKOUT_READY:'支付页面已准备，付款仍需核验',UNCERTAIN:'支付页面创建结果待确认，请先核验',FULFILLED:'付款已核验',REFUNDED:'退款已核验，本订单权益已停用',DISPUTED:'付款存在争议，本订单权益已停用',REVIEW_REQUIRED:'付款需进一步核对，本订单权益已暂停',EXPIRED:'报价已到期'};

export function MemberCommerce({disabled=false}:{disabled?:boolean}){
 const [expanded,setExpanded]=useState(false),[catalog,setCatalog]=useState<Catalog|null>(null),[orders,setOrders]=useState<Order[]>([]),[historyAvailable,setHistoryAvailable]=useState(false);
 const [loading,setLoading]=useState(false),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const [accepted,setAccepted]=useState<string|null>(null),[checkout,setCheckout]=useState<{order:string;url:string}|null>(null);
 const [observedNow,setObservedNow]=useState(Date.now);
 const now=Math.max(observedNow,Date.now());
 const blocked=useRef(disabled);blocked.current=disabled;
 const wasDisabled=useRef(disabled),active=useRef(true),locked=useRef(false),epoch=useRef(0),flight=useRef<AbortController|null>(null),keys=useRef(new Map<string,{key:string;order?:string}>());
 useEffect(()=>{active.current=true;return()=>{active.current=false;epoch.current++;flight.current?.abort()}},[]);
 useEffect(()=>{
  const previous=wasDisabled.current;wasDisabled.current=disabled;
  if(disabled){epoch.current++;flight.current?.abort();flight.current=null;locked.current=false;setBusy(false);setLoading(false);setCheckout(null);setAccepted(null);setOrders([]);setHistoryAvailable(false);setMessage('');setError('')}
  else if(previous&&expanded)void load();
 },[disabled,expanded]);
 useEffect(()=>{
  if(!expanded||disabled)return;
  const update=()=>setObservedNow(previous=>Math.max(previous,Date.now()));
  const current=Math.max(observedNow,Date.now());
  if(orders.some(order=>!terminalOrder(order)&&order.expires_at*1000<=current&&order.expires_at*1000>observedNow))update();
  const deadlines=orders.filter(order=>!terminalOrder(order)&&quoteOpen(order,current)).map(order=>order.expires_at*1000);
  const timer=deadlines.length?setTimeout(update,Math.min(Math.min(...deadlines)-current,2147483647)):undefined;
  // Background timers can be suspended. Recheck on resume without a payment
  // request, and never revive an observed expiry if the client clock retreats.
  window.addEventListener('focus',update);document.addEventListener('visibilitychange',update);
  return()=>{clearTimeout(timer);window.removeEventListener('focus',update);document.removeEventListener('visibilitychange',update)};
 },[disabled,expanded,orders,observedNow]);
 async function load(){
  if(blocked.current)return;
  const token=++epoch.current;flight.current?.abort();const controller=new AbortController();flight.current=controller;const timeout=setTimeout(()=>controller.abort(),15000);
  setLoading(true);setError('');setMessage('');setCheckout(null);
  const [offers,history]=await Promise.allSettled([api<Catalog>('/v1/billing/catalog',undefined,controller.signal),api<{available:boolean;orders:Order[]}>('/v1/billing/orders',undefined,controller.signal)]);
  clearTimeout(timeout);if(!active.current||blocked.current||token!==epoch.current)return;
  if(offers.status==='fulfilled'){setCatalog(offers.value);setAccepted(null)}else{setCatalog(null);setError('暂时无法读取套餐，请重新读取；不会自动创建订单')}
  if(history.status==='fulfilled'){setOrders(history.value.orders);setHistoryAvailable(history.value.available)}else{setHistoryAvailable(false);setError('暂时无法读取订单，请重新读取，勿重复付款')}
  setLoading(false);if(flight.current===controller)flight.current=null;
 }
 async function action(work:(signal:AbortSignal)=>Promise<void>){
  if(locked.current||blocked.current)return;locked.current=true;setBusy(true);setError('');setMessage('');setCheckout(null);
  const token=++epoch.current;flight.current?.abort();const controller=new AbortController();flight.current=controller;const timeout=setTimeout(()=>controller.abort(),15000);
  try{await work(controller.signal)}catch{if(active.current&&token===epoch.current)setError(controller.signal.aborted?'结果尚未确认，请重新读取订单并核验，勿重复付款；不会自动重试':'订单操作未确认，请重新读取订单后核验，勿重复付款')}
  finally{clearTimeout(timeout);if(flight.current===controller){flight.current=null;locked.current=false;if(active.current&&token===epoch.current)setBusy(false)}}
 }
 async function prepare(order:Order,signal:AbortSignal){
  if(!canPrepare(order,Math.max(observedNow,Date.now()))){setMessage(quoteOpen(order,Math.max(observedNow,Date.now()))?'请查看或核验原订单；不会重新准备支付。':expiredQuote);return}
  const value=await api<{checkout_url:string}>(`/v1/billing/orders/${encodeURIComponent(order.order_id)}/checkout`,{},signal);
  if(!active.current||blocked.current||signal.aborted)return;
  const url=new URL(value.checkout_url);if(url.protocol!=='https:'||url.username||url.password||url.hash)throw new Error('Invalid destination');
  const latest=await api<Order>(`/v1/billing/orders/${encodeURIComponent(order.order_id)}`,undefined,signal);
  if(!active.current||blocked.current||signal.aborted)return;
  setOrders(rows=>[latest,...rows.filter(row=>row.order_id!==latest.order_id)]);
  if(!quoteOpen(latest,Math.max(observedNow,Date.now()))){setMessage(expiredQuote);return}
  if(latest.state!=='CHECKOUT_READY'){setMessage('订单状态已更新，请查看或核验原订单；不会重新准备支付。');return}
  setCheckout({order:latest.order_id,url:value.checkout_url});
 }
 async function purchase(offer:Offer){
  const id=offer.plan_id+':'+offer.version;if(accepted!==id)return;
  await action(async signal=>{
   let attempt=keys.current.get(id);const previous=orders.find(order=>order.order_id===attempt?.order);
   // Only another explicit purchase can replace a known terminal/expired
   // quote. A lost creation response retains its original idempotency key.
   if(previous&&(terminalOrder(previous)||!quoteOpen(previous,Math.max(observedNow,Date.now()))))attempt=undefined;
   if(!attempt){attempt={key:crypto.randomUUID()};keys.current.set(id,attempt)}
   const order=await api<Order>('/v1/billing/orders',{plan_id:offer.plan_id,version:offer.version,idempotency_key:attempt.key,terms_digest:offer.terms_digest},signal);
   if(!active.current||blocked.current||signal.aborted)return;setOrders(rows=>[order,...rows.filter(row=>row.order_id!==order.order_id)]);setHistoryAvailable(true);
   attempt.order=order.order_id;
   await prepare(order,signal);
  });
 }
 async function verify(order:string){
  await action(async signal=>{
   const value=await api<Order>(`/v1/billing/orders/${encodeURIComponent(order)}/reconcile`,{},signal);
   if(!active.current||blocked.current||signal.aborted)return;setOrders(rows=>rows.map(row=>row.order_id===value.order_id?value:row));
   setMessage(value.verification_deferred?'核验暂时受限，请稍后再次核验此订单；不会自动重复支付或查询':value.state==='FULFILLED'?'付款已由服务器核验。会员状态正在重新读取；已有草稿与历史保留。':value.state==='REFUNDED'||value.state==='DISPUTED'||value.state==='REVIEW_REQUIRED'?'付款状态已更新，请查看本订单权益。':'付款尚未完成或核验仍在处理中，请勿重复付款。');
   if(value.state==='FULFILLED'){keys.current.delete(value.plan_id+':'+value.plan_version)}
   window.dispatchEvent(new Event('hcla-member-status-refresh'));
  });
 }
 const checkoutOrder=checkout?orders.find(order=>order.order_id===checkout.order):undefined;
 function guardCheckoutClick(event:React.MouseEvent<HTMLAnchorElement>){
  if(!checkoutOrder||!quoteOpen(checkoutOrder,Math.max(observedNow,Date.now()))){event.preventDefault();setObservedNow(previous=>Math.max(previous,Date.now()));setMessage(expiredQuote)}
 }
 return <section aria-label="会员购买与订单" className="member-commerce"><h3>会员购买与订单</h3>
  <p>账号注册、付款核验与模型额度分别检查。不会自动扣款或自动续费。</p>{disabled&&<p role="status">正在恢复或退出账号，订单操作暂时不可用。</p>}
  <button aria-expanded={expanded} disabled={busy||disabled} onClick={()=>{setExpanded(value=>!value);if(!expanded)void load()}}>{expanded?'收起购买与订单':'查看购买与订单'}</button>
  {expanded&&<>
   {loading&&<p role="status">正在读取套餐与订单…</p>}{error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}
   {catalog&&!catalog.available&&<p>{catalog.reason||'会员购买尚未开放'}</p>}
   {catalog?.available&&<><p>平台所有获准用户与测试共用每月 ¥500 模型额度，按北京时间自然月计算；额度耗尽时暂停模型使用，不承诺无限使用。</p>
    {catalog.plans.map(offer=>{const id=offer.plan_id+':'+offer.version;const unfinished=orders.some(order=>order.plan_id===offer.plan_id&&order.plan_version===offer.version&&quoteOpen(order,now)&&['PENDING','CREATING','CHECKOUT_READY','UNCERTAIN'].includes(order.state));return <article key={id} aria-label={offer.title}><h4>{offer.title}</h4><p>{money(offer.amount_minor)}，{offer.duration_days} 天。主动续费会衔接已有有效会员周期，不会自动扣款。</p>
     <p>每个北京时间自然月最多 {offer.max_requests} 次、¥{offer.max_cost_cny} 模型额度，同时受平台共享总额度限制。{offer.temporary?'支持临时对话。':''}{offer.persistent?'支持保存对话。':''}</p>
     {unfinished&&<p>这个套餐已有未完成订单，请先在下方继续或核验原订单，避免重复付款。</p>}
     <label><input type="checkbox" checked={accepted===id} disabled={busy||loading||disabled} onChange={event=>setAccepted(event.target.checked?id:null)}/>我已核对 {offer.title} 的价格、期限、额度与共享额度到限暂停说明</label>
     <button disabled={busy||loading||disabled||!historyAvailable||unfinished||accepted!==id} onClick={()=>void purchase(offer)}>创建订单并准备支付</button></article>})}</>}
   {checkout&&!disabled&&checkoutOrder?.state==='CHECKOUT_READY'&&quoteOpen(checkoutOrder,now)&&<p role="status">支付页已准备。<a href={checkout.url} target="_blank" rel="noopener noreferrer" onClick={guardCheckoutClick} onAuxClick={guardCheckoutClick}>在支付服务打开订单</a> 完成后回到这里核验；打开页面不代表已付款。</p>}
   {historyAvailable&&<><h4>最近订单</h4>{orders.length===0?<p>当前账号暂无订单。</p>:<ul>{orders.map(order=><li key={order.order_id}><p>{money(order.amount_minor)} · {orderLabels[order.state]||'订单状态待核验'}</p><p>订单号：{order.order_id}</p>
    {order.verification_state==='VERIFIED_FAILED'&&order.state!=='FULFILLED'&&<p>支付服务尚未确认成功付款，会员未开通。</p>}
    {order.access_starts_at&&order.access_expires_at?<p>本订单权益：{date(order.access_starts_at)} 至 {date(order.access_expires_at)}（北京时间）。{order.access_enabled===false?'已停用。':''}</p>:<p>报价有效期至 {date(order.expires_at)}（北京时间）。过期后请勿付款；若已付款，请核验原订单。</p>}
    {!terminalOrder(order)&&!quoteOpen(order,now)&&<p role="status">{expiredQuote}</p>}
    {canPrepare(order,now)&&<button disabled={busy||loading||disabled} onClick={()=>void action(signal=>prepare(order,signal))}>准备或打开此订单支付页</button>}
    {order.state!=='PENDING'&&<button disabled={busy||loading||disabled} onClick={()=>void verify(order.order_id)}>核验此订单付款</button>}
   </li>)}</ul>}</>}
   <button disabled={busy||loading||disabled} onClick={()=>void load()}>重新读取套餐与订单</button>
  </>}
 </section>;
}
