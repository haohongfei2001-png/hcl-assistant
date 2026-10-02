"""Virtual delayed SSE and timing-envelope checks; no model/network calls."""
import json
from pathlib import Path
from types import SimpleNamespace
import threading
import time
import unittest
from unittest.mock import patch
from packages.adapter.deepseek import DeepSeekAdapter
from packages.cloud.timing import PROVIDER_WALL_SECONDS,REQUEST_PROVIDER_DEADLINE_SECONDS,EXECUTION_LEASE_SECONDS
from tests.test_deepseek_adapter import FakeTransport,event,chunk,DONE,USAGE,MODEL,SECRET,REASONING,MESSAGES

class CloudTimingTests(unittest.TestCase):
    def setUp(self):
        guard=patch('socket.create_connection',side_effect=AssertionError('network forbidden'));guard.start();self.addCleanup(guard.stop)

    def delayed(self,wall=PROVIDER_WALL_SECONDS,absolute=None,cancel=None):
        clock=[100.0]
        class Delayed(FakeTransport):
            def __init__(self):super().__init__();self.phase=0
            def read(self,size):
                self.phase+=1
                if self.phase==1:return event(chunk(reasoning=REASONING))
                if self.phase==2:
                    time.sleep(.05)  # Let the consumer observe the first synthetic chunk.
                    clock[0]+=70
                    if cancel is not None:cancel.set()
                    return event(chunk('Synthetic final answer',finish='stop',usage=USAGE))+DONE
                return b''
        fake=Delayed();deltas=[]
        adapter=DeepSeekAdapter(base_url='https://api.deepseek.com',model=MODEL,api_key=SECRET,transport_factory=lambda *_:fake,wall_timeout=wall,request_deadline=absolute)
        with patch('packages.adapter.deepseek.time',SimpleNamespace(monotonic=lambda:clock[0])):
            result=adapter.generate(MESSAGES,max_tokens=8192,cancel_event=cancel,on_delta=deltas.append)
        self.assertEqual(fake.post_calls,1);self.assertNotIn(REASONING,repr(result)+repr(deltas));self.assertNotIn(SECRET,repr(result));self.assertTrue(result.transport_stopped)
        return result,deltas,fake

    def test_delayed_answer_after_old_sixty_second_limit_completes_with_same_wire_policy(self):
        old,_,_=self.delayed(wall=60)
        self.assertEqual((old.outcome,old.error_code),('UNKNOWN','wall_timeout'))
        result,deltas,fake=self.delayed()
        self.assertEqual(result.outcome,'SUCCEEDED');self.assertEqual(deltas,['Synthetic final answer'])
        self.assertEqual(result.stream_counts,{'chunks':2,'reasoning_chunks':1,'answer_chunks':1})
        wire=json.loads(fake.body);self.assertEqual(wire['max_tokens'],8192);self.assertEqual(wire['thinking'],{'type':'enabled'});self.assertEqual(wire['reasoning_effort'],'high')

    def test_absolute_request_deadline_wins_over_longer_provider_timeout(self):
        result,deltas,_=self.delayed(absolute=150)
        self.assertEqual((result.outcome,result.error_code),('UNKNOWN','wall_timeout'));self.assertEqual(deltas,[])
        self.assertEqual(result.stream_counts,{'chunks':1,'reasoning_chunks':1,'answer_chunks':0})

    def test_expired_request_never_constructs_transport_or_sends(self):
        factory=lambda *_:self.fail('Expired request must not construct transport')
        adapter=DeepSeekAdapter(base_url='https://api.deepseek.com',model=MODEL,api_key=SECRET,transport_factory=factory,request_deadline=0)
        result=adapter.generate(MESSAGES,max_tokens=8192)
        self.assertEqual((result.outcome,result.error_code,result.send_state),('FAILED','wall_timeout','not_sent'))
        self.assertTrue(result.transport_stopped);self.assertEqual(result.stream_counts,{'chunks':0,'reasoning_chunks':0,'answer_chunks':0})

    def test_cancellation_still_wins_during_delayed_answer(self):
        result,deltas,_=self.delayed(cancel=threading.Event())
        self.assertEqual(result.outcome,'CANCELLED');self.assertEqual(deltas,[])

    def test_timing_envelope_retains_platform_settlement_margin_and_ownership(self):
        platform=json.loads(Path('vercel.json').read_text())['functions']['api/index.py']['maxDuration']
        self.assertEqual(platform,300)
        self.assertLess(PROVIDER_WALL_SECONDS,REQUEST_PROVIDER_DEADLINE_SECONDS)
        self.assertLess(REQUEST_PROVIDER_DEADLINE_SECONDS,EXECUTION_LEASE_SECONDS)
        self.assertLess(EXECUTION_LEASE_SECONDS,platform)
        self.assertGreaterEqual(platform-REQUEST_PROVIDER_DEADLINE_SECONDS,60)

    def test_invalid_absolute_deadlines_are_rejected(self):
        for value in (True,'240',float('nan'),float('inf')):
            with self.assertRaises(ValueError):DeepSeekAdapter(base_url='https://api.deepseek.com',model=MODEL,api_key=SECRET,request_deadline=value)
