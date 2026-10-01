"""Original offline model bytes; never opens a socket or uses a provider key."""
import json
from tests.support.live_server import FakeTransport

class CloudFakeTransport(FakeTransport):
    def post(self,body,headers):
        status,metadata=super().post(body,headers)
        requested=json.loads(body)['model']
        self.data=self.data.replace(b'offline-explicit-model',requested.encode())
        return status,metadata
