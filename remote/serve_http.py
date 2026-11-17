"""Serve an installed FastMCP server over streamable HTTP with a bearer-token check.

Both mevzuat-mcp 0.3.0 and yargi-mcp 0.2.2 are FastMCP servers whose module
exposes a FastMCP instance called `app`, so no stdio bridge is needed: we take
FastMCP's own streamable-HTTP ASGI app and put a token check in front of it.

Usage (run inside the server's own uvx environment, see start_demo.ps1):
  uvx --from mevzuat-mcp@0.3.0 --with uvicorn python remote/serve_http.py mevzuat_mcp_server 8101
  uvx --with "mcp<2" --from yargi-mcp@0.2.2 --with uvicorn python remote/serve_http.py mcp_server_main 8102

Env:
  MCP_BEARER_TOKEN  required; clients must send `Authorization: Bearer <token>`
                    (fallback for header-less clients: append `?token=<token>` to the URL)
Endpoint: http://127.0.0.1:<port>/mcp   (GET /healthz is open, returns "ok", for tunnel checks)
"""
import hmac
import importlib
import json
import logging
import os
import sys

import uvicorn

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("serve_http")


class BearerAuth:
    """Pure ASGI middleware: rejects HTTP requests without the right bearer token."""

    def __init__(self, app, token: str):
        self.app = app
        self.expected = f"Bearer {token}".encode()
        self.token = token.encode()

    def _query_token(self, scope) -> bytes:
        # Fallback for clients that cannot set headers: ...?token=<token>
        from urllib.parse import parse_qs
        vals = parse_qs(scope.get("query_string", b"").decode()).get("token", [""])
        return vals[0].encode()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":          # lifespan etc. pass straight through
            return await self.app(scope, receive, send)
        if scope["path"] == "/healthz":
            return await self._reply(send, 200, b"ok", b"text/plain")
        got = dict(scope.get("headers") or []).get(b"authorization", b"")
        if not (hmac.compare_digest(got, self.expected) or hmac.compare_digest(self._query_token(scope), self.token)):
            client = (scope.get("client") or ["?"])[0]
            log.warning("401 %s %s from %s", scope.get("method"), scope["path"], client)
            body = json.dumps({"error": "unauthorized"}).encode()
            return await self._reply(send, 401, body, b"application/json", [(b"www-authenticate", b'Bearer realm="regcheck-mcp"')])
        return await self.app(scope, receive, send)

    @staticmethod
    async def _reply(send, status, body, ctype, extra=()):
        await send({"type": "http.response.start", "status": status,
                    "headers": [(b"content-type", ctype), (b"content-length", str(len(body)).encode()), *extra]})
        await send({"type": "http.response.body", "body": body})


def main():
    module_name, port = sys.argv[1], int(sys.argv[2])
    token = os.environ.get("MCP_BEARER_TOKEN", "")
    if len(token) < 32:
        sys.exit("MCP_BEARER_TOKEN missing or too short (need >= 32 chars)")
    mcp = importlib.import_module(module_name).app
    # json_response + stateless: plain JSON replies, no SSE streams and no sticky
    # sessions. Cloudflare quick tunnels do not support SSE.
    kwargs = dict(path="/mcp", json_response=True, stateless_http=True)
    try:   # the tunnel forwards a public Host header; allow it
        http_app = mcp.http_app(**kwargs, allowed_hosts=["*"], allowed_origins=["*"])
    except TypeError:
        http_app = mcp.http_app(**kwargs)
    log.info("serving %s (%s) on http://127.0.0.1:%d/mcp", module_name, mcp.name, port)
    uvicorn.run(BearerAuth(http_app, token), host="127.0.0.1", port=port, log_level="info", proxy_headers=True)


if __name__ == "__main__":
    main()
