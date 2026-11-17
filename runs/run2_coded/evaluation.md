# Evaluation: `run2_coded`

| Doc | Overall (got / expected) | Elements | Findings matched | Escalation correct | Hard FP | Escalated FP | Dupes | Citations grounded | Quotes verbatim | Conf. rule | Wall time | Agent time | Turns | Tool calls | Cost |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_uyumlu | ✅ compliant / compliant | 5/5 | 0/0 | 0/0 | 0 | 0 | 0 | 0/0 | 0/0 | ✅ | 21s | 18s | 4 | 1 | $0.080 |
| B_eksik | ✅ non_compliant / non_compliant | 5/5 | 2/2 | 2/2 | 0 | 0 | 0 | 5/5 | 5/5 | ✅ | 33s | 30s | 6 | 4 | $0.094 |
| C_sinirda | ✅ needs_human_review / needs_human_review | 5/5 | 1/1 | 1/1 | 0 | 0 | 0 | 2/2 | 2/2 | ✅ | 29s | 26s | 6 | 4 | $0.089 |

## Totals
- Overall assessment correct: **3/3**
- Element checks correct: **15/15**
- Expected findings found: **3/3**
- Escalation decision correct on matched findings: **3/3**
- False positives: **0 high-confidence**, 0 escalated
- Citations grounded in this run's tool output / prompt: **7/7**
- Supporting quotes verbatim: **7/7**
- Penalty exposure correct: 3/3 · human_review flag consistent: 3/3
- Disallowed tool calls: 0 · tool errors: 0
- Total wall time: 83s · total cost: $0.263

## A_uyumlu

| Element | Got | Accepted | |
|---|---|---|---|
| 10/1-a | present | present | ✅ |
| 10/1-b | present | present | ✅ |
| 10/1-c | present | present | ✅ |
| 10/1-ç | present | present | ✅ |
| 10/1-d | present | present | ✅ |

Tool calls: {'check_government_servers_health': 1}

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
| B-1 | F2 | 10/1-ç | 0.88 | False | False |
| B-2 | F1 | 10/1-d | 0.95 | False | False |

Tool calls: {'check_government_servers_health': 1, 'search_kvkk_decisions': 2, 'get_kvkk_document_markdown': 1}

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

Tool calls: {'check_government_servers_health': 1, 'search_kvkk_decisions': 1, 'get_kvkk_document_markdown': 2}
