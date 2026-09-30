# L2.5 experimental development bridge

Pin: `haohongfei2001-png/human-cognition-layer@a8229fcf22eccb851c58502a09ae7cecb346faf5`.
Bridge version / serialization / receipt: `1.0`. Interface identity: `hcl-epistemic-callables-v1` is a product-owned adapter contract over existing HCL callables, not a claimed native research version. Native version is unspecified. Exact file Git blob/SHA256, source tree, artifact and interface digests are in `contracts/runtime-bridge.lock.json`. Repin requires a reviewed lock and new bridge version; no automatic main/tag tracking.

Allowlist is exactly `hcl/cognition/core.py`, `hcl/cognition/semantic.py`, `hcl/cognition/epistemic.py`. Acquisition uses only the exact commit metadata and these three exact content endpoints. Source lives in an external disposable artifact directory; no research tree or package initializer is copied into product source. Each worker validates bytes again, constructs isolated package shells and loads only these modules. Controller/UI never import research classes. Provider backends are not created.

`belief_interpretation` and `information_access` are discovered as development-only EXPERIMENTAL, PENDING_I06, production_enabled=false. Others remain unbridged candidates, honestly unsupported. English explicit named speech/modal forms are narrow syntax coverage, not certified language coverage; Chinese, ambiguous pronouns, arbitrary prose and unrecognized input are unsupported/no treatment. The source and ordinary question must be preserved verbatim, without rewriting to force eligibility. No generated model answer, actual private belief, world truth, production retention or efficacy inference follows from a preparation result.

Run acquisition and checks as shown in README. Missing/corrupt material, wrong SHA, floating ref, interface/digest mismatch or unknown capability fail closed. No fallback to mock or newer HCL. The experimental manifest is projected separately; the existing L2 mock manifest remains unchanged.

L2.5-01 acceptance covers A23/A24 and A29 handshake policy. L2.5-02 adds actual Controller execution and A25–A29 lifecycle/receipts. L3 still needs I06 disposition, a pinned production-permitted artifact/interface, product adapter scope validation, and explicit execution/data authorization. Provider-backed paths need separate authorization and are unexecuted.
