"""Durable request ownership. Expiry is UNKNOWN, never permission to replay."""
import threading
import time
from packages.store.ledger import Fault, now, uid
from packages.controller.interaction import Controller

LEASE_SECONDS=120  # Adapter wall deadline is 60s; Vercel maxDuration is 300s.

class Lifecycle:
    def __init__(self, store): self.store=store
    def recover(self):
        with self.store.transaction():
            rows=self.store.db.execute('SELECT run_id FROM execution WHERE expires_at <= clock_timestamp() AND finished=false').fetchall()
            for row in rows:
                identity=row['run_id']
                self.store.db.execute("UPDATE execution SET finished=true, owner='' WHERE run_id=?",(identity,))
                try: run=self.store.get(self.store.tenant,'run',identity)
                except Fault: continue  # Temporary bodies were never stored.
                if run['pending']:
                    run.update(pending=False,answer=None,errors=['REQUEST_INTERRUPTED_UNKNOWN'])
                    run['stream']=[e for e in run['stream'] if not e['type'].startswith('answer.')]
                    run['run_receipt'].update(outcome='UNKNOWN',errors=run['errors'],finished_at=now())
                    Controller.emit(run,'run.failed',{'reason':'Request interrupted; provider is never replayed'})
                    self.store.put(self.store.tenant,'run',run)
            # active reservations remain blocked, even after lease expiry.
    def claim(self, run_id, payload_hash=None, temporary=False):
        with self.store.transaction():
            old=self.store.db.execute('SELECT * FROM execution WHERE run_id=?',(run_id,)).fetchone()
            if old:
                if payload_hash is not None and old['payload_hash'] != payload_hash: raise Fault(409,'Idempotency payload conflict')
                return None
            owner=uid()
            self.store.db.execute('INSERT INTO execution(run_id,owner,expires_at,payload_hash,temporary) VALUES(?,?,clock_timestamp() + (? * interval \'1 second\'),?,?)',(run_id,owner,LEASE_SECONDS,payload_hash,temporary))
            return owner
    def finish(self, run_id, owner):
        with self.store.transaction():
            self.store.db.execute('UPDATE execution SET finished=true WHERE run_id=? AND owner=?',(run_id,owner))
    def cancel_temporary(self, run_id):
        with self.store.transaction():
            self.store.db.execute('UPDATE execution SET cancelled=true WHERE run_id=? AND temporary=true',(run_id,))

class DurableCancellation:
    """Adapter event-compatible bounded DB probe, including silent thinking.

    DB uncertainty cancels fail-closed. Checks run on both adapter threads; the
    ledger guard serializes one request connection. There is no background poller.
    """
    def __init__(self, store, run_id, temporary=False):
        self.store=store;self.run_id=run_id;self.temporary=temporary
        self.local=threading.Event();self._lock=threading.RLock();self.next_check=0
    def set(self): self.local.set()
    def is_set(self):
        if self.local.is_set(): return True
        if time.monotonic() < self.next_check: return self.local.is_set()
        try:
            # Lock order matches Controller callbacks on the adapter main thread.
            with self.store.lock, self._lock:
                if time.monotonic() < self.next_check: return self.local.is_set()
                self.next_check=time.monotonic()+.25
                row=self.store.db.execute('SELECT cancelled FROM execution WHERE run_id=?',(self.run_id,)).fetchone()
                stopped=row is None or row['cancelled']
                if not self.temporary:
                    run=self.store.get(self.store.tenant,'run',self.run_id)
                    stopped=stopped or not run['pending'] or self.store.version(self.store.tenant)!=run['state_version_after'] or self.store.account(self.store.tenant)['policy']!=run['selected_context']['policy_revision']
                if stopped: self.local.set()
        except Exception: self.local.set()
        return self.local.is_set()
