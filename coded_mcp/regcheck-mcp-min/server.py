"""RegCheck UiPath Coded MCP server: the 3 tools the RegCheck agent uses.

Same names and parameters as the upstream servers:
  - search_within_kanun              (vendored mevzuat-mcp 0.3.0, MIT) -> www.mevzuat.gov.tr
  - check_government_servers_health  (vendored yargi-mcp 0.2.2, MIT)   -> karararama.yargitay.gov.tr, bedesten.adalet.gov.tr
  - get_kvkk_document_markdown       (vendored yargi-mcp 0.2.2, MIT)   -> www.kvkk.gov.tr

No decision-search tool: for the demo the agent gets a curated list of Kurul decisions in its
system prompt and reads them with get_kvkk_document_markdown. (Upstream's search_kvkk_decisions
needs the paid Brave Search API, so it is not part of this package.) No API keys are needed.

Runs on mcp==1.30.0 (the version uipath-mcp 0.3.2 pins), using mcp's built-in FastMCP
like the UiPath samples. Logs go to stderr; stdout carries the MCP stdio protocol.
"""
import logging
import sys
from pathlib import Path
from typing import Annotated, Any, Dict

from bs4 import BeautifulSoup
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from pydantic import Field

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "vendor" / "mevzuat_mcp"))   # vendored modules import each other top-level
sys.path.insert(0, str(HERE / "vendor" / "yargi_mcp"))     # upstream imports kvkk_mcp_module top-level
sys.path.insert(0, str(HERE / "vendor"))

from mevzuat_client import MevzuatApiClientNew  # noqa: E402  (vendored, unmodified)
from mevzuat_models import MevzuatArticleContent  # noqa: E402
from article_search import ArticleSearchResult, format_search_results, search_articles_by_keyword  # noqa: E402
from yargi_mcp import health_check as yargi_health  # noqa: E402  (vendored excerpt)
import kvkk_tools as yargi_kvkk  # noqa: E402  (vendored excerpt; creates upstream's KvkkApiClient)

logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("regcheck-mcp-min")


class NoBrowserMevzuatClient(MevzuatApiClientNew):
    """Upstream get_content_from_html() loads the legislation iframe with Playwright +
    headless Chromium, which a UiPath serverless robot does not have (and the Playwright
    import sits outside its try block, so it would raise).

    The iframe page is server-rendered, so we fetch the same URL with upstream's own httpx
    client and then run upstream's exact parsing steps (BeautifulSoup/lxml cleanup ->
    div.mevzuat or body -> upstream _markdown_from_html). Upstream's browser-free fallbacks
    are NOT equivalent: the .doc conversion fails in markitdown 0.1.3, and the PDF text does
    not split into articles. Vendored files stay unmodified."""

    async def get_content_from_html(self, mevzuat_no: str, mevzuat_tur: int = 1, mevzuat_tertip: str = "3") -> MevzuatArticleContent:
        cache_key = f"html:{mevzuat_tur}.{mevzuat_tertip}.{mevzuat_no}" if self._cache_enabled else None
        if cache_key and self._cache:
            cached = self._cache.get(cache_key)
            if cached:
                return MevzuatArticleContent(madde_id=mevzuat_no, mevzuat_id=mevzuat_no, markdown_content=cached)
        iframe_url = (f"{self.BASE_URL}/anasayfa/MevzuatFihristDetayIframe"
                      f"?MevzuatTur={mevzuat_tur}&MevzuatNo={mevzuat_no}&MevzuatTertip={mevzuat_tertip}")
        try:
            logger.info(f"Fetching iframe (httpx, no browser): {iframe_url}")
            resp = await self._http_client.get(iframe_url)
            resp.raise_for_status()
            # --- from here on: same steps as upstream get_content_from_html ---
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script", "style", "nav", "header", "footer"]):
                tag.decompose()
            content_div = soup.find("div", class_="mevzuat") or soup.find("body")
            if content_div:
                md = self._markdown_from_html(str(content_div), cache_key=f"html_parse:{hash(str(content_div))}")
                if md:
                    logger.info(f"HTML fetch successful for {mevzuat_no}: {len(md)} chars")
                    if cache_key and self._cache:
                        self._cache.put(cache_key, md)
                    return MevzuatArticleContent(madde_id=mevzuat_no, mevzuat_id=mevzuat_no, markdown_content=md)
            return MevzuatArticleContent(madde_id=mevzuat_no, mevzuat_id=mevzuat_no, markdown_content="",
                                         error_message="Could not extract content from HTML page")
        except Exception as e:
            logger.error(f"HTML fetch failed: {e}")
            return MevzuatArticleContent(madde_id=mevzuat_no, mevzuat_id=mevzuat_no, markdown_content="",
                                         error_message=f"HTML fetch error: {e}")


mevzuat_client = NoBrowserMevzuatClient(cache_ttl=3600, enable_cache=True)   # same settings as upstream
mcp = FastMCP("RegCheck (mevzuat + yargi, 3 tools)")


@mcp.tool()
async def search_within_kanun(
    mevzuat_no: Annotated[str, Field(description="The legislation number to search within (e.g., '6362', '5237')")],
    keyword: Annotated[str, Field(description='Search query supporting advanced operators: simple keyword ("yatırımcı"), exact phrase ("mali sıkıntı"), AND/OR/NOT operators (yatırımcı AND tazmin, yatırımcı OR müşteri, yatırımcı NOT kurum). Operators must be uppercase.')],
    mevzuat_tertip: Annotated[str, Field(description="Legislation series from search results (e.g., '3', '5')")] = "5",
    case_sensitive: Annotated[bool, Field(description="Whether to match case when searching (default: False)")] = False,
    max_results: Annotated[int, Field(ge=1, le=50, description="Maximum number of matching articles to return (1-50, default: 25)")] = 25,
) -> str:
    """Search for a keyword within a specific legislation's articles with advanced query operators.

    Fetches the full law from mevzuat.gov.tr, splits it into articles (madde) and returns only the
    matching articles, sorted by relevance. Operators must be uppercase: AND, OR, NOT, "exact phrase".
    Example: mevzuat_no="6698", keyword="yöntemi AND hukuki AND sebebi" returns KVKK md. 10.
    """
    # Body mirrors upstream mevzuat_mcp_server.search_within_kanun (mevzuat-mcp 0.3.0).
    logger.info(f"Tool 'search_within_kanun' called: {mevzuat_no}, keyword: '{keyword}'")
    try:
        content_result = await mevzuat_client.get_content(mevzuat_no=mevzuat_no, mevzuat_tur=1, mevzuat_tertip=mevzuat_tertip)
        if content_result.error_message:
            return f"Error fetching legislation content: {content_result.error_message}"
        matches = search_articles_by_keyword(markdown_content=content_result.markdown_content, keyword=keyword,
                                             case_sensitive=case_sensitive, max_results=max_results)
        result = ArticleSearchResult(mevzuat_no=mevzuat_no, mevzuat_tur=1, keyword=keyword,
                                     total_matches=len(matches), matching_articles=matches)
        if len(matches) == 0:
            return f"No articles found containing '{keyword}' in Kanun {mevzuat_no}"
        return format_search_results(result)
    except Exception as e:
        logger.exception(f"Error in tool 'search_within_kanun' for {mevzuat_no}")
        return f"An unexpected error occurred: {str(e)}"


@mcp.tool(description="Use this when checking if Turkish legal database servers are online and responding.",
          annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def check_government_servers_health() -> Dict[str, Any]:
    """Check health status of Turkish government legal database servers."""
    return await yargi_health.check_government_servers_health()


# Description and annotations copied from upstream mcp_server_main.py (yargi-mcp 0.2.2).
@mcp.tool(description="Use this when retrieving full text of a KVKK data protection decision. Returns paginated Markdown with metadata.",
          annotations=ToolAnnotations(readOnlyHint=True, openWorldHint=False, idempotentHint=True))
async def get_kvkk_document_markdown(
    decision_url: Annotated[str, Field(description="KVKK decision URL from search results")],
    page_number: Annotated[int, Field(ge=1, description="Page number for paginated Markdown content (1-indexed, accepts int). Default is 1 (first 5,000 characters).")] = 1,
) -> Dict[str, Any]:
    """Get KVKK decision as paginated Markdown."""
    return await yargi_kvkk.get_kvkk_document_markdown(decision_url=decision_url, page_number=page_number)


if __name__ == "__main__":
    mcp.run()   # stdio, as declared in mcp.json
