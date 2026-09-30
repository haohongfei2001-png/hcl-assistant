"""TEMPORARY conversations and all of their bodies live only in process memory."""
from packages.store.ledger import Ledger, Fault


class Stores:
    def __init__(self, persistent):
        self.persistent=persistent
        self.temporary=Ledger()

    def conversation(self, tenant, **kwargs):
        if kwargs.get('memory')=='TEMPORARY':
            if kwargs.get('topic_id'): raise Fault(403,'Temporary conversations cannot join persistent Topics')
            return self.temporary.conversation(tenant,**kwargs)
        return self.persistent.conversation(tenant,**kwargs)

    def for_conversation(self, tenant, identity):
        try: self.temporary.get(tenant,'conversation',identity); return self.temporary
        except Fault: self.persistent.get(tenant,'conversation',identity); return self.persistent

    def for_run(self, tenant, identity):
        try: self.temporary.get(tenant,'run',identity); return self.temporary
        except Fault: self.persistent.get(tenant,'run',identity); return self.persistent

    def conversations(self, tenant):
        return self.persistent.list(tenant,'conversation')+self.temporary.list(tenant,'conversation')
