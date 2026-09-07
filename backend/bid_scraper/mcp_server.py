"""
OmniTender MCP Bid Scraper - FastMCP / MCPServer Tool Provider.
Exposes autonomous municipal bid scraping, document extraction, search,
and NCGS-compliant proposal generation tools for Daystrom fleet AI agents.
"""

import os
import json
import logging
from typing import Optional, Dict, Any, List

# MCP 2.x renamed FastMCP to MCPServer, maintain full backward/forward compatibility
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    try:
        from mcp.server.fastmcp import FastMCP as MCPServer
    except ImportError:
        MCPServer = None

from backend.bid_scraper.models import (
    TenderSearchFilter,
    ProposalGenerationRequest,
    BidStatus,
    TradeCategory,
)
from backend.bid_scraper.db import (
    search_tenders,
    get_tender,
    get_all_portals_from_db,
    get_stats,
    init_db,
)
from backend.bid_scraper.scrapers import AggregatorScraper
from backend.bid_scraper.proposal_generator import generate_municipal_proposal

logger = logging.getLogger("omnitender.mcp_bid_scraper")

# Initialize MCP Server instance
server = MCPServer(
    name="OmniTender-Municipal-Bid-Scraper",
    version="1.0.0",
    instructions=(
        "Autonomous North Carolina municipal RFP aggregation engine. "
        "Provides tools to search active solicitations across NC counties (Burke, Wake, Mecklenburg, "
        "Buncombe, Guilford), extract attached specifications and addenda, inspect buyer requirements, "
        "and generate statutory NCGS-compliant public bidding proposals."
    ),
) if MCPServer else None


def _ensure_initialized(db_path: Optional[str] = None):
    """Ensures database is initialized and seeded if empty."""
    init_db(db_path)
    # Check if tenders table is empty, if so trigger baseline sync
    results, total = search_tenders(TenderSearchFilter(limit=1), db_path=db_path)
    if total == 0:
        logger.info("Municipal bids database is empty; performing initial certified seed...")
        agg = AggregatorScraper(db_path=db_path)
        agg.run_all(use_playwright=False)


if server is not None:

    @server.tool(
        name="search_tenders",
        description=(
            "Search and filter active North Carolina municipal bids and RFPs across Burke, Wake, "
            "Mecklenburg, Buncombe, and Guilford counties. Filter by trade (hvac, electrical, plumbing, "
            "roofing, general_construction, water_sewer), county, budget range, keyword, or status."
        ),
    )
    def search_tenders_tool(
        query: Optional[str] = None,
        county: Optional[str] = None,
        trade: Optional[str] = None,
        min_budget: Optional[float] = None,
        max_budget: Optional[float] = None,
        status: str = "OPEN",
        limit: int = 20,
        offset: int = 0,
    ) -> str:
        """Searches tenders and returns structured JSON output."""
        _ensure_initialized()
        filter_params = TenderSearchFilter(
            query=query,
            county=county,
            trade=trade,
            min_budget=min_budget,
            max_budget=max_budget,
            status=status,
            limit=limit,
            offset=offset,
        )
        results, total = search_tenders(filter_params)

        payload = {
            "total_found": total,
            "returned_count": len(results),
            "limit": limit,
            "offset": offset,
            "filters_applied": {
                "query": query,
                "county": county,
                "trade": trade,
                "min_budget": min_budget,
                "max_budget": max_budget,
                "status": status,
            },
            "tenders": [
                {
                    "id": t.id,
                    "rfp_number": t.rfp_number,
                    "title": t.title,
                    "jurisdiction": t.jurisdiction,
                    "county": t.county,
                    "trade": t.trade.value if hasattr(t.trade, "value") else str(t.trade),
                    "issuing_agency": t.issuing_agency,
                    "estimated_budget": t.estimated_budget,
                    "closing_date": t.closing_date,
                    "status": t.status.value if hasattr(t.status, "value") else str(t.status),
                    "source_url": t.source_url,
                    "documents_count": len(t.documents),
                    "summary": t.description[:180] + ("..." if len(t.description) > 180 else ""),
                }
                for t in results
            ],
        }
        return json.dumps(payload, indent=2)

    @server.tool(
        name="extract_rfp_docs",
        description=(
            "Extract all attached documents, architectural drawings, specification manuals, "
            "addenda, and mandatory compliance requirements for a specific NC municipal tender."
        ),
    )
    def extract_rfp_docs_tool(tender_id: str) -> str:
        """Extracts documents and requirements for a given tender ID."""
        _ensure_initialized()
        tender = get_tender(tender_id.strip())
        if not tender:
            return json.dumps({
                "error": f"Tender with ID '{tender_id}' not found.",
                "valid_id_example": "NC-BURKE-2026-001"
            }, indent=2)

        payload = {
            "tender_id": tender.id,
            "rfp_number": tender.rfp_number,
            "title": tender.title,
            "jurisdiction": tender.jurisdiction,
            "county": tender.county,
            "issuing_agency": tender.issuing_agency,
            "pre_bid_meeting": tender.pre_bid_meeting,
            "requirements": tender.requirements,
            "documents_count": len(tender.documents),
            "documents": [
                {
                    "doc_id": doc.doc_id,
                    "name": doc.name,
                    "url": doc.url,
                    "doc_type": doc.doc_type,
                    "size_bytes": doc.size_bytes,
                    "size_kb": round(doc.size_bytes / 1024, 1) if doc.size_bytes else None,
                    "content_snippet": doc.content_snippet,
                }
                for doc in tender.documents
            ],
        }
        return json.dumps(payload, indent=2)

    @server.tool(
        name="get_tender_details",
        description=(
            "Retrieve complete solicitation details for a specific NC municipal RFP, "
            "including full project description, buyer contacts, budget, deadline, requirements, and docs."
        ),
    )
    def get_tender_details_tool(tender_id: str) -> str:
        """Returns the full tender dossier."""
        _ensure_initialized()
        tender = get_tender(tender_id.strip())
        if not tender:
            return json.dumps({"error": f"Tender '{tender_id}' not found."}, indent=2)
        return json.dumps(tender.model_dump(), indent=2)

    @server.tool(
        name="generate_bid_proposal",
        description=(
            "Generate an autonomous, statutory NCGS-compliant public bidding proposal package "
            "tailored to a specific North Carolina municipal RFP. Includes statutory citations "
            "(NCGS 143-128/129), phased technical methodology, line-item cost breakdown (GMP), "
            "and contractor qualification certifications."
        ),
    )
    def generate_bid_proposal_tool(
        tender_id: str,
        contractor_name: str,
        license_num: str,
        base_estimate: float,
        trade: Optional[str] = None,
    ) -> str:
        """Generates proposal markdown package."""
        _ensure_initialized()
        req = ProposalGenerationRequest(
            tender_id=tender_id.strip(),
            contractor_name=contractor_name.strip(),
            license_num=license_num.strip(),
            base_estimate=base_estimate,
            trade=trade.strip() if trade else None,
        )
        try:
            resp = generate_municipal_proposal(req)
            return json.dumps({
                "tender_id": resp.tender_id,
                "tender_title": resp.tender_title,
                "county": resp.county,
                "contractor_name": resp.contractor_name,
                "license_num": resp.license_num,
                "total_bid": resp.total_bid,
                "proposal_markdown": resp.proposal_markdown,
                "generated_at": resp.generated_at,
            }, indent=2)
        except Exception as err:
            return json.dumps({"error": str(err)}, indent=2)

    @server.tool(
        name="sync_portals",
        description=(
            "Execute live or snapshot aggregation across North Carolina municipal procurement portals "
            "(Burke, Wake, Mecklenburg, Buncombe, Guilford) and update the local database."
        ),
    )
    def sync_portals_tool(portal_id: Optional[str] = None, use_playwright: bool = False) -> str:
        """Triggers aggregation and returns execution summary metrics."""
        _ensure_initialized()
        agg = AggregatorScraper()
        if portal_id:
            items = agg.run_portal(portal_id=portal_id.strip(), use_playwright=use_playwright)
            return json.dumps({
                "portal_id": portal_id,
                "bids_scraped": len(items),
                "status": "success",
            }, indent=2)
        else:
            summary = agg.run_all(use_playwright=use_playwright)
            return json.dumps(summary, indent=2)

    @server.tool(
        name="list_portals",
        description="List the 5 North Carolina municipal portals tracked by the scraper with active sync status.",
    )
    def list_portals_tool() -> str:
        """Lists portals with status."""
        _ensure_initialized()
        portals = get_all_portals_from_db()
        return json.dumps([p.model_dump() for p in portals], indent=2)

    @server.tool(
        name="get_municipal_stats",
        description="Get aggregate statistics on open municipal solicitations, total contract values, county breakdown, and trade distribution.",
    )
    def get_municipal_stats_tool() -> str:
        """Returns aggregate metrics."""
        _ensure_initialized()
        stats = get_stats()
        return json.dumps(stats, indent=2)


def create_mcp_server():
    """Factory returning the configured MCPServer instance."""
    return server


if __name__ == "__main__":
    import sys
    _ensure_initialized()
    if server is not None:
        print("Starting OmniTender MCP Bid Scraper stdio server...", file=sys.stderr)
        server.run(transport="stdio")
    else:
        print("Error: MCP Server SDK not available.", file=sys.stderr)
        sys.exit(1)
