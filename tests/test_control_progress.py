import copy
import json
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import check_planning


class ProgressTests(unittest.TestCase):
    def setUp(self): self.p=json.loads((Path(__file__).resolve().parents[1]/'control/plan.json').read_text())
    def test_duplicate_ready_and_unsatisfied_completion_rejected(self):
        self.p['packages'][1]['state']='WAITING_DEPENDENCY';self.p['packages'][2]['state']='COMPLETE'
        with self.assertRaises(check_planning.PlanningError): check_planning.validate_plan(self.p)
    def test_complete_stop_requires_l3_handoff(self):
        for r in self.p['packages']: r['state']='COMPLETE'
        self.p.update(next_package_id=None,next_ready='STOP_WITH_HANDOFF_L3_PRODUCTION_ACTIVATION_GATED',phase='L2_5_COMPLETE')
        check_planning.validate_plan(self.p)
        self.p['next_ready']='L3_AUTO_ACTIVATE'
        with self.assertRaises(check_planning.PlanningError): check_planning.validate_plan(self.p)
