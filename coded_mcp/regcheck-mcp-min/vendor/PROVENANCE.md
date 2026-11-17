# Vendored third-party code

Both upstream projects are MIT-licensed (Copyright (c) 2025 saidsurucu). Their LICENSE files sit next to the code taken from them.

| Folder | Upstream release | sdist SHA-256 (verified against PyPI) | Files | Changes |
|---|---|---|---|---|
| `mevzuat_mcp/` | mevzuat-mcp **0.3.0**, PyPI `mevzuat_mcp-0.3.0.tar.gz` | matches PyPI digest (checked 2026-11-04) | `mevzuat_client.py`, `mevzuat_models.py`, `article_search.py`, `LICENSE` | **None**, byte-for-byte copies |
| `yargi_mcp/` | yargi-mcp **0.2.2**, PyPI `yargi_mcp-0.2.2.tar.gz` | matches PyPI digest (checked 2026-11-04) | `health_check.py` (excerpt of `mcp_server_main.py`, lines 1776–1785 and 1796–1939), `LICENSE` | The `@app.tool(...)` decorator was removed. A module header and the imports these two functions need were added. The function bodies are verbatim. |
| `yargi_mcp/kvkk_mcp_module/` | yargi-mcp **0.2.2** (same sdist) | same as above | `__init__.py`, `client.py`, `models.py` | `__init__.py` and `models.py`: none. **`client.py`: one 3-line patch.** Upstream lines 44–46 (the hard-coded fallback Brave API key and its log line) were replaced by a marked `[RegCheck patch]` comment and a neutral `logger.info(...)`. No key is stored anywhere in this package. Nothing else in the file changed (`diff` against the sdist shows exactly these 3 lines). The Brave-based `search_decisions()` method is still in the file but is **never exposed or called**. |
| `yargi_mcp/kvkk_tools.py` | yargi-mcp **0.2.2** (same sdist) | same as above | Excerpt of `mcp_server_main.py`: KVKK import block (lines 314–320), `kvkk_client_instance = KvkkApiClient()` (line 374), `get_kvkk_document_markdown` (lines 1989–2043) | Its `@app.tool(...)` decorator was not copied. A module header and generic imports (`logging`, `typing`, `pydantic.Field/HttpUrl`) were added. The function body is verbatim. `search_kvkk_decisions` is **intentionally not included**. |
| `yargi_mcp/__init__.py` | (ours) | n/a | one-line docstring | new file, so `yargi_mcp` is a regular package |

Tool registration happens in our `server.py`, using mcp's built-in FastMCP (mcp 1.30.0) instead of upstream's standalone `fastmcp`. Tool names, parameter names, defaults and bounds, descriptions and annotations are copied from upstream. The schemas were compared with upstream on 2026-11-04 and match.

## Package scope: 3 tools, no decision search
The package exposes `search_within_kanun`, `check_government_servers_health` and `get_kvkk_document_markdown`. Upstream `search_kvkk_decisions` is left out on purpose, because it needs the paid **Brave Search API** (`api.search.brave.com`), not kvkk.gov.tr. For the demo, the agent instead gets a **curated list of 7 Kurul decisions** in its system prompt (`agent/system_prompt.md`, section 2). It reads them with `get_kvkk_document_markdown` and may cite them only from that tool's output. Each listed decision was fetched through this package on 2026-11-04 and reviewed (full texts in `tools/out/decisions/`). Two otherwise relevant decisions, **2024/284** and **2024/540**, were excluded: upstream's converter fails on them ("Could not convert document content to Markdown").

## Behavioural difference: mevzuat fetch without a browser
This difference is made in our own `server.py`, not in the vendored files. Upstream loads the legislation iframe (`www.mevzuat.gov.tr/anasayfa/MevzuatFihristDetayIframe?...`) with **Playwright + headless Chromium**. UiPath serverless robots have no browser, so `server.py` fetches the same server-rendered URL with upstream's own httpx client and then applies upstream's exact parsing steps.
- For KVKK (6698) articles 10, 11 and 18, the tool output is **byte-identical** to upstream with Playwright (checked 2026-11-04; see `tools/out/coded_art*.txt` against `t5.txt`, `art_11.txt`, `t2.txt`).
- Upstream's own browser-free fallbacks were tested and rejected: the `.doc` conversion fails in markitdown 0.1.3, and the PDF route returns text that doesn't split into articles, so "No articles found".

`get_kvkk_document_markdown` behaves exactly as upstream. Output for 2022/1358 page 1 and 2021/85 page 3 matched upstream on 2026-11-04 (`tools/out/up_kvkk_doc*.txt` against `tools/out/coded_kvkk_doc*.txt`).

## Dependency deviation: markitdown 0.1.9 instead of 0.1.3 (package 0.0.2)
Upstream pins `markitdown[pdf]==0.1.3`. That version (and its magika 0.6.x) caps onnxruntime at 1.20.1 on Windows, the uv lock applied that version everywhere, and onnxruntime 1.20.1 has no wheel for CPython 3.14, which UiPath serverless runs. We use **markitdown 0.1.9 + magika 1.0.3 + onnxruntime 1.31.1**. Vendored code is unchanged.

Output check on 2026-11-04 (CPython 3.14.6, against the saved 0.1.3 outputs):
- `search_within_kanun` for md. 10, 11, 18: **byte-identical**.
- `get_kvkk_document_markdown`, all pages of 12 decisions (`tools/out/decisions` vs `tools/out/decisions_py314`): **10 byte-identical**. 2022/545 and 2022/137 differ **only** in that underlined passages are now wrapped in `<u>…</u>` (3 and 4 places). They are identical once the tags are removed. None of the curated decisions the demo runs cite (2021/85, 2020/404) changed.

## Inherited from upstream (kept as-is, worth knowing)
- The health check calls Yargıtay with `verify=False` (TLS verification off). The KVKK client uses `verify=True`.
- Some KVKK decision pages fail to convert (e.g. 2024/284, 2024/540). The tool then returns `error_message: "Could not convert document content to Markdown"`.
