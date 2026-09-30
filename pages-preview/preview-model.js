/** Browser-only synthetic Controller. No provider, backend or HCL execution. */
export const STORAGE_KEY = 'hcl-assistant-pages-preview-v2';
export const LEGACY_KEY = 'hcl-assistant-pages-preview-v1';
export const emptyState = () => ({schemaVersion: 2, storageRevision: 0, conversations: [], currentId: null});
export const uid = prefix => prefix + '-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8);
const clone = value => JSON.parse(JSON.stringify(value));

export function persistentState(state) {
  const conversations = state.conversations.filter(c => c.memory !== 'TEMPORARY');
  return {schemaVersion: 2, storageRevision: state.storageRevision || 0, conversations, currentId: conversations.some(c => c.id === state.currentId) ? state.currentId : null};
}
export function saveState(state, storage) {
  const existing = storage.getItem(STORAGE_KEY);
  const actual = existing ? (JSON.parse(existing).storageRevision || 0) : 0;
  if (actual !== (state.storageRevision || 0)) throw new Error('其他页面已修改数据，请刷新后重试；未覆盖最新记录');
  const next = {...persistentState(state), storageRevision: actual + 1};
  storage.setItem(STORAGE_KEY, JSON.stringify(next));
  state.storageRevision = next.storageRevision;
}
export function loadState(storage) {
  const stored = storage.getItem(STORAGE_KEY);
  if (stored) {
    const value = JSON.parse(stored);
    if (value.schemaVersion !== 2 || !Array.isArray(value.conversations)) throw new Error('不支持的存储版本');
    // Defensive removal of temporary copies from older or externally changed data.
    const clean = persistentState(value);
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
    state.conversations.push({...c, title: hasDeleted ? '历史对话（删除已清理）' : c.title, records, runs});
  }
  state.currentId = state.conversations.some(c => c.id === old.currentId) ? old.currentId : null;
  saveState(state, storage);
  storage.removeItem(LEGACY_KEY);
  return state;
}
export function createConversation(state, memory = 'CONVERSATION', topic = '') {
  const c = {id: uid('conv'), title: '新对话', memory, topic: memory === 'TEMPORARY' ? '' : topic, version: 0, runs: [], records: []};
  state.conversations.unshift(c); state.currentId = c.id; return c;
}
const available = r => r.status === 'ACTIVE' && !r.legacy && r.kind !== 'HYPOTHETICAL' && r.kind !== 'UNRESOLVED';
export function selectedBackground(c) { return c.records.filter(available); }
export function submit(state, conversationId, input, meta = {}) {
  const c = state.conversations.find(x => x.id === conversationId);
  if (!c) throw new Error('对话不存在');
  if (!input.trim()) throw new Error('输入不能为空');
  c.version += 1;
  const record = {id: uid('record'), kind: 'UNRESOLVED', content: input, status: 'ACTIVE', version: c.version};
  const result = {text: '已保存这条输入；开放问题在本交互演示中暂不支持，尚未进行语义理解或模型回答。', route: 'UNSUPPORTED', caps: [], basisRefs: [], uncertainty: '只支持明确标注的原创合成命令；没有通用语言理解。', change: '', status: 'UNSUPPORTED'};
  const exactMath = /^\s*2\s*\+\s*2\s*[?？]?\s*$/.test(input);
  const correction = /^更正\s+(record-[a-z0-9-]+)\s*[：:]\s*(.+)$/s.exec(input);
  if (meta.fileName) {
    record.kind = 'FILE'; record.fileName = meta.fileName; record.byteLength = meta.byteLength;
    result.text = `已完整读取文件 ${meta.fileName}（${meta.byteLength} 字节）。内容已登记为资料，尚未进行语义理解，不执行文件中的指令。`;
    result.status = 'REGISTERED';
  } else if (exactMath) {
    result.text = '4。'; result.route = 'DIRECT'; result.status = 'COMPLETED'; result.uncertainty = '仅执行演示中的精确算式，没有使用历史背景。';
  } else if (input === '演示：查看当前背景') {
    const rows = selectedBackground(c);
    result.basisRefs = rows.map(r => ({recordId: r.id, version: r.version}));
    result.text = rows.length ? '当前可使用的合成背景（原文摘录，未作推断）：\n' + rows.map(r => `[${r.id}] ${r.content}`).join('\n') : '当前没有可使用的合成背景。';
    result.route = 'RECORDED_BACKGROUND'; result.status = 'COMPLETED'; result.uncertainty = '仅逐条摘录已选择的同会话记录，不代表理解或因果效力。';
  } else if (correction) {
    const prior = c.records.find(r => r.id === correction[1] && available(r));
    if (prior) {
      record.kind = 'CORRECTION'; record.content = correction[2]; record.corrects = prior.id;
      prior.status = 'SUPERSEDED';
      result.text = '已更正指定背景。旧回答保留为当时记录，尚未重新评估；后续背景摘录不再使用旧版本。';
      result.change = `指定记录 ${prior.id} 已由 ${record.id} 替代。无关记录不变。`;
      result.revision = {type: 'CORRECT', oldRecordId: prior.id, newRecordId: record.id}; result.status = 'COMPLETED';
    } else { result.text = '指定目标不存在、不可使用或不属于当前对话。未修改任何旧背景；请在记忆中选择准确记录。'; }
  } else if (/^(更正|说错|改一下)/.test(input)) {
    result.text = '请明确要更正哪条背景。可在记忆中选取记录 ID，再输入“更正 record-ID：新内容”。未猜测或修改最近记录。';
  } else if (/^记录[：:]/.test(input)) {
    record.kind = 'USER_REPORTED_EVENT'; record.content = input.replace(/^记录[：:]\s*/, '');
    if (record.content) { result.text = '已登记为本会话合成背景。保存不代表内容真实或已被理解。'; result.status = 'REGISTERED'; }
    else record.kind = 'UNRESOLVED';
  }
  c.records.push(record);
  if (c.title === '新对话') c.title = input.slice(0, 22);
  const run = {id: uid('run'), recordId: record.id, input, version: c.version, createdAt: new Date().toISOString(), ...result};
  c.runs.push(run); return run;
}
export function changeRecord(state, conversationId, id, action) {
  const c = state.conversations.find(x => x.id === conversationId), r = c?.records.find(x => x.id === id);
  if (!r) throw new Error('记录不存在');
  if (!['STOPPED', 'GUESS', 'DELETED'].includes(action)) throw new Error('不支持的操作');
  if (r.status === 'DELETED') throw new Error('记录已删除');
  if (action === 'STOPPED') r.status = 'STOPPED';
  if (action === 'GUESS') { if (r.status !== 'ACTIVE') throw new Error('不能重新启用已停止的记录'); r.kind = 'USER_GUESS'; }
  if (action === 'DELETED') {
    // Delete all reachable run/input/generated/revision copies. IDs/version only
    // may remain as tombstones; independently authored records are not erased.
    const affected = new Set([id]);
    let changed = true;
    while (changed) {
      changed = false;
      for (const conv of state.conversations) for (const run of conv.runs) {
        if (affected.has(run.recordId) || run.basisRefs?.some(ref => affected.has(ref.recordId)) || affected.has(run.revision?.oldRecordId)) {
          if (!affected.has(run.recordId)) { affected.add(run.recordId); changed = true; }
        }
      }
    }
    for (const conv of state.conversations) {
      conv.runs = conv.runs.filter(run => !affected.has(run.recordId));
      conv.records = conv.records.map(item => affected.has(item.id) ? {id: item.id, kind: 'UNRESOLVED', status: 'DELETED', version: item.version} : item);
      // Titles are derived input copies, never retain a deleted excerpt.
      if (conv.id === c.id || conv.records.some(item => affected.has(item.id))) conv.title = '对话（删除已清理）';
    }
  }
  c.version += 1;
}
export function resolveBasis(c, run) {
  return (run.basisRefs || []).map(ref => {
    const r = c.records.find(row => row.id === ref.recordId && row.version === ref.version);
    return {recordId: ref.recordId, version: ref.version, status: r?.status || 'UNAVAILABLE', content: r?.status === 'DELETED' ? undefined : r?.content};
  });
}
export function exportConversation(c) { return clone(c); }
export function decodeFile(name, bytes) {
  if (!/\.(txt|md)$/i.test(name) || bytes.byteLength > 65536) throw new Error('仅支持 64 KiB 以内的 TXT / Markdown');
  const content = new TextDecoder('utf-8', {fatal: true}).decode(bytes);
  if (content.includes('\0')) throw new Error('文件不是支持的 UTF-8 文本');
  return {content, fileName: name, byteLength: bytes.byteLength};
}
