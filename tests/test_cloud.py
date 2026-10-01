"""Provider-free configuration and temporary-state unit regressions."""
import json
import os
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
from packages.cloud.auth import password_verifier,valid_verifier,check_password
from packages.cloud.config import CloudConfig,provider_from_grant
from packages.cloud.postgres import translate
from packages.cloud.temporary import pack,unpack,SYNTHETIC_TENANT
from packages.store.ledger import Ledger,Fault

class CloudUnitTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.verifier=password_verifier('offline password fixture')
    def env(self):
        return {'HCLA_DATABASE_URL':'postgresql://runtime:fixture@db.example.test/postgres?sslmode=verify-full','HCLA_PUBLIC_ORIGIN':'https://hcla.example.test','HCLA_OWNER_LOGIN':'owner','HCLA_OWNER_PASSWORD_HASH':self.verifier,'HCLA_TEMPORARY_STATE_KEY':'1'*64}
    def test_owner_verifier_has_fixed_cost_and_random_salt(self):
        self.assertTrue(valid_verifier(self.verifier));self.assertFalse(valid_verifier('scrypt$1$8$1$'+'0'*32+'$'+'0'*64))
        self.assertNotIn('offline password',self.verifier)
    def test_cloud_config_never_silently_enables_provider(self):
        config=CloudConfig.from_env(self.env());self.assertIsNone(config.provider)
        e=self.env();e['HCLA_CLOUD_PROVIDER_ENABLED']='true'
        with self.assertRaises(ValueError):CloudConfig.from_env(e)
    def test_exact_https_tls_and_signing_key_are_required(self):
        for key,value in [('HCLA_PUBLIC_ORIGIN','http://hcla.example.test'),('HCLA_PUBLIC_ORIGIN','https://hcla.example.test/path'),('HCLA_DATABASE_URL','postgresql://runtime@db.example.test/postgres?sslmode=require'),('HCLA_TEMPORARY_STATE_KEY','short')]:
            with self.subTest(key=key):
                e=self.env();e[key]=value
                with self.assertRaises(ValueError):CloudConfig.from_env(e)
    def test_sql_translation_preserves_parameters_and_targeted_conflicts(self):
        self.assertEqual(translate('SELECT body FROM objects WHERE tenant=? ORDER BY rowid'),'SELECT body FROM objects WHERE tenant=%s ORDER BY ordinal')
        self.assertIn('ON CONFLICT (id,version)',translate('INSERT OR REPLACE INTO records VALUES(?,?,?,?)'))
        with self.assertRaises(ValueError):translate('PRAGMA secure_delete=ON')
    def test_temporary_snapshot_is_signed_session_bound_and_expiring(self):
        store=Ledger();c=store.conversation(SYNTHETIC_TENANT,memory='TEMPORARY')
        store.append(SYNTHETIC_TENANT,c['id'],None,'TEMPORARY_BODY_CANARY',0,'one')
        snapshot=pack(store,'1'*64,'session-a',c['id'],1)
        restored=unpack(snapshot,'1'*64,'session-a',c['id'])
        self.assertIn('TEMPORARY_BODY_CANARY',str(restored.history(SYNTHETIC_TENANT,c['id']))+str(restored.db.execute('SELECT body FROM sources').fetchall()[0][0]));restored.close()
        with self.assertRaises(Fault):unpack(snapshot,'1'*64,'session-b',c['id'])
        with patch('packages.cloud.temporary.time.time',return_value=10**12):
            with self.assertRaises(Fault):unpack(snapshot,'1'*64,'session-a',c['id'])
        snapshot['state']['revision']=5
        with self.assertRaises(Fault):unpack(snapshot,'1'*64,'session-a',c['id'])
        store.close()

    @unittest.skipUnless(os.environ.get('HCL_DEVELOPMENT_ARTIFACT'),'Reviewed runtime required for bundle smoke')
    def test_production_bundle_is_absolute_verified_and_repeatable(self):
        from scripts.build_cloud_runtime import build
        from packages.runtime_bridge.bridge import RuntimeBridge
        with tempfile.TemporaryDirectory() as d:
            path=build(Path(d)/'bundle')
            self.assertTrue(path.is_absolute())
            self.assertEqual(RuntimeBridge(path).handshake()['handshake_status'],'READY')
            with patch('scripts.build_cloud_runtime.acquire',side_effect=AssertionError('Verified cache must not fetch')):
                self.assertEqual(build(path),path)
            link=Path(d)/'symlink';link.symlink_to(path,target_is_directory=True)
            with self.assertRaises(ValueError):build(link)

    def test_private_owner_bundle_and_no_implicit_grant(self):
        e=self.env();owner={'schema_version':1,'login':'owner','verifier':self.verifier,'temporary_state_key':'1'*64}
        for key in ('HCLA_OWNER_LOGIN','HCLA_OWNER_PASSWORD_HASH','HCLA_TEMPORARY_STATE_KEY'):e.pop(key)
        e['HCLA_OWNER_CONFIG']=json.dumps(owner)
        self.assertIsNone(CloudConfig.from_env(e).provider)
        e['HCLA_DEEPSEEK_API_KEY']='offline-fixture'
        self.assertIsNone(CloudConfig.from_env(e).provider)
        e['HCLA_MODEL_GRANT']=json.dumps({'budget_id':'offline-new-cloud-grant','max_requests':3,'max_cost_usd':'10'})
        config=CloudConfig.from_env(e)
        self.assertEqual(config.provider.model,'deepseek-v4-pro');self.assertEqual(config.provider.max_requests,3)
        e['HCLA_MODEL_GRANT']='{"budget_id":"one","budget_id":"two","max_requests":1,"max_cost_usd":"10"}'
        with self.assertRaises(ValueError):CloudConfig.from_env(e)
        e.pop('HCLA_MODEL_GRANT');owner['schema_version']=True;e['HCLA_OWNER_CONFIG']=json.dumps(owner)
        with self.assertRaises(ValueError):CloudConfig.from_env(e)
        owner['schema_version']=1;owner['extra']='refuse';e['HCLA_OWNER_CONFIG']=json.dumps(owner)
        with self.assertRaises(ValueError):CloudConfig.from_env(e)
    def test_browser_verifier_fixed_params_match_server_and_fail_closed(self):
        import hashlib
        value='synthetic owner password only';salt=bytes([7]*16)
        derived=hashlib.pbkdf2_hmac('sha256',value.encode(),salt,600000,dklen=32).hex()
        verifier='pbkdf2-sha256$600000$'+salt.hex()+'$'+derived
        self.assertTrue(valid_verifier(verifier));self.assertTrue(check_password(value,verifier))
        self.assertFalse(check_password('wrong synthetic password',verifier))
        self.assertFalse(valid_verifier(verifier.replace('600000','1')))
        unicode_value='😀'*12
        unicode_key=hashlib.pbkdf2_hmac('sha256',unicode_value.encode(),salt,600000,dklen=32).hex()
        unicode_verifier='pbkdf2-sha256$600000$'+salt.hex()+'$'+unicode_key
        self.assertTrue(check_password(unicode_value,unicode_verifier))
        self.assertFalse(check_password('😀'*6,unicode_verifier))
    def test_new_grant_requires_all_bounds_and_cannot_renew_consumed(self):
        for grant in ({}, {'budget_id':'anything','max_requests':True,'max_cost_usd':'10'}, {'budget_id':'hcla-20261001-six-requests-usd10','max_requests':6,'max_cost_usd':'10'}):
            with self.assertRaises(ValueError):provider_from_grant(grant,'offline-fixture')
