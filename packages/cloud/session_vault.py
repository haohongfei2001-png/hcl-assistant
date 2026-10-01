"""Authenticated encryption for server-only account refresh material."""
import base64
import json
import secrets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class SessionVault:
    PURPOSE=b'hcla-member-refresh-v1'
    MAX_MATERIAL=8192
    MAX_ENVELOPE=12000
    def __init__(self,state_key):
        raw=bytes.fromhex(state_key)
        if len(raw)!=32:raise ValueError('Server session key required')
        key=HKDF(algorithm=hashes.SHA256(),length=32,salt=None,info=self.PURPOSE).derive(raw)
        self._cipher=AESGCM(key)
    def aad(self,issuer,subject,session_key,absolute_expiry):
        return json.dumps([1,issuer,subject,session_key,absolute_expiry],separators=(',',':')).encode()
    def seal(self,token,issuer,subject,session_key,absolute_expiry):
        if not isinstance(token,str) or not 8<=len(token)<=self.MAX_MATERIAL:raise ValueError('Invalid refresh material')
        nonce=secrets.token_bytes(12)
        ciphertext=self._cipher.encrypt(nonce,token.encode(),self.aad(issuer,subject,session_key,absolute_expiry))
        return base64.urlsafe_b64encode(b'\x01'+nonce+ciphertext).decode()
    def open(self,ciphertext,issuer,subject,session_key,absolute_expiry):
        if not isinstance(ciphertext,str) or len(ciphertext)>self.MAX_ENVELOPE:raise ValueError('Invalid session envelope')
        raw=base64.b64decode(ciphertext,altchars=b'-_',validate=True)
        if len(raw)<30 or raw[0]!=1:raise ValueError('Invalid session envelope')
        return self._cipher.decrypt(raw[1:13],raw[13:],self.aad(issuer,subject,session_key,absolute_expiry)).decode()
