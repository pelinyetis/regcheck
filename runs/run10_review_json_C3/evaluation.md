# Evaluation: `run10_review_json_C3`

| Doc | MCP | Overall (got / expected) | Elements | Findings matched | Escalation correct | Hard FP | Escalated FP | Dupes | Citations grounded | Quotes verbatim | Conf. rule | Wall time | Agent time | Turns | Tool calls | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| C_sinirda | ✅ | ✅ needs_human_review / needs_human_review | 5/5 | 1/1 | 1/1 | 0 | 0 | 0 | 2/2 | 2/2 | ✅ | 32s | 25s | 3 | 1 | $0.037 |

## Totals
- **Valid runs (all MCP servers connected): 1/1**
- Overall assessment correct: **1/1**
- Element checks correct: **5/5**
- Expected findings found: **1/1**
- Escalation decision correct on matched findings: **1/1**
- False positives: **0 high-confidence**, 0 escalated
- Citations grounded in this run's tool output / prompt: **2/2**
- Supporting quotes verbatim: **2/2**
- Penalty exposure correct: 1/1 · human_review flag consistent: 1/1
- Disallowed tool calls: 0 · tool errors: 0
- Total wall time: 32s · total cost: $0.037

## C_sinirda

| Element | Got | Accepted | |
|---|---|---|---|
| 10/1-a | present | present | ✅ |
| 10/1-b | present | present | ✅ |
| 10/1-c | deficient | deficient, present | ✅ |
| 10/1-ç | present | present | ✅ |
| 10/1-d | present | present | ✅ |

| Expected | Agent finding | Element | Confidence | Escalated | Expected escalate |
|---|---|---|---|---|---|
| C-1 | F1 | 10/1-c | 0.55 | True | True |

Tool calls: {'get_kvkk_document_markdown': 1}
