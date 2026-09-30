# Original synthetic trajectories and declared coverage

All examples were authored in this product Work; no research tests or external sources were read. `tests/test_scenarios.py` fixes three trajectories and their change/invariance checks before real runtime work:

- Cooperation: late meeting disclosure, repeated attributed guess, local time correction plus unrelated arithmetic, explicit retraction; unrelated demonstration goal survives.
- Goal/role: temporary role, later attributed value self-report, new conversation in the same Topic after SQLite restart, retraction; expression never certifies private truth or permanent personality.
- Concept/value: two source-local meanings of fairness, conditional hypothetical branch, return to actual background; unrecognized Chinese/anaphora remains unresolved.

The mock accepts only authored prefixes: `报告[人物]：正文`, `猜测[人物]：正文`, `自述[人物]：正文`, `转述[人物]：正文`, `规则[人物]：正文`, `概念[人物]：正文`. `更正：唯一匹配的旧正文 => 新正文`, `撤回：唯一匹配的旧正文`, and `假设：唯一匹配的旧正文 => 条件` are scripted commands. `；2+2` demonstrates correction-before-Direct. Ambiguous/nonmatching targets do not mutate state. People IDs are scoped to Topic or conversation.

Outputs use the current eligible record content and registered claim bindings; they are not psychological gold or generalization results. Unknown temporal/receipt information remains unknown. The prefix syntax is a limited mock tool, not a requirement for the future real Assistant. No scenario number routes the answer. Explain/Lab show authored/mock status. Real semantic understanding, efficacy and arbitrary Chinese coverage remain NOT_TESTED.
