"""Small one-time setup surface; non-secret defaults are versioned in the repo."""
from dataclasses import dataclass,field
import json
from pathlib import Path
import re
from urllib.parse import urlsplit,parse_qs
from packages.adapter.development_budget import DevelopmentConfig
from packages.cloud.auth import valid_verifier

CONSUMED={'hcla-20261001-six-requests-usd10','hcla-development-20261001-initial-six'}
PROFILE=Path(__file__).resolve().parents[2]/'control/cloud-profile.json'

def strict_json(value):
    if not isinstance(value,str) or len(value)>16384:raise ValueError('Invalid setup value')
    def pairs(items):
        result={}
        for key,item in items:
            if key in result:raise ValueError('Duplicate setup field')
            result[key]=item
        return result
    return json.loads(value,object_pairs_hook=pairs)

def provider_from_grant(grant,api_key):
    """A grant is authorization metadata, never a source of implicit capacity."""
    if not isinstance(grant,dict) or set(grant)!={'budget_id','max_requests','max_cost_usd'}:raise ValueError('Explicit bounded grant required')
    if not isinstance(grant['budget_id'],str) or type(grant['max_requests']) is not int or not isinstance(grant['max_cost_usd'],str):raise ValueError('Invalid grant bounds')
    if grant['budget_id'] in CONSUMED:raise ValueError('Consumed grant cannot be renewed')
    profile=json.loads(PROFILE.read_text())
    if profile['provider_enabled_without_approved_grant'] is not False or profile['grant']['default'] is not None:raise ValueError('Unsafe cloud profile')
    model=profile['provider']
    if model['model']!='deepseek-v4-pro' or model['thinking']!='enabled' or model['reasoning_effort']!='high':raise ValueError('Requested model profile required')
    return DevelopmentConfig.from_env({
        'HCLA_DEEPSEEK_API_KEY':api_key,'HCLA_DEEPSEEK_BASE_URL':model['base_url'],
        'HCLA_DEEPSEEK_MODEL':model['model'],'HCLA_DEV_ACCESS_TOKEN':'cloud-auth-has-separate-owner-login',
        'HCLA_DEV_MAX_REQUESTS':str(grant['max_requests']),'HCLA_DEV_MAX_COST_USD':grant['max_cost_usd'],
        'HCLA_DEV_INPUT_USD_PER_MILLION':model['input_usd_per_million'],
        'HCLA_DEV_OUTPUT_USD_PER_MILLION':model['output_usd_per_million'],
        'HCLA_DEV_MAX_OUTPUT_TOKENS':str(model['max_output_tokens']),'HCLA_DEV_BUDGET_ID':grant['budget_id'],
    })

@dataclass(repr=False)
class CloudConfig:
    database_url:str=field(repr=False)
    origin:str
    login:str=field(repr=False)
    verifier:str=field(repr=False)
    state_key:str=field(repr=False)
    provider:DevelopmentConfig|None=field(repr=False)
    trial:object|None=field(default=None,repr=False)
    cloud_api_key:str=field(default='',repr=False)
    member_provider:object|None=field(default=None,repr=False)
    member_recovery:bool=False
    selected_provider:str='deepseek'
    @classmethod
    def from_env(cls,env):
        if not env.get('HCLA_DATABASE_URL') or not env.get('HCLA_PUBLIC_ORIGIN'):raise ValueError('Cloud setup incomplete')
        if 'HCLA_OWNER_CONFIG' in env:
            try:
                owner=strict_json(env['HCLA_OWNER_CONFIG'])
                if set(owner)!={'schema_version','login','verifier','temporary_state_key'} or type(owner['schema_version']) is not int or owner['schema_version']!=1:raise ValueError()
                login,verifier,state_key=owner['login'],owner['verifier'],owner['temporary_state_key']
            except (ValueError,TypeError,KeyError):raise ValueError('Invalid private owner configuration') from None
        else:
            # Compatibility with the initial explicit operator fields. Never shown in the normal setup.
            login,verifier,state_key=(env.get(k) for k in ('HCLA_OWNER_LOGIN','HCLA_OWNER_PASSWORD_HASH','HCLA_TEMPORARY_STATE_KEY'))
        if not isinstance(login,str) or not 1<=len(login)<=80 or any(ord(c)<32 for c in login):raise ValueError('Owner login required')
        origin=urlsplit(env['HCLA_PUBLIC_ORIGIN']);db=urlsplit(env['HCLA_DATABASE_URL'])
        if origin.scheme!='https' or not origin.hostname or origin.username or origin.password or origin.path or origin.query or origin.fragment or origin.port not in (None,443):raise ValueError('Exact HTTPS public origin required')
        if db.scheme not in {'postgres','postgresql'} or not db.hostname or parse_qs(db.query).get('sslmode')!=['verify-full']:raise ValueError('TLS verified Postgres required')
        if not valid_verifier(verifier):raise ValueError('Owner password verifier required')
        if not isinstance(state_key,str) or not re.fullmatch(r'[0-9a-f]{64}',state_key):raise ValueError('Temporary state signing key required')
        provider=None
        selected_provider=env.get('HCLA_PROVIDER','deepseek')
        if selected_provider not in ('deepseek','qwen'):raise ValueError('Explicit supported provider required')
        if selected_provider=='qwen':
            if 'HCLA_MODEL_GRANT' in env or env.get('HCLA_CLOUD_PROVIDER_ENABLED')=='true' or 'HCLA_TRIAL_WINDOW' in env:
                raise ValueError('Qwen cannot reuse legacy USD or trial authorization')
            if 'HCLA_QWEN_MODEL_GRANT' in env:
                from packages.cloud.qwen_config import QwenConfig
                provider=QwenConfig.from_grant(strict_json(env['HCLA_QWEN_MODEL_GRANT']),env.get('HCLA_QWEN_API_KEY',''))
        elif 'HCLA_QWEN_MODEL_GRANT' in env:
            raise ValueError('Explicit Qwen provider selection required')
        elif 'HCLA_MODEL_GRANT' in env:
            try:grant=strict_json(env['HCLA_MODEL_GRANT'])
            except (ValueError,TypeError):raise ValueError('Invalid approved grant') from None
            provider=provider_from_grant(grant,env.get('HCLA_DEEPSEEK_API_KEY',''))
        elif env.get('HCLA_CLOUD_PROVIDER_ENABLED')=='true':
            # Legacy operator policy, still strictly validated and never a default.
            mapping=dict(env);mapping['HCLA_DEV_ACCESS_TOKEN']='cloud-auth-has-separate-owner-login'
            provider=DevelopmentConfig.from_env(mapping)
        if provider and selected_provider=='deepseek':
            if provider.budget_id in CONSUMED:raise ValueError('Consumed grant cannot be renewed')
            if provider.model!='deepseek-v4-pro':raise ValueError('Requested deepseek-v4-pro required')
            from decimal import Decimal
            if provider.input_usd_per_million<Decimal('1.32') or provider.output_usd_per_million<Decimal('3.96'):raise ValueError('Configured peak rates required')
        trial=None
        if 'HCLA_TRIAL_WINDOW' in env:
            from packages.cloud.trial import TrialWindow
            trial=TrialWindow.from_value(strict_json(env['HCLA_TRIAL_WINDOW']))
            if provider is None:raise ValueError('Trial requires a new explicit model grant')
        from packages.cloud.member_auth import MemberProviderConfig
        member_provider=MemberProviderConfig.from_env(env)
        recovery=env.get('HCLA_MEMBER_RECOVERY','')
        if recovery not in ('','pkce') or (recovery and member_provider is None):raise ValueError('Invalid account recovery configuration')
        return cls(env['HCLA_DATABASE_URL'],env['HCLA_PUBLIC_ORIGIN'],login,verifier,state_key,provider,trial,env.get('HCLA_DEEPSEEK_API_KEY','') if selected_provider=='deepseek' else '',member_provider,recovery=='pkce',selected_provider)
