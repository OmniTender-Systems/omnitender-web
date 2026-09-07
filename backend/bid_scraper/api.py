"""
OmniTender MCP Bid Scraper - FastAPI REST Router.
Exposes municipal RFP search, document extraction, portal sync status,
and NCGS-compliant proposal generation endpoints for the OmniTender Web UI.
"""

from typing import Optional, List, Dict, Any
from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from backend.bid_scraper.models import (
    TenderItem,
    RFPDocument,
    MunicipalPortal,
    TenderSearchFilter,
    TenderSearchResponse,
    ProposalGenerationRequest,
    ProposalGenerationResponse,
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

router = APIRouter(prefix="/api/bids", tags=["Municipal Bids Scraper"])


class SyncResponse(BaseModel):
    status: str
    message: str
    portals_scraped: int
    total_bids_persisted: int
    portal_breakdown: Dict[str, int]


@router.get("/search", response_model=TenderSearchResponse)
def search_municipal_bids(
    query: Optional[str] = Query(None, description="Search keyword in title, description, or RFP number"),
    county: Optional[str] = Query(None, description="NC County filter (e.g. Burke, Wake, Mecklenburg, Buncombe, Guilford)"),
    trade: Optional[str] = Query(None, description="Trade classification (hvac, electrical, plumbing, roofing, etc.)"),
    min_budget: Optional[float] = Query(None, description="Minimum estimated budget in USD"),
    max_budget: Optional[float] = Query(None, description="Maximum estimated budget in USD"),
    status: Optional[str] = Query("OPEN", description="Bid status (OPEN, CLOSED, ALL)"),
    limit: int = Query(20, ge=1, le=100, description="Page limit"),
    offset: int = Query(0, ge=0, description="Page offset"),
):
    """
    Search and filter active North Carolina municipal solicitations across 5 county portals.
    """
    filter_status = None if status and status.upper() == "ALL" else status
    filter_params = TenderSearchFilter(
        query=query,
        county=county,
        trade=trade,
        min_budget=min_budget,
        max_budget=max_budget,
        status=filter_status,
        limit=limit,
        offset=offset,
    )
    results, total = search_tenders(filter_params)
    return TenderSearchResponse(
        total=total,
        count=len(results),
        limit=limit,
        offset=offset,
        results=results,
    )


@router.get("/stats")
def get_municipal_bid_stats() -> Dict[str, Any]:
    """Returns aggregated metrics for open municipal opportunities and county distributions."""
    return get_stats()


@router.get("/portals", response_model=List[MunicipalPortal])
def list_municipal_portals():
    """Lists the 5 tracked North Carolina municipal procurement portals and sync status."""
    return get_all_portals_from_db()


@router.get("/{tender_id}", response_model=TenderItem)
def get_tender_detail(tender_id: str):
    """Retrieves full solicitation detail, requirements, and attached documents for a tender ID."""
    tender = get_tender(tender_id.strip())
    if not tender:
        raise HTTPException(status_code=404, detail=f"Tender '{tender_id}' not found.")
    return tender


@router.get("/{tender_id}/documents", response_model=List[RFPDocument])
def get_tender_documents(tender_id: str):
    """Returns all attached specifications, addenda, drawings, and files for a tender."""
    tender = get_tender(tender_id.strip())
    if not tender:
        raise HTTPException(status_code=404, detail=f"Tender '{tender_id}' not found.")
    return tender.documents


@router.post("/sync", response_model=SyncResponse)
def trigger_portal_sync(
    portal_id: Optional[str] = None,
    use_playwright: bool = False,
):
    """
    Triggers an on-demand aggregation scrape of NC municipal portals.
    """
    agg = AggregatorScraper()
    if portal_id:
        items = agg.run_portal(portal_id=portal_id.strip(), use_playwright=use_playwright)
        return SyncResponse(
            status="SUCCESS",
            message=f"Synced portal '{portal_id}' successfully.",
            portals_scraped=1,
            total_bids_persisted=len(items),
            portal_breakdown={portal_id: len(items)},
        )
    else:
        summary = agg.run_all(use_playwright=use_playwright)
        return SyncResponse(
            status="SUCCESS",
            message="Aggregated all 5 North Carolina municipal portals.",
            portals_scraped=summary.get("portals_scraped", 5),
            total_bids_persisted=summary.get("total_bids_persisted", 0),
            portal_breakdown=summary.get("portal_breakdown", {}),
        )


@router.post("/proposals/generate", response_model=ProposalGenerationResponse)
def generate_proposal(request: ProposalGenerationRequest):
    """
    Generates an autonomous, NCGS-compliant formal public bid proposal package in markdown.
    """
    try:
        return generate_municipal_proposal(request)
    except ValueError as val_err:
        raise HTTPException(status_code=404, detail=str(val_err))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error drafting proposal: {str(e)}")
