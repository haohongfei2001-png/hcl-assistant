"""Recovery-only PKCE state; no product access or automatic mutation retries."""
import base64
import hashlib
import hmac
from http.cookies import SimpleCookie,CookieError
import re
import secrets
import uuid
from packages.cloud.member_auth import VerifiedRecovery,VerifiedPrincipal,PasswordMutationRejected
from packages.cloud.session_vault import SessionVault
from packages.cloud import auth_generation
from packages.store.ledger import Fault

COOKIE='__Host-hcla-recovery'
DEADLINE=900

class RecoveryVault(SessionVault):
    PURPOSE=b'hcla-member-recovery-v1'
    MAX_MATERIAL=16384
    MAX_ENVELOPE=24000

class RecoveryAuth:
    def __init__(self,member_auth,state_key):
        self.member=member_auth;self.store=member_auth.store;self.provider=member_auth.provider
        self.origin=member_auth.origin;self.host=member_auth.host;self.boundary=member_auth.boundary
        self._key=bytes.fromhex(state_key);self.vault=RecoveryVault(state_key)
        self.epoch=hmac.new(self._key,b'hcla-recovery-epoch-v1',hashlib.sha256).hexdigest()
        self.redirect=self.origin+'/account/recovery'

    def identity(self,email):
        if not isinstance(email,str) or len(email)>254 or not re.fullmatch(r'[^\s@]{1,128}@[^\s@]{1,125}\.[^\s@]{1,63}',email):
            raise Fault(400,'请输入有效的邮箱地址')
        return hmac.new(self._key,('recovery-email\n'+email.casefold()).encode(),hashlib.sha256).hexdigest()

    def key(self,cookie):
        try:
            parsed=SimpleCookie();parsed.load(cookie or '');token=parsed[COOKIE].value
            if not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):raise ValueError()
            return hashlib.sha256(token.encode()).hexdigest()
        except (KeyError,ValueError,CookieError):raise Fault(401,'恢复链接无效或已过期，请重新申请') from None

    def row(self,key):
        self.store.recovery_session_key=key
        with self.store.transaction():
            return self.store.db.execute('SELECT *,FLOOR(EXTRACT(EPOCH FROM expires_at))::bigint AS deadline,FLOOR(EXTRACT(EPOCH FROM access_expires_at))::bigint AS access_deadline FROM member_recovery WHERE request_key=? AND issuer=? AND auth_epoch=? AND expires_at>clock_timestamp()',(key,self.provider.issuer,self.epoch)).fetchone()

    def begin(self,data,previous_cookie=None):
        if not isinstance(data,dict) or set(data)!={'email'}:raise Fault(400,'请输入邮箱地址')
        email=data['email'];identity=self.identity(email);self.member.throttle(email,'recovery')
        try:old=self.key(previous_cookie)
        except Fault:old=None
        token=secrets.token_urlsafe(32);key=hashlib.sha256(token.encode()).hexdigest();verifier=secrets.token_urlsafe(48)
        challenge=base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip('=')
        with self.store.transaction():
            self.store.db.execute("SELECT set_config('hcla.recovery_gc','on',true)")
            self.store.db.execute("DELETE FROM member_recovery WHERE expires_at<=clock_timestamp() AND phase<>'updating'")
            self.store.db.execute("SELECT set_config('hcla.recovery_gc','off',true)")
        if old:
            self.store.recovery_session_key=old
            with self.store.transaction():self.store.db.execute("DELETE FROM member_recovery WHERE request_key=? AND phase<>'updating'",(old,))
        self.store.recovery_session_key=key
        with self.store.transaction():
            deadline=int(self.member.clock())+DEADLINE;started=auth_generation.ticket(self.store)
            encrypted=self.vault.seal(verifier,self.provider.issuer,'pkce:'+identity,key,deadline)
            self.store.db.execute("INSERT INTO member_recovery(request_key,identity_key,issuer,auth_epoch,start_ticket,expires_at,phase,secret_ciphertext) VALUES(?,?,?,?,?,to_timestamp(?),'requested',?)",(key,identity,self.provider.issuer,self.epoch,started,deadline,encrypted))
        try:self.provider.request_recovery(email,challenge,self.redirect)
        except Exception:pass # Same response/cookie/state; never expose provider text or account existence.
        return token,{'requested':True,'expires_at':deadline,'message':'如果该邮箱可以找回账号，你会收到恢复链接。请在当前浏览器打开；本次申请15分钟内有效。未收到时可稍后重新申请。'}

    def status(self,cookie):
        try:row=self.row(self.key(cookie))
        except Fault:row=None
        if row is None:return {'available':True,'ready':False,'requested':False}
        ready=row['phase']=='ready' and row['access_deadline'] and row['access_deadline']>self.member.clock()
        locked=False;stale=False
        if row['tenant'] and row['subject']:
            principal=VerifiedPrincipal(row['issuer'],str(row['subject']),row['deadline']);self.store.bind_member(principal)
            generation=auth_generation.current(self.store);locked=bool(generation['reset_pending']);stale=row['bound_generation']!=generation['generation']
            if locked or stale:ready=False
        return {'available':True,'ready':bool(ready),'locked':locked,'requested':row['phase']=='requested',
                'updated':row['outcome']=='updated','restart_required':not locked and row['outcome']!='updated' and (stale or row['phase'] in ('used','uncertain','exchanging','updating')),
                'expires_at':min(row['deadline'],row['access_deadline'] or row['deadline'])}

    def verified(self,value,identity):
        if not isinstance(value,VerifiedRecovery) or not isinstance(value.principal,VerifiedPrincipal):raise Fault(401,'恢复验证未通过')
        principal=value.principal
        try:subject=str(uuid.UUID(principal.subject))
        except (ValueError,TypeError,AttributeError):raise Fault(401,'恢复验证未通过') from None
        if (subject!=principal.subject or principal.issuer!=self.provider.issuer or principal.expires_at<=self.member.clock()
                or not hmac.compare_digest(self.identity(value.email),identity)):
            raise Fault(401,'恢复验证未通过')
        return principal

    def exchange(self,data,cookie):
        if not isinstance(data,dict) or set(data)!={'code'}:raise Fault(400,'恢复链接无效')
        code=data['code']
        try:
            if not isinstance(code,str) or str(uuid.UUID(code))!=code:raise ValueError()
        except (ValueError,TypeError,AttributeError):raise Fault(400,'恢复链接无效') from None
        key=self.key(cookie);row=self.row(key);operation=secrets.token_hex(16)
        if row is None or row['phase']!='requested':raise Fault(401,'恢复链接已使用或已过期，请重新申请')
        with self.store.transaction():
            claimed=self.store.db.execute("UPDATE member_recovery SET phase='exchanging',operation_key=? WHERE request_key=? AND phase='requested' AND expires_at>clock_timestamp() RETURNING request_key",(operation,key)).fetchone()
            if claimed is None:raise Fault(401,'恢复链接已使用或已过期，请重新申请')
        started=row['start_ticket'];principal=None
        try:
            verifier=self.vault.open(row['secret_ciphertext'],row['issuer'],'pkce:'+row['identity_key'],key,row['deadline'])
            value=self.provider.exchange_recovery(code,verifier);principal=self.verified(value,row['identity_key'])
            self.store.bind_member(principal)
            encrypted=self.vault.seal(value.access_token,row['issuer'],'access:'+row['identity_key']+':'+principal.subject,key,row['deadline'])
            with self.store.transaction():
                generation=auth_generation.current(self.store)['generation'];auth_generation.require(self.store,generation,started)
                expires=min(principal.expires_at,int(self.member.clock())+300,row['deadline'])
                changed=self.store.db.execute("UPDATE member_recovery SET phase='ready',tenant=?,subject=?,secret_ciphertext=?,access_expires_at=to_timestamp(?),bound_generation=?,operation_key=NULL WHERE request_key=? AND phase='exchanging' AND operation_key=? AND expires_at>clock_timestamp() RETURNING request_key",(principal.tenant,principal.subject,encrypted,expires,generation,key,operation)).fetchone()
                if changed is None:raise Fault(401,'恢复链接已失效')
        except Exception:
            with self.store.transaction():
                if principal is not None and self.store.tenant==principal.tenant:
                    self.store.db.execute("UPDATE member_recovery SET tenant=?,subject=? WHERE request_key=? AND phase='exchanging' AND operation_key=?",(principal.tenant,principal.subject,key,operation))
                self.store.db.execute("UPDATE member_recovery SET phase='used',outcome='rejected',secret_ciphertext=NULL,operation_key=NULL WHERE request_key=? AND phase='exchanging' AND operation_key=?",(key,operation))
            raise Fault(401,'恢复链接无效、已使用或已过期，请在发起申请的浏览器重新申请') from None
        return self.status(cookie)

    def complete(self,data,cookie):
        if not isinstance(data,dict) or set(data)!={'password','confirmation'}:raise Fault(400,'请输入并确认新密码')
        password=data['password']
        if not isinstance(password,str) or not 12<=len(password)<=1024 or password!=data['confirmation']:
            raise Fault(400,'两次密码须一致，长度为12至1024个字符')
        key=self.key(cookie);row=self.row(key)
        if row is None or row['phase']!='ready' or not row['access_deadline'] or row['access_deadline']<=self.member.clock():
            raise Fault(401,'恢复验证已过期，请重新申请链接')
        self.member.throttle(row['identity_key'],'recovery')
        try:
            token=self.vault.open(row['secret_ciphertext'],row['issuer'],'access:'+row['identity_key']+':'+str(row['subject']),key,row['deadline'])
            principal=self.verified(self.provider.recovery_identity(token),row['identity_key'])
            if principal.subject!=str(row['subject']) or principal.tenant!=row['tenant']:raise ValueError()
        except Exception:raise Fault(401,'恢复验证未完成，请重新申请链接') from None
        self.store.bind_member(principal);operation=secrets.token_hex(16)
        with self.store.transaction():
            claimed=self.store.db.execute("UPDATE member_recovery SET phase='updating',operation_key=?,attempts=attempts+1 WHERE request_key=? AND phase='ready' AND attempts<3 AND expires_at>clock_timestamp() AND access_expires_at>clock_timestamp() RETURNING attempts",(operation,key)).fetchone()
            if claimed is None:raise Fault(401,'恢复验证已使用或已过期')
            generation=auth_generation.claim_reset(self.store,key,row['bound_generation'])
            self.store.db.execute('UPDATE member_recovery SET reset_generation=? WHERE request_key=?',(generation,key))
        try:self.provider.update_password(token,password,principal.subject)
        except PasswordMutationRejected as rejected:
            with self.store.transaction():
                retry=bool(rejected.retryable and claimed['attempts']<3)
                changed=self.store.db.execute("UPDATE member_recovery SET phase=?,outcome='rejected',bound_generation=?,secret_ciphertext=CASE WHEN ? THEN secret_ciphertext ELSE NULL END,operation_key=NULL WHERE request_key=? AND phase='updating' AND operation_key=? RETURNING request_key",('ready' if retry else 'used',generation,retry,key,operation)).fetchone()
                if changed is None:raise Fault(409,'恢复申请已变化，请继续最新的申请')
                auth_generation.finish_reset(self.store,generation,key)
            raise Fault(400 if retry else 401,'密码未更新，请使用符合要求的新密码重试，或重新申请恢复链接') from None
        except Exception:
            # A timeout cannot prove the mutation stopped. Keep the tenant
            # barrier pending for authoritative provider reconciliation. Fresh
            # mailbox control cannot prove that an old remote write stopped.
            with self.store.transaction():
                auth_generation.mark_uncertain(self.store,generation,key)
                self.store.db.execute("UPDATE member_recovery SET phase='uncertain',outcome='uncertain',secret_ciphertext=NULL,operation_key=NULL WHERE request_key=? AND phase='updating' AND operation_key=?",(key,operation))
            raise Fault(503,'无法确认密码是否已更新。现有登录已结束，恢复暂时锁定，请联系管理员核对结果') from None
        with self.store.transaction():
            changed=self.store.db.execute("UPDATE member_recovery SET phase='used',outcome='updated',secret_ciphertext=NULL,operation_key=NULL WHERE request_key=? AND phase='updating' AND operation_key=? RETURNING request_key",(key,operation)).fetchone()
            if changed is None:raise Fault(409,'恢复申请已变化，请继续最新的申请')
            auth_generation.finish_reset(self.store,generation,key)
        return {'updated':True,'message':'密码已更新，请使用新密码重新登录。'}

    @staticmethod
    def cookie(token):return COOKIE+'='+token+'; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=900'

    @staticmethod
    def clear_cookie():return COOKIE+'=; Secure; HttpOnly; SameSite=Strict; Path=/; Max-Age=0'
