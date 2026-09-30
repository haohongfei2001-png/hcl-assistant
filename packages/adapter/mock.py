"""No provider transport exists. Invocation requires a server-issued permit."""
from packages.store.ledger import Fault


class MockAdapter:
    def __init__(self):
        self._permits={}
        self.invocations=0

    def authorize(self, run_id):
        permit=object(); self._permits[permit]=run_id; return permit

    def generate(self, permit, text, simulation=None):
        if type(permit) is not object or permit not in self._permits: raise Fault(403,'Controller authorization required')
        self._permits.pop(permit); self.invocations+=1
        if simulation=='failed': raise RuntimeError('Synthetic adapter failure')
        if simulation=='unknown': raise TimeoutError('Synthetic transport result unknown')
        return text
