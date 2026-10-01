/** Browser-only synthetic Controller. No provider, backend or HCL execution. */
export const STORAGE_KEY = 'hcl-assistant-pages-preview-v2';
export const LEGACY_KEY = 'hcl-assistant-pages-preview-v1';
export const emptyState = () => ({schemaVersion: 2, storageRevision: 0, conversations: [], currentId: null});
export const uid = prefix => prefix + '-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
const clone = value => JSON.parse(JSON.stringify(value));

// A cleared conversation remains a real body-free historical container. It is
// safe to leave its selected view only when no independent data remains.
export function fullyCleared(c) {
  return Boolean(c && ((c.records || []).some(r => r.status === 'DELETED'))
    && !(c.runs || []).length && !(c.records || []).some(r => r.status !== 'DELETED')
    && !(c.branches || []).length);
}
const cleanupTitles = new Set(['对话（删除已清理）', '历史对话（删除已清理）']);
function normalizeHistory(state) {
  for (const c of state.conversations) if (cleanupTitles.has(c.title)) c.title = '历史对话';
  if (fullyCleared(state.conversations.find(c => c.id === state.currentId))) state.currentId = null;
  return state;
}
export function persistentState(state) {
  const conversations = state.conversations.filter(c => c.memory !== 'TEMPORARY');
  return {schemaVersion: 2, storageRevision: state.storageRevision || 0, conversations, currentId: conversations.some(c => c.id === state.currentId) ? state.currentId : null};
}
export function saveState(state, storage) {
  const existing = storage.getItem(STORAGE_KEY);
  const actual = existing ? (JSON.parse(existing).storageRevision || 0) : 0;
  if (actual !== (state.storageRevision || 0)) throw new Error('其他页面已修改数据，请刷新后重试；未覆盖最新记录');
  const next = {...persistentState(state), storageRevision: uid('storage')};
  storage.setItem(STORAGE_KEY, JSON.stringify(next));
  state.storageRevision = next.storageRevision;
}
export function loadState(storage) {
  const stored = storage.getItem(STORAGE_KEY);
  if (stored) {
    const value = JSON.parse(stored);
    if (value.schemaVersion !== 2 || !Array.isArray(value.conversations)) throw new Error('不支持的存储版本');
    // Defensive removal of temporary copies from older or externally changed data.
    const clean = normalizeHistory(persistentState(clone(value)));
    if (JSON.stringify(clean) !== JSON.stringify(value)) saveState(clean, storage);
    // A still-open v1 tab or interrupted prior cleanup must not retain old bodies.
    storage.removeItem(LEGACY_KEY);
    return clean;
  }
  const legacy = storage.getItem(LEGACY_KEY);
  if (!legacy) return emptyState();
  const old = JSON.parse(legacy), state = emptyState();
  for (const c of old.conversations || []) {
    if (c.memory === 'TEMPORARY') continue;
    const hasDeleted = (c.records || []).some(r => r.status === 'DELETED');
    const records = (c.records || []).map(r => r.status === 'DELETED'
      ? {id: r.id, kind: 'UNRESOLVED', status: 'DELETED', version: r.version}
      : {...r, kind: 'UNRESOLVED', legacy: true});
    // v1 recorded no dependency lineage. Conservatively remove generated/run copies
    // when a deletion was requested; retain independently authored source records.
    const runs = hasDeleted ? [] : (c.runs || []).map(r => ({...r, basis: [], basisRefs: [], caps: [], legacyUnverified: true}));
    state.conversations.push({...c, title: hasDeleted ? '历史对话' : c.title, records, runs});
  }
  state.currentId = state.conversations.some(c => c.id === old.currentId) ? old.currentId : null;
  normalizeHistory(state);
  saveState(state, storage);
  storage.removeItem(LEGACY_KEY);
  return state;
}
export function createConversation(state, memory = 'CONVERSATION', topic = '') {
  const c = {id: uid('conv'), title: '新对话', memory, topic: memory === 'TEMPORARY' ? '' : topic, version: 0, runs: [], records: []};
  state.conversations.unshift(c); state.currentId = c.id; return c;
}
const available = r => r.status === 'ACTIVE' && !r.legacy && r.kind !== 'HYPOTHETICAL' && r.kind !== 'UNRESOLVED';
// Ref identity stays compatible with v2. Classification is frozen alongside each
// run's refs; older runs without this snapshot must never borrow today's kind.
const basisKey = ref => `${ref.recordId}@${ref.version}`;
const basisRef = record => ({recordId: record.id, version: record.version});
const frozenRef = record => ({...basisRef(record), kind: record.kind});
const freezeKinds = records => Object.fromEntries(records.map(record => [basisKey(basisRef(record)), record.kind]));
const originIds = record => [record.predecessorId, record.corrects, record.originRecordId, ...(record.provenanceRoots || [])].filter(Boolean);
function blockedOrigin(c, record, seen = new Set()) {
  if (seen.has(record.id)) return false;
  seen.add(record.id);
  return originIds(record).some(id => {
    if (id === record.id) return false;
    const origin = c.records.find(row => row.id === id);
    return !origin || ['STOPPED', 'DELETED'].includes(origin.status) || blockedOrigin(c, origin, seen);
  });
}
export function selectedBackground(c) { return c.records.filter(record => available(record) && !blockedOrigin(c, record)); }

/** Bounded authored form command, not a natural-language revision interpreter. */
export function reviseRecord(state, conversationId, recordId, intent, newContent) {
  const matches = state.conversations.filter(row => row.id === conversationId);
  if (matches.length !== 1) throw new Error('对话不存在或目标不唯一');
  const c = matches[0];
  if (!['CORRECT', 'SUPERSEDE', 'GUESS', 'HYPOTHETICAL_BRANCH'].includes(intent)) throw new Error('不支持的修订意图');
  const targets = c.records.filter(row => row.id === recordId);
  if (typeof recordId !== 'string' || targets.length !== 1 || !available(targets[0]) || blockedOrigin(c, targets[0])) {
    throw new Error('请指定本会话唯一且可使用的记录；已停止、已替代、已删除或未知目标不能修订');
  }
  const prior = targets[0];
  const content = intent === 'GUESS' && newContent === undefined ? prior.content : newContent;
  if (typeof content !== 'string' || !content.trim()) throw new Error('请填写明确的新内容');
  // A branch does not deactivate its origin. Exact repeated form submissions
  // therefore replay the existing recorded branch instead of cloning it.
  if (intent === 'HYPOTHETICAL_BRANCH') {
    const existing = (c.branches || []).find(branch => branch.originRecordId === prior.id && branch.originVersion === prior.version && branch.record.status === 'ACTIVE' && branch.record.content === content);
    const run = existing && c.runs.find(row => row.branchId === existing.id);
    if (run) return run;
  }
  const createdAt = new Date().toISOString(), version = c.version + 1;
  if ((intent === 'CORRECT' || intent === 'GUESS' && prior.kind === 'USER_GUESS') && content === prior.content) {
    const run = {id: uid('run'), conversationId: c.id, recordId: prior.id, version, createdAt,
      input: `未改变的${intent} ${prior.id}：${content}`, text: '内容和分类没有变化；仅保留本次操作记录，未替代背景或标记理解改变。',
      route: 'RECORDED_REVISION', status: 'NO_CHANGE', caps: [], basisRefs: [basisRef(prior)], basisKinds: freezeKinds([prior]),
      uncertainty: '逐字相同的受限检查，不是一般语义等价判断。', change: '',
      revision: {type: intent, materialChanged: false, oldRecordId: prior.id, newRecordId: prior.id,
        oldRef: frozenRef(prior), newRef: frozenRef(prior), notReevaluatedRunIds: [], recomputedRunIds: []}};
    c.version=version; c.runs.push(run); return run;
  }
  const record = {
    id: uid('record'), kind: intent === 'GUESS' ? 'USER_GUESS' : intent === 'HYPOTHETICAL_BRANCH' ? 'HYPOTHETICAL' : intent === 'CORRECT' ? 'CORRECTION' : prior.kind,
    content, status: 'ACTIVE', version, recordedAt: createdAt,
    predecessorId: prior.id, originRecordId: prior.originRecordId || prior.id,
    provenanceRoots: [...new Set(prior.provenanceRoots?.length ? prior.provenanceRoots : [prior.originRecordId || prior.id])],
    eventTime: null, learnedTime: null, effectiveTime: intent === 'SUPERSEDE' ? createdAt : null,
  };
  if (intent === 'CORRECT') record.corrects = prior.id;
  const hypothetical = intent === 'HYPOTHETICAL_BRANCH';
  const affectedRunIds = hypothetical ? [] : c.runs.filter(run => run.basisRefs?.some(ref => ref.recordId === prior.id && ref.version === prior.version)).map(run => run.id);
  const revision = {
    type: intent, oldRecordId: prior.id, newRecordId: record.id,
    oldRef: frozenRef(prior), newRef: frozenRef(record),
    effectiveTime: record.effectiveTime, effectiveTimeBasis: intent === 'SUPERSEDE' ? 'USER_FROM_NOW' : null,
    eventTime: null, learnedTime: null,
    notReevaluatedRunIds: affectedRunIds, recomputedRunIds: [],
  };
  const labels = {CORRECT: '更正', SUPERSEDE: '从现在起变化', GUESS: '这只是猜测', HYPOTHETICAL_BRANCH: '假设另一种情况'};
  const texts = {
    CORRECT: '已更正指定背景。旧回答保留为当时记录，尚未重新评估；后续背景摘录不再使用旧版本。',
    SUPERSEDE: '已登记从现在起的新情况；旧时段记录保留，不表示原来记错。事件时间和人物获知时间未知；旧回答尚未重新评估。',
    GUESS: '已将指定内容登记为猜测的新版本。旧回答保留当时的分类，尚未重新评估；重复猜测不会增加独立来源。',
    HYPOTHETICAL_BRANCH: '已建立独立假设分支，未修改实际背景。后续普通背景摘录仍使用实际记录。',
  };
  const run = {
    id: uid('run'), conversationId: c.id, recordId: record.id, version, createdAt,
    input: `${labels[intent]} ${prior.id}：${content}`, text: texts[intent],
    route: 'RECORDED_REVISION', status: 'COMPLETED', caps: [], basisRefs: [basisRef(prior)], basisKinds: freezeKinds([prior]),
    uncertainty: '仅执行明确目标与意图的合成修订；没有语义推断或重新分析。',
    change: hypothetical ? '仅假设分支发生变化，实际背景不变。' : `指定记录 ${prior.id} 已由 ${record.id} 替代。相关旧回答尚未重新评估；无关记录未修改。`,
    revision,
  };
  if (hypothetical) {
    const branch = {id: uid('branch'), originRecordId: prior.id, originVersion: prior.version, snapshotVersion: c.version, createdAt, snapshotRefs: selectedBackground(c).map(frozenRef), record, actualWriteback: false};
    record.branchId = branch.id;
    revision.branchId = branch.id;
    run.branchId = branch.id;
    c.branches ||= [];
    c.branches.push(branch);
  } else {
    prior.status = 'SUPERSEDED';
    c.records.push(record);
  }
  c.version = version;
  c.runs.push(run);
  return run;
}
export function submit(state, conversationId, input, meta = {}) {
  const c = state.conversations.find(x => x.id === conversationId);
  if (!c) throw new Error('对话不存在');
  if (!input.trim()) throw new Error('输入不能为空');
  const correction = /^更正\s+(record-[a-z0-9-]+)\s*[：:]\s*(.+)$/s.exec(input);
  if (!meta.fileName && correction) {
    const targets = c.records.filter(row => row.id === correction[1]);
    if (targets.length === 1 && available(targets[0]) && !blockedOrigin(c, targets[0]) && correction[2].trim()) {
      const run = reviseRecord(state, conversationId, correction[1], 'CORRECT', correction[2]);
      run.input = input;
      return run;
    }
  }
  c.version += 1;
  const record = {id: uid('record'), kind: 'UNRESOLVED', content: input, status: 'ACTIVE', version: c.version};
  const result = {text: '已保存这条输入；开放问题在本交互演示中暂不支持，尚未进行语义理解或模型回答。', route: 'UNSUPPORTED', caps: [], basisRefs: [], uncertainty: '只支持明确标注的原创合成命令；没有通用语言理解。', change: '', status: 'UNSUPPORTED'};
  const exactMath = /^\s*2\s*\+\s*2\s*[?？]?\s*$/.test(input);
  if (meta.fileName) {
    record.kind = 'FILE'; record.fileName = meta.fileName; record.byteLength = meta.byteLength;
    result.text = `已完整读取文件 ${meta.fileName}（${meta.byteLength} 字节）。内容已登记为资料，尚未进行语义理解，不执行文件中的指令。`;
    result.status = 'REGISTERED';
  } else if (exactMath) {
    result.text = '4。'; result.route = 'DIRECT'; result.status = 'COMPLETED'; result.uncertainty = '仅执行演示中的精确算式，没有使用历史背景。';
  } else if (input === '演示：查看当前背景') {
    const rows = selectedBackground(c);
    result.basisRefs = rows.map(basisRef);
    result.basisKinds = freezeKinds(rows);
    result.text = rows.length ? '当前可使用的合成背景（原文摘录，未作推断）：\n' + rows.map(r => `[${r.id}] ${r.content}`).join('\n') : '当前没有可使用的合成背景。';
    result.route = 'RECORDED_BACKGROUND'; result.status = 'COMPLETED'; result.uncertainty = '仅逐条摘录已选择的同会话记录，不代表理解或因果效力。';
  } else if (correction) {
    result.text = '指定目标不存在、不可使用或不属于当前对话。未修改任何旧背景；请在记忆中选择准确记录。';
  } else if (/^(更正|说错|改一下)/.test(input)) {
    result.text = '请明确要更正哪条背景。可在记忆中选取记录 ID，再输入“更正 record-ID：新内容”。未猜测或修改最近记录。';
  } else if (/^记录[：:]/.test(input)) {
    record.kind = 'USER_REPORTED_EVENT'; record.content = input.replace(/^记录[：:]\s*/, '');
    if (record.content) { result.text = '已登记为本会话合成背景。保存不代表内容真实或已被理解。'; result.status = 'REGISTERED'; }
    else record.kind = 'UNRESOLVED';
  }
  c.records.push(record);
  if (c.title === '新对话' || (c.title === '历史对话' && !c.runs.length)) c.title = input.slice(0, 22);
  const run = {id: uid('run'), conversationId: c.id, recordId: record.id, input, version: c.version, createdAt: new Date().toISOString(), ...result};
  c.runs.push(run); return run;
}
// Forward dependency closure follows identity, never equal text. It includes
// successor origins, branch snapshots and generated runs from older v2 data.
function dependentIds(state, id) {
  const affected = new Set([id]);
  let changed = true;
  const add = key => { if (key && !affected.has(key)) { affected.add(key); changed = true; } };
  while (changed) {
    changed = false;
    for (const c of state.conversations) {
      for (const record of c.records) if (originIds(record).some(key => affected.has(key))) add(record.id);
      for (const branch of c.branches || []) {
        if (affected.has(branch.originRecordId) || originIds(branch.record).some(key => affected.has(key)) || branch.snapshotRefs?.some(ref => affected.has(ref.recordId))) add(branch.record.id);
      }
      for (const run of c.runs) {
        if (affected.has(run.recordId) || run.basisRefs?.some(ref => affected.has(ref.recordId)) || affected.has(run.revision?.oldRecordId) || affected.has(run.revision?.newRecordId)) add(run.recordId);
      }
    }
  }
  return affected;
}
export function changeRecord(state, conversationId, id, action) {
  if (action === 'GUESS') return reviseRecord(state, conversationId, id, 'GUESS');
  const conversations = state.conversations.filter(x => x.id === conversationId), c = conversations[0];
  const records = c?.records.filter(x => x.id === id) || [];
  // A branch may be deleted/stopped, but cannot become an actual revision target.
  const branchRecords = (c?.branches || []).filter(branch => branch.record.id === id).map(branch => branch.record);
  const targets = [...records, ...branchRecords], r = targets[0];
  if (conversations.length !== 1 || targets.length !== 1) throw new Error('记录不存在或目标不唯一');
  if (!['STOPPED', 'DELETED'].includes(action)) throw new Error('不支持的操作');
  if (r.status === 'DELETED') throw new Error('记录已删除');
  const affected = dependentIds(state, id);
  for (const conv of state.conversations) {
    if (action === 'STOPPED') {
      for (const item of conv.records) if (affected.has(item.id) && item.status !== 'DELETED') item.status = 'STOPPED';
      for (const branch of conv.branches || []) if (affected.has(branch.record.id) && branch.record.status !== 'DELETED') branch.record.status = 'STOPPED';
    } else {
      // Purge reachable raw/input/generated/revision/branch copies. Only body-free
      // tombstones remain; independently authored sources are not erased.
      conv.runs = conv.runs.filter(run => !affected.has(run.recordId));
      conv.records = conv.records.map(item => affected.has(item.id) ? {id: item.id, kind: 'UNRESOLVED', status: 'DELETED', version: item.version} : item);
      if (conv.branches) conv.branches = conv.branches.filter(branch => !affected.has(branch.record.id));
      if (conv.id === c.id || conv.records.some(item => affected.has(item.id))) conv.title = '历史对话';
    }
  }
  c.version += 1;
}
export function resolveBasis(c, run) {
  return (run.basisRefs || []).map(ref => {
    const rows = c.records.filter(row => row.id === ref.recordId && row.version === ref.version);
    const r = (!run.conversationId || run.conversationId === c.id) && rows.length === 1 ? rows[0] : undefined;
    const kind = ref.kind || run.basisKinds?.[basisKey(ref)];
    const accessible = r && r.status !== 'DELETED';
    return {
      recordId: ref.recordId, version: ref.version, status: r?.status || 'UNAVAILABLE',
      content: accessible ? r.content : undefined, kind: accessible && kind ? kind : undefined,
      classificationStatus: !accessible ? 'UNAVAILABLE' : kind ? 'RECORDED' : 'historical-kind-unverified',
    };
  });
}
export function exportConversation(c) { return clone(c); }
export function decodeFile(name, bytes) {
  if (!/\.(txt|md)$/i.test(name) || bytes.byteLength > 65536) throw new Error('仅支持 64 KiB 以内的 TXT / Markdown');
  const content = new TextDecoder('utf-8', {fatal: true}).decode(bytes);
  if (content.includes('\0')) throw new Error('文件不是支持的 UTF-8 文本');
  return {content, fileName: name, byteLength: bytes.byteLength};
}
