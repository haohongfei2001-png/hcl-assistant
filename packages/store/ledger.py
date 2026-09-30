"""Synthetic SQLite ledger. All mutations are atomic and tenant scoped."""
from __future__ import annotations
import hashlib
import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone


def now():
    return datetime.now(timezone.utc).isoformat()


def uid():
    return uuid.uuid4().hex


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'))


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


class Fault(ValueError):
    def __init__(self, status, message):
        self.status = status
        super().__init__(message)


class Ledger:
    def __init__(self, path=':memory:'):
        self.db = sqlite3.connect(path, isolation_level=None, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.lock = threading.RLock()
        self.volatile = path == ':memory:'
        self.db.executescript('''
        PRAGMA foreign_keys=ON;
        PRAGMA secure_delete=ON;
        CREATE TABLE IF NOT EXISTS accounts(tenant TEXT PRIMARY KEY, version INTEGER NOT NULL DEFAULT 0, policy INTEGER NOT NULL DEFAULT 0);
        CREATE TABLE IF NOT EXISTS objects(id TEXT PRIMARY KEY, tenant TEXT NOT NULL, type TEXT NOT NULL, body TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS objects_scope ON objects(tenant,type);
        CREATE TABLE IF NOT EXISTS sources(id TEXT, tenant TEXT, version INTEGER, body TEXT NOT NULL, PRIMARY KEY(id,version));
        CREATE TABLE IF NOT EXISTS events(id TEXT PRIMARY KEY, tenant TEXT, conversation TEXT, version INTEGER, body TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS idempotency(tenant TEXT, conversation TEXT, key TEXT, hash TEXT NOT NULL, result TEXT NOT NULL, PRIMARY KEY(tenant,conversation,key));
        CREATE TABLE IF NOT EXISTS records(id TEXT, tenant TEXT, version INTEGER, body TEXT NOT NULL, PRIMARY KEY(id,version));
        CREATE TABLE IF NOT EXISTS tombstones(id TEXT PRIMARY KEY, tenant TEXT NOT NULL);
        PRAGMA user_version=1;
        ''')

    def close(self):
        self.db.close()

    @contextmanager
    def transaction(self):
        with self.lock:
            self.db.execute('BEGIN IMMEDIATE')
            try:
                yield
                self.db.execute('COMMIT')
            except BaseException:
                self.db.execute('ROLLBACK')
                raise

    def account(self, tenant):
        self.db.execute('INSERT OR IGNORE INTO accounts(tenant) VALUES(?)', (tenant,))
        return dict(self.db.execute('SELECT * FROM accounts WHERE tenant=?', (tenant,)).fetchone())

    def version(self, tenant):
        return self.account(tenant)['version']

    def put(self, tenant, typ, body):
        body = dict(body)
        body.setdefault('id', uid())
        body.setdefault('schema_version', '1.0')
        body.setdefault('created_at', now())
        body['tenant_id'] = tenant
        self.db.execute('INSERT OR REPLACE INTO objects VALUES(?,?,?,?)', (body['id'], tenant, typ, canonical(body)))
        return body

    def get(self, tenant, typ, identity):
        row = self.db.execute('SELECT body FROM objects WHERE id=? AND tenant=? AND type=?', (identity, tenant, typ)).fetchone()
        if not row:
            raise Fault(403, 'Object is unavailable in this account')
        return json.loads(row['body'])

    def list(self, tenant, typ):
        return [json.loads(r['body']) for r in self.db.execute('SELECT body FROM objects WHERE tenant=? AND type=? ORDER BY rowid', (tenant, typ))]

    def topic(self, tenant, title):
        with self.transaction():
            self.account(tenant)
            return self.put(tenant, 'topic', {'title': title})

    def conversation(self, tenant, title='新对话', topic_id=None, memory='CONVERSATION'):
        if memory == 'TEMPORARY' and not self.volatile:
            raise Fault(403, 'Temporary conversations require the volatile store')
        if memory not in {'TEMPORARY', 'CONVERSATION', 'TOPIC'}:
            raise Fault(403, 'Cross-topic reuse is not implemented')
        with self.transaction():
            self.account(tenant)
            if topic_id:
                self.get(tenant, 'topic', topic_id)
            if memory == 'TOPIC' and not topic_id:
                raise Fault(400, 'Topic membership required')
            return self.put(tenant, 'conversation', {'title': title, 'topic_id': topic_id, 'memory': memory})

    def scope(self, tenant, conversation, topic_id=None):
        obj = self.get(tenant, 'conversation', conversation)
        if obj['topic_id'] != topic_id:
            raise Fault(403, 'Conversation/topic mismatch')
        return obj

    def source(self, tenant, ref, conversation=None, topic_id=None):
        row = self.db.execute('SELECT body FROM sources WHERE id=? AND tenant=? AND version=?', (ref['source_id'], tenant, ref['version'])).fetchone()
        if not row:
            raise Fault(403, 'Source unavailable')
        obj = json.loads(row['body'])
        if obj.get('deleted') or obj['sha256'] != ref.get('sha256', ref.get('content_sha256')):
            raise Fault(409, 'Source hash/version mismatch')
        if conversation and obj['conversation_id'] != conversation and not (obj['memory'] == 'TOPIC' and topic_id and obj['topic_id'] == topic_id):
            raise Fault(403, 'Source outside allowed scope')
        span = ref.get('span')
        if span and not (0 <= span[0] <= span[1] <= len(obj['text'])):
            raise Fault(400, 'Invalid exact span')
        return obj

    def write_source(self, tenant, conversation, topic_id, text, name='message', source_id=None, family=None, memory='CONVERSATION'):
        self.scope(tenant, conversation, topic_id)
        if not isinstance(text, str) or len(text.encode()) > 65536:
            raise Fault(413, 'Text limit: 64 KiB')
        if name != 'message' and not name.lower().endswith(('.txt', '.md')):
            raise Fault(400, 'Only TXT/Markdown supported')
        identity = source_id or uid()
        versions = self.db.execute('SELECT body FROM sources WHERE id=? ORDER BY version DESC', (identity,)).fetchall()
        if versions:
            old = json.loads(versions[0]['body'])
            if old['tenant_id'] != tenant or old['conversation_id'] != conversation:
                raise Fault(403, 'Source ownership mismatch')
        version = len(versions) + 1
        obj = {'schema_version':'1.0', 'id':identity, 'source_id':identity, 'tenant_id':tenant, 'conversation_id':conversation, 'topic_id':topic_id, 'memory':memory, 'version':version, 'parse_version':1, 'parse_source_version':version, 'sha256':digest(text), 'text':text, 'name':name, 'family':family or (json.loads(versions[0]['body'])['family'] if versions else identity), 'created_at':now(), 'coverage':'PARTIAL', 'deleted':False}
        self.db.execute('INSERT INTO sources VALUES(?,?,?,?)', (identity, tenant, version, canonical(obj)))
        return obj

    def atomic(self, tenant, conversation, key, payload, expected, work):
        if not isinstance(key, str) or not key or len(key) > 200:
            raise Fault(400, 'Idempotency key required')
        payload_hash = digest(canonical(payload))
        with self.transaction():
            old = self.db.execute('SELECT * FROM idempotency WHERE tenant=? AND conversation=? AND key=?', (tenant, conversation, key)).fetchone()
            if old:
                if old['hash'] != payload_hash:
                    raise Fault(409, 'Idempotency payload conflict')
                return json.loads(old['result'])
            if type(expected) is not int or expected != self.version(tenant):
                raise Fault(409, 'State version conflict')
            result = work(expected + 1)
            self.db.execute('UPDATE accounts SET version=version+1 WHERE tenant=?', (tenant,))
            self.db.execute('INSERT INTO idempotency VALUES(?,?,?,?,?)', (tenant, conversation, key, payload_hash, canonical(result)))
            return result

    def append(self, tenant, conversation, topic_id, text, expected, key, name='message', fail=False):
        payload = {'text':text, 'topic_id':topic_id, 'name':name}
        def work(version):
            source = self.write_source(tenant, conversation, topic_id, text, name)
            if fail:
                raise RuntimeError('Injected transaction interruption')
            event = {'id':uid(), 'schema_version':'1.0', 'tenant_id':tenant, 'conversation_id':conversation, 'topic_id':topic_id, 'source_refs':[{'source_id':source['id'],'version':source['version'],'sha256':source['sha256']}], 'recorded_at':now(), 'state_version':version, 'status':'UNRESOLVED'}
            self.db.execute('INSERT INTO events VALUES(?,?,?,?,?)', (event['id'], tenant, conversation, version, canonical(event)))
            return {'event':event, 'source':source, 'state_version':version}
        return self.atomic(tenant, conversation, key, payload, expected, work)

    def history(self, tenant, conversation):
        self.get(tenant, 'conversation', conversation)
        return [json.loads(r['body']) for r in self.db.execute('SELECT body FROM events WHERE tenant=? AND conversation=? ORDER BY version', (tenant, conversation))]

    def revise(self, *args, **kwargs):
        raise Fault(422, 'Revision not implemented; original text is preserved')
