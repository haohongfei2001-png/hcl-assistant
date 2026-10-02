"""Original offline model bytes; never opens a socket or uses a provider key."""
import json
import time
from tests.support.live_server import FakeTransport

class CloudFakeTransport(FakeTransport):
    def post(self,body,headers):
        status,metadata=super().post(body,headers)
        requested=json.loads(body)['model']
        self.data=self.data.replace(b'offline-explicit-model',requested.encode())
        self.thinking_only=any(message.get('content')=='ORIGINAL_THINKING_TIMEOUT_FIXTURE' for message in json.loads(body)['messages'])
        if self.thinking_only:
            self.data=('data: '+json.dumps({'model':requested,'choices':[{'index':0,'delta':{'reasoning_content':'OFFLINE_HIDDEN_REASONING_MUST_NOT_RENDER'}}]})+'\n\n').encode()
        return status,metadata

    def read(self,size):
        if self.closed:return b''
        if getattr(self,'thinking_only',False) and not self.data:
            time.sleep(.02)
            return b': synthetic heartbeat\n\n'
        return super().read(size)
