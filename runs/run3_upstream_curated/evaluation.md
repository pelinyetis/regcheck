# Evaluation: `run3_upstream_curated`

| Doc | MCP | Overall (got / expected) | Elements | Findings matched | Escalation correct | Hard FP | Escalated FP | Dupes | Citations grounded | Quotes verbatim | Conf. rule | Wall time | Agent time | Turns | Tool calls | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_uyumlu | ❌ INVALID | ✅ compliant / compliant | 5/5 | 0/0 | 0/0 | 0 | 0 | 0 | 0/0 | 0/0 | ✅ | 54s | 19s | 2 | 0 | $0.061 |
| B_eksik | ❌ INVALID | ✅ non_compliant / non_compliant | 5/5 | 2/2 | 2/2 | 0 | 0 | 0 | 3/3 | 3/3 | ✅ | 55s | 20s | 2 | 0 | $0.045 |
| C_sinirda | ✅ | ✅ needs_human_review / needs_human_review | 5/5 | 1/1 | 1/1 | 0 | 0 | 0 | 2/2 | 2/2 | ✅ | 62s | 42s | 4 | 2 | $0.093 |

## Totals
- **Valid runs (all MCP servers connected): 1/3**
- Overall assessment correct: **3/3**
- Element checks correct: **15/15**
- Expected findings found: **3/3**
- Escalation decision correct on matched findings: **3/3**
- False positives: **0 high-confidence**, 0 escalated
- Citations grounded in this run's tool output / prompt: **5/5**
- Supporting quotes verbatim: **5/5**
- Penalty exposure correct: 3/3 · human_review flag consistent: 3/3
- Disallowed tool calls: 0 · tool errors: 0
- Total wall time: 171s · total cost: $0.200

## A_uyumlu

| Element | Got | Accepted | |
|---|---|---|---|
| 10/1-a | present | present | ✅ |
| 10/1-b | present | present | ✅ |
| 10/1-c | present | present | ✅ |
| 10/1-ç | present | present | ✅ |
| 10/1-d | present | present | ✅ |

Tool calls: {}

Issues:
- INVALID RUN: MCP servers not connected: mevzuat-mcp=failed, yargi-mcp=failed

## B_eksik

| Element | Got | Accepted | |
|---|---|---|---|
| 10/1-a | present | present | ✅ |
| 10/1-b | present | present | ✅ |
| 10/1-c | present | present | ✅ |
| 10/1-ç | deficient | missing, deficient | ✅ |
| 10/1-d | missing | missing | ✅ |

| Expected | Agent finding | Element | Confidence | Escalated | Expected escalate |
|---|---|---|---|---|---|
| B-1 | F2 | 10/1-ç | 0.9 | False | False |
| B-2 | F1 | 10/1-d | 0.95 | False | False |

Tool calls: {}

Issues:
- INVALID RUN: MCP servers not connected: mevzuat-mcp=pending, yargi-mcp=pending

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

Tool calls: {'check_government_servers_health': 1, 'get_kvkk_document_markdown': 1}
