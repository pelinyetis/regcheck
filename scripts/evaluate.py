"""Score a run directory against expected_findings.md (its ```json expected``` block).
Usage: python scripts/evaluate.py runs/<timestamp>
Writes runs/<timestamp>/evaluation.md and prints it.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MEVZUAT_URL = "https://www.mevzuat.gov.tr/mevzuat?MevzuatNo=6698&MevzuatTur=1&MevzuatTertip=5"
PROMPT_ARTICLES = {10, 11, 18}


def norm(s: str) -> str:
    s = (s or "").replace("**", "").replace("\\n", " ")
    s = re.sub(r"[“”\"'’‘]", "", s)
    s = s.replace("…", "").replace("[...]", " ").replace("...", " ")
    return re.sub(r"\s+", " ", s).strip().lower()


def unwrap(r):
    """Current agent output: {"review_json": "<review object as JSON string>", "human_review_required", "overall_assessment"}.
    run9 used {"review": {...}}, run7 {"result": {...}}; older runs are flat."""
    if isinstance(r, dict) and isinstance(r.get("review_json"), str):
        inner = json.loads(r["review_json"])
        inner["_contract"] = {k: r.get(k) for k in ("human_review_required", "overall_assessment")}
        return inner
    for key in ("review", "result"):
        if isinstance(r, dict) and isinstance(r.get(key), dict) and "findings" in r[key]:
            return r[key]
    return r


def load_expected() -> dict:
    md = (ROOT / "expected_findings.md").read_text(encoding="utf-8")
    return json.loads(re.search(r"```json expected\n(.*?)```", md, re.S).group(1))


def evaluate_doc(doc_id: str, exp: dict, res: dict, meta: dict, prompt_text: str) -> dict:
    calls = [c for c in meta["tool_calls"] if c["name"] != "StructuredOutput"]
    corpus = "\n".join((c.get("result") or "") for c in calls)
    corpus_norm = norm(corpus)
    prompt_norm = norm(prompt_text)
    kanun_articles = set(int(n) for n in re.findall(r"=== MADDE (\d+) ===", corpus))
    allowed_tools = {"search_within_kanun", "get_kvkk_document_markdown"}   # any server prefix (upstream or coded backend)
    out = {"doc": doc_id, "issues": []}

    # 1. elements
    got = {e["element"]: e["status"] for e in res["element_checks"]}
    el_ok = {k: got.get(k) in v for k, v in exp["elements"].items()}
    out["elements_correct"] = sum(el_ok.values())
    out["elements_total"] = len(el_ok)
    out["element_detail"] = {k: (got.get(k), exp["elements"][k], el_ok[k]) for k in el_ok}

    # 2. findings matching
    findings = res["findings"]
    used = set()
    matches = []
    for ef in exp["findings"]:
        hit = next((i for i, f in enumerate(findings) if i not in used and f["element"] in ef["elements"]), None)
        if hit is not None:
            used.add(hit)
        matches.append((ef, None if hit is None else findings[hit]))
    accepted_any = {el for ef in exp["findings"] for el in ef["elements"]}
    extra = [f for i, f in enumerate(findings) if i not in used]
    duplicates = [f for f in extra if f["element"] in accepted_any]
    fps = [f for f in extra if f["element"] not in accepted_any]
    out["expected_findings"] = len(exp["findings"])
    out["matched"] = sum(1 for _, f in matches if f)
    out["duplicates"] = len(duplicates)
    out["fp_hard"] = sum(1 for f in fps if not f["escalate"])
    out["fp_escalated"] = sum(1 for f in fps if f["escalate"])
    out["escalation_correct"] = sum(1 for ef, f in matches if f and f["escalate"] == ef["escalate"])
    out["match_detail"] = [(ef["id"], f["id"] if f else None, f["element"] if f else None,
                            f["confidence"] if f else None, f["escalate"] if f else None, ef["escalate"]) for ef, f in matches]
    out["fp_detail"] = [(f["id"], f["element"], f["confidence"], f["escalate"], f["title"]) for f in fps]

    # 3. citations
    n_cit = n_grounded = n_quote = 0
    must_missing = []
    for ef, f in matches:
        if f:
            for mc in ef["must_cite"]:
                if not any(mc in c["reference"] for c in f["citations"]):
                    must_missing.append(f"{ef['id']}: {mc}")
    for f in findings:
        if not f["citations"]:
            out["issues"].append(f"{f['id']} has no citation")
        for c in f["citations"]:
            n_cit += 1
            ok = bool(c["reference"]) and c["source_url"].startswith("https://")
            if c["type"] == "kanun":
                m = re.search(r"md\.?\s*(\d+)", c["reference"])
                art = int(m.group(1)) if m else None
                ok = ok and c["source_url"] == MEVZUAT_URL and (art in PROMPT_ARTICLES or art in kanun_articles)
            else:
                num = re.search(r"\d{4}/\d+", c["reference"])
                ok = ok and c["source_url"].rstrip("/") in corpus and bool(num) and num.group(0) in corpus
            n_grounded += ok
            if not ok:
                out["issues"].append(f"{f['id']}: ungrounded citation {c['reference']} {c['source_url']}")
            q = norm(c["supporting_quote"])
            parts = [p.strip() for p in re.split(r"\s{2,}|\.\.\.|…", c["supporting_quote"]) if p.strip()]
            verbatim = bool(q) and (q in corpus_norm or q in prompt_norm or
                                    all(norm(p) in corpus_norm or norm(p) in prompt_norm for p in parts))
            n_quote += verbatim
            if not verbatim:
                out["issues"].append(f"{f['id']}: quote not verbatim in sources ({c['reference']}): {c['supporting_quote'][:90]}…")
    out["citations"] = n_cit
    out["citations_grounded"] = n_grounded
    out["quotes_verbatim"] = n_quote
    out["must_cite_missing"] = must_missing

    # 4. rules
    out["confidence_rule_violations"] = [f["id"] for f in findings if f["escalate"] != (f["confidence"] < 0.7)]
    # deterministic rule (system prompt section 5): deficient/vague/other -> escalate=true and confidence <= 0.60
    out["confidence_rule_violations"] += [f["id"] + "(issue_type)" for f in findings
                                          if f["issue_type"] != "missing" and (not f["escalate"] or f["confidence"] > 0.6)]
    if re.search(r"sunucu|erişilemez|erişilebilir|server", res["summary"] + res["penalty_exposure"]["note"]
                 + " ".join(f["description"] for f in findings), re.I):
        out["issues"].append("report mentions server/source availability")
    out["overall_ok"] = res["overall_assessment"] == exp["overall"]
    out["overall"] = (res["overall_assessment"], exp["overall"])
    out["penalty_ok"] = res["penalty_exposure"]["applicable"] == exp["penalty"]
    out["hr_ok"] = res["human_review_required"] == any(f["escalate"] for f in findings)
    if "_contract" in res:   # top-level copies (review_json contract) must match the review object
        c = res["_contract"]
        out["hr_ok"] = out["hr_ok"] and c["human_review_required"] == res["human_review_required"]
        if c["human_review_required"] != res["human_review_required"] or c["overall_assessment"] != res["overall_assessment"]:
            out["issues"].append(f"top-level fields {c} do not match review_json")
    out["disallowed_tool_calls"] = [c["name"] for c in calls
                                    if not (c["name"].startswith("mcp__") and c["name"].split("__")[-1] in allowed_tools)]
    out["tool_counts"] = {}
    for c in calls:
        k = c["name"].split("__")[-1]
        out["tool_counts"][k] = out["tool_counts"].get(k, 0) + 1
    out["tool_errors"] = sum(1 for c in calls if c.get("is_error"))
    out["time"] = (meta["duration_s"], meta["agent_duration_s"], meta["num_turns"], meta["cost_usd"])
    servers = meta.get("mcp_servers") or []
    out["mcp_ok"] = bool(servers) and all(s.get("status") == "connected" for s in servers)
    if not out["mcp_ok"]:
        out["issues"].insert(0, "INVALID RUN: MCP servers not connected: "
                             + ", ".join(f"{s.get('name')}={s.get('status')}" for s in servers))
    return out


def main(run_dir: Path):
    exp = load_expected()
    prompt_text = (ROOT / "uipath" / "agent" / "system_prompt.md").read_text(encoding="utf-8")
    rows = []
    for doc_id, e in exp.items():
        rp, mp = run_dir / f"{doc_id}.result.json", run_dir / f"{doc_id}.meta.json"
        if not rp.exists():
            print(f"!! {doc_id}: no result in {run_dir}")
            continue
        rows.append(evaluate_doc(doc_id, e, unwrap(json.loads(rp.read_text(encoding="utf-8"))),
                                 json.loads(mp.read_text(encoding="utf-8")), prompt_text))

    L = [f"# Evaluation: `{run_dir.name}`", ""]
    L += ["| Doc | MCP | Overall (got / expected) | Elements | Findings matched | Escalation correct | Hard FP | Escalated FP | Dupes | Citations grounded | Quotes verbatim | Conf. rule | Wall time | Agent time | Turns | Tool calls | Cost |",
          "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['doc']} | {'✅' if r['mcp_ok'] else '❌ INVALID'} | {'✅' if r['overall_ok'] else '❌'} {r['overall'][0]} / {r['overall'][1]} | {r['elements_correct']}/{r['elements_total']} | "
                 f"{r['matched']}/{r['expected_findings']} | {r['escalation_correct']}/{r['matched']} | {r['fp_hard']} | {r['fp_escalated']} | {r['duplicates']} | "
                 f"{r['citations_grounded']}/{r['citations']} | {r['quotes_verbatim']}/{r['citations']} | "
                 f"{'✅' if not r['confidence_rule_violations'] else '❌ ' + ','.join(r['confidence_rule_violations'])} | "
                 f"{r['time'][0]:.0f}s | {r['time'][1]:.0f}s | {r['time'][2]} | {sum(r['tool_counts'].values())} | ${r['time'][3]:.3f} |")
    tot = lambda k: sum(r[k] for r in rows)
    L += ["", "## Totals",
          f"- **Valid runs (all MCP servers connected): {sum(r['mcp_ok'] for r in rows)}/{len(rows)}**",
          f"- Overall assessment correct: **{sum(r['overall_ok'] for r in rows)}/{len(rows)}**",
          f"- Element checks correct: **{tot('elements_correct')}/{tot('elements_total')}**",
          f"- Expected findings found: **{tot('matched')}/{tot('expected_findings')}**",
          f"- Escalation decision correct on matched findings: **{tot('escalation_correct')}/{tot('matched')}**",
          f"- False positives: **{tot('fp_hard')} high-confidence**, {tot('fp_escalated')} escalated",
          f"- Citations grounded in this run's tool output / prompt: **{tot('citations_grounded')}/{tot('citations')}**",
          f"- Supporting quotes verbatim: **{tot('quotes_verbatim')}/{tot('citations')}**",
          f"- Penalty exposure correct: {sum(r['penalty_ok'] for r in rows)}/{len(rows)} · human_review flag consistent: {sum(r['hr_ok'] for r in rows)}/{len(rows)}",
          f"- Disallowed tool calls: {sum(len(r['disallowed_tool_calls']) for r in rows)} · tool errors: {tot('tool_errors')}",
          f"- Total wall time: {sum(r['time'][0] for r in rows):.0f}s · total cost: ${sum(r['time'][3] for r in rows):.3f}", ""]
    for r in rows:
        L += [f"## {r['doc']}", "", "| Element | Got | Accepted | |", "|---|---|---|---|"]
        L += [f"| {k} | {g} | {', '.join(a)} | {'✅' if ok else '❌'} |" for k, (g, a, ok) in r["element_detail"].items()]
        if r["match_detail"]:
            L += ["", "| Expected | Agent finding | Element | Confidence | Escalated | Expected escalate |", "|---|---|---|---|---|---|"]
            L += [f"| {a} | {b or '—'} | {c or '—'} | {d if d is not None else '—'} | {e} | {f} |" for a, b, c, d, e, f in r["match_detail"]]
        if r["fp_detail"]:
            L += ["", "False positives:"] + [f"- {i} `{el}` conf={c} escalated={e}: {t}" for i, el, c, e, t in r["fp_detail"]]
        L += ["", f"Tool calls: {r['tool_counts']}"]
        if r["must_cite_missing"]:
            L.append(f"Must-cite missing: {r['must_cite_missing']}")
        if r["issues"]:
            L += ["", "Issues:"] + [f"- {i}" for i in r["issues"]]
        L.append("")
    text = "\n".join(L)
    (run_dir / "evaluation.md").write_text(text, encoding="utf-8")
    print(text)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main(Path(sys.argv[1]))
