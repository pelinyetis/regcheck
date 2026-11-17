# UiPath Coded MCP: RegCheck

This is the alternative to the tunnel setup in `../mcp_setup.md`, which stays in place unchanged as the fallback. The goal is to host the MCP servers **inside UiPath**, as a Coded MCP server on a serverless robot, instead of on this PC.

**Current stage:** `regcheck-mcp-min/` is one package with **exactly the 3 tools the RegCheck agent uses**. **No API keys** are needed. Publish it and test from UiPath's cloud whether the government sources are reachable from there.

> **No decision search (demo decision, 2026-11-04).** Upstream `search_kvkk_decisions` needs the paid Brave Search API, so it is left out. The agent instead gets a **curated list of 7 Kurul decisions** in its system prompt and reads them with `get_kvkk_document_markdown`. The trade-off: the agent can't discover decisions outside that list.

---

## 1. Compatibility check (2026-11-04)

| Package | mcp requirement | What actually resolves |
|---|---|---|
| **uipath-mcp 0.3.2** (latest, 2026-10-21) | **`mcp==1.30.0`** (exact pin; 0.3.1 also pins 1.30.0; ≤ 0.3.0 pinned 1.26.0) | mcp 1.30.0 |
| **yargi-mcp 0.2.2** | `fastmcp>=2.10.5`, no direct mcp pin. It **breaks on mcp 2.x** (`AttributeError: 'types.UnionType' object has no attribute 'model_rebuild'`), hence our `mcp<2` | with `mcp<2`: **mcp 1.30.0** + fastmcp 3.4.11 ✅ |
| **mevzuat-mcp 0.3.0** | `fastmcp>=2.12.0`, no mcp pin | unpinned: mcp 2.3.0 + fastmcp 4.1.6. With `mcp==1.30.0`: fastmcp 3.4.11, and **all 18 tools load** ✅ |

**Verdict: no conflict.** `mcp<2` (yargi) and `mcp==1.30.0` (uipath-mcp) intersect at exactly 1.30.0. One environment and one package are enough.

If a future uipath-mcp moves to mcp 2.x, yargi would conflict. The fallback then is separate packages, one per server, or patching yargi.

**Python 3.14 on serverless (found 2026-11-04, fixed in 0.0.2).** UiPath serverless runs **CPython 3.14** and installs from our `uv.lock` (`includeUvLock: true`). Version 0.0.1 failed with `onnxruntime==1.20.1 … doesn't have a … wheel for the current platform (cp314)`.
- Chain: `markitdown` → `magika` → `onnxruntime`. markitdown 0.1.3 and magika 0.6.3 both cap `onnxruntime<=1.20.1` on Windows; the universal lock applied that one version to every platform, and 1.20.1 has no cp314 wheel.
- onnxruntime can't simply be dropped: markitdown imports magika at import time, and both KVKK decision conversion and the mevzuat client use markitdown.
- Fix: `markitdown[pdf]==0.1.9` + `magika>=1.0.2,<2` → **onnxruntime 1.31.1** (cp311–cp314 wheels for Linux and Windows).
- A Python pin was **not** used: the only evidence is that our `.python-version` (3.11) was ignored. It's a dotfile and isn't packed, and UiPath's docs say nothing about honouring `requires-python`. So the package is made to work on 3.14 instead of hoping for an older interpreter.
- Verified locally with CPython 3.14.6: `uv sync --frozen` OK; all 3 tools pass checks 0–3; md. 10/11/18 byte-identical; 10 of 12 fetched decisions byte-identical, 2 differ only by `<u>…</u>` underline tags (see PROVENANCE).

**A bigger issue than versions:** mevzuat-mcp fetches law text with **Playwright + headless Chromium**, which a serverless robot doesn't have. The package replaces only that fetch with plain httpx on the same, server-rendered URL. The output for KVKK md. 10, 11 and 18 is **byte-identical** to upstream. Details are in `regcheck-mcp-min/vendor/PROVENANCE.md`.

## 2. The package: `regcheck-mcp-min/`

```
regcheck-mcp-min/
  server.py            # one MCP server (mcp's built-in FastMCP), exactly 3 tools
  mcp.json             # "regcheck-min": stdio, python server.py
  pyproject.toml       # uipath-mcp==0.3.2, mcp==1.30.0, vendored code's deps; no playwright/fastmcp
  uv.lock (packed: includeUvLock), .python-version (3.14, local only; dotfiles aren't packed)
  uipath.json          # from `uipath init`; packOptions.filesIncluded adds the 2 LICENSE files
  bindings.json        # from `uipath init`
  vendor/
    PROVENANCE.md      # sources, sha256, every change
    mevzuat_mcp/       # mevzuat-mcp 0.3.0: 3 .py files + LICENSE (byte-identical)
    yargi_mcp/         # yargi-mcp 0.2.2: LICENSE
      kvkk_mcp_module/ #   __init__.py, models.py (identical), client.py (3-line patch: hard-coded Brave key removed)
      health_check.py  #   verbatim excerpt (health tool)
      kvkk_tools.py    #   verbatim excerpt (get_kvkk_document_markdown only)
```

| Tool | Upstream | Host it reaches | Local check (2026-11-04) |
|---|---|---|---|
| `search_within_kanun` | mevzuat-mcp 0.3.0 | `www.mevzuat.gov.tr` | md. 10/11/18 byte-identical to upstream |
| `check_government_servers_health` | yargi-mcp 0.2.2 | `karararama.yargitay.gov.tr`, `bedesten.adalet.gov.tr` | healthy, 2/2 |
| `get_kvkk_document_markdown` | yargi-mcp 0.2.2 | `www.kvkk.gov.tr` | identical to upstream; all 7 curated decisions fetched OK |

`uipath pack`'s own file selector ships the server, the vendored code and both LICENSE files, and **not** `.env`.

**Not verifiable here without your login:** `uipath init` (it needs auth to write `entry-points.json`), `pack`, and `publish`.

## 3. Pack and publish: exact commands (PowerShell)

```powershell
cd "C:\Users\PelinYetiş\Desktop\RegCheck Demo\coded_mcp\regcheck-mcp-min"
$env:PYTHONUTF8 = "1"                   # avoids encoding issues with the "ş" in the user path

uv sync                                 # ensures .venv matches uv.lock
uv run uipath auth                      # browser login; pick your tenant. Writes .env (never packed)
uv run uipath init                      # now completes: writes entry-points.json (entrypoint "regcheck-min")

# check that init kept our LICENSE entries (re-add them if init overwrote packOptions):
Get-Content uipath.json | Select-String LICENSE

# optional: self-hosted smoke test. Runs on THIS PC but registers in Orchestrator.
# (needs UIPATH_FOLDER_PATH in .env, e.g. UIPATH_FOLDER_PATH=Shared). Ctrl+C to stop.
# uv run uipath run regcheck-min

uv run uipath pack                      # -> .uipath\regcheck-mcp-min.0.0.2.nupkg
uv run uipath publish --my-workspace    # publishes the latest package; auto-creates the process in My Workspace
```

To re-publish after a change, bump `version` in `pyproject.toml` (for example 0.0.2), then run `uipath pack` and `uipath publish --my-workspace` again.

## 4. What to do in Orchestrator (manual)

Use **My Workspace**, the simplest option: publishing there auto-creates the process. No environment variables or assets are needed.

1. **Orchestrator → My Workspace → MCP Servers → Add MCP Server.**
2. Set **Type: `Coded`**, **Process: `regcheck-mcp-min`**, then click **Add**.
3. The server starts as a job on a serverless robot. Watch the job status in the MCP Server side panel until it is running and the **3 tools** appear.
4. Copy the **MCP Server URL** from the MCP Servers page.
5. *(Later, for the agent)* In Agent Builder, add this MCP server and enable only `search_within_kanun` and `get_kvkk_document_markdown`. `check_government_servers_health` is for the reachability test below, not for the agent (removed from the agent prompt on 2026-11-05).

If you use a different folder instead of My Workspace, you also have to:
- create a process from the package
- assign a serverless machine to the folder
- assign a user with unattended robot permissions

## 5. The reachability test

**Option A: from this PC through UiPath.** The tool calls execute on UiPath's robot, which is exactly what we want to test. You need a UiPath Personal Access Token (PAT) with *Orchestrator API Access* scopes.

```powershell
cd "C:\Users\PelinYetiş\Desktop\RegCheck Demo\tools"
$env:MCP_BEARER_TOKEN = "<your PAT>"
$U = "<MCP Server URL from Orchestrator>"

# 0) tools visible?                      expect: "3 tools"
uv run --no-project --python 3.12 --with "mcp<2" python -I mcpcall.py $U list

# 1) yargitay + bedesten                 expect: "overall_status": "healthy"
uv run --no-project --python 3.12 --with "mcp<2" python -I mcpcall.py $U call check_government_servers_health

# 2) mevzuat.gov.tr                      expect: "=== MADDE 10 ==="
uv run --no-project --python 3.12 --with "mcp<2" python -I mcpcall.py $U call search_within_kanun mevzuat_no=6698 "keyword=yöntemi AND hukuki AND sebebi" max_results=1

# 3) kvkk.gov.tr                         expect: "decision_number": "2022/1358", "total_pages": 2, "error_message": null
uv run --no-project --python 3.12 --with "mcp<2" python -I mcpcall.py $U call get_kvkk_document_markdown decision_url=https://www.kvkk.gov.tr/Icerik/7595/2022-1358

Remove-Item Env:MCP_BEARER_TOKEN
```
Pass arguments as `key=value`, because quoted JSON gets mangled by Windows PowerShell 5.1. Checks 2 and 3 were run in exactly this form in PowerShell against the local stdio server on 2026-11-04.

**Option B: in Agent Builder.** Add the MCP server to a test agent and ask: *"Sırayla çalıştır: check_government_servers_health; 6698 sayılı Kanunda search_within_kanun ile 'yöntemi AND hukuki AND sebebi'; get_kvkk_document_markdown ile https://www.kvkk.gov.tr/Icerik/7595/2022-1358. Her birinin sonucunu kısaca raporla."*

**How to read the result:**

| Check | ✅ Pass | ❌ Fail looks like | What a fail means |
|---|---|---|---|
| 1 health | `healthy` (2/2) | `"reason": "Connection error: …"`, `HTTP 403`, `degraded` | Yargıtay/Bedesten block or can't be reached from UiPath's region (geo/IP filtering, WAF). Not used by our agent directly, but it's an early warning for other adalet.gov.tr hosts. |
| 2 mevzuat | `=== MADDE 10 ===` | `Error fetching legislation content: HTML fetch error …` | mevzuat.gov.tr is unreachable from UiPath, so the tunnel is needed for legislation. |
| 3 **kvkk.gov.tr** | `markdown_chunk` with text, `error_message: null` | `error_message: "Error retrieving KVKK document: …"` (timeout, `403`, SSL) | **kvkk.gov.tr is unreachable from UiPath. The agent can't read decisions**, so the tunnel is needed for KVKK. |
| any | — | The job never reaches Running, or fewer than 3 tools appear | A packaging or dependency problem, not reachability. Send me the job logs. |

**Decision rule:** if checks 2 and 3 pass, the agent's whole toolchain works from UiPath's cloud, and we can move on to wiring the agent to this server. If only one fails, a mixed setup is possible: Coded MCP for the reachable source, the tunnel for the other.
