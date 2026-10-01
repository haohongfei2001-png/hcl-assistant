"""Tenant-local session revocation, with server-owned ordering tickets."""
from packages.store.ledger import Fault


def ticket(store):
    with store.transaction():
        return int(store.db.execute("SELECT nextval('hcla.member_auth_order') AS ticket").fetchone()['ticket'])


def current(store):
    if not store.tenant.startswith('member-'):raise Fault(401,'Account sign-in required')
    with store.transaction():
        return store.db.execute('SELECT generation,terminal_ticket,reset_pending,reset_phase,uncertainty_ticket FROM member_auth_generations WHERE tenant=?',(store.tenant,)).fetchone() or {'generation':0,'terminal_ticket':0,'reset_pending':False,'reset_phase':'idle','uncertainty_ticket':0}


def require(store,generation,login_ticket=None):
    value=current(store)
    if value['reset_pending'] or value['generation']!=generation or (login_ticket is not None and login_ticket<=value['terminal_ticket']):
        raise Fault(401,'Account session changed; sign in again')
    return value['generation']


def claim_reset(store,owner,bound_generation):
    with store.transaction():
        previous=current(store)
        if previous['reset_pending']:
            raise Fault(409,'上次密码修改尚未确认，恢复暂时锁定，请联系管理员核对服务端结果')
        if previous['generation']!=bound_generation:raise Fault(401,'恢复验证已失效，请重新申请链接')
        started=ticket(store)
        row=store.db.execute("INSERT INTO member_auth_generations(tenant,generation,terminal_ticket,reset_pending,reset_owner,reset_phase) VALUES(?,1,?,true,?,'updating') ON CONFLICT(tenant) DO UPDATE SET generation=member_auth_generations.generation+1,terminal_ticket=GREATEST(member_auth_generations.terminal_ticket,EXCLUDED.terminal_ticket),reset_pending=true,reset_owner=EXCLUDED.reset_owner,reset_phase='updating',uncertainty_ticket=0 RETURNING generation",(store.tenant,started,owner)).fetchone()
        return row['generation']


def finish_reset(store,generation,owner):
    with store.transaction():
        ended=ticket(store)
        changed=store.db.execute("UPDATE member_auth_generations SET terminal_ticket=?,reset_pending=false,reset_owner=NULL,reset_phase='idle' WHERE tenant=? AND generation=? AND reset_owner=? AND reset_pending=true RETURNING generation",(ended,store.tenant,generation,owner)).fetchone()
        if changed is None:raise Fault(401,'Recovery was superseded; request a new link')


def mark_uncertain(store,generation,owner):
    with store.transaction():
        marker=ticket(store)
        store.db.execute("UPDATE member_auth_generations SET reset_phase='uncertain',uncertainty_ticket=? WHERE tenant=? AND generation=? AND reset_owner=? AND reset_pending=true AND reset_phase='updating'",(marker,store.tenant,generation,owner))
