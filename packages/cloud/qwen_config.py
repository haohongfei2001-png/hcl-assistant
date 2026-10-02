"""Explicit CNY authorization for the user-selected Beijing Qwen model.

This never reads credentials, installs a grant, converts currencies or grants
member/guest access. A key by itself has no effect.
"""
from dataclasses import dataclass, field
from decimal import Decimal
import hashlib
import json

from packages.adapter.development_budget import _DECIMAL, _IDENTIFIER, _key, _money
from packages.adapter.qwen import (MODEL, REGION, endpoint, OUTPUT_TOKEN_MARGIN,
                                  MAX_COMPLETION_TOKENS, INPUT_TOKEN_RESERVATION)


@dataclass(frozen=True, repr=False)
class QwenConfig:
    api_key: str = field(repr=False)
    base_url: str
    model: str
    region: str
    currency: str
    budget_id: str
    max_requests: int
    max_cost_cny: Decimal
    input_cny_per_million: Decimal
    output_cny_per_million: Decimal
    max_output_tokens: int
    smoke: dict | None = field(default=None, repr=False)
    monthly: dict | None = field(default=None, repr=False)
    provider_id = 'qwen'
    input_token_reservation = INPUT_TOKEN_RESERVATION

    def __repr__(self):
        return 'QwenConfig(configured=True)'

    @property
    def reserved_output_tokens(self):
        return self.max_output_tokens + OUTPUT_TOKEN_MARGIN

    def as_grant(self):
        result = {'provider': self.provider_id, 'model': self.model, 'region': self.region,
                'currency': self.currency, 'base_url': self.base_url, 'budget_id': self.budget_id,
                'max_requests': self.max_requests, 'max_cost_cny': _money(self.max_cost_cny),
                'input_cny_per_million': _money(self.input_cny_per_million),
                'output_cny_per_million': _money(self.output_cny_per_million),
                'max_completion_tokens': self.max_output_tokens}
        if self.smoke is not None:result['smoke']=dict(self.smoke)
        if self.monthly is not None:result['monthly']=dict(self.monthly)
        return result

    def authorize_request(self, request, conversation):
        if self.smoke is None:return
        from packages.store.ledger import Fault
        event=request.get('event',{}); execution=request.get('development_execution',{})
        text=event.get('text'); query=execution.get('query')
        if (conversation.get('memory')!='TEMPORARY' or request.get('expected_state_version')!=0
                or event.get('type','message')!='message' or not isinstance(text,str) or not isinstance(query,str)
                or execution.get('capability_id')!='belief_interpretation'
                or hashlib.sha256(text.encode()).hexdigest()!=self.smoke['input_sha256']
                or hashlib.sha256(query.encode()).hexdigest()!=self.smoke['query_sha256']):
            raise Fault(403,'This Qwen grant permits only the approved fresh temporary synthetic smoke')

    @classmethod
    def from_grant(cls, grant, api_key):
        fields = {'provider', 'model', 'region', 'currency', 'base_url', 'budget_id',
                  'max_requests', 'max_cost_cny', 'input_cny_per_million',
                  'output_cny_per_million', 'max_completion_tokens'}
        if not isinstance(grant, dict) or not fields<=set(grant) or set(grant)-fields-{'smoke','monthly'}:
            raise ValueError('Explicit bounded Qwen CNY grant required')
        if (grant['provider'] != 'qwen' or grant['model'] != MODEL
                or grant['region'] != REGION or grant['currency'] != 'CNY'):
            raise ValueError('Requested Beijing Qwen CNY contract required')
        endpoint(grant['base_url'])
        if (not isinstance(api_key, str) or not 1 <= len(api_key) <= 4096
                or any(ord(c) < 33 or ord(c) > 126 for c in api_key)):
            raise ValueError('Server Qwen key required')
        if (not isinstance(grant['budget_id'], str)
                or not _IDENTIFIER.fullmatch(grant['budget_id'])
                or not grant['budget_id'].startswith('hcla-qwen-cny-')):
            raise ValueError('Separate Qwen CNY budget identity required')
        if type(grant['max_requests']) is not int or not 1 <= grant['max_requests'] <= 1000000:
            raise ValueError('Finite request bound required')
        cap = grant['max_completion_tokens']
        if type(cap) is not int or not 1 <= cap <= MAX_COMPLETION_TOKENS:
            raise ValueError('Finite total output bound required')
        values = {}
        for name in ('max_cost_cny', 'input_cny_per_million', 'output_cny_per_million'):
            value = grant[name]
            if not isinstance(value, str) or not _DECIMAL.fullmatch(value) or Decimal(value) <= 0:
                raise ValueError('Explicit finite CNY prices and ceiling required')
            values[name] = Decimal(value)
        # Official Beijing pay-as-you-go uncached prices checked 2026-10-02.
        # Discounts never enlarge authorization. Recheck before live activation.
        if values['input_cny_per_million'] < 12 or values['output_cny_per_million'] < 36:
            raise ValueError('Reviewed Beijing price floors required')
        smoke=grant.get('smoke')
        monthly=grant.get('monthly')
        if 'monthly' in grant:
            if (monthly!={'timezone':'Asia/Shanghai','scope':'OWNER_ONLY','limit_cny':'500'}
                    or values['max_cost_cny']!=500 or grant['max_requests']>1000000 or 'smoke' not in grant):
                raise ValueError('Approved owner-only Shanghai monthly CNY500 contract required')
            monthly=dict(monthly)
        if 'smoke' in grant:
            import re
            if (not isinstance(smoke,dict) or set(smoke)!={'scope','input_sha256','query_sha256'}
                    or smoke['scope']!='OWNER_ONLY_SYNTHETIC_SMOKE' or (monthly is None and grant['max_requests']!=1)
                    or not all(isinstance(smoke[k],str) and re.fullmatch('[0-9a-f]{64}',smoke[k]) for k in ('input_sha256','query_sha256'))):
                raise ValueError('Exact owner-only one-call synthetic smoke required')
            smoke=dict(smoke)
        return cls(api_key, grant['base_url'].rstrip('/'), MODEL, REGION, 'CNY',
                   grant['budget_id'], grant['max_requests'],
                   values['max_cost_cny'], values['input_cny_per_million'],
                   values['output_cny_per_million'], cap, smoke, monthly)

    def policy(self):
        policy = {
            'version': 1, 'provider': self.provider_id, 'model': self.model,
            'region': self.region, 'currency': self.currency,
            'budget_key': _key(self.budget_id),
            'endpoint_model_key': hashlib.sha256((self.base_url + '\n' + self.model).encode()).hexdigest(),
            'max_requests': self.max_requests, 'max_cost_cny': _money(self.max_cost_cny),
            'input_cny_per_million': _money(self.input_cny_per_million),
            'output_cny_per_million': _money(self.output_cny_per_million),
            'max_completion_tokens': self.max_output_tokens,
            'output_token_margin': OUTPUT_TOKEN_MARGIN,
            'reserved_output_tokens': self.reserved_output_tokens,
            'input_token_reservation': INPUT_TOKEN_RESERVATION,
            'max_input_bytes': 8192, 'enable_thinking': True,
            'reasoning_effort': 'xhigh', 'refund_policy': 'NEVER',
        }
        if self.smoke is not None:policy['smoke']=dict(self.smoke)
        if self.monthly is not None:
            policy.update(version=2,monthly=dict(self.monthly),refund_policy='CONTROLLER_PUBLISHED_VERIFIED_USAGE_ONLY',
                          month_end_admission_margin_seconds=300,initial_smoke_max_completion_tokens=self.max_output_tokens)
        return json.dumps(policy, sort_keys=True, separators=(',', ':'))
