import React,{useEffect,useState} from 'react';
import {api} from './api';

type Budget={currency?:string;period?:string;timezone?:string;charged_cost_cny?:string;max_cost_cny?:string;remaining_cny?:string};

export function MonthlyBudget(){
 const [value,setValue]=useState<Budget|null>(null),[failed,setFailed]=useState(false),[revision,setRevision]=useState(0);
 useEffect(()=>{
  const controller=new AbortController();let active=true;
  setFailed(false);setValue(null);
  const timeout=setTimeout(()=>controller.abort(),15000);
  void api<Budget>('/v1/development/budget',undefined,controller.signal).then(result=>{if(active)setValue(result)}).catch(()=>{if(active)setFailed(true)}).finally(()=>clearTimeout(timeout));
  return()=>{active=false;clearTimeout(timeout);controller.abort()};
 },[revision]);
 if(failed)return <section><p>暂时无法读取本月额度；不会因此增加额度或重复模型请求。</p><button onClick={()=>setRevision(x=>x+1)}>重新读取额度</button></section>;
 if(!value)return <p role="status">正在读取本月额度…</p>;
 if(value.currency!=='CNY'||!value.period)return <p>人民币月额度尚未启用。</p>;
 return <section aria-label="人民币月额度"><h3>{value.period} 模型额度</h3><p>已计入额度 ¥{value.charged_cost_cny} / ¥{value.max_cost_cny}，剩余 ¥{value.remaining_cny}。</p><p>按北京时间自然月计算，测试与本人使用共用。包含未确认请求的保守预留，金额不是阿里云账单；到限停止，不自动充值。</p><button onClick={()=>setRevision(x=>x+1)}>刷新额度</button></section>;
}
