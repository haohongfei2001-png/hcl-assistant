# Upstream sync implementation evidence

Product baseline: `972234e8fdb868a51a519ba7f7c98cdb5a80583b`, exact local main = remote main at task start; no open PR/writer claim. Adopted-main CI [36767804473](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36767804473) passed. Implementation branch: `product/upstream-runtime-sync`.

## Live candidate validation

The first complete real sync run was against the implementation working-tree content digest, not a claimed committed test SHA. It observed and tested `439d9363588ed8dea96f2c795b2f4b5d6c5e1c3c` while preserving stable `a8229fcf22eccb851c58502a09ae7cecb346faf5`. Interface `hcl-epistemic-callables-v1`, candidate bridge version `1.1`. Acquisition verified the exact tree and three Git blob/SHA256 values through public endpoints; no HCL clone/tree traversal or protected material. Handshake READY; manifest discovery retained only belief_interpretation/information_access as EXPERIMENTAL, false production activation. Actual Controller smoke outcomes: NO_TREATMENT / EXECUTED / NO_TREATMENT / UNSUPPORTED. Provider calls/spend = 0/0, efficacy NOT_TESTED.

- Initial live source digest: `sha256:9cc32331ca1f301e3b8291042e40e44d11a082a1de71a6bc53a2e3a3c7826836`
- Initial live candidate product digest: `sha256:157012ae23775a585f2cde0f8365373a070cbb1d289cda3b758aba3d80c0a933`
- Candidate artifact digest: `sha256:7d07acafb4c3978bf76627e961c5986aa45faffaaf25bcd0d9eb4eb2b2fd32be`
- Manifest digest: `sha256:dc85fed349e46d492378a69c8beaf513851a5c4bfe98e1228b74e677fc4039f5`
- All eleven validation stages passed, including 137 Python tests at that checkpoint, TypeScript/Vite build and 12 headless browser journeys (15.4 seconds). Complete acquisition/manifest/handshake/smoke/test logs and receipt are available locally in `/private/tmp/hcl-assistant-upstream-live-sync`. The real publication evidence validator accepted the complete artifact before later implementation changes. No remote write or stable repin occurred.

## Final implementation acceptance

The final suite adds 16 synthetic sync orchestration/publisher/real bounded-command tests to the existing 126. It covers unchanged/new SHA; exact repository/commit/tree/blob/missing file and symlink/submodule and post-validation SHA256 tampering; interface/manifest/activation drift; failure at every required stage; stale-output removal; unchanged stable bytes; incomplete/modified receipts/source refusal; exact clean product-commit binding; concurrent main/writer and foreign-branch refusal; idempotent lock-only PR publication; dispatched CI and auto-merge protection; real token scrubbing, process timeout and error behavior. Existing runtime timeout/cancel, source/history/deletion and original browser journeys remain required. No failed assertion was removed or weakened; only initial-pin literal provenance assertions became comparisons to the current exact lock.

Final root checkers, full Python suite, stable build/browser and exact-head hosted CI are required before review handoff. Subsequent exact-commit candidate validation and hosted CI results are recorded in the implementation PR, avoiding self-referential receipt commits. Workflow failure logs and receipts are retained as artifacts for 14 days. Implementation keeps the stable lock byte-identical; the automated pin PR is emitted after this mechanism is adopted on canonical main.

Current repository settings: auto-merge disabled; main protection absent (HTTP 404). No settings change was made. Future sync PRs remain review-ready unless existing settings/protections allow safe auto-merge. The hourly schedule becomes active only after this workflow is adopted on main. A main move or unrelated writer claim defers publication.

L3 remains gated by I06 disposition, production-permitted pinned artifact/interface, product adapter scope validation, and explicit execution/data authorization. No production activation, efficacy claim or provider-backed authorization.

Final review added ancestor-directory Git mode proof before candidate content acquisition because GitHub Contents API can dereference symlinks. Only root → hcl → cognition metadata is selected; no recursive tree or other subtree/blob is read. A dedicated regression confirms symlink/submodule/missing/incorrect-tree candidates fail before any content request. This preserves the existing bridge and fetcher. The final Python suite is 142 tests. Earlier 137/141 runs remain historical checkpoints.


## Publication exit-status correction (2026-10-02)

The original publisher logs from [run36965025069](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36965025069) and [run36969313759](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36969313759) show Python raising HTTP403 while POSTing the runtime pull request. Both publish jobs nevertheless reported success. Their logged shell is `bash -e`, and the command pipes Python through a successful `tee`; without `pipefail`, the last process masks the publisher failure.

On product baseline `7233348f69e9fc8df0a8a1fc58cf5146cabf9d5f`, three new local synthetic regressions execute the actual extracted workflow command under that observed shell in a temporary directory containing only a stub publisher. The minimal environment carries no token or provider configuration, and no API publisher or candidate validation is invoked. Before the fix, stub exit7 and23 both incorrectly produce shell exit0. Successful summary output and a failing summary write are retained as positive/negative controls. Adding only `set -o pipefail` to the publish step makes all three cases pass; the complete19-test synthetic sync suite passes. The local full suite passes382 tests with59 explicit disposable-database deferrals, and both root checkers pass. Independent source review accepts this bounded correction.

This repairs job-status propagation only. The real runtime PR-creation HTTP403 remains an authorization/configuration blocker; its exact policy cause is not established by the retained traceback. Earlier settings observations above are historical and were not re-queried for this correction. No permission, token, repository setting, publisher API behavior, schedule, runtime lock, Auth/migration/email/provider/trial activation or protected research data is changed. No failed runtime PR is manually recreated and no full upstream validation is repeated for this correction. Stable pin remains `a8229fcf22eccb851c58502a09ae7cecb346faf5`; a successful candidate validation is not adoption. The sole product queue stays gated. Adoption of this workflow fix requires ordinary exact-head and exact-main CI; a future genuine publisher failure should be red rather than silently successful.
