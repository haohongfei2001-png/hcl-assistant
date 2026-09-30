import base64
import json
import os
from pathlib import Path
import tempfile
import unittest
from packages.runtime_bridge.contract import load_config, verify_artifact
from scripts.fetch_development_runtime import acquire


class AcquisitionTests(unittest.TestCase):
    def test_only_exact_allowed_endpoints_and_restart_provenance(self):
        config=load_config(); original=Path(os.environ['HCL_DEVELOPMENT_ARTIFACT']); calls=[]
        def get(endpoint):
            calls.append(endpoint)
            if endpoint=='git/commits/'+config['source_commit_sha']:
                return {'sha':config['source_commit_sha'],'tree':{'sha':config['source_tree_sha']}}
            expected={ 'contents/'+p+'?ref='+config['source_commit_sha']:p for p in config['allowed_runtime_paths'] }
            self.assertIn(endpoint,expected); path=expected[endpoint]
            return {'type':'file','path':path,'encoding':'base64','sha':config['files'][path]['git_blob_sha'],
                    'content':base64.b64encode((original/path).read_bytes()).decode()}
        with tempfile.TemporaryDirectory() as temp:
            result=acquire(temp,get)
            self.assertEqual(len(calls),4);self.assertEqual(result['runtime_blobs_read'],3)
            self.assertEqual(result['provider_calls'],0);verify_artifact(temp,config)
            identity=Path(temp)/'identity.json'; value=json.loads(identity.read_text());value['source_commit_sha']='f'*40;identity.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,'UNSUPPORTED_VERSION'):verify_artifact(temp,config)

    def test_wrong_commit_prevents_any_content_fetch(self):
        calls=[]
        def get(endpoint):
            calls.append(endpoint);return {'sha':'f'*40,'tree':{'sha':'f'*40}}
        with tempfile.TemporaryDirectory() as temp, self.assertRaises(ValueError):acquire(temp,get)
        self.assertEqual(len(calls),1)
