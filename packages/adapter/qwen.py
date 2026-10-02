"""Bounded text-only Model Studio Beijing adapter; no implicit live selection.

The shared transport owns cancellation, SSE limits and reasoning-text disposal.
Only this reviewed model and exact regional HTTPS endpoints may receive a key.
"""
from urllib.parse import urlsplit
import json
import re

from packages.adapter.deepseek import DeepSeekAdapter

MODEL = 'qwen3.8-max'
REGION = 'cn-beijing'
OUTPUT_TOKEN_MARGIN = 10
MAX_COMPLETION_TOKENS = 131072
INPUT_TOKEN_RESERVATION = 1000000
MAX_PROMPT_BYTES = 8192
PROMPT_FRAMING_ALLOWANCE_BYTES = 512


def endpoint(base_url):
    try:
        parsed = urlsplit(base_url)
        port = parsed.port
    except (TypeError, ValueError):
        raise ValueError('invalid_base_url') from None
    host = parsed.hostname or ''
    official = host == 'dashscope.aliyuncs.com' or re.fullmatch(
        r'[a-z0-9][a-z0-9-]{0,62}\.cn-beijing\.maas\.aliyuncs\.com', host)
    if (parsed.scheme != 'https' or not official or port not in (None, 443)
            or parsed.username or parsed.password or parsed.query or parsed.fragment
            or '\\' in base_url or any(c.isspace() for c in base_url)
            or parsed.path not in ('/compatible-mode/v1', '/compatible-mode/v1/')):
        raise ValueError('official_beijing_endpoint_required')
    return 'https://' + host + '/compatible-mode/v1/chat/completions'


class QwenAdapter(DeepSeekAdapter):
    provider_id = 'qwen'

    def __init__(self, *, base_url, model, api_key, **kwargs):
        if model != MODEL:
            raise ValueError('requested_qwen_model_required')
        if 'thinking_enabled' in kwargs or 'reasoning_effort' in kwargs:
            raise ValueError('fixed_qwen_thinking_contract_required')
        super().__init__(base_url=base_url, model=model, api_key=api_key, **kwargs)
        self.reasoning_effort = 'xhigh'

    def _endpoint(self, base_url, injected):
        # Even an injected transport never broadens the credential destination.
        return endpoint(base_url)

    def _request_payload(self, messages, max_tokens):
        if type(max_tokens) is not int or not 1 <= max_tokens <= MAX_COMPLETION_TOKENS:
            raise ValueError('bounded_total_output_required')
        if len(json.dumps(messages, ensure_ascii=False).encode('utf-8')) + PROMPT_FRAMING_ALLOWANCE_BYTES > MAX_PROMPT_BYTES:
            raise ValueError('bounded_input_required')
        payload = {'model': self.model, 'messages': messages, 'stream': True,
                   'stream_options': {'include_usage': True},
                   'enable_thinking': True, 'reasoning_effort': 'xhigh',
                   'max_completion_tokens': max_tokens}
        if len(json.dumps(payload, ensure_ascii=False).encode('utf-8')) > MAX_PROMPT_BYTES:
            raise ValueError('bounded_request_body_required')
        return payload

    def _completion_error(self, usage, consistent, max_tokens):
        # Qwen completion_tokens includes thinking; absent/malformed evidence
        # cannot certify a completed bounded request or release a reservation.
        if not consistent:
            return 'usage_unverified'
        if (usage['prompt_tokens'] > INPUT_TOKEN_RESERVATION
                or usage['completion_tokens'] > max_tokens + OUTPUT_TOKEN_MARGIN):
            return 'usage_limit'
        return None
