"""Explicit authored input grammar; no general semantic extraction claim."""
import re

KINDS={'报告':'USER_REPORTED_EVENT','猜测':'USER_GUESS','自述':'CHARACTER_SELF_REPORT','转述':'THIRD_PARTY_REPORT','规则':'CONDITIONAL_RULE','概念':'CONDITIONAL_RULE'}
GRAMMAR=re.compile(r'^(报告|猜测|自述|转述|规则|概念)\[([^\]\n]{1,24})\]：(\S.*)$',re.S)


def extract(text, context, tenant, conversation, topic):
    records=[]; revisions=[]; unresolved=[]
    for part in text.split('；'):
        part=part.strip()
        if not part: continue
        match=GRAMMAR.fullmatch(part)
        if match:
            label,actor,content=match.groups()
            records.append({'kind':KINDS[label],'content':content,'subject_refs':[(topic or conversation)+':'+actor], 'origin':'direct_user'})
            continue
        if part.startswith(('更正：','撤回：','假设：')):
            action={'更正':'CORRECT','撤回':'RETRACT','假设':'HYPOTHETICAL_BRANCH'}[part.split('：')[0]]
            body=part.split('：',1)[1]; old,_,replacement=body.partition(' => ')
            candidates=[r for r in context.project(tenant,conversation,topic) if r['content']==old]
            if len(candidates)==1 and (action=='RETRACT' or replacement):
                command={'action':action,'target_ids':[candidates[0]['record_id']]}
                if replacement: command['new_record']={'kind':candidates[0]['kind'],'content':replacement,'subject_refs':candidates[0]['subject_refs']}
                revisions.append(command)
                continue
            unresolved.append('Revision target ambiguous or unsupported; no record changed')
        elif re.fullmatch(r'2\s*\+\s*2(?:\s*(?:等于几|是多少|=|？|\?))*',part):
            continue
        else:
            unresolved.append('Unsupported input fragment; scripted extraction only')
    return records,revisions,unresolved
