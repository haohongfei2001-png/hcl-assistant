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

    def test_optional_ci_token_is_header_only_and_redirects_are_refused(self):
        from unittest.mock import patch, MagicMock
        config=load_config();response=MagicMock();response.__enter__.return_value.read.return_value=json.dumps({'sha':'f'*40,'tree':{'sha':'f'*40}})
        opener=MagicMock();opener.open.return_value=response
        with patch('scripts.fetch_development_runtime.urllib.request.build_opener',return_value=opener) as build, tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError,'UNSUPPORTED_VERSION'):acquire(temp,github_read_token='synthetic-ephemeral-read-token')
            request=opener.open.call_args.args[0]
            self.assertEqual(request.get_header('Authorization'),'Bearer synthetic-ephemeral-read-token')
            self.assertEqual(request.full_url,'https://api.github.com/repos/'+config['source_repository']+'/git/commits/'+config['source_commit_sha'])
            self.assertIsNone(build.call_args.args[0]().redirect_request(None,None,302,'',{},'https://example.invalid/'))
            self.assertEqual(list(Path(temp).iterdir()),[])
