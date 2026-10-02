"""Current A2 queue migration; legacy safety assertions remain in original tests."""
import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from scripts.check_planning import PlanningError, validate_plan, validate_tree, IGNORED_DIRS, L3_STOP
from scripts.advance_package import advance
ROOT = Path(__file__).resolve().parents[1]

class CurrentQueueTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / 'control/plan.json').read_text())
        q=self.plan['product_development']; q.update(next_package_id='P0-01',next_ready='P0-01_TRUTHFUL_PREVIEW_CONTRACT_REPAIR',phase='ASSISTANT_FIRST_REFINEMENT_IMPLEMENTING')
        for i,r in enumerate(q['packages']): r.update(state='NEXT_READY' if i==0 else 'WAITING_DEPENDENCY',evidence='NOT_IMPLEMENTED')
    def reject(self):
        with self.assertRaises(PlanningError): validate_plan(self.plan)
    def test_current_not_legacy_is_reported(self):
        result = validate_tree(ROOT)
        self.assertEqual(result['queue_authority'], 'product_development')
        self.assertEqual(result['next_ready'], json.loads((ROOT/'control/plan.json').read_text())['product_development']['next_ready'])
        self.assertEqual(result['legacy_stage_next_ready'], L3_STOP)
        self.assertEqual(result['package_count'], 11)
        self.assertEqual(result['current_package_count'], 11)
    def test_recovery_code_cannot_authorize_live_mail_or_auth(self):
        for key in ('live_mail_authorized','live_activation_authorized'):
            value=copy.deepcopy(self.plan);value['product_development']['password_recovery'][key]=True
            with self.assertRaises(PlanningError):validate_plan(value)
    def test_development_gate_cannot_inherit_research_budget(self):
        for key,value in [('provider_default','ENABLED'),('live_requires_explicit_product_budget',False),('research_budget_reuse_allowed',True),('bridge_lock_unchanged',False),('production_enabled',True),('private_data_allowed',True)]:
            p=copy.deepcopy(self.plan);p['product_development']['development_chat'][key]=value
            with self.assertRaises(PlanningError):validate_plan(p)
    def test_duplicate_ready_and_unknown_dependency(self):
        base = copy.deepcopy(self.plan)
        self.plan['product_development']['packages'][1]['state'] = 'NEXT_READY'; self.reject()
        self.plan = base
        self.plan['product_development']['packages'][1]['depends_on'] = ['UNKNOWN']; self.reject()
    def test_current_mirror_cannot_point_at_legacy_stop(self):
        self.plan['product_development']['next_ready'] = L3_STOP; self.reject()
    def test_completed_forward_dependency_is_rejected(self):
        self.plan['product_development']['packages'][-1].update(state='COMPLETE', evidence='not sufficient'); self.reject()
    def test_current_permissions_and_each_l3_gate_remain_closed(self):
        for key in ('real_private_data_allowed', 'production_activation_allowed', 'judge_implementation_authorized', 'agent_execution_authorized'):
            with self.subTest(key=key):
                p = copy.deepcopy(self.plan); p['product_development'][key] = True
                with self.assertRaises(PlanningError): validate_plan(p)
        for gate in self.plan['l3_gates']:
            p = copy.deepcopy(self.plan); p['l3_gates'].remove(gate)
            with self.assertRaises(PlanningError): validate_plan(p)
    def test_unmigrated_consumer_and_changed_acceptance_rejected(self):
        p=copy.deepcopy(self.plan); self.plan['field_authority']['automation_support']='LEGACY_STAGE_CHECKS_ONLY_CURRENT_QUEUE_MANUALLY_REVIEWED'; self.reject()
        self.plan=p; self.plan['product_development']['packages'][0]['acceptance'].pop(); self.reject()
    def test_advance_preserves_canonical_docs_legacy_runtime_and_boundaries(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'product'; shutil.copytree(ROOT, root, ignore=shutil.ignore_patterns(*IGNORED_DIRS))
            before=json.loads((root/'control/plan.json').read_text())
            old_status=(root/'STATUS.md').read_text()
            q=before['product_development']; package=q['next_package_id']
            if package is None: return
            with self.assertRaises(PlanningError): advance('L2.5-02','wrong queue',root)
            with self.assertRaises(PlanningError): advance(package,'',root)
            advance(package,'synthetic reviewed receipt reference',root)
            after=json.loads((root/'control/plan.json').read_text())
            for k in before.keys()-{'product_development'}: self.assertEqual(before[k],after[k],k)
            self.assertIn('## Production gate and compatibility record',(root/'STATUS.md').read_text())
            from scripts.advance_package import refresh_queue_summary
            self.assertEqual(refresh_queue_summary(old_status, after['product_development']), (root/'STATUS.md').read_text())
            validate_tree(root)
    def test_duplicate_header_or_state_mirror_drift_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)/'product'; shutil.copytree(ROOT,root,ignore=shutil.ignore_patterns(*IGNORED_DIRS))
            p=root/'STATUS.md'; p.write_text(p.read_text()+'\n**NEXT_READY: WRONG**\n')
            with self.assertRaises(PlanningError): validate_tree(root)
