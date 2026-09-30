import json
import threading
import unittest
import urllib.request
import urllib.error
from apps.api.server import Application, serve


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.app=Application(); self.server=serve(self.app,0); self.thread=threading.Thread(target=self.server.serve_forever,daemon=True); self.thread.start(); self.base='http://127.0.0.1:'+str(self.server.server_port)
    def tearDown(self): self.server.shutdown(); self.server.server_close(); self.thread.join(); self.app.close()
    def call(self,path,body=None,identity='demo-a'):
        req=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Content-Type':'application/json','X-Synthetic-Identity':identity})
        with urllib.request.urlopen(req) as response: return json.load(response)
    def test_http_sse_reconnect_no_invocation_and_tenant_isolation(self):
        c=self.call('/v1/conversations',{})['id']
        body={'scope':{'topic_id':None},'event':{'text':'2+2'},'expected_state_version':0,'idempotency_key':'one'}
        run=self.call('/v1/conversations/'+c+'/events',body)
        with urllib.request.urlopen(self.base+'/v1/runs/'+run['run_id']+'/events') as res: text=res.read().decode()
        self.assertIn('answer.completed',text)
        with urllib.request.urlopen(self.base+'/v1/runs/'+run['run_id']+'/events?after=99') as res: self.assertEqual(res.read(),b'')
        self.assertEqual(self.call('/v1/conversations/'+c)['state_version'],1)
        with self.assertRaises(urllib.error.HTTPError) as cm: self.call('/v1/conversations/'+c,identity='demo-b')
        self.assertEqual(cm.exception.code,403)
        self.assertEqual(next(iter(self.app.controllers.values())).adapter.invocations,0)
    def test_half_json_and_unknown_api_do_not_commit(self):
        req=urllib.request.Request(self.base+'/v1/conversations',data=b'{"title":',method='POST')
        with self.assertRaises(urllib.error.HTTPError) as cm: urllib.request.urlopen(req)
        self.assertEqual(cm.exception.code,400)
        self.assertEqual(self.call('/v1/conversations'),[])
        with self.assertRaises(urllib.error.HTTPError): self.call('/v1/provider',{})
