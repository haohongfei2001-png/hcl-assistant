"""Opaque scope/version-bound cursors, never permission credentials."""
import base64
import json
from packages.store.ledger import Fault, canonical, digest


def page(items, tenant, version, policy, limit, cursor=None, scope=''):
    if not 1<=limit<=100: raise Fault(400,'Page limit must be 1..100')
    binding=digest(canonical([tenant,scope,version,policy])); offset=0
    if cursor:
        try:
            decoded=json.loads(base64.urlsafe_b64decode(cursor.encode()))
            if decoded['binding']!=binding: raise Fault(409,'Cursor scope/state/policy changed; restart paging')
            offset=decoded['offset']
            if type(offset) is not int or offset<0: raise ValueError()
        except (ValueError,KeyError,TypeError): raise Fault(400,'Invalid opaque cursor')
    next_offset=offset+limit
    next_cursor=base64.urlsafe_b64encode(canonical({'binding':binding,'offset':next_offset}).encode()).decode() if next_offset<len(items) else None
    return {'items':items[offset:next_offset],'next_cursor':next_cursor,'state_version':version,'policy_revision':policy}
