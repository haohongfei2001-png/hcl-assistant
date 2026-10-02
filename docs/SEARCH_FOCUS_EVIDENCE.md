# Search-result focus commitment

A bounded correction to existing historical search, based on main `2f76a762050e29200d6fcd83088454c37466fa69`. This does not adopt any upstream runtime candidate or change the reviewed lock.

## Retained initiating failure

[Upstream run36951354687](https://github.com/haohongfei2001-png/hcl-assistant/actions/runs/36951354687) evaluated product `9f0aeb5f031da663337bf606052d1a2fc384dd4b` with candidate `5cc6abcef4df46db7f36641614aaef5f5433a1e8`. Acquisition, handshake, smoke, Python and build passed; browser validation passed75 cases and failed the existing historical-search result focus assertion in revision-loop.spec.js. Publication was skipped, provider calls/spend stayed0, and stable runtime remains `a8229fcf22eccb851c58502a09ae7cecb346faf5`. The retained artifact has logs and receipt but no trace, so it does not establish whether target absence or modal teardown caused that original failure.

Source review found that the shell focuses the target in one animation frame after asynchronous navigation resolves. The parent's requested run need not yet be committed to the DOM, and an older navigation can still finish after a newer selection. Independent review confirmed ProductDialog performs modal cleanup and normal trigger-focus restoration in layout cleanup, before surviving parent post-commit layout effects.

## Controlled browser reproduction

The first draft mounts the real AssistantShell with a browser-only synthetic parent that can resolve navigation separately from committing its target. It checks delayed target commitment, older-versus-newer search selection, and preserved ordinary dismissal plus newer input intent. The fixture makes zero application API calls and is served only through the test's intercepted HTML route; it is not a production entry. The existing end-to-end revision-loop focus assertion remains unchanged. Hosted reproduction is pending.

No live Auth/email, credential, schema, entitlement, provider call, trial clock or runtime-lock change is part of this work. Exact-head review/browser/capture evidence and exact-main gates remain required.
