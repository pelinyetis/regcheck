"""Tiny MCP client (stdio or streamable HTTP). Usage:
  mcpcall.py <server> list [filter]
  mcpcall.py <server> schema <tool>
  mcpcall.py <server> call <tool> '<json args>'
  mcpcall.py <server> call <tool> key=value ["key=value with spaces" ...]   (PowerShell-safe)
<server> is "mevzuat" / "yargi" (local stdio) or an https://…/mcp URL.
For URLs the bearer token is read from env MCP_BEARER_TOKEN, else from secrets/mcp_token.txt.
"""
import asyncio, json, os, sys
from contextlib import asynccontextmanager
from pathlib import Path
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamablehttp_client
sys.stdout.reconfigure(encoding="utf-8")


def parse_args(items):
    """Tool arguments as one JSON object ('{"a":1}') or as key=value pairs.
    key=value is shell-proof on Windows PowerShell 5.1, where quoted JSON gets mangled.
    Values are sent as strings; the server's pydantic validation coerces "25" -> 25 and
    "false" -> False where the tool expects int/bool (but never int -> str, hence strings)."""
    if not items:
        return {}
    if len(items) == 1 and items[0].lstrip().startswith("{"):
        return json.loads(items[0])
    out = {}
    for it in items:
        k, sep, v = it.partition("=")
        if not sep:
            raise SystemExit(f"bad argument {it!r}: use key=value or a single JSON object")
        out[k] = v
    return out


def _token():
    t = os.environ.get("MCP_BEARER_TOKEN")
    if not t:
        f = Path(__file__).resolve().parent.parent / "secrets" / "mcp_token.txt"
        t = f.read_text(encoding="utf-8").strip() if f.exists() else ""
    return t


@asynccontextmanager
async def connect(name):
    if name.startswith("http"):
        async with streamablehttp_client(name, headers={"Authorization": f"Bearer {_token()}"}, timeout=60) as (r, w, _):
            yield r, w
    else:
        cmd, args = SERVERS[name]
        # The SDK only forwards a small safe set of env vars to stdio servers; add the ones we need.
        from mcp.client.stdio import get_default_environment
        env = get_default_environment()
        env.update({k: os.environ[k] for k in ("PYTHONUTF8",) if os.environ.get(k)})
        params = StdioServerParameters(command=cmd, args=args, env=env)
        async with stdio_client(params, errlog=open("server_stderr.log", "a", encoding="utf-8")) as (r, w):
            yield r, w

SERVERS = {
    "mevzuat": ["uvx", ["mevzuat-mcp@0.3.0"]],
    "yargi": ["uvx", ["--with", "mcp<2", "yargi-mcp@0.2.2"]],
    # UiPath Coded MCP (minimal) server, run from its own project venv
    "coded-min": [str(Path(__file__).resolve().parent.parent / "coded_mcp" / "regcheck-mcp-min" / ".venv" / "Scripts" / "python.exe"),
                  [str(Path(__file__).resolve().parent.parent / "coded_mcp" / "regcheck-mcp-min" / "server.py")]],
}

async def main():
    name, action = sys.argv[1], sys.argv[2]
    async with connect(name) as (r, w):
        async with ClientSession(r, w) as s:
            await s.initialize()
            if action == "list":
                flt = sys.argv[3].lower() if len(sys.argv) > 3 else ""
                tools = (await s.list_tools()).tools
                print(f"{len(tools)} tools")
                for t in tools:
                    if flt in t.name.lower():
                        print(f"- {t.name}: {(t.description or '').strip().splitlines()[0][:140]}")
            elif action == "schema":
                for t in (await s.list_tools()).tools:
                    if t.name == sys.argv[3]:
                        print((t.description or "")[:1500]); print(json.dumps(t.inputSchema, ensure_ascii=False, indent=1)[:4000])
            elif action == "call":
                res = await s.call_tool(sys.argv[3], parse_args(sys.argv[4:]))
                print("isError:", res.isError)
                for c in res.content:
                    print(getattr(c, "text", c))
                if getattr(res, "structuredContent", None) and not res.content:
                    print(json.dumps(res.structuredContent, ensure_ascii=False)[:8000])

if __name__ == "__main__":
    asyncio.run(main())
