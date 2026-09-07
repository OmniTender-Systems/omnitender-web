"""
OmniTender MCP Bid Scraper - Domain Models & Standardized JSON Schema.
Defines schemas for North Carolina municipal solicitations, RFPs, attached docs,
portal configurations, search filters, and proposal responses.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class BidStatus(str, Enum):
    OPEN = "OPEN"
    CLOSING_SOON = "CLOSING_SOON"
    CLOSED = "CLOSED"
    AWARDED = "AWARDED"
    UNDER_REVIEW = "UNDER_REVIEW"
    CANCELLED = "CANCELLED"


class TradeCategory(str, Enum):
    HVAC = "hvac"
    ELECTRICAL = "electrical"
    PLUMBING = "plumbing"
    ROOFING = "roofing"
    GENERAL_CONSTRUCTION = "general_construction"
    PAVING_ROADWORK = "paving_roadwork"
    WATER_SEWER = "water_sewer"
    FIRE_SAFETY = "fire_safety"
    IT_TELECOM = "it_telecom"
    LANDSCAPING = "landscaping"
    OTHER = "other"


class RFPDocument(BaseModel):
    doc_id: str
    name: str
    url: str
    doc_type: str = "specifications"  # specifications, drawings, addendum, bid_form, qa_notice
    size_bytes: Optional[int] = None
    content_snippet: Optional[str] = None


class MunicipalPortal(BaseModel):
    portal_id: str
    name: str
    jurisdiction: str
    county: str
    base_url: str
    portal_type: str = "municipal_html"
    active: bool = True
    last_scraped_at: Optional[str] = None
    total_bids_found: int = 0
    notes: Optional[str] = None


class TenderItem(BaseModel):
    """
    Standardized schema for municipal and county RFPs across North Carolina.
    Matches OmniTender contractor requirements and MCP tool responses.
    """
    id: str = Field(..., description="Unique canonical solicitation ID (e.g. NC-BURKE-2026-001)")
    portal_id: str = Field(..., description="Source portal identifier")
    jurisdiction: str = Field(..., description="County / Municipality (e.g. Burke County, NC)")
    county: str = Field(..., description="NC County name (e.g. Burke)")
    rfp_number: str = Field(..., description="Official solicitation number")
    title: str = Field(..., description="Project / RFP Title")
    description: str = Field(..., description="Full project scope summary")
    category: str = Field(..., description="High-level trade or category description")
    trade: TradeCategory = Field(default=TradeCategory.OTHER, description="Normalized trade category")
    issuing_agency: str = Field(..., description="Issuing municipal department or division")
    estimated_budget: Optional[float] = Field(default=None, description="Estimated budget in USD if published")
    budget_currency: str = Field(default="USD", description="Currency ISO code")
    posted_date: Optional[str] = Field(default=None, description="ISO8601 publication date")
    closing_date: Optional[str] = Field(default=None, description="ISO8601 submission deadline")
    status: BidStatus = Field(default=BidStatus.OPEN, description="Current bidding status")
    source_url: str = Field(..., description="Direct URL to portal solicitation page")
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    documents: List[RFPDocument] = Field(default_factory=list, description="Attached specifications & PDFs")
    requirements: List[str] = Field(default_factory=list, description="Mandatory licensing, insurance, or bonds")
    pre_bid_meeting: Optional[str] = Field(default=None, description="Pre-bid conference date & location details")
    scraped_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    raw_payload: Optional[Dict[str, Any]] = None


class TenderSearchFilter(BaseModel):
    query: Optional[str] = None
    county: Optional[str] = None
    trade: Optional[str] = None
    min_budget: Optional[float] = None
    max_budget: Optional[float] = None
    status: Optional[str] = "OPEN"
    limit: int = Field(default=20, ge=1, le=100)
    offset: int = Field(default=0, ge=0)


class TenderSearchResponse(BaseModel):
    total: int
    count: int
    limit: int
    offset: int
    results: List[TenderItem]


class ProposalGenerationRequest(BaseModel):
    tender_id: str
    contractor_name: str
    license_num: str
    trade: Optional[str] = None
    base_estimate: float


class ProposalGenerationResponse(BaseModel):
    tender_id: str
    tender_title: str
    county: str
    contractor_name: str
    license_num: str
    total_bid: float
    proposal_markdown: str
    generated_at: str
