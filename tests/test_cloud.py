"""Provider-free configuration and temporary-state unit regressions."""
import json
import unittest
from unittest.mock import patch
from packages.cloud.auth import password_verifier,valid_verifier
from packages.cloud.config import CloudConfig
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
