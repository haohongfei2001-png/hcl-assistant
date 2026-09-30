"""Physical relocation tests only; no L1 implementation or research/provider use."""
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import check_planning as planning
import check_repository as repository


class RepositorySplitTests(unittest.TestCase):
    def setUp(self):
        self.plan = json.loads((ROOT / 'control/plan.json').read_text())

    def reject(self):
        with self.assertRaises(planning.PlanningError):
            planning.validate_plan(self.plan)

    def test_complete_root_migration(self):
        result = repository.check_repository(ROOT)
        self.assertEqual(result['physical_split'], 'COMPLETE')
        self.assertEqual(result['imported_origin_files'], 22)

    def test_research_repository_cannot_be_canonical(self):
        self.plan['boundary']['hosting_repository'] = 'haohongfei2001-png/human-cognition-layer'
        self.reject()

    def test_old_product_prefix_is_rejected(self):
        self.plan['boundary']['path'] = 'products/hcl-assistant'
        self.reject()

    def test_split_cannot_be_reverted(self):
        self.plan['boundary']['physical_repository_split'] = False
        self.reject()

    def test_split_does_not_authorize_real_data(self):
        self.plan['boundary']['real_data_allowed'] = True
        self.reject()

    def test_split_does_not_authorize_deployment(self):
        self.plan['boundary']['public_deployment_allowed'] = True
        self.reject()

    def test_split_is_satisfied_not_outstanding(self):
        self.assertIn('PHYSICAL_PRODUCT_REPOSITORY_SPLIT', self.plan['satisfied_gates'])
        self.assertNotIn('PHYSICAL_PRODUCT_REPOSITORY_SPLIT', self.plan['l3_gates'])

    def test_research_import_remains_forbidden(self):
        self.plan['boundary']['research_import_allowed'] = True
        self.reject()

    def test_next_ready_has_not_started(self):
        if self.plan['phase'] != 'L0_COMPLETE':
            self.skipTest('Historical migration-only assertion; product implementation phase advanced')
        self.assertEqual(self.plan['next_ready'], 'L1-01_EVENT_SOURCE_STATE_LEDGER')
        self.assertEqual(self.plan['packages'][0]['state'], 'COMPLETE')
        self.assertEqual(self.plan['packages'][1]['state'], 'NEXT_READY')
        self.assertEqual(self.plan['evidence']['product_implementation'], 'NOT_IMPLEMENTED')

    def test_forbidden_source_paths(self):
        for path in ('eval/gold.json', 'confirmation/source.txt', 'data/user.json', 'LongMemEval/run.json'):
            with self.subTest(path=path), self.assertRaises(planning.PlanningError):
                repository.inspect_file(path, b'{}')

    def test_credential_pattern_rejected(self):
        value = ('ghp_' + 'A' * 36).encode()
        with self.assertRaises(planning.PlanningError):
            repository.inspect_file('README.md', value)

    def test_private_key_rejected(self):
        marker = ('-----BEGIN ' + 'PRIVATE KEY-----').encode()
        with self.assertRaises(planning.PlanningError):
            repository.inspect_file('README.md', marker)

    def test_research_import_rejected(self):
        with self.assertRaises(planning.PlanningError):
            repository.inspect_file('apps/check.py', b'import hcl.cognition')

    def test_binary_payload_rejected(self):
        with self.assertRaises(planning.PlanningError):
            repository.inspect_file('docs/payload.txt', bytes([0, 255]))

    def test_prohibition_documentation_is_not_data(self):
        repository.inspect_file('docs/BOUNDARY.md', b'Never copy confirmation gold or LongMemEval.')

    def test_migration_inventory_preserves_all_product_directories(self):
        ledger = json.loads((ROOT / 'control/repository-migration.json').read_text())
        self.assertEqual(len(ledger['files']), 22)
        for name in ('contracts', 'control', 'docs', 'apps', 'packages', 'scripts', 'tests'):
            self.assertTrue(any(p.startswith(name + '/') for p in ledger['files']), name)
        self.assertIn('.github/workflows/hcl-assistant-planning.yml', ledger['files'])


if __name__ == '__main__':
    unittest.main()
