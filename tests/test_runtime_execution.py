"""Original synthetic provider-free runtime/Controller smoke and regressions."""
import copy
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from packages.runtime_bridge.bridge import RuntimeBridge, TransportFailure
from packages.runtime_bridge.contract import fingerprint, load_config
from packages.runtime_bridge.serialization import decode, validate_request, validate_response
from packages.store.ledger import Ledger, Fault
from packages.controller.interaction import Controller
from packages.controller.lab import inspect
from packages.explain.projection import project
from apps.api.server import Application

TENANT='synthetic-demo-a'
TEXT='Ada said, "I believe that the workshop starts Friday."'


def request(text=TEXT,capability='belief_interpretation',query='What does Ada believe?',timeout=3000):
    return {'schema_version':'1.0','request_id':'original-workshop-1','capability_id':capability,'query':query,
            'sources':[{'source_id':'original-source','version':1,'text':text,'sha256':hashlib.sha256(text.encode()).hexdigest()}],
            'input_class':'SYNTHETIC_NON_CONFIRMATION','fixture_family':'original_workshop_20261001','purpose':'DEVELOPMENT_INTEGRATION_ONLY','timeout_ms':timeout}


class ExecutionTests(unittest.TestCase):
    def setUp(self):
        self.assertIn('HCL_DEVELOPMENT_ARTIFACT',os.environ,'Mandatory real-runtime smoke needs acquired allowlisted material; never skipped.')
        self.bridge=RuntimeBridge(os.environ['HCL_DEVELOPMENT_ARTIFACT'])

    def test_real_source_unchanged_semantic_check_and_negative_private_truth(self):
        req=request();before=copy.deepcopy(req);result=self.bridge.execute(req)
        self.assertEqual(req,before);self.assertEqual(result['status'],'EXECUTED',result)
        self.assertTrue(result['selected']);self.assertTrue(result['executed']);self.assertTrue(result['result_produced']);self.assertFalse(result['used_in_answer'])
        row=result['outputs'][0];self.assertEqual(row['quote'],TEXT);self.assertEqual(row['span'],[0,len(TEXT)])
        self.assertEqual(row['expression'],{'holder':'Ada','operator':'BELIEF','polarity':'AFFIRM','content':'the workshop starts Friday'})
        self.assertEqual(row['private_state'],'NOT_ESTABLISHED');self.assertEqual(row['world_truth'],'NOT_ESTABLISHED')
        self.assertEqual(result['provider_calls'],0);self.assertEqual(result['provenance']['source_commit_sha'],load_config()['source_commit_sha'])
        self.assertTrue(result['native_receipt_digest'].startswith('sha256:'));self.assertFalse(result['provenance']['production_enabled'])

    def test_available_access_operators_remain_distinct_from_world_truth(self):
        for utterance,expected in [('I heard that the venue changed.','EXPOSURE_CLAIM'),('I understand that the venue changed.','UNDERSTANDING_CLAIM'),('I know that the venue changed.','KNOWLEDGE_CLAIM')]:
            result=self.bridge.execute(request('Ada said, "'+utterance+'"','information_access'))
            self.assertEqual(result['status'],'EXECUTED',result);self.assertEqual(result['outputs'][0]['expression']['operator'],expected)
            self.assertEqual(result['outputs'][0]['world_truth'],'NOT_ESTABLISHED')

    def test_nested_denial_preserves_outer_scope_without_detaching_private_state(self):
        text='Ada said, "I do not believe that Ben believes that the gate is open."'
        result=self.bridge.execute(request(text))
        self.assertEqual(result['status'],'EXECUTED',result)
        tree=result['outputs'][0]['expression']
        self.assertEqual(tree['holder'],'Ada');self.assertEqual(tree['polarity'],'DENY')
        self.assertEqual(tree['content']['holder'],'Ben');self.assertEqual(tree['content']['polarity'],'AFFIRM')
        self.assertEqual(result['outputs'][0]['private_state'],'NOT_ESTABLISHED')

    def test_ordinary_chinese_and_prose_are_not_rewritten_to_force_treatment(self):
        for text in ['我的合成同事晚到了，我不确定原因。','The synthetic workshop begins tomorrow.']:
            req=request(text);result=self.bridge.execute(req)
            self.assertEqual(result['status'],'NO_TREATMENT');self.assertEqual(result['outputs'],[])
            self.assertTrue(result['executed']);self.assertFalse(result['result_produced']);self.assertEqual(req['sources'][0]['text'],text)
        result=self.bridge.execute(request(capability='goal_plan'))
        self.assertEqual(result['status'],'UNSUPPORTED');self.assertFalse(result['selected']);self.assertFalse(result['executed'])
        self.assertEqual(self.bridge.execute(request(capability='information_access'))['status'],'NO_TREATMENT')

    def test_unresolved_pronoun_and_exceeded_runtime_capacity_stay_visible(self):
        ambiguous=self.bridge.execute(request('she said, "I believe that the workshop starts Friday."'))
        self.assertEqual(ambiguous['status'],'UNRESOLVED');self.assertFalse(ambiguous['result_produced'])
        overflow=self.bridge.execute(request('\n'.join('Ada said, "I believe that event '+str(i)+' starts Friday."' for i in range(40))))
        self.assertEqual(overflow['status'],'FAILED',overflow);self.assertTrue(overflow['executed']);self.assertFalse(overflow['outputs'])
        self.assertEqual(overflow['diagnostics'],[{'reason':'RUNTIME_INPUT_OR_CAPACITY_FAILURE'}])

    def test_strict_schema_bounds_lineage_and_forbidden_input_classes(self):
        for key,value in [('schema_version','2.0'),('input_class','CONFIRMATION'),('input_class','LONGMEMEVAL'),('input_class','REAL_PRIVATE'),
                          ('purpose','FORMAL_EVAL_TUNING'),('timeout_ms',0),('timeout_ms',10001),('provider',{}),('production_enabled',True),('hidden_reasoning','forbidden')]:
            req=request();req[key]=value
            with self.subTest(key=key,value=value),self.assertRaises(ValueError):self.bridge.execute(req)
        for field,value in [('path','eval/source.txt'),('url','https://example.invalid'),('sha256','wrong'),('text','x'*64001)]:
            req=request();req['sources'][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_request(req)
        for raw in [b'{',b'{"a":1,"a":2}',b'{"a":NaN}',b'[]',b'x'*262145]:
            with self.subTest(raw=raw[:20]),self.assertRaises(ValueError):decode(raw)

    def test_wrong_identity_and_corrupt_artifact_do_not_execute_or_fallback(self):
        bad=load_config();bad['source_commit_sha']='f'*40
        result=RuntimeBridge(self.bridge.directory,bad).execute(request())
        self.assertEqual(result['status'],'FAILED');self.assertFalse(result['executed']);self.assertEqual(result['diagnostics'][0]['reason'],'UNSUPPORTED_VERSION')
        with tempfile.TemporaryDirectory() as temp:
            result=RuntimeBridge(temp).execute(request())
            self.assertEqual(result['status'],'FAILED');self.assertFalse(result['outputs'])

    def test_response_version_provenance_flags_and_source_integrity_refused(self):
        req=request();result=self.bridge.execute(req)
        for field,value in [('schema_version','2.0'),('request_id','other'),('provider_calls',1),('used_in_answer',True),('executed',False),('hidden_reasoning','forbidden')]:
            changed=copy.deepcopy(result);changed[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):validate_response(changed,req,result['provenance'])
        for change in [{'source_version':2},{'quote':'invented'},{'world_truth':'TRUE'},{'span':[1,len(TEXT)]},{'output_id':'invented'}]:
            changed=copy.deepcopy(result);changed['outputs'][0].update(change)
            with self.assertRaises(ValueError):validate_response(changed,req,result['provenance'])
        changed=copy.deepcopy(result);changed['provenance']['source_commit_sha']='f'*40
        with self.assertRaises(ValueError):validate_response(changed,req,result['provenance'])
        # Transport contract violations remain unresolved, never accepted treatment.
        with patch.object(self.bridge,'_exchange',return_value=changed):
            refused=self.bridge.execute(req);self.assertEqual(refused['status'],'UNRESOLVED');self.assertIsNone(refused['executed'])

    def test_real_timeout_and_precancel_are_bounded_and_honest(self):
        started=time.monotonic();result=self.bridge.execute(request(timeout=1))
        self.assertLess(time.monotonic()-started,1)
        self.assertEqual(result['status'],'UNRESOLVED');self.assertIsNone(result['executed']);self.assertEqual(result['diagnostics'][0]['reason'],'TIMEOUT_EXECUTION_UNKNOWN')
        event=threading.Event();event.set();cancelled=self.bridge.execute(request(),event)
        self.assertEqual(cancelled['status'],'CANCELLED');self.assertFalse(cancelled['executed'])

    def test_process_error_invalid_json_and_output_overflow_keep_unknown_execution(self):
        for reason in ['PROCESS_EXIT_FAILED','TRANSPORT_RESPONSE_UNRESOLVED','RESPONSE_BOUND_EXCEEDED']:
            with patch.object(self.bridge,'_exchange',side_effect=TransportFailure(reason,True)):
                result=self.bridge.execute(request());self.assertEqual(result['status'],'UNRESOLVED');self.assertIsNone(result['executed'])
        with patch.object(self.bridge,'_exchange',side_effect=TransportFailure('PROCESS_START_FAILED')):
            result=self.bridge.execute(request());self.assertEqual(result['status'],'FAILED');self.assertFalse(result['executed'])

    def test_actual_process_failure_garbage_bounds_and_active_cancel_reap_children(self):
        original=subprocess.Popen
        for code,reason in [("import os;os._exit(7)",'PROCESS_EXIT_FAILED'),("print('not JSON')",'TRANSPORT_RESPONSE_UNRESOLVED'),
                            ("print('x'*300000)",'RESPONSE_BOUND_EXCEEDED')]:
            processes=[]
            def spawn(args,**kwargs):
                process=original([sys.executable,'-I','-c',code],**kwargs);processes.append(process);return process
            with self.subTest(reason=reason),patch('packages.runtime_bridge.bridge.subprocess.Popen',side_effect=spawn):
                result=self.bridge.execute(request())
                self.assertEqual(result['status'],'UNRESOLVED');self.assertEqual(result['diagnostics'][0]['reason'],reason)
                self.assertEqual(len(processes),1);self.assertIsNotNone(processes[0].poll())
        event=threading.Event();processes=[]
        def spawn_wait(args,**kwargs):
            process=original([sys.executable,'-I','-c','import time;time.sleep(10)'],**kwargs);processes.append(process);return process
        timer=threading.Timer(.1,event.set);timer.start();started=time.monotonic()
        with patch('packages.runtime_bridge.bridge.subprocess.Popen',side_effect=spawn_wait):result=self.bridge.execute(request(),event)
        timer.join();self.assertEqual(result['status'],'CANCELLED');self.assertIsNone(result['executed'])
        self.assertLess(time.monotonic()-started,1);self.assertIsNotNone(processes[0].poll())

    def test_worker_disallows_network_subprocess_and_writes(self):
        code="""import sys
from pathlib import Path
sys.path.insert(0,str(Path.cwd()))
from packages.runtime_bridge.worker import isolate
import socket,subprocess
isolate()
for operation in (lambda: socket.socket(), lambda: subprocess.run(['false']), lambda: open('/tmp/hcl-bridge-forbidden-write','w')):
    try:operation()
    except PermissionError:continue
    raise AssertionError('forbidden operation allowed')
print('DENIED')
"""
        result=subprocess.run([sys.executable,'-I','-B','-c',code],capture_output=True,text=True,timeout=3,
                              env={'PATH':os.defpath})
        self.assertEqual(result.returncode,0,result.stderr);self.assertEqual(result.stdout.strip(),'DENIED')


class ControllerDevelopmentTests(unittest.TestCase):
    def setUp(self):
        self.store=Ledger();self.conversation=self.store.conversation(TENANT,memory='TEMPORARY')['id']
        self.bridge=RuntimeBridge(os.environ['HCL_DEVELOPMENT_ARTIFACT']);self.controller=Controller(self.store,development_bridge=self.bridge)
    def tearDown(self):self.store.close()
    def body(self,text=TEXT,capability='belief_interpretation',query='What does Ada believe?',timeout=3000):
        spec=request(text,capability,query,timeout);spec={k:v for k,v in spec.items() if k not in {'sources','request_id'}}
        return {'scope':{'conversation_id':self.conversation},'event':{'text':text},'expected_state_version':self.store.version(TENANT),
                'idempotency_key':str(self.store.version(TENANT)),'development_execution':spec}

    def test_synthetic_real_runtime_e2e_same_run_explain_and_receipts(self):
        req=self.body();run=self.controller.handle_interaction(TENANT,req)
        self.assertEqual(run['run_receipt']['mode'],'REAL');self.assertEqual(run['run_receipt']['actual_treatment'],'EXECUTED')
        self.assertEqual(run['run_receipt']['outcome'],'COMPLETED');self.assertIn(TEXT,run['answer']['text'])
        op=run['operation_receipts'][0]
        for flag in ['selected','executed','result_produced','used_in_answer','actual_treatment']:self.assertTrue(op[flag])
        self.assertEqual(run['run_receipt']['operations'],run['operation_receipts']);self.assertEqual(run['answer_preparation']['operation_output_refs'],op['output_ids'])
        explain=project(run);self.assertEqual(explain['mode'],'REAL');self.assertTrue(explain['development_only'])
        self.assertEqual(explain['answer_id'],run['answer']['answer_id']);self.assertEqual(explain['judgment_basis'][0]['source_refs'][0]['span'],[0,len(TEXT)])
        lab=inspect(self.controller,TENANT,run['run_id']);self.assertEqual(lab['mode'],'EXPERIMENTAL');self.assertFalse(lab['compare_enabled'])
        self.assertEqual(self.controller.context.records(TENANT),{});self.assertEqual(self.controller.adapter.invocations,0)
        frozen=json.loads(json.dumps(run));self.assertEqual(frozen['run_receipt']['bridge_provenance']['config_hash'],fingerprint(self.bridge.config))
        with patch.object(self.bridge,'execute',side_effect=AssertionError('Must not repeat runtime')):
            self.assertEqual(self.controller.handle_interaction(TENANT,req)['run_id'],run['run_id'])
            self.assertEqual(self.controller.events(TENANT,run['run_id'],run['last_seq']),[])
        self.bridge.config['source_commit_sha']='f'*40
        self.assertEqual(frozen['run_receipt']['bridge_provenance']['source_commit_sha'],load_config()['source_commit_sha'])
        self.assertEqual(self.controller.read(TENANT,run['run_id'])['run_receipt']['bridge_provenance'],frozen['run_receipt']['bridge_provenance'])

    def test_pin_change_after_acceptance_refuses_execution_without_rewriting_receipt(self):
        run=self.controller.handle_interaction(TENANT,self.body(),defer=True)
        original=copy.deepcopy(run['run_receipt']['bridge_provenance']);self.bridge.config['source_commit_sha']='f'*40
        with patch.object(self.bridge,'execute',side_effect=AssertionError('Never follow a changed pin')):
            self.controller.finish(TENANT,run['run_id'])
        refused=self.controller.read(TENANT,run['run_id'])
        self.assertEqual(refused['errors'],['PIN_CHANGED_REPIN_REQUIRED']);self.assertFalse(refused['operation_receipts'][0]['executed'])
        self.assertEqual(refused['run_receipt']['bridge_provenance'],original);self.assertIsNone(refused['answer'])

    def test_direct_no_specialized_and_unsupported_runs_are_not_fake_success(self):
        with patch.object(self.bridge,'execute',side_effect=AssertionError('Direct needs no mechanism')):
            direct=self.controller.handle_interaction(TENANT,self.body(query='2+2'))
        self.assertEqual(direct['route'],'DIRECT');self.assertEqual(direct['answer']['text'],'2 + 2 = 4。');self.assertEqual(direct['operation_receipts'],[])
        unsupported=self.controller.handle_interaction(TENANT,self.body(capability='goal_plan'))
        self.assertEqual(unsupported['run_receipt']['outcome'],'UNRESOLVED');self.assertEqual(unsupported['run_receipt']['actual_treatment'],'UNSUPPORTED')
        self.assertFalse(unsupported['operation_receipts'][0]['executed']);self.assertEqual(unsupported['selected_capability_ids'],[])
        untreated=self.controller.handle_interaction(TENANT,self.body('普通原创中文输入'))
        self.assertEqual(untreated['run_receipt']['actual_treatment'],'NO_TREATMENT');self.assertFalse(untreated['operation_receipts'][0]['used_in_answer'])

    def test_no_production_retention_authority_or_unconfigured_bypass(self):
        persistent=self.store.conversation(TENANT)['id'];body=self.body();body['scope']['conversation_id']=persistent
        with self.assertRaises(Fault):self.controller.handle_interaction(TENANT,body)
        with self.assertRaises(Fault):Controller(self.store).handle_interaction(TENANT,self.body())
        for extra in [{'records':[{'kind':'USER_REPORTED_EVENT','content':'invented'}]}, {'revisions':[{'action':'ADD'}]}, {'simulation':'failed'}]:
            body=self.body();body['event'].update(extra)
            with self.assertRaises(Fault):self.controller.handle_interaction(TENANT,body)
        self.assertEqual(self.store.history(TENANT,self.conversation),[])
        self.assertEqual(self.store.version(TENANT),0)
        with self.assertRaises(Fault):self.controller.handle_interaction('other-account',self.body())

    def test_cancel_before_and_during_execution_never_publishes_and_retry_is_new_attempt(self):
        pending=self.controller.handle_interaction(TENANT,self.body(),defer=True)
        cancelled=self.controller.cancel(TENANT,pending['run_id']);self.controller.finish(TENANT,pending['run_id'])
        self.assertEqual(cancelled['run_receipt']['outcome'],'CANCELLED');self.assertFalse(cancelled['operation_receipts'][0]['executed'])
        retry=self.controller.retry(TENANT,pending['run_id'],'retry-exp')
        self.assertEqual(retry['run_receipt']['outcome'],'COMPLETED');self.assertNotEqual(retry['run_receipt']['attempt_id'],cancelled['run_receipt']['attempt_id'])
        self.assertNotEqual(retry['operation_receipts'][0]['operation_id'],cancelled['operation_receipts'][0]['operation_id']);self.assertEqual(len(self.store.history(TENANT,self.conversation)),1)
        entered=threading.Event()
        def wait_exchange(envelope,timeout,cancel):
            entered.set();self.assertTrue(cancel.wait(2));raise TransportFailure('CANCELLED',True)
        pending=self.controller.handle_interaction(TENANT,self.body(),defer=True)
        with patch.object(self.bridge,'_exchange',side_effect=wait_exchange):
            worker=threading.Thread(target=self.controller.finish,args=(TENANT,pending['run_id']));worker.start();self.assertTrue(entered.wait(2))
            cancelled=self.controller.cancel(TENANT,pending['run_id']);worker.join(2);self.assertFalse(worker.is_alive())
        final=self.controller.read(TENANT,pending['run_id']);self.assertEqual(final['run_receipt']['outcome'],'CANCELLED');self.assertIsNone(final['answer']);self.assertIsNone(final['operation_receipts'][0]['executed'])

    def test_failure_retry_timeout_unknown_no_blind_retry(self):
        text='\n'.join('Ada said, "I believe that event '+str(i)+' starts Friday."' for i in range(40))
        failed=self.controller.handle_interaction(TENANT,self.body(text))
        self.assertEqual(failed['run_receipt']['outcome'],'FAILED');self.assertIsNone(failed['answer'])
        retry=self.controller.retry(TENANT,failed['run_id'],'failed-retry');self.assertEqual(retry['run_receipt']['outcome'],'FAILED')
        self.assertEqual(self.controller.read(TENANT,failed['run_id'])['run_receipt']['outcome'],'FAILED')
        timeout=self.controller.handle_interaction(TENANT,self.body(timeout=1))
        self.assertEqual(timeout['run_receipt']['outcome'],'UNKNOWN');self.assertIsNone(timeout['answer'])
        with self.assertRaises(Fault):self.controller.retry(TENANT,timeout['run_id'],'unknown-no-retry')

    def test_concurrent_revision_withholds_old_output_and_delete_removes_nested_copies(self):
        pending=self.controller.handle_interaction(TENANT,self.body(),defer=True)
        self.controller.handle_interaction(TENANT,{'scope':{'conversation_id':self.conversation},'event':{'text':'2+2'},'expected_state_version':self.store.version(TENANT),'idempotency_key':'new-version'})
        self.controller.finish(TENANT,pending['run_id']);old=self.controller.read(TENANT,pending['run_id'])
        self.assertIsNone(old['answer']);self.assertEqual(old['run_receipt']['outcome'],'PARTIAL')
        self.assertTrue(old['operation_receipts'][0]['executed']);self.assertFalse(old['operation_receipts'][0]['used_in_answer'])
        self.assertEqual(old['operation_receipts'][0]['publication_status'],'WITHHELD_STALE')
        executed=self.controller.handle_interaction(TENANT,self.body())
        self.controller.handle_interaction(TENANT,{'scope':{'conversation_id':self.conversation},'event':{'text':'delete synthetic','revisions':[{'action':'DELETE','target_ids':[executed['input_source_ref']['source_id']]}]},'expected_state_version':self.store.version(TENANT),'idempotency_key':'delete'})
        exported=inspect(self.controller,TENANT,executed['run_id']);self.assertNotIn('workshop starts Friday',json.dumps(exported));self.assertTrue(exported['run']['redacted'])
        self.assertEqual(project(exported['run'])['redactions'],['CURRENT_POLICY_REDACTED'])

    def test_application_temporary_isolation_restart_loss_and_no_database_body(self):
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'synthetic.sqlite';app=Application(path,self.bridge.directory)
            conversation=app.stores.conversation(TENANT,memory='TEMPORARY')['id'];ctrl=app.controller(app.stores.for_conversation(TENANT,conversation))
            body=self.body();body['scope']['conversation_id']=conversation;body['expected_state_version']=0
            run=ctrl.handle_interaction(TENANT,body);self.assertEqual(run['run_receipt']['actual_treatment'],'EXECUTED')
            self.assertEqual(app.stores.persistent.list(TENANT,'run'),[]);app.close()
            self.assertNotIn(TEXT.encode(),path.read_bytes())
            restarted=Application(path,self.bridge.directory)
            with self.assertRaises(Fault):restarted.stores.for_run(TENANT,run['run_id'])
            restarted.close()
