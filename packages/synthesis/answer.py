"""Natural projection of registered authored records, not a semantic judge."""
LABELS={'USER_REPORTED_EVENT':'你报告','USER_GUESS':'你猜测','CHARACTER_SELF_REPORT':'人物自述','THIRD_PARTY_REPORT':'转述中提到','SYSTEM_INTERPRETATION':'一个有条件的解释是','CONDITIONAL_RULE':'给定的判据是','HYPOTHETICAL':'在假设分支中'}


def synthesize(records):
    usable=[r for r in records if r['kind'] in LABELS]
    if not usable: return '这段输入尚未解析。可以说明具体事件、人物和时间；当前模拟不具备任意语言理解能力。',[],['当前输入未覆盖，不能据此确定人物动机。']
    selected=usable[-4:]
    claims=[{'claim':r['content'],'record_id':r['record_id'],'kind':r['kind']} for r in selected]
    snippets=[LABELS[r['kind']]+'“'+r['content']+'”' for r in selected]
    text='；'.join(snippets)+'。'
    if any(r['kind']=='USER_GUESS' for r in selected): text+='猜测仍是待核对的解释，重复提及不会增加独立证据。'
    if any(r['kind']=='CHARACTER_SELF_REPORT' for r in selected): text+='自述记录的是表达，并不能直接确定私人真实想法。'
    text+='先核对关键条件，再决定下一步；目前不据此判断永久人格或唯一动机。'
    return text,claims,['信息来自合成的报告与条件，尚未独立验证。']
