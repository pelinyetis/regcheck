"""VENDORED EXCERPT from yargi-mcp 0.2.2 (MIT License, Copyright (c) 2025 saidsurucu; see LICENSE).

Source: PyPI sdist yargi_mcp-0.2.2.tar.gz, file mcp_server_main.py
  - get_or_create_health_check_client: original lines 1776-1785
  - check_government_servers_health:   original lines 1796-1939
Copied verbatim, except that the @app.tool(...) decorator was removed (the tool is
registered in server.py instead). The imports and the module-level client variable
below are the ones these functions use in the original module.
"""
import logging
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)

_health_check_client: Optional[httpx.AsyncClient] = None

def get_or_create_health_check_client() -> httpx.AsyncClient:
    """Get or create a reusable HTTP client for health checks."""
    global _health_check_client
    if _health_check_client is None:
        _health_check_client = httpx.AsyncClient(
            timeout=10.0,
            verify=False,
            follow_redirects=True
        )
    return _health_check_client


async def check_government_servers_health() -> Dict[str, Any]:
    """Check health status of Turkish government legal database servers."""
    logger.info("Health check tool called for government servers")
    
    health_results = {}
    
    # Check Yargıtay server
    try:
        yargitay_payload = {
            "data": {
                "aranan": "karar",
                "arananKelime": "karar", 
                "pageSize": 10,
                "pageNumber": 1
            }
        }
        
        async with httpx.AsyncClient(
            headers={
                "Accept": "*/*",
                "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
                "Connection": "keep-alive",
                "Content-Type": "application/json; charset=UTF-8",
                "Origin": "https://karararama.yargitay.gov.tr",
                "Referer": "https://karararama.yargitay.gov.tr/",
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors", 
                "Sec-Fetch-Site": "same-origin",
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
                "X-Requested-With": "XMLHttpRequest"
            },
            timeout=30.0,
            verify=False
        ) as client:
            response = await client.post(
                "https://karararama.yargitay.gov.tr/aramalist",
                json=yargitay_payload
            )
        
        if response.status_code == 200:
            response_data = response.json()
            records_total = response_data.get("data", {}).get("recordsTotal", 0)
            
            if records_total > 0:
                health_results["yargitay"] = {
                    "status": "healthy",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            else:
                health_results["yargitay"] = {
                    "status": "unhealthy", 
                    "reason": "recordsTotal is 0 or missing",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
        else:
            health_results["yargitay"] = {
                "status": "unhealthy", 
                "reason": f"HTTP {response.status_code}",
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        
    except Exception as e:
        health_results["yargitay"] = {
            "status": "unhealthy",
            "reason": f"Connection error: {str(e)}"
        }
    
    # Check Bedesten API server
    try:
        bedesten_payload = {
            "data": {
                "pageSize": 5,
                "pageNumber": 1,
                "itemTypeList": ["YARGITAYKARARI"], 
                "phrase": "karar",
                "sortFields": ["KARAR_TARIHI"],
                "sortDirection": "desc"
            },
            "applicationName": "UyapMevzuat",
            "paging": True
        }
        
        client = get_or_create_health_check_client()
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0 Health Check"
        }
        
        response = await client.post(
            "https://bedesten.adalet.gov.tr/emsal-karar/searchDocuments",
            json=bedesten_payload,
            headers=headers
        )
        
        if response.status_code == 200:
            response_data = response.json()
            logger.debug(f"Bedesten API response: {response_data}")
            if response_data and isinstance(response_data, dict):
                data_section = response_data.get("data")
                if data_section and isinstance(data_section, dict):
                    total_found = data_section.get("total", 0)
                else:
                    total_found = 0
            else:
                total_found = 0
            
            if total_found > 0:
                health_results["bedesten"] = {
                    "status": "healthy", 
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
            else:
                health_results["bedesten"] = {
                    "status": "unhealthy",
                    "reason": "total is 0 or missing in data field",
                    "response_time_ms": response.elapsed.total_seconds() * 1000
                }
        else:
            health_results["bedesten"] = {
                "status": "unhealthy",
                "reason": f"HTTP {response.status_code}",
                "response_time_ms": response.elapsed.total_seconds() * 1000
            }
        
    except Exception as e:
        health_results["bedesten"] = {
            "status": "unhealthy", 
            "reason": f"Connection error: {str(e)}"
        }
    
    # Overall health assessment
    healthy_servers = sum(1 for server in health_results.values() if server["status"] == "healthy")
    total_servers = len(health_results)
    
    overall_status = "healthy" if healthy_servers == total_servers else "degraded" if healthy_servers > 0 else "unhealthy"
    
    return {
        "overall_status": overall_status,
        "healthy_servers": healthy_servers,
        "total_servers": total_servers,
        "servers": health_results,
        "check_timestamp": f"{__import__('datetime').datetime.now().isoformat()}"
    }
