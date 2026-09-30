import test from 'node:test';
import assert from 'node:assert/strict';
import {
  emptyState, createConversation, submit, reviseRecord, changeRecord,
  selectedBackground, resolveBasis, exportConversation, saveState, loadState,
} from '../../pages-preview/preview-model.js';

const setup = memory => {
  const state = emptyState(), c = createConversation(state, memory);
  return {state, c};
};
const store = () => {
  const values = new Map();
  return {getItem: key => values.get(key) || null, setItem: (key, value) => values.set(key, value), removeItem: key => values.delete(key), bytes: () => JSON.stringify([...values])};
};
const authored = (state, c, content) => submit(state, c.id, `记录：${content}`);
const background = (state, c) => submit(state, c.id, '演示：查看当前背景');
const row = (c, id) => c.records.find(record => record.id === id);
const savedKind = (run, ref) => run.basisKinds[`${ref.recordId}@${ref.version}`];

test('CORRECT creates a successor and new run while keeping prior content/classification/version', () => {
  const {state, c} = setup();
  const original = authored(state, c, 'P1_ORIGINAL_BEFORE_PEBBLE'), old = background(state, c);
  const independent = authored(state, c, 'P1_INDEPENDENT_TEA'), oldBytes = JSON.stringify(old);
  const changed = reviseRecord(state, c.id, original.recordId, 'CORRECT', 'P1_CORRECTED_AFTER_PEBBLE');
  assert.notEqual(changed.id, old.id);
  assert.equal(changed, c.runs.at(-1));
  assert.equal(row(c, original.recordId).status, 'SUPERSEDED');
  assert.equal(row(c, original.recordId).content, 'P1_ORIGINAL_BEFORE_PEBBLE');
  assert.equal(row(c, original.recordId).kind, 'USER_REPORTED_EVENT');
  assert.equal(row(c, original.recordId).version, 1);
  assert.equal(row(c, independent.recordId).status, 'ACTIVE');
  assert.equal(JSON.stringify(old), oldBytes);
  assert.deepEqual(changed.revision.oldRef, {recordId: original.recordId, version: 1, kind: 'USER_REPORTED_EVENT'});
  assert.deepEqual(changed.revision.notReevaluatedRunIds, [old.id]);
  assert.deepEqual(changed.revision.recomputedRunIds, []);
  assert.equal(row(c, changed.recordId).corrects, original.recordId);
  const next = background(state, c);
  assert(!next.text.includes('P1_ORIGINAL_BEFORE_PEBBLE'));
  assert(next.text.includes('P1_CORRECTED_AFTER_PEBBLE'));
  assert.equal(resolveBasis(c, old)[0].kind, 'USER_REPORTED_EVENT');
  assert.equal(resolveBasis(c, next)[1].kind, 'CORRECTION');
});

test('precise authored correction grammar routes through the same revision receipt', () => {
  const {state, c} = setup(), original = authored(state, c, 'Thursday lantern'), old = background(state, c);
  const input = `更正  ${original.recordId} : Friday lantern`;
  const changed = submit(state, c.id, input);
  assert.equal(changed.input, input);
  assert.equal(changed.revision.type, 'CORRECT');
  assert.equal(changed.version, old.version + 1);
  assert.equal(c.runs.length, 3);
  assert.equal(row(c, changed.recordId).predecessorId, original.recordId);
  const before = JSON.stringify(selectedBackground(c));
  for (const input of ['现在不是星期四', '从现在起是星期六', '假设白纸', '这只是猜测', '更正：星期日']) {
    assert.equal(submit(state, c.id, input).status, 'UNSUPPORTED');
  }
  assert.equal(JSON.stringify(selectedBackground(c)), before);
});

test('SUPERSEDE is explicit from-now replacement with unknown event/learned time', () => {
  const {state, c} = setup(), original = authored(state, c, 'Entrance east'), old = background(state, c);
  const changed = reviseRecord(state, c.id, original.recordId, 'SUPERSEDE', 'Entrance south');
  const successor = row(c, changed.recordId);
  assert.equal(changed.revision.type, 'SUPERSEDE');
  assert.equal(changed.revision.effectiveTimeBasis, 'USER_FROM_NOW');
  assert.equal(successor.effectiveTime, changed.createdAt);
  assert.equal(changed.revision.effectiveTime, changed.createdAt);
  assert.equal(successor.recordedAt, changed.createdAt);
  for (const item of [successor, changed.revision]) {
    assert.equal(item.eventTime, null);
    assert.equal(item.learnedTime, null);
  }
  assert.equal(successor.corrects, undefined);
  assert.equal(successor.kind, 'USER_REPORTED_EVENT');
  assert.equal(resolveBasis(c, old)[0].content, 'Entrance east');
  assert.equal(resolveBasis(c, background(state, c))[0].content, 'Entrance south');
  assert(changed.text.includes('不表示原来记错'));
  assert(changed.text.includes('尚未重新评估'));
});

test('GUESS and compatibility action create successors without changing historical classifications', () => {
  const {state, c} = setup(), original = authored(state, c, 'Registrations may decrease'), old = background(state, c);
  const before = JSON.stringify(old), guess = changeRecord(state, c.id, original.recordId, 'GUESS');
  assert.equal(guess.revision.type, 'GUESS');
  assert.notEqual(guess.recordId, original.recordId);
  assert.equal(row(c, original.recordId).kind, 'USER_REPORTED_EVENT');
  assert.equal(row(c, guess.recordId).kind, 'USER_GUESS');
  assert.equal(row(c, guess.recordId).content, row(c, original.recordId).content);
  assert.equal(JSON.stringify(old), before);
  const current = background(state, c);
  assert.equal(resolveBasis(c, old)[0].kind, 'USER_REPORTED_EVENT');
  assert.equal(resolveBasis(c, current)[0].kind, 'USER_GUESS');
  assert.equal(savedKind(current, current.basisRefs[0]), 'USER_GUESS');
  const repeated = reviseRecord(state, c.id, guess.recordId, 'GUESS');
  assert.deepEqual(row(c, repeated.recordId).provenanceRoots, [original.recordId]);
  assert.equal(selectedBackground(c).length, 1);
  assert.equal(selectedBackground(c)[0].kind, 'USER_GUESS');
  assert.equal(resolveBasis(c, current)[0].kind, 'USER_GUESS');
});

test('new basis classifications are frozen; old references lacking a snapshot stay unverified', () => {
  const {state, c} = setup(), original = authored(state, c, 'Original classification'), old = background(state, c);
  const legacy = {...old, id: 'run-legacy', basisKinds: undefined};
  row(c, original.recordId).kind = 'USER_GUESS'; // Synthetic legacy in-place mutation, not a supported action.
  assert.equal(resolveBasis(c, old)[0].kind, 'USER_REPORTED_EVENT');
  assert.equal(resolveBasis(c, old)[0].classificationStatus, 'RECORDED');
  assert.equal(resolveBasis(c, legacy)[0].kind, undefined);
  assert.equal(resolveBasis(c, legacy)[0].classificationStatus, 'historical-kind-unverified');
  const versionMismatch = {...old, basisRefs: [{recordId: original.recordId, version: 999}]};
  assert.equal(resolveBasis(c, versionMismatch)[0].status, 'UNAVAILABLE');
  assert.equal(resolveBasis(c, versionMismatch)[0].classificationStatus, 'UNAVAILABLE');
  const other = createConversation(state);
  assert.equal(resolveBasis(other, old)[0].content, undefined);
});

test('HYPOTHETICAL_BRANCH separates its record/snapshot and never writes actual background', () => {
  const {state, c} = setup(), original = authored(state, c, 'Actual blue paper'), old = background(state, c);
  const actual = JSON.stringify(c.records), historical = JSON.stringify(old);
  const hypothetical = reviseRecord(state, c.id, original.recordId, 'HYPOTHETICAL_BRANCH', 'Hypothetical white paper');
  assert.equal(JSON.stringify(c.records), actual);
  assert.equal(JSON.stringify(old), historical);
  assert.equal(c.branches.length, 1);
  const branch = c.branches[0];
  assert.equal(branch.id, hypothetical.branchId);
  assert.equal(branch.id, hypothetical.revision.branchId);
  assert.equal(branch.record.kind, 'HYPOTHETICAL');
  assert.equal(branch.record.id, hypothetical.recordId);
  assert.equal(branch.record.branchId, branch.id);
  assert.equal(branch.actualWriteback, false);
  assert.deepEqual(branch.snapshotRefs, [{recordId: original.recordId, version: 1, kind: 'USER_REPORTED_EVENT'}]);
  assert.deepEqual(hypothetical.revision.notReevaluatedRunIds, []);
  const next = background(state, c);
  assert(next.text.includes('Actual blue paper'));
  assert(!next.text.includes('Hypothetical white paper'));
  assert.equal(next.basisRefs[0].recordId, original.recordId);
  assert.throws(() => reviseRecord(state, c.id, branch.record.id, 'CORRECT', 'Do not promote a branch'));
});

test('repeated hypothesis submission replays its recorded run, including after reload', () => {
  const {state, c} = setup(), s = store(), original = authored(state, c, 'Actual blue paper');
  const first = reviseRecord(state, c.id, original.recordId, 'HYPOTHETICAL_BRANCH', 'White paper');
  const before = JSON.stringify(state);
  assert.equal(reviseRecord(state, c.id, original.recordId, 'HYPOTHETICAL_BRANCH', 'White paper'), first);
  assert.equal(JSON.stringify(state), before);
  saveState(state, s);
  const reloaded = loadState(s), conv = reloaded.conversations[0];
  assert.equal(reviseRecord(reloaded, conv.id, original.recordId, 'HYPOTHETICAL_BRANCH', 'White paper').id, first.id);
  assert.equal(conv.branches.length, 1);
  assert.equal(conv.runs.length, 2);
  assert.equal(selectedBackground(conv)[0].content, 'Actual blue paper');
});

for (const intent of ['CORRECT', 'SUPERSEDE', 'GUESS', 'HYPOTHETICAL_BRANCH']) {
  test(`${intent} refuses ambiguous, unknown, cross-scope, stopped and deleted targets atomically`, () => {
    const {state, c} = setup();
    const first = authored(state, c, 'Duplicate authored text'), second = authored(state, c, 'Duplicate authored text');
    const other = createConversation(state), cross = authored(state, other, 'Other conversation');
    const stopped = authored(state, c, 'STOPPED_TARGET'), deleted = authored(state, c, 'DELETED_TARGET');
    changeRecord(state, c.id, stopped.recordId, 'STOPPED');
    changeRecord(state, c.id, deleted.recordId, 'DELETED');
    const unresolved = submit(state, c.id, 'ordinary unsupported input');
    for (const id of [undefined, '', 'Duplicate authored text', [first.recordId, second.recordId], 'record-unknown', cross.recordId, stopped.recordId, deleted.recordId, unresolved.recordId]) {
      const before = JSON.stringify(state);
      assert.throws(() => reviseRecord(state, c.id, id, intent, 'New authored content'));
      assert.equal(JSON.stringify(state), before);
    }
    c.records.push({...row(c, first.recordId)}); // Ambiguous/corrupt identity must not choose the first.
    const before = JSON.stringify(state);
    assert.throws(() => reviseRecord(state, c.id, first.recordId, intent, 'Ambiguous ID'));
    assert.equal(JSON.stringify(state), before);
  });
}

test('unsupported intents, empty contents and missing conversations do not partly mutate state', () => {
  const {state, c} = setup(), original = authored(state, c, 'No partial write');
  const before = JSON.stringify(state);
  for (const [conversationId, intent, content] of [
    ['conv-missing', 'CORRECT', 'new'], [c.id, 'UNRECOGNIZED', 'new'],
    [c.id, 'CORRECT', undefined], [c.id, 'SUPERSEDE', '   '], [c.id, 'GUESS', ''], [c.id, 'HYPOTHETICAL_BRANCH', null],
  ]) {
    assert.throws(() => reviseRecord(state, conversationId, original.recordId, intent, content));
    assert.equal(JSON.stringify(state), before);
  }
});

test('duplicate successor submission cannot apply twice or revive a superseded target', () => {
  const {state, c} = setup(), original = authored(state, c, 'First version');
  const changed = reviseRecord(state, c.id, original.recordId, 'CORRECT', 'Second version');
  const before = JSON.stringify(state);
  assert.throws(() => reviseRecord(state, c.id, original.recordId, 'CORRECT', 'Second version'));
  assert.equal(JSON.stringify(state), before);
  assert.equal(c.runs.find(run => run.id === changed.id), changed); // Lost acknowledgment can recover the recorded run.
  assert.equal(selectedBackground(c).length, 1);
});

test('unrelated authored records and direct math never manufacture revision/impact receipts', () => {
  const {state, c} = setup();
  authored(state, c, 'Lantern materials'); background(state, c);
  for (const run of [authored(state, c, 'Unrelated tea time'), submit(state, c.id, '2+2')]) {
    assert.equal(run.revision, undefined);
    assert.equal(run.change, '');
    assert.deepEqual(run.basisRefs, []);
    assert.deepEqual(run.caps, []);
  }
});

test('delete an origin purges descendant revisions, hypotheses, raw/generated/export/reload copies', () => {
  const {state, c} = setup(), s = store();
  const first = authored(state, c, 'P1_DELETE_FERN'); background(state, c);
  const independent = authored(state, c, 'P1_INDEPENDENT_KEEP');
  const corrected = reviseRecord(state, c.id, first.recordId, 'CORRECT', 'P1_CORRECTED_FERN');
  const guess = reviseRecord(state, c.id, corrected.recordId, 'GUESS');
  reviseRecord(state, c.id, guess.recordId, 'HYPOTHETICAL_BRANCH', 'P1_HYPOTHETICAL_FERN');
  const latest = reviseRecord(state, c.id, guess.recordId, 'SUPERSEDE', 'P1_SUPERSEDED_FERN'); background(state, c);
  // Synthetic older-format origin-dependent copy, whose generating run is absent.
  c.records.push({id: 'record-origin-copy', content: 'P1_DELETE_FERN', kind: 'CORRECTION', status: 'ACTIVE', version: c.version, originRecordId: first.recordId});
  changeRecord(state, c.id, first.recordId, 'DELETED');
  saveState(state, s);
  for (const bytes of [JSON.stringify(state), JSON.stringify(exportConversation(c)), s.bytes(), JSON.stringify(loadState(s))]) {
    for (const canary of ['P1_DELETE_FERN', 'P1_CORRECTED_FERN', 'P1_HYPOTHETICAL_FERN', 'P1_SUPERSEDED_FERN']) assert(!bytes.includes(canary));
    assert(bytes.includes('P1_INDEPENDENT_KEEP'));
  }
  assert.equal(c.branches.length, 0);
  assert.equal(row(c, latest.recordId).status, 'DELETED');
  assert.deepEqual(Object.keys(row(c, latest.recordId)).sort(), ['id', 'kind', 'status', 'version']);
  assert.equal(selectedBackground(c)[0].id, independent.recordId);
  assert.equal(resolveBasis(c, latest)[0].classificationStatus, 'UNAVAILABLE');
});

test('deleting a successor preserves historical predecessors and truly independent equal-text sources', () => {
  const {state, c} = setup();
  const original = authored(state, c, 'Historical unchanged root');
  const corrected = reviseRecord(state, c.id, original.recordId, 'CORRECT', 'Independent equal content');
  const independent = authored(state, c, 'Independent equal content');
  changeRecord(state, c.id, corrected.recordId, 'DELETED');
  assert.equal(row(c, original.recordId).content, 'Historical unchanged root');
  assert.equal(row(c, original.recordId).status, 'SUPERSEDED');
  assert.equal(row(c, independent.recordId).content, 'Independent equal content');
  assert.equal(row(c, independent.recordId).status, 'ACTIVE');
  assert.equal(selectedBackground(c).length, 1);
  assert.equal(selectedBackground(c)[0].id, independent.recordId);
  assert.throws(() => reviseRecord(state, c.id, original.recordId, 'GUESS'));
});

test('stop propagates to descendants without deleting history or reviving any ancestor', () => {
  const {state, c} = setup(), original = authored(state, c, 'STOP_ORIGIN_CANARY');
  const guess = reviseRecord(state, c.id, original.recordId, 'GUESS'), old = background(state, c);
  const branch = reviseRecord(state, c.id, guess.recordId, 'HYPOTHETICAL_BRANCH', 'STOP_HYPOTHESIS_CANARY');
  changeRecord(state, c.id, original.recordId, 'STOPPED');
  assert.equal(row(c, guess.recordId).status, 'STOPPED');
  assert.equal(c.branches[0].record.status, 'STOPPED');
  assert.equal(selectedBackground(c).length, 0);
  assert.equal(resolveBasis(c, old)[0].status, 'STOPPED');
  assert.equal(resolveBasis(c, old)[0].kind, 'USER_GUESS');
  assert.equal(resolveBasis(c, branch)[0].content, 'STOP_ORIGIN_CANARY');
  assert.throws(() => changeRecord(state, c.id, guess.recordId, 'GUESS'));
  const next = background(state, c);
  assert(!next.text.includes('STOP_ORIGIN_CANARY'));
  assert(!next.text.includes('STOP_HYPOTHESIS_CANARY'));
});

test('branch deletion and stop never change actual origin or other branches', () => {
  const {state, c} = setup(), original = authored(state, c, 'Actual preserved');
  const branch = reviseRecord(state, c.id, original.recordId, 'HYPOTHETICAL_BRANCH', 'P1_DELETE_ONLY_BRANCH');
  const other = reviseRecord(state, c.id, original.recordId, 'HYPOTHETICAL_BRANCH', 'P1_OTHER_BRANCH');
  changeRecord(state, c.id, branch.recordId, 'DELETED');
  assert(!JSON.stringify(c).includes('P1_DELETE_ONLY_BRANCH'));
  assert.equal(c.branches.length, 1);
  assert.equal(c.branches[0].id, other.branchId);
  changeRecord(state, c.id, other.recordId, 'STOPPED');
  assert.equal(c.branches[0].record.status, 'STOPPED');
  assert.equal(row(c, original.recordId).status, 'ACTIVE');
  assert.equal(selectedBackground(c)[0].content, 'Actual preserved');
});

test('persistence keeps historical/new classifications and branch separation; stale saves cannot resurrect revisions', () => {
  const {state, c} = setup(), s = store(), original = authored(state, c, 'P1_RELOAD_CANARY'), old = background(state, c);
  const guess = reviseRecord(state, c.id, original.recordId, 'GUESS'), guessed = background(state, c);
  reviseRecord(state, c.id, guess.recordId, 'HYPOTHETICAL_BRANCH', 'P1_RELOAD_BRANCH');
  saveState(state, s);
  const reloaded = loadState(s), conv = reloaded.conversations[0], stale = loadState(s);
  assert.equal(resolveBasis(conv, conv.runs.find(run => run.id === old.id))[0].kind, 'USER_REPORTED_EVENT');
  assert.equal(resolveBasis(conv, conv.runs.find(run => run.id === guessed.id))[0].kind, 'USER_GUESS');
  assert.equal(selectedBackground(conv)[0].content, 'P1_RELOAD_CANARY');
  assert(!background(reloaded, conv).text.includes('P1_RELOAD_BRANCH'));
  changeRecord(reloaded, conv.id, original.recordId, 'DELETED'); saveState(reloaded, s);
  assert.throws(() => saveState(stale, s), /其他页面/);
  assert(!s.bytes().includes('P1_RELOAD_CANARY'));
  assert(!s.bytes().includes('P1_RELOAD_BRANCH'));
});

test('temporary revision and branch bodies never enter persistent storage', () => {
  const {state, c} = setup('TEMPORARY'), s = store(), original = authored(state, c, 'P1_TEMP_LANTERN');
  const guess = reviseRecord(state, c.id, original.recordId, 'GUESS');
  reviseRecord(state, c.id, guess.recordId, 'HYPOTHETICAL_BRANCH', 'P1_TEMP_BRANCH');
  saveState(state, s);
  assert(!s.bytes().includes('P1_TEMP_LANTERN'));
  assert(!s.bytes().includes('P1_TEMP_BRANCH'));
  assert.equal(loadState(s).conversations.length, 0);
});
