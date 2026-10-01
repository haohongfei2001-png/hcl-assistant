"""One-time owner configuration. Browser status contains no configuration values."""
from dataclasses import dataclass,field
import re
from urllib.parse import urlsplit,parse_qs
from packages.adapter.development_budget import DevelopmentConfig
from packages.cloud.auth import valid_verifier

CONSUMED={'hcla-20261001-six-requests-usd10','hcla-development-20261001-initial-six'}
@dataclass(repr=False)
class CloudConfig:
    database_url:str=field(repr=False)
    origin:str
    login:str=field(repr=False)
    verifier:str=field(repr=False)
    state_key:str=field(repr=False)
    provider:DevelopmentConfig|None=field(repr=False)
    @classmethod
    def from_env(cls,env):
        required=('HCLA_DATABASE_URL','HCLA_PUBLIC_ORIGIN','HCLA_OWNER_LOGIN','HCLA_OWNER_PASSWORD_HASH','HCLA_TEMPORARY_STATE_KEY')
        if any(not env.get(k) for k in required): raise ValueError('Cloud setup incomplete')
        origin=urlsplit(env['HCLA_PUBLIC_ORIGIN']);db=urlsplit(env['HCLA_DATABASE_URL'])
        if origin.scheme!='https' or not origin.hostname or origin.username or origin.password or origin.path or origin.query or origin.fragment or origin.port not in (None,443): raise ValueError('Exact HTTPS public origin required')
        if db.scheme not in {'postgres','postgresql'} or not db.hostname or parse_qs(db.query).get('sslmode')!=['verify-full']: raise ValueError('TLS verified Postgres required')
        if not valid_verifier(env['HCLA_OWNER_PASSWORD_HASH']): raise ValueError('Owner password verifier required')
        if not re.fullmatch(r'[0-9a-f]{64}',env['HCLA_TEMPORARY_STATE_KEY']): raise ValueError('Temporary state signing key required')
        provider=None
        if env.get('HCLA_CLOUD_PROVIDER_ENABLED')=='true':
            mapping=dict(env);mapping['HCLA_DEV_ACCESS_TOKEN']='cloud-auth-has-separate-owner-login'
            provider=DevelopmentConfig.from_env(mapping)
            if provider.budget_id in CONSUMED: raise ValueError('Consumed grant cannot be renewed')
            if provider.model!='deepseek-v4-pro': raise ValueError('Requested deepseek-v4-pro required')
            from decimal import Decimal
            if provider.input_usd_per_million<Decimal('1.32') or provider.output_usd_per_million<Decimal('3.96'): raise ValueError('Configured peak rates required')
        return cls(env['HCLA_DATABASE_URL'],env['HCLA_PUBLIC_ORIGIN'],env['HCLA_OWNER_LOGIN'],env['HCLA_OWNER_PASSWORD_HASH'],env['HCLA_TEMPORARY_STATE_KEY'],provider)
