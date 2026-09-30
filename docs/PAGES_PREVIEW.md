# GitHub Pages synthetic preview

Public preview: `https://haohongfei2001-png.github.io/hcl-assistant/`.

Browser-only static React bundle using the shared AssistantShell (built by Vite): no Python API, SQLite service, SSE backend, provider transport, real HCL runtime, server authentication/persistence, research/confirmation/LongMemEval/protected data or credentials. **Use only synthetic information, never real private data.** Current behavior comes from the adopted product commit, not from a capability claim about arbitrary language.

## Bounded P0 behavior

- Temporary conversations stay in memory and disappear on refresh/reopen. Persistent conversations use this browser's localStorage. Storage does not imply general understanding
- Stop-use blocks future background selection. Delete removes the targeted body and dependent input/answer/revision copies, plus derived titles. Other independently authored sources remain; this is not a promise to erase external copies
- Writes use Web Locks and persisted revision checks; stale tabs cannot silently overwrite newer deletion/stop-use. Other tabs refresh records and dismiss cached panels. A failed save keeps original records and the draft, with an explicit error. Browsers without Web Locks cannot write this preview safely and are refused
- The v1 migration removes wrongly persisted temporary/deleted copies. Unparsed legacy records do not become reusable facts; old unsupported generated templates are explicitly marked historical/unverified
- UTF-8 TXT/Markdown up to64KiB is fully retained. Unsupported formats, invalid UTF-8, NUL binary and oversize files are refused. File registration never means complete semantic understanding; file commands cannot change memory policy

Supported demonstrations: exact `2+2`; explicit `记录：合成背景`; `演示：查看当前背景` (exact read/quoted source records); and `更正 record-ID：新内容` for a specific active record in the current conversation. Find record IDs in memory controls. Ordinary negation is not a correction; ambiguous targets prompt for precision without changing the latest record. Open questions remain unsupported rather than producing relationship/motive templates with invented historical basis.

## Evidence and limits

Original failures at main7d36a78 were reproduced and preserved in [P0 evidence](P0_01_EVIDENCE.md). That document links actual exact-SHA hosted checks for the repaired Pages and local-product surfaces separately. Neither local SQLite tests nor screenshots certify Pages storage. Failed verification iterations remain recorded.

Target interaction remains [Master1.2](../HCL_ASSISTANT_PRODUCT_MASTER_PLAN.md), [UX A2](UX_SPEC.md), [Visual System](VISUAL_SYSTEM.md). P1-01 implements the shared shell/input/reading system with the isolated browser adapter; [evidence](P1_01_EVIDENCE.md) distinguishes its checks. The later revision-loop/integrated-experience packages are not yet claimed. The sole live queue is [Development Plan](../DEVELOPMENT_PLAN.md), machine-projected in product_development.

L3/I06 gates remain unsatisfied. No provider calls, real data, general language understanding, efficacy, Judge or agent activation is authorized or claimed.
