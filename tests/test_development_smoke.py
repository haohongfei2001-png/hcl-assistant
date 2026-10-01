import unittest
from scripts.smoke_development_chat import verify_single_hosted_attempt, GRANT

class HostedGrantTests(unittest.TestCase):
    def setUp(self):self.env={'HCLA_APPROVED_GRANT':GRANT,'GITHUB_REPOSITORY':'haohongfei2001-png/hcl-assistant','GITHUB_REF':'refs/heads/main','GITHUB_RUN_ATTEMPT':'1','GITHUB_RUN_ID':'123'}
    def get(self,path):return {'workflow_id':456,'run_number':1,'event':'workflow_dispatch','head_branch':'main'} if path=='/actions/runs/123' else {'workflow_runs':[{'id':123}],'total_count':1}
    def test_first_manual_main_only(self):verify_single_hosted_attempt(self.env,self.get)
    def test_any_previous_attempt_refuses_even_failure_or_cancellation(self):
        def previous(path):return self.get(path) if path=='/actions/runs/123' else {'workflow_runs':[{'id':123},{'id':122,'conclusion':'cancelled'}],'total_count':2}
        with self.assertRaisesRegex(ValueError,'grant_already_attempted'):verify_single_hosted_attempt(self.env,previous)
    def test_rerun_fork_branch_and_unapproved_grant_refused(self):
        for key,value in [('GITHUB_RUN_ATTEMPT','2'),('GITHUB_REF','refs/heads/feature'),('GITHUB_REPOSITORY','other/repo'),('HCLA_APPROVED_GRANT','research-experiment')]:
            with self.subTest(key=key),self.assertRaises(ValueError):verify_single_hosted_attempt({**self.env,key:value},self.get)
    def test_missing_current_or_deleted_history_never_reopens_grant(self):
        for listing in [{'workflow_runs':[],'total_count':0},{'workflow_runs':[{'id':122}],'total_count':1}]:
            with self.assertRaises(ValueError):verify_single_hosted_attempt(self.env,lambda path:self.get(path) if path=='/actions/runs/123' else listing)
        with self.assertRaisesRegex(ValueError,'run_number'):verify_single_hosted_attempt(self.env,lambda path:{**self.get(path),'run_number':2} if path=='/actions/runs/123' else self.get(path))
    def test_api_failure_cannot_spend(self):
        def fail(path):raise OSError('offline')
        with self.assertRaises(OSError):verify_single_hosted_attempt(self.env,fail)
