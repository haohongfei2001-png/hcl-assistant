# Continuum V1 — Owner-approved design adoption

Design ID: `CONTINUUM-V1-20261001`. Product architecture remains **Canonical 1.2 / A2-Product**. This is an appearance/interaction implementation amendment, not a new product strategy.

**Repository adoption is complete at the asset/specification level once this change is on `main`.** The Owner approved these five designs. The repository's canonical boundary check intentionally rejects binary payload files, so each approved PNG is stored as a UTF-8 SVG wrapper containing the exact original PNG payload losslessly in base64. Decoding the embedded payload reproduces the approved PNG byte-for-byte; the manifest retains original byte size, SHA-256 and original Git blob identity plus the wrapper blob identity. These five wrappers are the canonical Continuum V1 visual references. This does not mean the application implements them: implementation and visual acceptance remain P1-03 work, and exact-head plus exact-main CI remain required for this adoption change.

## Approved source set

All references originate from 1448 × 1086 PNGs. Preserve the embedded original payload without crops, recompression, replacement screenshots or regenerated lookalikes. The text-only SVG container is a repository-storage adaptation only, not a visual transformation. [Asset manifest](asset-manifest.json) records original attachment identity, byte size, SHA-256, original Git blob identity and wrapper blob identity.

| ID | Required repository path | Meaning |
|---|---|---|
| UI-01 | `assets/01-home.svg` | Home / initial input; approved navigation, header, composer, surface and spacing family |
| UI-02 | `assets/02-conversation.svg` | Conversation / long-answer viewport, attached files, table, answer-level evidence layer |
| UI-03 | `assets/03-evidence-revision.svg` | Evidence list, selected excerpt, revision comparison, return to answer |
| M-01 | `assets/04-companion-orb.svg` | Floating-core / asymmetric-shell companion candidate |
| M-02 | `assets/05-companion-receiver.svg` | Input / container / signal-receiver companion candidate |

UI-02 is a static long-answer viewport. It is not evidence that a three-turn conversation or a file-reading flow has been implemented. The two companion sheets are design references, not actual animations or proof of listening/understanding.

## Adopted appearance; no further direction exploration

Retain the latest images' pale ice-blue/lavender field, translucent white surfaces, navy typography, blue-violet active controls, softly lit edges, rounded layered panels and restrained dimensional companions. Keep their header, lightweight navigation, reading surface, composer and contextual evidence arrangement. Backgrounds are plain color or quiet frosted haze only; no landscapes, architecture, furniture, objects or promotional scenery.

This supersedes the old warm-white/gray-green quiet-editor direction and the earlier purely matte/teal/seam proposal. Do not fall back to either of those looks or an unmodified component-library theme. Reusable primitives may implement behavior, but must reproduce the adopted design. Responsive reductions and truthful semantic substitutions below do not authorize a visual redesign.

## Authority and semantic corrections

Appearance: these five image references and [implementation specification](IMPLEMENTATION_SPEC.md). Product meaning: Master Plan 1.2, UX, Product Contracts, permissions and actual receipts. Verification: [visual and interaction acceptance](ACCEPTANCE.md) plus the existing acceptance matrix. Scheduling: only `control/plan.json.product_development`, mirrored in Development Plan.

The images contain illustrative copy, organization names, filenames, dates, quotes and numbers. In particular, **HCL Technologies is not this project's identity or a source proving HCL Assistant's capabilities**. Gartner/McKinsey labels and alleged white-paper excerpts must not ship as facts, citations or demo evidence. Replace them with explicitly original synthetic fixtures whose bytes, versions and locations actually exist. User-private data and research confirmation material remain prohibited.

| Image element | Required product interpretation |
|---|---|
| 工作空间 / 知识库 / 智能体 in the nav | Preserve the visual nav positions and hierarchy; map supported entries to chat/history, optional projects, background and settings. Do not add a workspace hierarchy, knowledge-base platform or agent section because it was drawn. Omit unsupported entries and record the difference. |
| 联网搜索 / 自动 model control | Not authorization or evidence of integration. Hide unsupported controls, or show a truthful non-operational capability explanation in an appropriate menu, without a fake successful action. |
| PDF / DOCX / XLSX tiles, sizes and page counts | File-tile appearance references only. Current real upload support remains that of the latest implementation/contracts (bounded UTF-8 TXT/Markdown, 64 KiB at this baseline). No new parser is authorized by an icon. |
| 已基于 3 个文件进行分析 / source counts | Display only from actual selected/read/used source records. Registered, readable, selected and used-in-answer are different states. |
| 已更新理解 / green checks / forecast numbers | Bind to actual revision and analysis receipts. Do not label pending reevaluation as completed understanding or invent efficiency gains. |
| Eye-like highlights / listening labels on companions | Preserve approved shapes/materials without adding a face, human traits, pet behavior or new claims. Decorative presence does not mean microphone access, surveillance, processing or truth. |
| Missing environment notice | Add a clearly readable prototype/mock/experimental notice required by canonical UX; do not hide it for screenshot fidelity. |

These are explicit semantic exceptions to screenshot text, not permission to change layout, color or material. Document every exception in the implementation comparison report.

## Two companions, no premature winner

`M-01` and `M-02` are both retained. `selected_companion = null`. Provide the same optional companion slot and A/B/off review states; do not hard-code a final brand choice or treat the Home image's candidate as the selected winner. The common UI and its acceptance do not wait for a unique mascot decision. A working conversation may omit the companion; disabling it must not remove status information or leave a hole in layout.

## Adoption versus implementation

This change may contain only design assets, specifications and plan metadata. It does not implement UI, change research mechanisms, repin runtime, grant provider/data/tool authority, change I02–I06, or satisfy L3 gates. Judge remains `LONG_TERM_GOAL_ONLY_NOT_IMPLEMENTED_NOT_VALIDATED_NOT_PRODUCTION_ENABLED`.

Existing P0-01 and P1-01 completion/evidence remain historical facts. P1-02 work in PR #10 is not taken over. V1 implementation is assigned to three dependent delivery slices **inside the existing pending P1-03 package**; these are not additional scheduler tasks. The checker currently fixes the four parent identities and version `1.2/A2-Product`; no checker/test/workflow is changed to manufacture compatibility. See Development Plan and the refinement work-package definition.

This adoption was reconciled against main `905ff1fbb3b2264757931e8d9ff5fdff54e7a32f`, after P1-02 merged. The five approved image payloads are stored through lossless text-only SVG wrappers; final wrapper readback and CI complete the storage verification. The change remains limited to design assets, specifications and plan metadata. Existing CI does not automatically validate future V01–V10 implementation evidence, so P1-03 must still supply the visual comparisons and playable journeys defined here.
