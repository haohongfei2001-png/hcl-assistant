# Product modules

- `store`: SQLite ledger, volatile registry and scope/version-bound cursors.
- `context`: authored versioned context/revision and conservative support/read/absence closure.
- `policy`: current-policy retrieval, expiry, stop/delete and simulated restore tombstones.
- `controller`: sole interaction entry, snapshot/run/stream lifecycle and read-only Lab.
- `adapter`: server-permitted mock only, no provider transport.
- `mock_runtime`: explicitly limited authored prefix grammar, no general semantic extraction.
- `synthesis`: natural projections bound to persisted claims; no private psychological facts added.
- `explain`: frozen run/answer/snapshot projection, no new model call.

These are Python modules in one process, not new microservices or a research-runtime replica. Contracts remain in the canonical contracts directory. L3 is gated.
