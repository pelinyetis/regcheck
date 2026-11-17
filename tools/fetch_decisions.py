"""Fetch the full text of KVKK decisions through our Coded MCP server (get_kvkk_document_markdown),
all pages, in one MCP session. Used to verify the curated decision list in agent/system_prompt.md.

Usage: uv run --no-project --python 3.12 --with "mcp<2" python -I fetch_decisions.py <candidates.json> <out_dir> [server, default coded-min]
candidates.json = {"2021-85": "https://www.kvkk.gov.tr/Icerik/7112/2021-85", ...}
"""
import asyncio
import json
import sys
from pathlib import Path

from mcp import ClientSession

sys.path.insert(0, str(Path(__file__).resolve().parent))   # python -I drops the script dir
from mcpcall import connect  # noqa: E402

sys.stdout.reconfigure(encoding="utf-8")


async def main(cands: dict, out: Path, server: str = "coded-min"):
    out.mkdir(parents=True, exist_ok=True)
    index = {}
    async with connect(server) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            for did, url in cands.items():
                chunks, page, meta = [], 1, {}
                while True:
                    res = await s.call_tool("get_kvkk_document_markdown", {"decision_url": url, "page_number": page})
                    d = json.loads(res.content[0].text)
                    if d.get("error_message"):
                        meta = {"error": d["error_message"]}
                        break
                    chunks.append(d.get("markdown_chunk") or "")
                    meta = {k: d.get(k) for k in ("title", "decision_date", "decision_number", "subject_summary", "total_pages")}
                    if page >= (d.get("total_pages") or 1):
                        break
                    page += 1
                text = "".join(chunks)
                (out / f"{did}.md").write_text(text, encoding="utf-8")
                index[did] = {"url": url, **meta, "chars": len(text)}
                print(f"{did:10} pages={meta.get('total_pages')} chars={len(text):6} {meta.get('error') or (meta.get('subject_summary') or '')[:90]}")
    (out / "index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main(json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")), Path(sys.argv[2]),
                     sys.argv[3] if len(sys.argv) > 3 else "coded-min"))
