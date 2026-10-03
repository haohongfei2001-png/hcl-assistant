"""Safe publisher diagnostics using synthetic HTTP responses; no network."""
import io
import json
import os
import traceback
import unittest
import urllib.error
from unittest.mock import patch

from scripts.publish_runtime_sync import github


class PublisherErrorTests(unittest.TestCase):
    def failure(self, body, *, code=403, headers=None, endpoint='pulls', method='POST'):
        source=io.BytesIO(body)
        error=urllib.error.HTTPError('https://example.test/PRIVATE_URL_CANARY',code,'PRIVATE_REASON_CANARY',headers or {},source)
        request_data={'body':'PRIVATE_REQUEST_CANARY'}
        with patch.dict(os.environ,{'GH_TOKEN':'SYNTHETIC_TOKEN_CANARY'}),patch('scripts.publish_runtime_sync.urllib.request.urlopen',side_effect=error) as opening:
            try:github(method,endpoint,request_data)
            except RuntimeError as caught:
                rendered=''.join(traceback.format_exception(caught))
                result=json.loads(str(caught))
            else:self.fail('Expected a nonzero publisher failure')
        self.assertEqual(opening.call_count,1);self.assertTrue(source.closed)
        for canary in ('PRIVATE_URL_CANARY','PRIVATE_REASON_CANARY','PRIVATE_REQUEST_CANARY','SYNTHETIC_TOKEN_CANARY','PRIVATE_BODY_CANARY'):
            self.assertNotIn(canary,rendered)
        return result

    def test_exact_policy_body_is_classified_without_unsafe_fields_or_retry(self):
        result=self.failure(json.dumps({'message':'GitHub Actions is not permitted to create or approve pull requests.','errors':'PRIVATE_BODY_CANARY','documentation_url':'https://example.test/PRIVATE_URL_CANARY'}).encode())
        self.assertEqual(result,{'status':'GITHUB_REQUEST_FAILED','http_status':403,'operation':'CREATE_PULL_REQUEST','category':'ACTIONS_PR_POLICY_REFUSED'})

    def test_integration_refusal_and_primary_rate_limit_remain_distinct(self):
        result=self.failure(b'{"message":"Resource not accessible by integration"}')
        self.assertEqual(result['category'],'INTEGRATION_ACCESS_REFUSED')
        result=self.failure(b'{"message":"PRIVATE_BODY_CANARY"}',headers={'x-ratelimit-remaining':'0'})
        self.assertEqual(result['category'],'PRIMARY_RATE_LIMIT_EXHAUSTED')
        self.assertEqual(self.failure(b'{"message":"Bad credentials"}',code=401)['category'],'AUTHENTICATION_REFUSED')

    def test_unknown_malformed_nested_or_oversized_bodies_never_invent_a_cause(self):
        for body in (b'{"message":"PRIVATE_BODY_CANARY"}',b'<html>PRIVATE_BODY_CANARY</html>',b'{"message":[]}',b'["PRIVATE_BODY_CANARY"]',b'\xff',b'['*2000+b']'*2000,b'{"message":"Resource not accessible by integration","extra":"'+b'x'*8192+b'"}'):
            with self.subTest(size=len(body)):
                self.assertEqual(self.failure(body)['category'],'UNCLASSIFIED')
        self.assertEqual(self.failure(b'{"message":"Resource not accessible by integration"}',code=500)['category'],'UNCLASSIFIED')

    def test_unknown_endpoint_is_not_logged_and_dispatch_has_a_fixed_label(self):
        result=self.failure(b'{}',endpoint='pulls/PRIVATE_URL_CANARY?token=SYNTHETIC_TOKEN_CANARY',method='PATCH')
        self.assertEqual(result['operation'],'OTHER_REPOSITORY_REQUEST')
        result=self.failure(b'{}',endpoint='actions/workflows/hcl-assistant-planning.yml/dispatches')
        self.assertEqual(result['operation'],'DISPATCH_ACCEPTANCE')

    def test_missing_get_retains_existing_behavior_and_closes_response(self):
        source=io.BytesIO(b'PRIVATE_BODY_CANARY')
        error=urllib.error.HTTPError('https://example.test/',404,'Missing',{},source)
        with patch.dict(os.environ,{'GH_TOKEN':'synthetic'}),patch('scripts.publish_runtime_sync.urllib.request.urlopen',side_effect=error) as opening:
            self.assertIsNone(github('GET','git/ref/heads/missing'))
        self.assertEqual(opening.call_count,1);self.assertTrue(source.closed)

    def test_successful_json_and_no_content_responses_are_unchanged(self):
        for status,body,expected in [(200,b'{"sha":"fixture"}',{'sha':'fixture'}),(204,b'',None)]:
            with self.subTest(status=status):
                response=io.BytesIO(body);response.status=status
                with patch.dict(os.environ,{'GH_TOKEN':'synthetic'}),patch('scripts.publish_runtime_sync.urllib.request.urlopen',return_value=response) as opening:
                    self.assertEqual(github('GET','git/ref/heads/main'),expected)
                self.assertEqual(opening.call_count,1);self.assertTrue(response.closed)
