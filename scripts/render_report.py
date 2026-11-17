"""Render an agent result JSON into the Markdown report template.
Usage: uv run --no-project --with jinja2 python scripts/render_report.py <result.json> [out.md] [meta.json]
"""
import json
import sys
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

ROOT = Path(__file__).resolve().parent.parent
LABELS = {
    "10/1-a": "Veri sorumlusunun (ve varsa temsilcisinin) kimliği",
    "10/1-b": "İşleme amaçları",
    "10/1-c": "Aktarım: alıcılar ve aktarım amacı",
    "10/1-ç": "Toplama yöntemi ve hukuki sebep",
    "10/1-d": "md. 11 kapsamındaki haklar",
}


def render(result: dict, meta: dict | None = None) -> str:
    env = Environment(loader=FileSystemLoader(ROOT / "uipath" / "agent"), trim_blocks=False, lstrip_blocks=False)
    if isinstance(result, dict) and isinstance(result.get("review_json"), str):   # current contract
        result = json.loads(result["review_json"])
    for key in ("review", "result"):   # older wrappers (run9 "review", run7 "result")
        if isinstance(result, dict) and isinstance(result.get(key), dict) and "findings" in result[key]:
            result = result[key]
    return env.get_template("report_template.md").render(r=result, meta=meta, labels=LABELS)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    result = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    meta = json.loads(Path(sys.argv[3]).read_text(encoding="utf-8")) if len(sys.argv) > 3 else None
    md = render(result, meta)
    if len(sys.argv) > 2:
        Path(sys.argv[2]).write_text(md, encoding="utf-8")
    else:
        print(md)
