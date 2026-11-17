"""VENDORED EXCERPT from yargi-mcp 0.2.2 (MIT License, Copyright (c) 2025 saidsurucu; see LICENSE).

Source: PyPI sdist yargi_mcp-0.2.2.tar.gz, file mcp_server_main.py
  - KVKK import block:            original lines 314-320
  - kvkk_client_instance:         original line  374
  - get_kvkk_document_markdown:   original lines 1989-2043
Copied verbatim; the @app.tool(...) decorator above the function was not copied (the tool is
registered in server.py instead). search_kvkk_decisions (Brave Search API) is intentionally
NOT included in this package. The generic imports below are the ones this function uses in
the original module. Requires vendor/yargi_mcp on sys.path (upstream imports kvkk_mcp_module
top-level).
"""
import logging
from typing import Any, Dict

from pydantic import Field, HttpUrl

logger = logging.getLogger(__name__)

# KVKK Module Imports
from kvkk_mcp_module.client import KvkkApiClient
from kvkk_mcp_module.models import (
    KvkkSearchRequest,
    KvkkSearchResult,
    KvkkDocumentMarkdown
)

kvkk_client_instance = KvkkApiClient()


async def get_kvkk_document_markdown(
    decision_url: str = Field(..., description="KVKK decision URL from search results"),
    page_number: int = Field(1, ge=1, description="Page number for paginated Markdown content (1-indexed, accepts int). Default is 1 (first 5,000 characters).")
) -> Dict[str, Any]:
    """Get KVKK decision as paginated Markdown."""
    logger.info(f"KVKK document retrieval tool called for URL: {decision_url}")

    if not decision_url or not decision_url.strip():
        return KvkkDocumentMarkdown(
            source_url=HttpUrl("https://www.kvkk.gov.tr"),
            title=None,
            decision_date=None,
            decision_number=None,
            subject_summary=None,
            markdown_chunk=None,
            current_page=page_number or 1,
            total_pages=0,
            is_paginated=False,
            error_message="Decision URL is required and cannot be empty."
        ).model_dump()
    
    try:
        # Validate URL format
        if not decision_url.startswith("https://www.kvkk.gov.tr/"):
            return KvkkDocumentMarkdown(
                source_url=HttpUrl(decision_url),
                title=None,
                decision_date=None,
                decision_number=None,
                subject_summary=None,
                markdown_chunk=None,
                current_page=page_number or 1,
                total_pages=0,
                is_paginated=False,
                error_message="Invalid KVKK decision URL format. URL must start with https://www.kvkk.gov.tr/"
            ).model_dump()

        result = await kvkk_client_instance.get_decision_document(decision_url, page_number or 1)
        logger.info(f"KVKK document retrieved successfully. Page {result.current_page}/{result.total_pages}, Content length: {len(result.markdown_chunk) if result.markdown_chunk else 0}")
        return result.model_dump()
        
    except Exception as e:
        logger.exception(f"Error retrieving KVKK document: {e}")
        return KvkkDocumentMarkdown(
            source_url=HttpUrl(decision_url),
            title=None,
            decision_date=None,
            decision_number=None,
            subject_summary=None,
            markdown_chunk=None,
            current_page=page_number or 1,
            total_pages=0,
            is_paginated=False,
            error_message=f"Error retrieving KVKK document: {str(e)}"
        ).model_dump()
