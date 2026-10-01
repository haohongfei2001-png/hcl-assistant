"""Hosted browser-test fixture only. All model bytes are local original fixtures."""
import json
import os
import time
from pathlib import Path
from apps.api.server import Application, serve
from apps.api.development_auth import DevelopmentAuth
from packages.adapter.development_budget import DevelopmentConfig, DevelopmentBudget
from packages.adapter.deepseek import DeepSeekAdapter
from packages.controller.live_chat import LiveChat

TOKEN='original-offline-browser-token-123456'
class FakeTransport:
    sent=False
    def __init__(self,*args):self.data=b'';self.closed=False
    def post(self,body,headers):
        self.sent=True;request=json.loads(body);messages=request['messages'];question=messages[-1]['content'];all_text=json.dumps(messages,ensure_ascii=False)
        if 'OFFLINE_ERROR' in question:return 429,{}
        answer='原创离线自然语言流程测试：可以安排一个纸灯工作坊。'
        if '"marker": "HCL1"' in messages[0]['content']:answer='Ada 明确表达了工作坊周五开始的信念。[HCL1]'
        elif '什么颜色' in question and '蓝色' in all_text:answer='按前面提供的原创合成设定，纸灯是蓝色。'
        parts=[{'id':'offline-fixture','model':'offline-explicit-model','choices':[{'delta':{'reasoning_content':'HIDDEN_REASONING_CANARY'},'finish_reason':None}]}]
        parts += [{'id':'offline-fixture','model':'offline-explicit-model','choices':[{'delta':{'content':answer[i:i+8]},'finish_reason':None}]} for i in range(0,len(answer),8)]
        parts += [{'id':'offline-fixture','model':'offline-explicit-model','choices':[{'delta':{},'finish_reason':'stop'}],'usage':{'prompt_tokens':64,'completion_tokens':24}}]
        self.data=''.join('data: '+json.dumps(p,ensure_ascii=False)+'\n\n' for p in parts).encode()+b'data: [DONE]\n\n'
        return 200,{}
    def read(self,size):
        if self.closed:return b''
        time.sleep(.015);chunk=self.data[:43];self.data=self.data[43:];return chunk
    def close(self):self.closed=True

if __name__=='__main__':
    Path('.tmp').mkdir(exist_ok=True)
    env={'HCLA_DEEPSEEK_API_KEY':'offline-fixture-key','HCLA_DEEPSEEK_BASE_URL':'https://api.deepseek.com','HCLA_DEEPSEEK_MODEL':'offline-explicit-model','HCLA_DEV_ACCESS_TOKEN':TOKEN,'HCLA_DEV_MAX_REQUESTS':'100','HCLA_DEV_MAX_COST_USD':'1','HCLA_DEV_INPUT_USD_PER_MILLION':'0.1','HCLA_DEV_OUTPUT_USD_PER_MILLION':'0.1','HCLA_DEV_MAX_OUTPUT_TOKENS':'512','HCLA_DEV_BUDGET_ID':'offline-browser-fixture'}
    config=DevelopmentConfig.from_env(env);budget=DevelopmentBudget('.tmp/live-browser-budget.sqlite',config)
    adapter=DeepSeekAdapter(base_url=config.base_url,model=config.model,api_key=config.api_key,transport_factory=FakeTransport)
    app=Application('.tmp/live-browser.sqlite',os.environ.get('HCL_DEVELOPMENT_ARTIFACT'),LiveChat(config,budget,adapter),DevelopmentAuth(TOKEN),True,{'configured':True,'missing':[],'invalid':[]})
    server=serve(app,8770)
    try:server.serve_forever()
    finally:server.server_close();app.close()
