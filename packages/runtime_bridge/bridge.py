"""Versioned bounded process transport. No retries or provider fallback."""
import copy
import json
import os
from pathlib import Path
import selectors
import signal
import subprocess
import sys
import time
from packages.runtime_bridge.contract import handshake, load_config, fingerprint
from packages.runtime_bridge.serialization import decode, validate_request, validate_response, provenance


class TransportFailure(Exception):
    def __init__(self, reason, launched=False): self.reason=reason; self.launched=launched


class RuntimeBridge:
    def __init__(self, directory, config=None):
        self.directory=Path(directory);self.config=load_config() if config is None else copy.deepcopy(config)

    def _exchange(self, envelope, timeout_ms, cancel=None):
        payload=json.dumps(envelope,ensure_ascii=False,allow_nan=False).encode()
        if len(payload)>131072: raise TransportFailure('REQUEST_BOUND_EXCEEDED')
        if cancel is not None and cancel.is_set(): raise TransportFailure('CANCELLED')
        worker=Path(__file__).with_name('worker.py');started=time.monotonic()
        try:
            process=subprocess.Popen([sys.executable,'-I','-B',str(worker),str(self.directory)],stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
                env={'PATH':os.defpath,'PYTHONDONTWRITEBYTECODE':'1'},start_new_session=True,cwd=str(worker.parent))
        except OSError: raise TransportFailure('PROCESS_START_FAILED') from None
        sent=0;output=bytearray();stderr_size=0;maximum=self.config['timeout_policy']['max_response_bytes']
        try:
            with selectors.DefaultSelector() as selector:
                for stream,mode in ((process.stdin,selectors.EVENT_WRITE),(process.stdout,selectors.EVENT_READ),(process.stderr,selectors.EVENT_READ)):
                    os.set_blocking(stream.fileno(),False);selector.register(stream,mode)
                while selector.get_map():
                    if cancel is not None and cancel.is_set(): raise TransportFailure('CANCELLED',True)
                    if (time.monotonic()-started)*1000 >= timeout_ms: raise TransportFailure('TIMEOUT_EXECUTION_UNKNOWN',True)
                    for key,_ in selector.select(.02):
                        stream=key.fileobj
                        if stream is process.stdin:
                            try: sent+=os.write(stream.fileno(),payload[sent:])
                            except BrokenPipeError: sent=len(payload)
                            if sent==len(payload): selector.unregister(stream);stream.close()
                        else:
                            data=os.read(stream.fileno(),16384)
                            if not data: selector.unregister(stream);continue
                            if stream is process.stdout:
                                output.extend(data)
                                if len(output)>maximum: raise TransportFailure('RESPONSE_BOUND_EXCEEDED',True)
                            else:
                                stderr_size+=len(data)
                                if stderr_size>maximum: raise TransportFailure('ERROR_BOUND_EXCEEDED',True)
                remaining=max(.001,timeout_ms/1000-(time.monotonic()-started))
                try: code=process.wait(timeout=remaining)
                except subprocess.TimeoutExpired: raise TransportFailure('TIMEOUT_EXECUTION_UNKNOWN',True) from None
                if code: raise TransportFailure('PROCESS_EXIT_FAILED',True)
                return decode(bytes(output),maximum)
        except (OSError,ValueError): raise TransportFailure('TRANSPORT_RESPONSE_UNRESOLVED',True) from None
        finally:
            # Kill the whole group, including any unexpected descendants, then reap.
            try: os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()
            for stream in (process.stdin,process.stdout,process.stderr):
                if not stream.closed: stream.close()

    def handshake(self):
        checked=handshake(self.directory,self.config)
        if checked['handshake_status']!='READY': return checked
        try:
            actual=self._exchange({'config':self.config,'action':'handshake'},3000)
            if actual!=checked:
                status='FAILED'
                if actual.get('source_commit_sha')!=checked['source_commit_sha']:status='UNSUPPORTED_VERSION'
                elif actual.get('artifact_digest')!=checked['artifact_digest']:status='DIGEST_MISMATCH'
                elif any(actual.get(k)!=checked[k] for k in ('interface_version','interface_digest','serialization_version','receipt_version')):status='INTERFACE_MISMATCH'
                elif any(actual.get(k)!=checked[k] for k in ('capability_manifest_digest','discovered_capabilities')):status='CAPABILITY_MANIFEST_INVALID'
                checked.update(handshake_status=status,errors=[status],discovered_capabilities=[])
                return checked
            return actual
        except (TransportFailure,ValueError):
            checked.update(handshake_status='FAILED',errors=['HANDSHAKE_PROCESS_FAILED'],discovered_capabilities=[])
            return checked

    def execute(self, request, cancel=None):
        request=copy.deepcopy(request);validate_request(request)
        checked=handshake(self.directory,self.config)
        identity=provenance(self.config,checked.get('capability_manifest_digest'))
        base={'schema_version':'1.0','request_id':request['request_id'],'selected':False,'executed':False,'result_produced':False,'used_in_answer':False,
              'outputs':[],'diagnostics':[],'provider_calls':0,'provenance':identity,'native_receipt_digest':None}
        if checked['handshake_status']!='READY':
            return {**base,'status':'FAILED','diagnostics':[{'reason':checked['handshake_status']}]}
        try:
            response=self._exchange({'config':self.config,'action':'execute','request':request},request['timeout_ms'],cancel)
            return validate_response(response,request,identity)
        except TransportFailure as failure:
            return {**base,'status':'CANCELLED' if failure.reason=='CANCELLED' else ('FAILED' if failure.reason=='PROCESS_START_FAILED' else 'UNRESOLVED'),
                    'selected':request['capability_id'] in self.config['interface']['capabilities'],
                    'executed':None if failure.launched else False,'diagnostics':[{'reason':failure.reason}]}
        except ValueError:
            return {**base,'status':'UNRESOLVED','selected':request['capability_id'] in self.config['interface']['capabilities'],
                    'executed':None,'diagnostics':[{'reason':'RESPONSE_CONTRACT_REFUSED'}]}
