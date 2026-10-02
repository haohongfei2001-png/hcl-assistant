"""Explicit adapter selection. No probing, fallback, environment reads or calls."""
from packages.adapter.deepseek import DeepSeekAdapter
from packages.adapter.qwen import QwenAdapter


def create_adapter(config, *, deepseek_factory=DeepSeekAdapter, **kwargs):
    provider = getattr(config, 'provider_id', 'deepseek')
    if provider not in ('deepseek', 'qwen'):
        raise ValueError('unsupported_provider')
    factory = QwenAdapter if provider == 'qwen' else deepseek_factory
    return factory(base_url=config.base_url, model=config.model,
                   api_key=config.api_key, **kwargs)
