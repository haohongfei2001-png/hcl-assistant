# L1/L2 execution ownership

Sole writer: this dedicated product Work, authorized to implement L1-01 through L2-04.
Claim branch: `product/l1-01`. No other open PR existed at initial remote-main audit.
Baseline: `79e996a26f7e9724a9aa62c7b57d2508b8b56158`, exact-main CI run 36721547291 successful; 44 local setup checks passed.

Eight coherent package checkpoints will be made in dependency order. Adjacent stable slices may share one PR, as permitted by the canonical package plan. No real provider, research runtime, private data or deployment.

Verification: Python >=3.11 standard library and SQLite; React/TypeScript browser tooling pinned by the client lockfile when L2 starts. Synthetic HTTP test identities only. Temporary test databases remain outside Git.

L1-01: SQLite ledger, atomic source/event/state version commits, tenant/topic checks, idempotency and exact source spans. `python3 scripts/check_planning.py`, `python3 scripts/check_repository.py`, `python3 -m unittest discover -s tests -v`: 49 passed. Persistence tests reopen a temporary SQLite database. Revisions are explicitly unsupported until L1-02. Raw text is unresolved, not semantically understood. Tenant version is conservative account-wide ordering, not last-write-wins.
