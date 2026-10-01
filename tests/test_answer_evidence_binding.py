"""Provider-free R13 evidence binding, pinned history, and policy regressions."""
import copy
import unittest

from packages.controller.interaction import Controller
from packages.explain.projection import claim_source_links, project
from packages.store.ledger import Ledger, canonical


class AnswerEvidenceBindingTests(unittest.TestCase):
    def setUp(self):
        self.store = Ledger()
        self.conversation = self.store.conversation('evidence')['id']
        self.controller = Controller(self.store)

    def tearDown(self):
        self.store.close()

    def say(self, text, **event):
        return self.controller.handle_interaction('evidence', {
            'scope': {'conversation_id': self.conversation, 'topic_id': None},
            'expected_state_version': self.store.version('evidence'),
            'idempotency_key': str(self.store.version('evidence')),
            'event': {'text': text, **event},
        })

    def assert_evidence(self, run, expected):
        self.assertEqual(run['answer']['citation_refs'], expected)
        self.assertEqual(run['explain_projection']['source_links'], expected)
        self.assertEqual(project(run)['source_links'], expected)
        completed = next(e for e in run['stream'] if e['type'] == 'answer.completed')
        self.assertEqual(completed['payload']['citation_refs'], expected)
        self.assertEqual(run['run_receipt']['usage']['provider_calls'], 0)

    def test_file_label_is_current_policy_projection_not_a_persisted_copy(self):
        for action in ('STOP_USING', 'DELETE'):
            with self.subTest(action=action):
                old=self.say('原创未解析文件内容', filename='ORIGINAL_FILE_LABEL_CANARY.txt')
                self.assertEqual(old['input_filename'],'ORIGINAL_FILE_LABEL_CANARY.txt')
                self.assertNotIn('input_filename',self.store.get('evidence','run',old['run_id']))
                self.say('撤除文件',revisions=[{'action':action,'target_ids':[old['input_source_ref']['source_id']]}])
                self.assertNotIn('input_filename',self.controller.read('evidence',old['run_id']))

    def test_direct_answer_keeps_selected_background_only_in_inspection(self):
        self.say('报告[榛]：原创纸灯工作坊背景')
        run = self.say('2+2')
        self.assertTrue(run['selected_context']['source_versions'])
        self.assertTrue(run['selected_context']['records'])
        self.assertEqual(project(run)['judgment_basis'], [])
        self.assertEqual(project(run)['known_information'], [])
        self.assert_evidence(run, [])

    def test_six_selected_records_only_four_claims_supply_answer_sources(self):
        for number in range(6):
            run = self.say(f'报告[榛]：原创纸灯资料编号{number}')
        claims = run['answer']['claim_bindings']
        used = {claim['record_id'] for claim in claims}
        self.assertEqual(len(run['selected_context']['records']), 6)
        self.assertEqual(len(used), 4)
        expected = [ref for record in run['selected_context']['records']
                    if record['record_id'] in used for ref in record['source_refs']]
        self.assert_evidence(run, expected)
        self.assertEqual({r['record_id'] for r in project(run)['known_information']}, used)

    def test_multiple_claims_share_one_exact_source_without_duplicate_links(self):
        run = self.say('原创合成来源包含多个记录', records=[
            {'kind': 'USER_REPORTED_EVENT', 'content': f'原创纸灯资料编号{n}'}
            for n in range(6)
        ])
        self.assertEqual(len(run['answer']['claim_bindings']), 4)
        self.assert_evidence(run, [run['input_source_ref']])

    def test_exact_version_hash_and_distinct_spans_are_not_collapsed(self):
        source = {'source_id': 'synthetic-source', 'version': 1, 'sha256': 'a', 'span': [0, 2]}
        refs = [source, {**source, 'span': [2, 4]},
                {**source, 'version': 2, 'sha256': 'b'}]
        records = [{'record_id': 'bound', 'source_refs': refs + [copy.deepcopy(source)]},
                   {'record_id': 'unused', 'source_refs': [{**source, 'source_id': 'unused'}]}]
        self.assertEqual(claim_source_links(records, [{'record_id': 'bound'}]), refs)
        self.assertEqual(claim_source_links(records, []), [])

    def test_correction_keeps_old_source_and_run_identity_frozen(self):
        old = self.say('报告[榛]：原创纸灯材料周四送达')
        before = copy.deepcopy(project(old))
        new = self.say('更正：原创纸灯材料周四送达 => 原创纸灯材料周五送达')
        historical = project(self.controller.read('evidence', old['run_id']))
        for field in ('judgment_basis', 'source_links', 'answer_id', 'run_id', 'snapshot_id', 'recorded_at'):
            self.assertEqual(historical[field], before[field])
        self.assertTrue(historical['outdated'])
        self.assertNotEqual(new['run_id'], old['run_id'])
        source = self.store.source('evidence', historical['source_links'][0])
        self.assertIn('周四送达', source['text'])
        self.assertNotIn('周五送达', source['text'])

    def test_legacy_projection_narrows_recorded_links_without_rewriting_run(self):
        self.say('报告[榛]：原创未使用背景')
        run = self.say('2+2')
        run['explain_projection']['source_links'] = copy.deepcopy(run['selected_context']['source_versions'])
        frozen = canonical(run)
        version = self.store.version('evidence')
        calls = self.controller.adapter.invocations
        self.assertEqual(project(run)['source_links'], [])
        self.assertEqual(canonical(run), frozen)
        self.assertEqual(self.store.version('evidence'), version)
        self.assertEqual(self.controller.adapter.invocations, calls)

    def test_development_explicit_output_source_projection_is_unchanged(self):
        # Projection fixture only: no bridge invocation or runtime artifact access.
        run = self.say('2+2')
        ref = copy.deepcopy(run['input_source_ref'])
        claims = [{'operation_output_id': 'synthetic-output', 'source_refs': [ref], 'text': 'synthetic'}]
        run['development_request'] = {'fixture': True}
        run['explain_projection'].update(judgment_basis=claims, source_links=[ref])
        self.assertEqual(project(run)['source_links'], [ref])
        self.assertEqual(project(run)['judgment_basis'], claims)
        self.assertEqual(project(run)['known_information'], [])

    def test_stop_and_delete_still_redact_even_unused_selected_background(self):
        for action in ('STOP_USING', 'DELETE'):
            with self.subTest(action=action):
                old = self.say('报告[榛]：原创需撤除合成背景')
                direct = self.say('2+2')
                self.say('撤除指定背景', revisions=[{
                    'action': action, 'target_ids': [old['accepted_change_ids'][0]],
                }])
                for previous in (old, direct):
                    result = project(self.controller.read('evidence', previous['run_id']))
                    self.assertTrue(result['redactions'])
                    self.assertEqual(result['source_links'], [])
                    self.assertEqual(result['judgment_basis'], [])

    def test_failed_and_unknown_runs_expose_no_answer_evidence(self):
        self.say('报告[榛]：原创背景')
        for simulation in ('failed', 'unknown'):
            with self.subTest(simulation=simulation):
                run = self.say('原创未覆盖输入', simulation=simulation)
                self.assertIsNone(run['answer'])
                self.assertEqual(project(run)['source_links'], [])
                self.assertEqual(project(run)['judgment_basis'], [])


if __name__ == '__main__':
    unittest.main()
